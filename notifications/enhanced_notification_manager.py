#!/usr/bin/env python3
"""
Social Media Surveillance System - Enhanced Notification Manager
Main coordinator for all notification services and alert management.
"""

import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from queue import Queue, Empty

from core.config import config
from ui.notification_system import Notification, NotificationType, NotificationPriority
from .enhanced_notifications import (
    EmailNotificationService, WebhookNotificationService, AlertThresholdManager,
    EscalationPolicyEngine, AlertContext, AlertType
)

logger = logging.getLogger(__name__)

class EnhancedNotificationManager:
    """Enhanced notification manager that coordinates all notification services"""
    
    def __init__(self):
        # Initialize services
        self.email_service = EmailNotificationService()
        self.webhook_service = WebhookNotificationService()
        self.threshold_manager = AlertThresholdManager()
        self.escalation_engine = EscalationPolicyEngine()
        
        # Notification queue for async processing
        self.notification_queue = Queue()
        self.processing_thread = None
        self.running = False
        
        # Event handlers
        self.event_handlers: Dict[AlertType, List[Callable]] = {}
        
        # Statistics
        self.stats = {
            'total_notifications': 0,
            'email_sent': 0,
            'webhook_sent': 0,
            'escalations_triggered': 0,
            'alerts_suppressed': 0
        }
        
        self.start_processing()
    
    def start_processing(self):
        """Start the notification processing thread"""
        if not self.running:
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_notifications, daemon=True)
            self.processing_thread.start()
            logger.info("Enhanced notification manager started")
    
    def stop_processing(self):
        """Stop the notification processing thread"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        # Stop escalation engine
        self.escalation_engine.stop_escalation_monitor()
        logger.info("Enhanced notification manager stopped")
    
    def send_notification(self, notification: Notification, context: AlertContext = None, 
                         channels: List[str] = None) -> bool:
        """Send notification through specified channels"""
        # Add to queue for async processing
        self.notification_queue.put((notification, context, channels))
        return True
    
    def _process_notifications(self):
        """Process notifications from the queue"""
        while self.running:
            try:
                # Get notification from queue (with timeout)
                try:
                    notification, context, channels = self.notification_queue.get(timeout=1)
                except Empty:
                    continue
                
                self._handle_notification(notification, context, channels)
                self.notification_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
    
    def _handle_notification(self, notification: Notification, context: AlertContext = None, 
                           channels: List[str] = None):
        """Handle a single notification"""
        try:
            self.stats['total_notifications'] += 1
            
            # Check if notification should be suppressed
            if context and self.threshold_manager.should_suppress_alert(
                context.alert_type, context.target_username):
                self.stats['alerts_suppressed'] += 1
                logger.info(f"Notification suppressed due to frequency limits: {notification.title}")
                return
            
            # Check Do Not Disturb
            if self._is_dnd_active(notification):
                logger.info(f"Notification suppressed due to DND: {notification.title}")
                return
            
            # Determine channels to use
            if channels is None:
                channels = config.get_notification_channels()
            
            # Send through each enabled channel
            success_count = 0
            
            if 'email' in channels and config.is_notification_channel_enabled('email'):
                if self.email_service.send_notification(notification, context):
                    self.stats['email_sent'] += 1
                    success_count += 1
            
            if 'webhook' in channels and config.is_notification_channel_enabled('webhook'):
                if self.webhook_service.send_notification(notification, context):
                    self.stats['webhook_sent'] += 1
                    success_count += 1
            
            # Register for escalation if needed
            if context and success_count > 0:
                self.escalation_engine.register_notification(notification, context)
            
            # Trigger event handlers
            if context and context.alert_type in self.event_handlers:
                for handler in self.event_handlers[context.alert_type]:
                    try:
                        handler(notification, context)
                    except Exception as e:
                        logger.error(f"Error in event handler: {e}")
            
            logger.info(f"Notification processed: {notification.title} (channels: {success_count})")
            
        except Exception as e:
            logger.error(f"Error handling notification: {e}")
    
    def _is_dnd_active(self, notification: Notification) -> bool:
        """Check if Do Not Disturb should suppress this notification"""
        if not config.is_dnd_active():
            return False
        
        # Allow critical notifications during DND if configured
        if (config.notification.dnd_override_critical and 
            notification.priority == NotificationPriority.CRITICAL):
            return False
        
        return True
    
    # Alert generation methods
    def alert_scraping_complete(self, target_username: str, scraper_type: str, 
                               items_scraped: int, duration_seconds: float):
        """Generate scraping completion alert"""
        notification = Notification(
            title=f"Scraping Complete: {target_username}",
            message=f"Successfully scraped {items_scraped} items from {target_username} "
                   f"using {scraper_type} in {duration_seconds:.1f} seconds",
            notification_type=NotificationType.SUCCESS,
            priority=NotificationPriority.MEDIUM
        )
        
        context = AlertContext(
            alert_type=AlertType.SCRAPING_COMPLETE,
            target_username=target_username,
            scraper_type=scraper_type,
            metrics={
                'items_scraped': items_scraped,
                'duration_seconds': duration_seconds,
                'items_per_second': items_scraped / duration_seconds if duration_seconds > 0 else 0
            }
        )
        
        self.send_notification(notification, context)
    
    def alert_scraping_error(self, target_username: str, scraper_type: str, 
                           error_message: str, error_details: Dict[str, Any] = None):
        """Generate scraping error alert"""
        notification = Notification(
            title=f"Scraping Error: {target_username}",
            message=f"Error occurred while scraping {target_username} with {scraper_type}: {error_message}",
            notification_type=NotificationType.ERROR,
            priority=NotificationPriority.HIGH
        )
        
        context = AlertContext(
            alert_type=AlertType.SCRAPING_ERROR,
            target_username=target_username,
            scraper_type=scraper_type,
            error_details=error_details or {'message': error_message}
        )
        
        self.send_notification(notification, context)
    
    def alert_rate_limit_warning(self, current_requests: int, max_requests: int, window_minutes: int = 60):
        """Generate rate limit warning alert"""
        usage_percent = (current_requests / max_requests) * 100
        
        notification = Notification(
            title="Rate Limit Warning",
            message=f"Rate limit usage at {usage_percent:.1f}% ({current_requests}/{max_requests} requests)",
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH
        )
        
        context = AlertContext(
            alert_type=AlertType.RATE_LIMIT_WARNING,
            metrics={
                'current_requests': current_requests,
                'max_requests': max_requests,
                'usage_percent': usage_percent,
                'window_minutes': window_minutes
            }
        )
        
        self.send_notification(notification, context)
    
    def alert_anti_detection_triggered(self, target_username: str, detection_type: str, 
                                     action_taken: str):
        """Generate anti-detection alert"""
        notification = Notification(
            title=f"Anti-Detection Triggered: {target_username}",
            message=f"Detection type: {detection_type}. Action taken: {action_taken}",
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.HIGH
        )
        
        context = AlertContext(
            alert_type=AlertType.ANTI_DETECTION_TRIGGERED,
            target_username=target_username,
            metrics={
                'detection_type': detection_type,
                'action_taken': action_taken
            }
        )
        
        self.send_notification(notification, context)
    
    def alert_data_quality_issue(self, target_username: str, quality_score: float, 
                                issues: List[str]):
        """Generate data quality alert"""
        notification = Notification(
            title=f"Data Quality Issue: {target_username}",
            message=f"Data quality score: {quality_score:.2f}. Issues: {', '.join(issues)}",
            notification_type=NotificationType.WARNING,
            priority=NotificationPriority.MEDIUM
        )
        
        context = AlertContext(
            alert_type=AlertType.DATA_QUALITY_ISSUE,
            target_username=target_username,
            metrics={
                'quality_score': quality_score,
                'issues': issues
            }
        )
        
        self.send_notification(notification, context)
    
    # Utility methods
    def register_event_handler(self, alert_type: AlertType, handler: Callable):
        """Register an event handler for specific alert types"""
        if alert_type not in self.event_handlers:
            self.event_handlers[alert_type] = []
        self.event_handlers[alert_type].append(handler)
    
    def acknowledge_notification(self, notification_id: int):
        """Acknowledge a notification to stop escalation"""
        self.escalation_engine.acknowledge_notification(notification_id)
    
    def resolve_notification(self, notification_id: int):
        """Mark notification as resolved"""
        self.escalation_engine.resolve_notification(notification_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return {
            **self.stats,
            'active_escalations': len(self.escalation_engine.active_escalations),
            'queue_size': self.notification_queue.qsize()
        }
    
    def test_all_channels(self) -> Dict[str, bool]:
        """Test all notification channels"""
        results = {}
        
        # Test email
        if config.is_notification_channel_enabled('email'):
            results['email'] = self.email_service.test_connection()
        
        # Test webhooks
        if config.is_notification_channel_enabled('webhook'):
            webhook_results = self.webhook_service.test_webhooks()
            results['webhooks'] = webhook_results
        
        return results

# Global instance
enhanced_notification_manager = EnhancedNotificationManager()
