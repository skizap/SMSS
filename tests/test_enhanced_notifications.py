#!/usr/bin/env python3
"""
Social Media Surveillance System - Enhanced Notification Tests
Comprehensive test suite for enhanced notification system.
"""

import unittest
import time
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Import the modules to test
from notifications.enhanced_notifications import (
    EmailNotificationService, WebhookNotificationService, AlertThresholdManager,
    EscalationPolicyEngine, AlertType, AlertContext
)
from notifications.enhanced_notification_manager import EnhancedNotificationManager
from notifications.integration import NotificationIntegration, with_notification_tracking
from ui.notification_system import Notification, NotificationType, NotificationPriority
from core.config import config

class TestEmailNotificationService(unittest.TestCase):
    """Test email notification service"""
    
    def setUp(self):
        self.email_service = EmailNotificationService()
        
    def test_email_configuration(self):
        """Test email configuration loading"""
        self.assertIsNotNone(self.email_service.config)
        self.assertEqual(self.email_service.config.smtp_server, "smtp.gmail.com")
        self.assertEqual(self.email_service.config.smtp_port, 587)
    
    @patch('smtplib.SMTP')
    def test_smtp_connection(self, mock_smtp):
        """Test SMTP connection establishment"""
        # Mock SMTP server
        mock_server = Mock()
        mock_smtp.return_value = mock_server
        
        # Configure email settings
        self.email_service.config.enabled = True
        self.email_service.config.username = "test@example.com"
        self.email_service.config.password = "encrypted_password"
        
        # Mock config decryption
        with patch.object(config, 'get_decrypted_email_credentials', return_value=("test@example.com", "password")):
            result = self.email_service._connect_smtp()
            
            self.assertTrue(result)
            mock_smtp.assert_called_once_with("smtp.gmail.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("test@example.com", "password")
    
    def test_email_body_creation(self):
        """Test email body HTML generation"""
        notification = Notification(
            title="Test Notification",
            message="This is a test message",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.MEDIUM
        )
        
        context = AlertContext(
            alert_type=AlertType.SCRAPING_COMPLETE,
            target_username="test_user",
            metrics={'items_scraped': 10}
        )
        
        body = self.email_service._create_email_body(notification, context)
        
        self.assertIn("Test Notification", body)
        self.assertIn("This is a test message", body)
        self.assertIn("test_user", body)
        self.assertIn("items_scraped", body)
        self.assertIn("#3498db", body)  # Info color

class TestWebhookNotificationService(unittest.TestCase):
    """Test webhook notification service"""
    
    def setUp(self):
        self.webhook_service = WebhookNotificationService()
        
    def test_webhook_configuration(self):
        """Test webhook configuration"""
        self.assertIsNotNone(self.webhook_service.config)
        self.assertIsNotNone(self.webhook_service.session)
    
    @patch('requests.Session.post')
    def test_webhook_sending(self, mock_post):
        """Test webhook notification sending"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        # Configure webhook
        self.webhook_service.config.enabled = True
        self.webhook_service.config.urls = ["http://example.com/webhook"]
        
        notification = Notification(
            title="Test Webhook",
            message="Test webhook message",
            notification_type=NotificationType.SUCCESS
        )
        
        result = self.webhook_service.send_notification(notification)
        
        self.assertTrue(result)
        mock_post.assert_called_once()
        
        # Check payload
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        self.assertEqual(payload['title'], "Test Webhook")
        self.assertEqual(payload['message'], "Test webhook message")
        self.assertEqual(payload['type'], "success")
    
    @patch('requests.Session.post')
    def test_webhook_retry_logic(self, mock_post):
        """Test webhook retry logic on failure"""
        # Mock failed responses
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response
        
        self.webhook_service.config.enabled = True
        self.webhook_service.config.urls = ["http://example.com/webhook"]
        self.webhook_service.config.retry_attempts = 2
        self.webhook_service.config.retry_delay = 0.1  # Fast retry for testing
        
        notification = Notification(
            title="Test Retry",
            message="Test retry message"
        )
        
        result = self.webhook_service.send_notification(notification)
        
        self.assertFalse(result)
        self.assertEqual(mock_post.call_count, 2)  # Should retry once

class TestAlertThresholdManager(unittest.TestCase):
    """Test alert threshold management"""
    
    def setUp(self):
        self.threshold_manager = AlertThresholdManager()
    
    def test_rate_limit_checking(self):
        """Test rate limit threshold checking"""
        # Test warning threshold
        alert_context = self.threshold_manager.check_rate_limits(160, 200)  # 80%
        self.assertIsNotNone(alert_context)
        self.assertEqual(alert_context.alert_type, AlertType.RATE_LIMIT_WARNING)
        
        # Test critical threshold
        alert_context = self.threshold_manager.check_rate_limits(190, 200)  # 95%
        self.assertIsNotNone(alert_context)
        self.assertEqual(alert_context.alert_type, AlertType.RATE_LIMIT_CRITICAL)
        
        # Test below threshold
        alert_context = self.threshold_manager.check_rate_limits(100, 200)  # 50%
        self.assertIsNone(alert_context)
    
    def test_failed_requests_checking(self):
        """Test consecutive failed requests checking"""
        # Test below threshold
        alert_context = self.threshold_manager.check_failed_requests(3)
        self.assertIsNone(alert_context)
        
        # Test above threshold
        alert_context = self.threshold_manager.check_failed_requests(6)
        self.assertIsNotNone(alert_context)
        self.assertEqual(alert_context.alert_type, AlertType.SCRAPING_ERROR)
    
    def test_data_quality_checking(self):
        """Test data quality threshold checking"""
        # Test below threshold
        alert_context = self.threshold_manager.check_data_quality(0.7, "test_user")
        self.assertIsNotNone(alert_context)
        self.assertEqual(alert_context.alert_type, AlertType.DATA_QUALITY_ISSUE)
        
        # Test above threshold
        alert_context = self.threshold_manager.check_data_quality(0.9, "test_user")
        self.assertIsNone(alert_context)
    
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_system_health_checking(self, mock_disk, mock_memory):
        """Test system health monitoring"""
        # Mock high memory usage
        mock_memory.return_value = Mock(percent=90.0)
        mock_disk.return_value = Mock(percent=70.0)
        
        alert_context = self.threshold_manager.check_system_health()
        self.assertIsNotNone(alert_context)
        self.assertEqual(alert_context.alert_type, AlertType.SYSTEM_HEALTH_WARNING)
        self.assertEqual(alert_context.metrics['issue'], 'high_memory_usage')
    
    def test_alert_suppression(self):
        """Test alert frequency suppression"""
        alert_type = AlertType.RATE_LIMIT_WARNING
        target = "test_user"
        
        # First alert should not be suppressed
        suppressed = self.threshold_manager.should_suppress_alert(alert_type, target)
        self.assertFalse(suppressed)
        
        # Simulate multiple alerts quickly
        for _ in range(5):
            self.threshold_manager.should_suppress_alert(alert_type, target)
        
        # 6th alert should be suppressed
        suppressed = self.threshold_manager.should_suppress_alert(alert_type, target)
        self.assertTrue(suppressed)

class TestEscalationPolicyEngine(unittest.TestCase):
    """Test escalation policy engine"""
    
    def setUp(self):
        self.escalation_engine = EscalationPolicyEngine()
        # Stop the monitoring thread for testing
        self.escalation_engine.stop_escalation_monitor()
    
    def test_notification_registration(self):
        """Test notification registration for escalation"""
        notification = Notification(
            title="Test Critical",
            message="Test critical message",
            priority=NotificationPriority.CRITICAL
        )
        
        context = AlertContext(alert_type=AlertType.SCRAPING_ERROR)
        
        self.escalation_engine.register_notification(notification, context)
        
        self.assertIn(notification.id, self.escalation_engine.active_escalations)
        state = self.escalation_engine.active_escalations[notification.id]
        self.assertEqual(state.alert_type, AlertType.SCRAPING_ERROR)
        self.assertEqual(state.current_level, 0)
    
    def test_notification_acknowledgment(self):
        """Test notification acknowledgment"""
        notification = Notification(
            title="Test Ack",
            message="Test acknowledgment",
            priority=NotificationPriority.HIGH
        )
        
        context = AlertContext(alert_type=AlertType.RATE_LIMIT_CRITICAL)
        
        self.escalation_engine.register_notification(notification, context)
        self.escalation_engine.acknowledge_notification(notification.id)
        
        state = self.escalation_engine.active_escalations[notification.id]
        self.assertTrue(state.acknowledged)
    
    def test_notification_resolution(self):
        """Test notification resolution"""
        notification = Notification(
            title="Test Resolve",
            message="Test resolution",
            priority=NotificationPriority.HIGH
        )
        
        context = AlertContext(alert_type=AlertType.DATA_QUALITY_ISSUE)
        
        self.escalation_engine.register_notification(notification, context)
        self.escalation_engine.resolve_notification(notification.id)
        
        self.assertNotIn(notification.id, self.escalation_engine.active_escalations)

class TestNotificationIntegration(unittest.TestCase):
    """Test notification integration layer"""
    
    def setUp(self):
        self.integration = NotificationIntegration()
    
    def test_request_tracking(self):
        """Test API request tracking"""
        endpoint = "test_endpoint"
        
        # Track multiple requests
        for _ in range(10):
            self.integration.track_request(endpoint)
        
        self.assertEqual(self.integration.request_counts[endpoint], 10)
    
    def test_failure_tracking(self):
        """Test request failure tracking"""
        target = "test_user"
        scraper = "test_scraper"
        
        # Track failures
        for _ in range(3):
            self.integration.track_request_failure(target, scraper, "Test error")
        
        key = f"{target}_{scraper}"
        self.assertEqual(self.integration.failure_counts[key], 3)
        
        # Track success (should reset)
        self.integration.track_request_success(target, scraper)
        self.assertNotIn(key, self.integration.failure_counts)
    
    def test_notification_tracking_decorator(self):
        """Test notification tracking decorator"""
        @with_notification_tracking("test_scraper")
        def mock_scraper_function(username):
            return [1, 2, 3, 4, 5]  # Return 5 items
        
        # Mock the integration to avoid actual notifications
        with patch.object(self.integration, 'track_request') as mock_track:
            with patch.object(self.integration, 'track_request_success') as mock_success:
                with patch.object(self.integration, 'notify_scraping_complete') as mock_notify:
                    result = mock_scraper_function("test_user")
                    
                    self.assertEqual(len(result), 5)
                    mock_track.assert_called_once()
                    mock_success.assert_called_once_with("test_user", "test_scraper")
                    mock_notify.assert_called_once()

class TestEnhancedNotificationManager(unittest.TestCase):
    """Test enhanced notification manager"""
    
    def setUp(self):
        self.manager = EnhancedNotificationManager()
        # Stop processing for testing
        self.manager.stop_processing()
    
    def test_notification_queuing(self):
        """Test notification queuing"""
        notification = Notification(
            title="Test Queue",
            message="Test queuing message"
        )
        
        result = self.manager.send_notification(notification)
        self.assertTrue(result)
        self.assertFalse(self.manager.notification_queue.empty())
    
    def test_statistics_tracking(self):
        """Test statistics tracking"""
        initial_stats = self.manager.get_statistics()
        self.assertIn('total_notifications', initial_stats)
        self.assertIn('email_sent', initial_stats)
        self.assertIn('webhook_sent', initial_stats)
    
    def test_alert_generation_methods(self):
        """Test alert generation methods"""
        # Test scraping complete alert
        with patch.object(self.manager, 'send_notification') as mock_send:
            self.manager.alert_scraping_complete("test_user", "test_scraper", 10, 5.0)
            mock_send.assert_called_once()
            
            # Check the notification
            call_args = mock_send.call_args[0]
            notification = call_args[0]
            context = call_args[1]
            
            self.assertIn("test_user", notification.title)
            self.assertEqual(context.alert_type, AlertType.SCRAPING_COMPLETE)
            self.assertEqual(context.metrics['items_scraped'], 10)

if __name__ == '__main__':
    # Create a test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_classes = [
        TestEmailNotificationService,
        TestWebhookNotificationService,
        TestAlertThresholdManager,
        TestEscalationPolicyEngine,
        TestNotificationIntegration,
        TestEnhancedNotificationManager
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print(f"\nTest Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
