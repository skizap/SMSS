#!/usr/bin/env python3
"""
Social Media Surveillance System - Phase 5 UI Testing Suite
Comprehensive testing of all UI components, user interaction flows,
error handling in UI, and integration with backend systems.
"""

import sys
import unittest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import PyQt6 for testing
try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtTest import QTest
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available - UI tests will be skipped")

# Import UI modules
if PYQT_AVAILABLE:
    from ui.main_dashboard import MainDashboard, ModernButton, StatusIndicator, ActivityFeedWidget
    from ui.surveillance_panel import SurveillancePanel, MonitoringControlWidget, TargetDetailsWidget
    from ui.analytics_panel import AnalyticsPanel, ChartWidget, AnalyticsControlWidget
    from ui.settings_panel import SettingsPanel, CredentialsWidget, MonitoringSettingsWidget
    from ui.notification_system import NotificationManager, ToastNotification, NotificationCenter
    from ui.realtime_updates import RealTimeUpdateManager, UpdateType, UpdateData
    from ui.themes import ThemeManager, ThemeType

logger = logging.getLogger(__name__)

class TestMainDashboard(unittest.TestCase):
    """Test main dashboard functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_dashboard_initialization(self):
        """Test dashboard initialization"""
        dashboard = MainDashboard()
        
        # Check basic properties
        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard.windowTitle(), "Social Media Surveillance System - Dashboard")
        self.assertGreaterEqual(dashboard.minimumWidth(), 1200)
        self.assertGreaterEqual(dashboard.minimumHeight(), 800)
        
        # Check UI components exist
        self.assertIsNotNone(dashboard.tab_widget)
        self.assertIsNotNone(dashboard.target_list_widget)
        self.assertIsNotNone(dashboard.activity_feed)
        self.assertIsNotNone(dashboard.system_stats)
        
    def test_modern_button(self):
        """Test modern button component"""
        button = ModernButton("Test Button")
        
        self.assertEqual(button.text(), "Test Button")
        self.assertGreaterEqual(button.minimumHeight(), 40)
        
        # Test click
        clicked = False
        def on_click():
            nonlocal clicked
            clicked = True
            
        button.clicked.connect(on_click)
        button.click()
        self.assertTrue(clicked)
        
    def test_status_indicator(self):
        """Test status indicator component"""
        indicator = StatusIndicator("online", "Test Status")
        
        self.assertEqual(indicator.status, "online")
        self.assertEqual(indicator.text, "Test Status")
        
        # Test status change
        indicator.set_status("offline", "New Status")
        self.assertEqual(indicator.status, "offline")
        self.assertEqual(indicator.text, "New Status")
        
    def test_activity_feed(self):
        """Test activity feed widget"""
        feed = ActivityFeedWidget()
        
        # Test adding activity
        initial_count = feed.activity_list.count()
        feed.add_activity("new_post", "Test activity message")
        
        self.assertEqual(feed.activity_list.count(), initial_count + 1)
        
        # Test activity limit
        for i in range(105):  # Add more than limit
            feed.add_activity("system", f"Test message {i}")
            
        self.assertLessEqual(feed.activity_list.count(), 100)

class TestSurveillancePanel(unittest.TestCase):
    """Test surveillance panel functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_surveillance_panel_initialization(self):
        """Test surveillance panel initialization"""
        panel = SurveillancePanel()
        
        self.assertIsNotNone(panel)
        self.assertIsNotNone(panel.monitoring_controls)
        self.assertIsNotNone(panel.target_details)
        self.assertIsNotNone(panel.recent_activity)
        
    def test_monitoring_controls(self):
        """Test monitoring control widget"""
        controls = MonitoringControlWidget()
        
        # Initially disabled
        self.assertFalse(controls.start_button.isEnabled())
        self.assertFalse(controls.stop_button.isEnabled())
        
        # Set target
        controls.set_target(1)
        self.assertTrue(controls.start_button.isEnabled())
        self.assertFalse(controls.stop_button.isEnabled())
        
        # Test monitoring signals
        monitoring_started = False
        def on_monitoring_started(target_id):
            nonlocal monitoring_started
            monitoring_started = True
            
        controls.monitoring_started.connect(on_monitoring_started)
        controls.start_monitoring()
        
        self.assertTrue(monitoring_started)
        self.assertFalse(controls.start_button.isEnabled())
        self.assertTrue(controls.stop_button.isEnabled())

