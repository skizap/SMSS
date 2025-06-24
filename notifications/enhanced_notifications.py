#!/usr/bin/env python3
"""
Social Media Surveillance System - Enhanced Notification System
Comprehensive notification system with email, webhook, and alert management capabilities.
"""

import logging
import smtplib
import requests
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass, asdict
from queue import Queue, Empty
import psutil

from core.config import config
from ui.notification_system import Notification, NotificationType, NotificationPriority

logger = logging.getLogger(__name__)

class AlertType(Enum):
    """Types of alerts that can be triggered"""
    SCRAPING_COMPLETE = "scraping_complete"
    SCRAPING_ERROR = "scraping_error"
    RATE_LIMIT_WARNING = "rate_limit_warning"
    RATE_LIMIT_CRITICAL = "rate_limit_critical"
    ANTI_DETECTION_TRIGGERED = "anti_detection_triggered"
    DATA_QUALITY_ISSUE = "data_quality_issue"
    SYSTEM_HEALTH_WARNING = "system_health_warning"
    ACCOUNT_CHANGE_DETECTED = "account_change_detected"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"

@dataclass
class AlertContext:
    """Context information for alerts"""
    alert_type: AlertType
    target_username: Optional[str] = None
    scraper_type: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class EmailNotificationService:
    """Email notification service with SMTP support"""
    
    def __init__(self):
        self.config = config.notification.email
        self.smtp_server = None
        self.last_connection_time = None
        self.connection_timeout = 300  # 5 minutes
        
    def _connect_smtp(self) -> bool:
        """Connect to SMTP server"""
        try:
            if not self.config.enabled:
                return False
                
            # Check if we need to reconnect
            if (self.smtp_server is None or 
                (self.last_connection_time and 
                 datetime.now() - self.last_connection_time > timedelta(seconds=self.connection_timeout))):
                
                if self.smtp_server:
                    try:
                        self.smtp_server.quit()
                    except:
                        pass
                
                self.smtp_server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
                
                if self.config.use_tls:
                    self.smtp_server.starttls()
                
                # Get credentials
                credentials = config.get_decrypted_email_credentials()
                if credentials:
                    username, password = credentials
                    self.smtp_server.login(username, password)
                else:
                    logger.error("No email credentials available")
                    return False
                
                self.last_connection_time = datetime.now()
                logger.info("SMTP connection established")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            self.smtp_server = None
            return False
    
    def send_notification(self, notification: Notification, context: AlertContext = None) -> bool:
        """Send email notification"""
        try:
            if not self._connect_smtp():
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.from_email or self.config.username
            msg['To'] = ', '.join(self.config.to_emails)
            msg['Subject'] = f"{self.config.subject_prefix} {notification.title}"
            
            # Create email body
            body = self._create_email_body(notification, context)
            msg.attach(MIMEText(body, 'html'))
            
            # Send email
            text = msg.as_string()
            self.smtp_server.sendmail(
                self.config.from_email or self.config.username,
                self.config.to_emails,
                text
            )
            
            logger.info(f"Email notification sent: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _create_email_body(self, notification: Notification, context: AlertContext = None) -> str:
        """Create HTML email body"""
        # Color scheme based on notification type
        colors = {
            NotificationType.INFO: "#3498db",
            NotificationType.SUCCESS: "#27ae60",
            NotificationType.WARNING: "#f39c12",
            NotificationType.ERROR: "#e74c3c",
            NotificationType.CRITICAL: "#8e44ad"
        }
        
        color = colors.get(notification.type, "#3498db")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: {color}; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
                .alert-details {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                .timestamp {{ color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>{notification.title}</h2>
                    <div class="timestamp">{notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
                <div class="content">
                    <p>{notification.message}</p>
        """
        
        # Add context details if available
        if context:
            html += f"""
                    <div class="alert-details">
                        <h4>Alert Details</h4>
                        <p><strong>Type:</strong> {context.alert_type.value}</p>
            """
            
            if context.target_username:
                html += f"<p><strong>Target:</strong> {context.target_username}</p>"
            
            if context.scraper_type:
                html += f"<p><strong>Scraper:</strong> {context.scraper_type}</p>"
            
            if context.error_details:
                html += f"<p><strong>Error Details:</strong> {json.dumps(context.error_details, indent=2)}</p>"
            
            if context.metrics:
                html += "<p><strong>Metrics:</strong></p><ul>"
                for key, value in context.metrics.items():
                    html += f"<li>{key}: {value}</li>"
                html += "</ul>"
            
            html += "</div>"
        
        html += """
                </div>
                <div class="footer">
                    <p>Instagram Scraper Surveillance System</p>
                    <p>This is an automated notification. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def test_connection(self) -> bool:
        """Test email connection"""
        return self._connect_smtp()
    
    def __del__(self):
        """Cleanup SMTP connection"""
        if self.smtp_server:
            try:
                self.smtp_server.quit()
            except:
                pass

class WebhookNotificationService:
    """Webhook notification service with retry logic"""
    
    def __init__(self):
        self.config = config.notification.webhook
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Instagram-Scraper-Notification-System/1.0'
        })
        
        # Add custom headers
        if self.config.custom_headers:
            self.session.headers.update(self.config.custom_headers)
        
        # Setup authentication
        self._setup_authentication()
    
    def _setup_authentication(self):
        """Setup webhook authentication"""
        if self.config.auth_type == "bearer" and self.config.auth_token:
            self.session.headers['Authorization'] = f"Bearer {self.config.auth_token}"
        elif self.config.auth_type == "basic" and self.config.auth_token:
            # Assume auth_token is base64 encoded username:password
            self.session.headers['Authorization'] = f"Basic {self.config.auth_token}"
    
    def send_notification(self, notification: Notification, context: AlertContext = None) -> bool:
        """Send webhook notification with retry logic"""
        if not self.config.enabled or not self.config.urls:
            return False
        
        payload = self._create_webhook_payload(notification, context)
        success_count = 0
        
        for url in self.config.urls:
            if self._send_to_webhook(url, payload):
                success_count += 1
        
        return success_count > 0
    
    def _send_to_webhook(self, url: str, payload: Dict[str, Any]) -> bool:
        """Send payload to a single webhook URL with retry logic"""
        for attempt in range(self.config.retry_attempts):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code in [200, 201, 202, 204]:
                    logger.info(f"Webhook notification sent successfully to {url}")
                    return True
                else:
                    logger.warning(f"Webhook returned status {response.status_code}: {response.text}")
                    
            except Exception as e:
                logger.error(f"Webhook attempt {attempt + 1} failed for {url}: {e}")
            
            # Wait before retry (except on last attempt)
            if attempt < self.config.retry_attempts - 1:
                time.sleep(self.config.retry_delay)
        
        logger.error(f"All webhook attempts failed for {url}")
        return False
    
    def _create_webhook_payload(self, notification: Notification, context: AlertContext = None) -> Dict[str, Any]:
        """Create webhook payload"""
        payload = {
            'timestamp': notification.timestamp.isoformat(),
            'title': notification.title,
            'message': notification.message,
            'type': notification.type.value,
            'priority': notification.priority.value,
            'notification_id': notification.id
        }
        
        if context:
            payload['alert_context'] = {
                'alert_type': context.alert_type.value,
                'target_username': context.target_username,
                'scraper_type': context.scraper_type,
                'error_details': context.error_details,
                'metrics': context.metrics,
                'timestamp': context.timestamp.isoformat()
            }
        
        return payload
    
    def test_webhooks(self) -> Dict[str, bool]:
        """Test all configured webhooks"""
        results = {}
        test_payload = {
            'timestamp': datetime.now().isoformat(),
            'title': 'Webhook Test',
            'message': 'This is a test notification from Instagram Scraper',
            'type': 'info',
            'priority': 'medium',
            'test': True
        }
        
        for url in self.config.urls:
            results[url] = self._send_to_webhook(url, test_payload)
        
        return results

class AlertThresholdManager:
    """Manages alert thresholds and triggers notifications"""

    def __init__(self):
        self.thresholds = config.get_alert_thresholds()
        self.alert_history = {}  # Track alert frequency
        self.system_metrics = {}
        self.last_metrics_update = None

    def check_rate_limits(self, current_requests: int, max_requests: int, window_minutes: int = 60) -> Optional[AlertContext]:
        """Check if rate limits are approaching"""
        if max_requests <= 0:
            return None

        usage_percent = (current_requests / max_requests) * 100

        if usage_percent >= self.thresholds['rate_limit_critical']:
            return AlertContext(
                alert_type=AlertType.RATE_LIMIT_CRITICAL,
                metrics={
                    'current_requests': current_requests,
                    'max_requests': max_requests,
                    'usage_percent': usage_percent,
                    'window_minutes': window_minutes
                }
            )
        elif usage_percent >= self.thresholds['rate_limit_warning']:
            return AlertContext(
                alert_type=AlertType.RATE_LIMIT_WARNING,
                metrics={
                    'current_requests': current_requests,
                    'max_requests': max_requests,
                    'usage_percent': usage_percent,
                    'window_minutes': window_minutes
                }
            )

        return None

    def check_failed_requests(self, consecutive_failures: int, scraper_type: str = None) -> Optional[AlertContext]:
        """Check for consecutive failed requests"""
        if consecutive_failures >= self.thresholds['failed_requests']:
            return AlertContext(
                alert_type=AlertType.SCRAPING_ERROR,
                scraper_type=scraper_type,
                metrics={
                    'consecutive_failures': consecutive_failures,
                    'threshold': self.thresholds['failed_requests']
                }
            )
        return None

    def check_data_quality(self, quality_score: float, target_username: str = None) -> Optional[AlertContext]:
        """Check data quality metrics"""
        if quality_score < self.thresholds['data_quality']:
            return AlertContext(
                alert_type=AlertType.DATA_QUALITY_ISSUE,
                target_username=target_username,
                metrics={
                    'quality_score': quality_score,
                    'threshold': self.thresholds['data_quality']
                }
            )
        return None

    def check_system_health(self) -> Optional[AlertContext]:
        """Check system health metrics"""
        try:
            # Update system metrics
            self._update_system_metrics()

            # Check memory usage
            if self.system_metrics.get('memory_percent', 0) > self.thresholds['memory_usage']:
                return AlertContext(
                    alert_type=AlertType.SYSTEM_HEALTH_WARNING,
                    metrics={
                        'memory_usage': self.system_metrics['memory_percent'],
                        'threshold': self.thresholds['memory_usage'],
                        'issue': 'high_memory_usage'
                    }
                )

            # Check disk usage
            if self.system_metrics.get('disk_percent', 0) > self.thresholds['disk_usage']:
                return AlertContext(
                    alert_type=AlertType.SYSTEM_HEALTH_WARNING,
                    metrics={
                        'disk_usage': self.system_metrics['disk_percent'],
                        'threshold': self.thresholds['disk_usage'],
                        'issue': 'high_disk_usage'
                    }
                )

        except Exception as e:
            logger.error(f"Error checking system health: {e}")

        return None

    def check_account_changes(self, target_username: str, follower_change: int,
                            engagement_change: float = None) -> Optional[AlertContext]:
        """Check for significant account changes"""
        metrics = {'follower_change': follower_change}

        # Check follower changes
        if abs(follower_change) >= self.thresholds['follower_change']:
            metrics['follower_threshold'] = self.thresholds['follower_change']

            return AlertContext(
                alert_type=AlertType.ACCOUNT_CHANGE_DETECTED,
                target_username=target_username,
                metrics=metrics
            )

        # Check engagement drops
        if engagement_change is not None and engagement_change <= -self.thresholds['engagement_drop']:
            metrics['engagement_change'] = engagement_change
            metrics['engagement_threshold'] = self.thresholds['engagement_drop']

            return AlertContext(
                alert_type=AlertType.ACCOUNT_CHANGE_DETECTED,
                target_username=target_username,
                metrics=metrics
            )

        return None

    def check_suspicious_activity(self, target_username: str, activity_count: int) -> Optional[AlertContext]:
        """Check for suspicious activity patterns"""
        if activity_count >= self.thresholds['suspicious_activity']:
            return AlertContext(
                alert_type=AlertType.SUSPICIOUS_ACTIVITY,
                target_username=target_username,
                metrics={
                    'activity_count': activity_count,
                    'threshold': self.thresholds['suspicious_activity']
                }
            )
        return None

    def _update_system_metrics(self):
        """Update system performance metrics"""
        try:
            # Update every 30 seconds to avoid excessive system calls
            now = datetime.now()
            if (self.last_metrics_update is None or
                (now - self.last_metrics_update).seconds >= 30):

                self.system_metrics = {
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent,
                    'cpu_percent': psutil.cpu_percent(interval=1),
                    'timestamp': now
                }
                self.last_metrics_update = now

        except Exception as e:
            logger.error(f"Error updating system metrics: {e}")

    def should_suppress_alert(self, alert_type: AlertType, target_username: str = None) -> bool:
        """Check if alert should be suppressed due to frequency limits"""
        key = f"{alert_type.value}_{target_username or 'global'}"
        now = datetime.now()

        # Get alert history for this key
        if key not in self.alert_history:
            self.alert_history[key] = []

        # Clean old alerts (older than 1 hour)
        self.alert_history[key] = [
            timestamp for timestamp in self.alert_history[key]
            if (now - timestamp).seconds < 3600
        ]

        # Check frequency limits
        recent_alerts = len(self.alert_history[key])

        # Suppress if more than 5 alerts in the last hour
        if recent_alerts >= 5:
            return True

        # Add current alert to history
        self.alert_history[key].append(now)
        return False

@dataclass
class EscalationState:
    """Tracks escalation state for notifications"""
    notification_id: int
    alert_type: AlertType
    initial_timestamp: datetime
    current_level: int = 0
    last_escalation: datetime = None
    acknowledged: bool = False
    resolved: bool = False

class EscalationPolicyEngine:
    """Manages notification escalation policies"""

    def __init__(self):
        self.policy = config.notification.escalation_policy
        self.active_escalations: Dict[int, EscalationState] = {}
        self.escalation_thread = None
        self.running = False

        if self.policy.enabled:
            self.start_escalation_monitor()

    def start_escalation_monitor(self):
        """Start the escalation monitoring thread"""
        if not self.running:
            self.running = True
            self.escalation_thread = threading.Thread(target=self._escalation_monitor, daemon=True)
            self.escalation_thread.start()
            logger.info("Escalation policy engine started")

    def stop_escalation_monitor(self):
        """Stop the escalation monitoring thread"""
        self.running = False
        if self.escalation_thread:
            self.escalation_thread.join(timeout=5)
        logger.info("Escalation policy engine stopped")

    def register_notification(self, notification: Notification, context: AlertContext):
        """Register a notification for potential escalation"""
        if not self.policy.enabled:
            return

        # Only escalate high priority and critical notifications
        if notification.priority in [NotificationPriority.HIGH, NotificationPriority.CRITICAL]:
            escalation_state = EscalationState(
                notification_id=notification.id,
                alert_type=context.alert_type,
                initial_timestamp=notification.timestamp
            )

            self.active_escalations[notification.id] = escalation_state
            logger.info(f"Registered notification {notification.id} for escalation monitoring")

    def acknowledge_notification(self, notification_id: int):
        """Acknowledge a notification to stop escalation"""
        if notification_id in self.active_escalations:
            self.active_escalations[notification_id].acknowledged = True
            logger.info(f"Notification {notification_id} acknowledged, escalation stopped")

    def resolve_notification(self, notification_id: int):
        """Mark notification as resolved and remove from escalation"""
        if notification_id in self.active_escalations:
            self.active_escalations[notification_id].resolved = True
            del self.active_escalations[notification_id]
            logger.info(f"Notification {notification_id} resolved and removed from escalation")

    def _escalation_monitor(self):
        """Monitor notifications for escalation"""
        while self.running:
            try:
                current_time = datetime.now()
                escalations_to_process = []

                for notification_id, state in self.active_escalations.items():
                    if state.acknowledged or state.resolved:
                        continue

                    # Check if escalation is due
                    time_since_initial = (current_time - state.initial_timestamp).total_seconds() / 60
                    time_since_last = 0

                    if state.last_escalation:
                        time_since_last = (current_time - state.last_escalation).total_seconds() / 60

                    # Escalate if enough time has passed
                    if (state.current_level == 0 and time_since_initial >= self.policy.escalation_delay_minutes) or \
                       (state.current_level > 0 and time_since_last >= self.policy.escalation_delay_minutes):

                        if state.current_level < self.policy.max_escalation_level:
                            escalations_to_process.append((notification_id, state))

                # Process escalations
                for notification_id, state in escalations_to_process:
                    self._escalate_notification(notification_id, state)

                # Clean up resolved notifications
                resolved_ids = [nid for nid, state in self.active_escalations.items() if state.resolved]
                for nid in resolved_ids:
                    del self.active_escalations[nid]

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in escalation monitor: {e}")
                time.sleep(60)

    def _escalate_notification(self, notification_id: int, state: EscalationState):
        """Escalate a notification to the next level"""
        try:
            state.current_level += 1
            state.last_escalation = datetime.now()

            # Create escalated notification
            escalated_notification = Notification(
                title=f"ESCALATED (Level {state.current_level}): {state.alert_type.value}",
                message=f"Alert has not been acknowledged for {self.policy.escalation_delay_minutes} minutes. "
                       f"Original notification ID: {notification_id}",
                notification_type=NotificationType.CRITICAL,
                priority=NotificationPriority.CRITICAL
            )

            # Send through escalation channels
            from .enhanced_notification_manager import EnhancedNotificationManager
            manager = EnhancedNotificationManager()

            for channel in self.policy.escalation_channels:
                if channel == 'email':
                    manager.email_service.send_notification(escalated_notification)
                elif channel == 'webhook':
                    manager.webhook_service.send_notification(escalated_notification)

            logger.warning(f"Escalated notification {notification_id} to level {state.current_level}")

        except Exception as e:
            logger.error(f"Error escalating notification {notification_id}: {e}")

    def get_active_escalations(self) -> List[Dict[str, Any]]:
        """Get list of active escalations"""
        escalations = []
        for notification_id, state in self.active_escalations.items():
            escalations.append({
                'notification_id': notification_id,
                'alert_type': state.alert_type.value,
                'initial_timestamp': state.initial_timestamp.isoformat(),
                'current_level': state.current_level,
                'last_escalation': state.last_escalation.isoformat() if state.last_escalation else None,
                'acknowledged': state.acknowledged,
                'resolved': state.resolved
            })
        return escalations
