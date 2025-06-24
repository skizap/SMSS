#!/usr/bin/env python3
"""
Social Media Surveillance System - Notification Integration
Integration points for enhanced notifications with core components.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from functools import wraps

from core.config import config
from .enhanced_notification_manager import enhanced_notification_manager
from .enhanced_notifications import AlertType, AlertContext
from ui.notification_system import Notification, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

class NotificationIntegration:
    """Integration layer for enhanced notifications with core components"""
    
    def __init__(self):
        self.manager = enhanced_notification_manager
        self.request_counts = {}  # Track requests for rate limiting
        self.failure_counts = {}  # Track consecutive failures
        self.last_reset_time = datetime.now()
        
    def reset_hourly_counters(self):
        """Reset hourly request counters"""
        current_time = datetime.now()
        if (current_time - self.last_reset_time).seconds >= 3600:  # 1 hour
            self.request_counts.clear()
            self.last_reset_time = current_time
    
    # Browser Engine Integration
    def track_request(self, endpoint: str = "instagram_api"):
        """Track API request for rate limiting"""
        self.reset_hourly_counters()
        
        if endpoint not in self.request_counts:
            self.request_counts[endpoint] = 0
        
        self.request_counts[endpoint] += 1
        
        # Check rate limits (Instagram typically allows ~200 requests per hour)
        max_requests = 200
        current_requests = self.request_counts[endpoint]
        
        alert_context = self.manager.threshold_manager.check_rate_limits(
            current_requests, max_requests
        )
        
        if alert_context:
            if alert_context.alert_type == AlertType.RATE_LIMIT_WARNING:
                self.manager.alert_rate_limit_warning(current_requests, max_requests)
            elif alert_context.alert_type == AlertType.RATE_LIMIT_CRITICAL:
                notification = Notification(
                    title="Critical Rate Limit Reached",
                    message=f"Rate limit critical: {current_requests}/{max_requests} requests used",
                    notification_type=NotificationType.CRITICAL,
                    priority=NotificationPriority.CRITICAL
                )
                self.manager.send_notification(notification, alert_context)
    
    def track_request_failure(self, target_username: str, scraper_type: str, error_message: str):
        """Track request failure for consecutive failure detection"""
        key = f"{target_username}_{scraper_type}"
        
        if key not in self.failure_counts:
            self.failure_counts[key] = 0
        
        self.failure_counts[key] += 1
        
        # Check for consecutive failures
        alert_context = self.manager.threshold_manager.check_failed_requests(
            self.failure_counts[key], scraper_type
        )
        
        if alert_context:
            self.manager.alert_scraping_error(target_username, scraper_type, error_message)
    
    def track_request_success(self, target_username: str, scraper_type: str):
        """Track successful request (resets failure count)"""
        key = f"{target_username}_{scraper_type}"
        if key in self.failure_counts:
            del self.failure_counts[key]
    
    def notify_anti_detection_triggered(self, target_username: str, detection_type: str, action_taken: str):
        """Notify when anti-detection measures are triggered"""
        self.manager.alert_anti_detection_triggered(target_username, detection_type, action_taken)
    
    def notify_scraping_complete(self, target_username: str, scraper_type: str, 
                                items_scraped: int, duration_seconds: float):
        """Notify when scraping task completes successfully"""
        self.manager.alert_scraping_complete(target_username, scraper_type, items_scraped, duration_seconds)
    
    # Data Manager Integration
    def notify_data_quality_issue(self, target_username: str, quality_score: float, issues: List[str]):
        """Notify about data quality issues"""
        self.manager.alert_data_quality_issue(target_username, quality_score, issues)
    
    def notify_account_changes(self, target_username: str, changes: Dict[str, Any]):
        """Notify about significant account changes"""
        follower_change = changes.get('follower_change', 0)
        engagement_change = changes.get('engagement_change', 0)
        
        alert_context = self.manager.threshold_manager.check_account_changes(
            target_username, follower_change, engagement_change
        )
        
        if alert_context:
            change_details = []
            if abs(follower_change) > 0:
                change_details.append(f"Followers: {follower_change:+d}")
            if engagement_change != 0:
                change_details.append(f"Engagement: {engagement_change:+.1%}")
            
            notification = Notification(
                title=f"Account Changes Detected: {target_username}",
                message=f"Significant changes detected: {', '.join(change_details)}",
                notification_type=NotificationType.INFO,
                priority=NotificationPriority.MEDIUM
            )
            
            self.manager.send_notification(notification, alert_context)
    
    # Error Handler Integration
    def notify_critical_error(self, error_id: str, error_message: str, context: Dict[str, Any]):
        """Notify about critical system errors"""
        notification = Notification(
            title=f"Critical System Error: {error_id}",
            message=f"Critical error occurred: {error_message}",
            notification_type=NotificationType.CRITICAL,
            priority=NotificationPriority.CRITICAL
        )
        
        alert_context = AlertContext(
            alert_type=AlertType.SCRAPING_ERROR,
            error_details={'error_id': error_id, 'context': context}
        )
        
        self.manager.send_notification(notification, alert_context)
    
    # System Health Monitoring
    def check_system_health(self):
        """Check and report system health"""
        alert_context = self.manager.threshold_manager.check_system_health()
        
        if alert_context:
            issue = alert_context.metrics.get('issue', 'unknown')
            
            if issue == 'high_memory_usage':
                memory_usage = alert_context.metrics.get('memory_usage', 0)
                notification = Notification(
                    title="High Memory Usage Warning",
                    message=f"System memory usage is at {memory_usage:.1f}%",
                    notification_type=NotificationType.WARNING,
                    priority=NotificationPriority.HIGH
                )
            elif issue == 'high_disk_usage':
                disk_usage = alert_context.metrics.get('disk_usage', 0)
                notification = Notification(
                    title="High Disk Usage Warning",
                    message=f"System disk usage is at {disk_usage:.1f}%",
                    notification_type=NotificationType.WARNING,
                    priority=NotificationPriority.HIGH
                )
            else:
                notification = Notification(
                    title="System Health Warning",
                    message=f"System health issue detected: {issue}",
                    notification_type=NotificationType.WARNING,
                    priority=NotificationPriority.HIGH
                )
            
            self.manager.send_notification(notification, alert_context)

# Decorators for easy integration
def with_notification_tracking(scraper_type: str):
    """Decorator to automatically track scraping operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract target username from args/kwargs
            target_username = None
            if args and hasattr(args[0], 'current_user'):
                target_username = args[0].current_user
            elif 'username' in kwargs:
                target_username = kwargs['username']
            elif 'target_username' in kwargs:
                target_username = kwargs['target_username']
            
            start_time = datetime.now()
            
            try:
                # Track the request
                notification_integration.track_request()
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Track success
                if target_username:
                    notification_integration.track_request_success(target_username, scraper_type)
                
                # Calculate metrics
                duration = (datetime.now() - start_time).total_seconds()
                items_scraped = 0
                
                # Try to extract items count from result
                if isinstance(result, (list, tuple)):
                    items_scraped = len(result)
                elif isinstance(result, dict) and 'items' in result:
                    items_scraped = len(result['items'])
                elif isinstance(result, dict) and 'count' in result:
                    items_scraped = result['count']
                
                # Notify completion
                if target_username and items_scraped > 0:
                    notification_integration.notify_scraping_complete(
                        target_username, scraper_type, items_scraped, duration
                    )
                
                return result
                
            except Exception as e:
                # Track failure
                if target_username:
                    notification_integration.track_request_failure(
                        target_username, scraper_type, str(e)
                    )
                raise
        
        return wrapper
    return decorator

def with_anti_detection_monitoring(detection_type: str):
    """Decorator to monitor anti-detection triggers"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Check if this is an anti-detection trigger
                error_message = str(e).lower()
                if any(keyword in error_message for keyword in ['blocked', 'captcha', 'rate limit', 'suspicious']):
                    # Extract target username
                    target_username = "unknown"
                    if args and hasattr(args[0], 'current_user'):
                        target_username = args[0].current_user
                    
                    notification_integration.notify_anti_detection_triggered(
                        target_username, detection_type, f"Exception caught: {str(e)}"
                    )
                raise
        
        return wrapper
    return decorator

# Global integration instance
notification_integration = NotificationIntegration()

# Health monitoring function to be called periodically
def monitor_system_health():
    """Monitor system health and send alerts if needed"""
    try:
        notification_integration.check_system_health()
    except Exception as e:
        logger.error(f"Error monitoring system health: {e}")