class TestAnalyticsPanel(unittest.TestCase):
    """Test analytics panel functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_analytics_panel_initialization(self):
        """Test analytics panel initialization"""
        panel = AnalyticsPanel()
        
        self.assertIsNotNone(panel)
        self.assertIsNotNone(panel.analytics_controls)
        self.assertIsNotNone(panel.stats_summary)
        self.assertIsNotNone(panel.main_chart)
        
    def test_chart_widget(self):
        """Test chart widget"""
        chart = ChartWidget()
        
        self.assertIsNotNone(chart)
        
        # Test chart update
        test_data = {
            'x': [1, 2, 3, 4, 5],
            'y': [10, 20, 15, 25, 30],
            'xlabel': 'Time',
            'ylabel': 'Value'
        }
        
        # Should not raise exception
        chart.update_chart("line", test_data, "Test Chart")
        
    def test_analytics_controls(self):
        """Test analytics control widget"""
        controls = AnalyticsControlWidget()
        
        # Test filter change signal
        filters_changed = False
        def on_filters_changed(filters):
            nonlocal filters_changed
            filters_changed = True
            
        controls.filters_changed.connect(on_filters_changed)
        controls.on_filters_changed()
        
        self.assertTrue(filters_changed)
        
        # Test filter values
        filters = controls.get_current_filters()
        self.assertIn('target_id', filters)
        self.assertIn('date_from', filters)
        self.assertIn('date_to', filters)
        self.assertIn('metric', filters)

class TestSettingsPanel(unittest.TestCase):
    """Test settings panel functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_settings_panel_initialization(self):
        """Test settings panel initialization"""
        panel = SettingsPanel()
        
        self.assertIsNotNone(panel)
        self.assertIsNotNone(panel.settings_tabs)
        self.assertIsNotNone(panel.credentials_widget)
        self.assertIsNotNone(panel.monitoring_widget)
        self.assertIsNotNone(panel.api_widget)
        
    def test_credentials_widget(self):
        """Test credentials widget"""
        widget = CredentialsWidget()
        
        # Test password visibility toggle
        widget.password_edit.setText("test_password")
        widget.show_password_check.setChecked(True)
        widget.toggle_password_visibility(True)
        
        # Should show password in normal mode
        self.assertEqual(widget.password_edit.echoMode(), widget.password_edit.EchoMode.Normal)
        
        widget.toggle_password_visibility(False)
        self.assertEqual(widget.password_edit.echoMode(), widget.password_edit.EchoMode.Password)
        
    def test_monitoring_settings(self):
        """Test monitoring settings widget"""
        widget = MonitoringSettingsWidget()
        
        # Test default values
        self.assertGreaterEqual(widget.refresh_interval_spin.value(), 30)
        self.assertLessEqual(widget.refresh_interval_spin.value(), 3600)
        
        # Test settings signals
        settings_updated = False
        def on_settings_updated(settings):
            nonlocal settings_updated
            settings_updated = True
            
        widget.settings_updated.connect(on_settings_updated)
        widget.save_settings()
        
        self.assertTrue(settings_updated)

class TestNotificationSystem(unittest.TestCase):
    """Test notification system functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_notification_manager_initialization(self):
        """Test notification manager initialization"""
        manager = NotificationManager()
        
        self.assertIsNotNone(manager)
        self.assertIsNotNone(manager.notification_center)
        self.assertIsNotNone(manager.tabs)
        
    def test_notification_center(self):
        """Test notification center"""
        center = NotificationCenter()
        
        # Test adding notification
        from ui.notification_system import Notification, NotificationType, NotificationPriority
        
        notification = Notification(
            title="Test Notification",
            message="This is a test message",
            notification_type=NotificationType.INFO,
            priority=NotificationPriority.MEDIUM
        )
        
        initial_count = len(center.notifications)
        center.add_notification(notification)
        
        self.assertEqual(len(center.notifications), initial_count + 1)
        self.assertEqual(center.notification_list.count(), initial_count + 1)

class TestRealTimeUpdates(unittest.TestCase):
    """Test real-time updates functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_update_manager_initialization(self):
        """Test update manager initialization"""
        manager = RealTimeUpdateManager()
        
        self.assertIsNotNone(manager)
        self.assertIsNotNone(manager.data_collector)
        
    def test_update_data_creation(self):
        """Test update data creation"""
        update_data = UpdateData(
            update_type=UpdateType.NEW_POST,
            target_id=1,
            data={'test': 'data'},
            timestamp=datetime.now(),
            priority=2
        )
        
        self.assertEqual(update_data.update_type, UpdateType.NEW_POST)
        self.assertEqual(update_data.target_id, 1)
        self.assertEqual(update_data.data['test'], 'data')
        self.assertEqual(update_data.priority, 2)

class TestThemeSystem(unittest.TestCase):
    """Test theme system functionality"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    def test_theme_manager_initialization(self):
        """Test theme manager initialization"""
        manager = ThemeManager()
        
        self.assertIsNotNone(manager)
        self.assertEqual(manager.current_theme, ThemeType.LIGHT)
        
    def test_theme_application(self):
        """Test theme application"""
        manager = ThemeManager()
        
        # Test light theme
        manager.apply_theme(ThemeType.LIGHT)
        self.assertEqual(manager.current_theme, ThemeType.LIGHT)
        
        # Test dark theme
        manager.apply_theme(ThemeType.DARK)
        self.assertEqual(manager.current_theme, ThemeType.DARK)
        
    def test_theme_colors(self):
        """Test theme color palettes"""
        manager = ThemeManager()
        
        # Light theme colors
        manager.apply_theme(ThemeType.LIGHT)
        light_colors = manager.get_theme_colors()
        
        self.assertIn('background', light_colors)
        self.assertIn('primary', light_colors)
        self.assertIn('text', light_colors)
        
        # Dark theme colors
        manager.apply_theme(ThemeType.DARK)
        dark_colors = manager.get_theme_colors()
        
        self.assertIn('background', dark_colors)
        self.assertIn('primary', dark_colors)
        self.assertIn('text', dark_colors)
        
        # Colors should be different
        self.assertNotEqual(light_colors['background'], dark_colors['background'])

class TestUIIntegration(unittest.TestCase):
    """Test UI integration with backend systems"""
    
    @unittest.skipUnless(PYQT_AVAILABLE, "PyQt6 not available")
    def setUp(self):
        """Set up test fixtures"""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
            
    @patch('core.data_manager.DataManager')
    def test_dashboard_data_integration(self, mock_data_manager):
        """Test dashboard integration with data manager"""
        # Mock data manager
        mock_instance = Mock()
        mock_data_manager.return_value = mock_instance
        mock_instance.get_all_targets.return_value = []
        mock_instance.get_dashboard_stats.return_value = {
            'total_targets': 5,
            'total_posts': 100,
            'total_followers': 1000,
            'avg_engagement': 5.5
        }
        
        dashboard = MainDashboard()
        
        # Should not raise exception
        dashboard.update_dashboard_stats()
        
        # Verify data manager was called
        mock_instance.get_dashboard_stats.assert_called()

def run_ui_tests():
    """Run all UI tests"""
    print("🧪 Running Phase 5 UI Testing Suite...")
    print("=" * 60)
    
    if not PYQT_AVAILABLE:
        print("❌ PyQt6 not available - UI tests cannot run")
        print("   Please install PyQt6: pip install PyQt6")
        return False
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestMainDashboard,
        TestSurveillancePanel,
        TestAnalyticsPanel,
        TestSettingsPanel,
        TestNotificationSystem,
        TestRealTimeUpdates,
        TestThemeSystem,
        TestUIIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"📊 UI Test Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\n🚨 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback.split('Exception:')[-1].strip()}")
    
    if not result.failures and not result.errors:
        print("\n✅ All UI tests passed successfully!")
        print("\n🎉 Phase 5 UI Implementation Complete!")
        print("   ✅ Main Dashboard Framework")
        print("   ✅ Surveillance Panel")
        print("   ✅ Analytics Panel")
        print("   ✅ Settings Panel")
        print("   ✅ Notification System")
        print("   ✅ Real-time Updates")
        print("   ✅ UI Styling and Themes")
        print("   ✅ Comprehensive Testing")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_ui_tests()
    sys.exit(0 if success else 1)
