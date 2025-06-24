#!/usr/bin/env python3
"""
Social Media Surveillance System - Notification System
Comprehensive notification system with real-time alerts, notification center,
alert rules management, and multiple delivery mechanisms.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QGroupBox, QScrollArea, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox, QDialog, QLineEdit, QDateTimeEdit,
    QSystemTrayIcon, QMenu, QApplication
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QDateTime, QPropertyAnimation,
    QRect, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QPen, QBrush
)

# Import project modules
from core.data_manager import DataManager

logger = logging.getLogger(__name__)

class NotificationType(Enum):
    """Notification types"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationPriority(Enum):
    """Notification priorities"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Notification:
    """Notification data class"""
    
    def __init__(self, title: str, message: str, notification_type: NotificationType = NotificationType.INFO,
                 priority: NotificationPriority = NotificationPriority.MEDIUM, timestamp: datetime = None,
                 target_id: int = None, data: dict = None):
        self.id = id(self)  # Simple ID generation
        self.title = title
        self.message = message
        self.type = notification_type
        self.priority = priority
        self.timestamp = timestamp or datetime.now()
        self.target_id = target_id
        self.data = data or {}
        self.read = False
        self.dismissed = False

class ToastNotification(QWidget):
    """Toast notification widget that appears temporarily"""
    
    def __init__(self, notification: Notification, parent=None):
        super().__init__(parent)
        self.notification = notification
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(350, 100)
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        """Setup the toast notification UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Main frame
        self.frame = QFrame()
        self.frame.setStyleSheet(self.get_style_for_type())
        frame_layout = QHBoxLayout(self.frame)
        frame_layout.setContentsMargins(15, 10, 15, 10)
        
        # Icon
        icon_label = QLabel(self.get_icon_for_type())
        icon_label.setFont(QFont("Segoe UI", 20))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_layout.addWidget(icon_label)
        
        # Content
        content_layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(self.notification.title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        content_layout.addWidget(title_label)
        
        # Message
        message_label = QLabel(self.notification.message)
        message_label.setFont(QFont("Segoe UI", 9))
        message_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)
        
        frame_layout.addLayout(content_layout)
        
        # Close button
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 10px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        """)
        close_button.clicked.connect(self.close)
        frame_layout.addWidget(close_button)
        
        layout.addWidget(self.frame)
        
    def get_style_for_type(self) -> str:
        """Get stylesheet based on notification type"""
        styles = {
            NotificationType.INFO: """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #3498db, stop:1 #2980b9);
                    border-radius: 10px;
                    border: 1px solid #2980b9;
                }
            """,
            NotificationType.SUCCESS: """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #27ae60, stop:1 #229954);
                    border-radius: 10px;
                    border: 1px solid #229954;
                }
            """,
            NotificationType.WARNING: """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #f39c12, stop:1 #e67e22);
                    border-radius: 10px;
                    border: 1px solid #e67e22;
                }
            """,
            NotificationType.ERROR: """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #e74c3c, stop:1 #c0392b);
                    border-radius: 10px;
                    border: 1px solid #c0392b;
                }
            """,
            NotificationType.CRITICAL: """
                QFrame {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #8e44ad, stop:1 #732d91);
                    border-radius: 10px;
                    border: 1px solid #732d91;
                }
            """
        }
        return styles.get(self.notification.type, styles[NotificationType.INFO])
        
    def get_icon_for_type(self) -> str:
        """Get icon based on notification type"""
        icons = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.CRITICAL: "🚨"
        }
        return icons.get(self.notification.type, "ℹ️")
        
    def setup_animation(self):
        """Setup slide-in animation"""
        # Start position (off-screen right)
        screen = QApplication.primaryScreen().geometry()
        start_pos = QRect(screen.width(), 100, self.width(), self.height())
        end_pos = QRect(screen.width() - self.width() - 20, 100, self.width(), self.height())
        
        self.setGeometry(start_pos)
        
        # Slide-in animation
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(300)
        self.slide_animation.setStartValue(start_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Auto-hide timer
        self.hide_timer = QTimer()
        self.hide_timer.timeout.connect(self.hide_notification)
        
    def show_notification(self):
        """Show the toast notification"""
        self.show()
        self.slide_animation.start()
        
        # Auto-hide after duration based on priority
        duration = {
            NotificationPriority.LOW: 3000,
            NotificationPriority.MEDIUM: 5000,
            NotificationPriority.HIGH: 8000,
            NotificationPriority.CRITICAL: 0  # Don't auto-hide critical notifications
        }
        
        hide_duration = duration.get(self.notification.priority, 5000)
        if hide_duration > 0:
            self.hide_timer.start(hide_duration)
            
    def hide_notification(self):
        """Hide the toast notification with animation"""
        screen = QApplication.primaryScreen().geometry()
        current_pos = self.geometry()
        end_pos = QRect(screen.width(), current_pos.y(), self.width(), self.height())
        
        # Slide-out animation
        self.slide_out_animation = QPropertyAnimation(self, b"geometry")
        self.slide_out_animation.setDuration(300)
        self.slide_out_animation.setStartValue(current_pos)
        self.slide_out_animation.setEndValue(end_pos)
        self.slide_out_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.slide_out_animation.finished.connect(self.close)
        self.slide_out_animation.start()
        
    def mousePressEvent(self, event):
        """Handle mouse click to dismiss notification"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_notification()

class NotificationCenter(QWidget):
    """Notification center widget for managing notifications"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notifications = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the notification center UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        
        header = QLabel("🔔 Notification Center")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Clear all button
        clear_button = QPushButton("🗑️ Clear All")
        clear_button.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        clear_button.clicked.connect(self.clear_all_notifications)
        header_layout.addWidget(clear_button)
        
        layout.addLayout(header_layout)
        
        # Notification list
        self.notification_list = QListWidget()
        self.notification_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                alternate-background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                min-height: 60px;
            }
            QListWidget::item:hover {
                background: #e3f2fd;
            }
            QListWidget::item:selected {
                background: #2196f3;
                color: white;
            }
        """)
        self.notification_list.itemClicked.connect(self.on_notification_clicked)
        layout.addWidget(self.notification_list)
        
    def add_notification(self, notification: Notification):
        """Add a notification to the center"""
        self.notifications.insert(0, notification)  # Add to beginning
        self.refresh_notification_list()
        
        # Limit to 100 notifications
        if len(self.notifications) > 100:
            self.notifications = self.notifications[:100]
            
    def refresh_notification_list(self):
        """Refresh the notification list display"""
        self.notification_list.clear()
        
        for notification in self.notifications:
            item_widget = self.create_notification_item(notification)
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, notification)
            
            self.notification_list.addItem(item)
            self.notification_list.setItemWidget(item, item_widget)
            
    def create_notification_item(self, notification: Notification) -> QWidget:
        """Create a notification item widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Icon
        icon_label = QLabel(self.get_icon_for_type(notification.type))
        icon_label.setFont(QFont("Segoe UI", 16))
        icon_label.setFixedSize(30, 30)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Content
        content_layout = QVBoxLayout()
        
        # Title and timestamp
        title_layout = QHBoxLayout()
        
        title_label = QLabel(notification.title)
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        time_label = QLabel(notification.timestamp.strftime("%H:%M"))
        time_label.setFont(QFont("Segoe UI", 8))
        time_label.setStyleSheet("color: #7f8c8d;")
        title_layout.addWidget(time_label)
        
        content_layout.addLayout(title_layout)
        
        # Message
        message_label = QLabel(notification.message)
        message_label.setFont(QFont("Segoe UI", 9))
        message_label.setStyleSheet("color: #555;")
        message_label.setWordWrap(True)
        content_layout.addWidget(message_label)
        
        layout.addLayout(content_layout)
        
        # Priority indicator
        priority_colors = {
            NotificationPriority.LOW: "#95a5a6",
            NotificationPriority.MEDIUM: "#3498db",
            NotificationPriority.HIGH: "#f39c12",
            NotificationPriority.CRITICAL: "#e74c3c"
        }
        
        priority_indicator = QFrame()
        priority_indicator.setFixedSize(4, 40)
        priority_indicator.setStyleSheet(f"""
            QFrame {{
                background: {priority_colors.get(notification.priority, '#95a5a6')};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(priority_indicator)
        
        return widget
        
    def get_icon_for_type(self, notification_type: NotificationType) -> str:
        """Get icon for notification type"""
        icons = {
            NotificationType.INFO: "ℹ️",
            NotificationType.SUCCESS: "✅",
            NotificationType.WARNING: "⚠️",
            NotificationType.ERROR: "❌",
            NotificationType.CRITICAL: "🚨"
        }
        return icons.get(notification_type, "ℹ️")
        
    def on_notification_clicked(self, item):
        """Handle notification click"""
        notification = item.data(Qt.ItemDataRole.UserRole)
        if notification:
            notification.read = True
            # Could show detailed notification dialog here
            
    def clear_all_notifications(self):
        """Clear all notifications"""
        reply = QMessageBox.question(
            self, "Clear Notifications",
            "Are you sure you want to clear all notifications?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.notifications.clear()
            self.refresh_notification_list()

class NotificationRulesWidget(QWidget):
    """Widget for managing notification rules and filters"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the notification rules UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("📋 Notification Rules")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)

        # Rules configuration
        rules_group = QGroupBox("Alert Rules")
        rules_layout = QFormLayout(rules_group)

        # New post notifications
        self.notify_new_posts = QCheckBox("Notify on new posts")
        self.notify_new_posts.setChecked(True)
        rules_layout.addRow("", self.notify_new_posts)

        # New follower notifications
        self.notify_new_followers = QCheckBox("Notify on new followers")
        self.notify_new_followers.setChecked(True)
        rules_layout.addRow("", self.notify_new_followers)

        # Follower threshold
        self.follower_threshold = QSpinBox()
        self.follower_threshold.setRange(1, 10000)
        self.follower_threshold.setValue(100)
        rules_layout.addRow("Follower change threshold:", self.follower_threshold)

        # Story notifications
        self.notify_stories = QCheckBox("Notify on new stories")
        self.notify_stories.setChecked(True)
        rules_layout.addRow("", self.notify_stories)

        # Bio change notifications
        self.notify_bio_changes = QCheckBox("Notify on bio changes")
        self.notify_bio_changes.setChecked(True)
        rules_layout.addRow("", self.notify_bio_changes)

        layout.addWidget(rules_group)

        # Delivery settings
        delivery_group = QGroupBox("Delivery Settings")
        delivery_layout = QFormLayout(delivery_group)

        # Toast notifications
        self.enable_toast = QCheckBox("Show toast notifications")
        self.enable_toast.setChecked(True)
        delivery_layout.addRow("", self.enable_toast)

        # System tray notifications
        self.enable_tray = QCheckBox("Show system tray notifications")
        self.enable_tray.setChecked(True)
        delivery_layout.addRow("", self.enable_tray)

        # Sound notifications
        self.enable_sound = QCheckBox("Play notification sounds")
        self.enable_sound.setChecked(False)
        delivery_layout.addRow("", self.enable_sound)

        # Do not disturb hours
        self.enable_dnd = QCheckBox("Enable Do Not Disturb hours")
        delivery_layout.addRow("", self.enable_dnd)

        # DND time range
        dnd_layout = QHBoxLayout()
        self.dnd_start = QComboBox()
        self.dnd_start.addItems([f"{i:02d}:00" for i in range(24)])
        self.dnd_start.setCurrentText("22:00")
        dnd_layout.addWidget(QLabel("From:"))
        dnd_layout.addWidget(self.dnd_start)

        self.dnd_end = QComboBox()
        self.dnd_end.addItems([f"{i:02d}:00" for i in range(24)])
        self.dnd_end.setCurrentText("08:00")
        dnd_layout.addWidget(QLabel("To:"))
        dnd_layout.addWidget(self.dnd_end)

        delivery_layout.addRow("DND Hours:", dnd_layout)

        layout.addWidget(delivery_group)

        # Save button
        save_button = QPushButton("💾 Save Rules")
        save_button.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #229954;
            }
        """)
        save_button.clicked.connect(self.save_rules)
        layout.addWidget(save_button)

        layout.addStretch()

    def save_rules(self):
        """Save notification rules"""
        QMessageBox.information(self, "Success", "Notification rules saved successfully!")

class NotificationManager(QWidget):
    """Main notification manager that coordinates all notification functionality"""

    notification_created = pyqtSignal(Notification)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_toasts = []
        self.notification_center = NotificationCenter()
        self.setup_ui()

        # Connect to notification center
        self.notification_created.connect(self.handle_new_notification)

    def setup_ui(self):
        """Setup the notification manager UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("🔔 Notification Management")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Tabs for different notification aspects
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #ddd;
                padding: 12px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background: #e9ecef;
            }
        """)

        # Add tabs
        self.tabs.addTab(self.notification_center, "📋 Notification Center")

        self.rules_widget = NotificationRulesWidget()
        self.tabs.addTab(self.rules_widget, "⚙️ Rules & Settings")

        # Test notifications tab
        test_widget = self.create_test_widget()
        self.tabs.addTab(test_widget, "🧪 Test Notifications")

        layout.addWidget(self.tabs)

    def create_test_widget(self) -> QWidget:
        """Create test notifications widget"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("🧪 Test Notifications")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        layout.addWidget(header)

        # Test buttons
        button_layout = QGridLayout()

        test_buttons = [
            ("Info", NotificationType.INFO, "Test info notification"),
            ("Success", NotificationType.SUCCESS, "Test success notification"),
            ("Warning", NotificationType.WARNING, "Test warning notification"),
            ("Error", NotificationType.ERROR, "Test error notification"),
            ("Critical", NotificationType.CRITICAL, "Test critical notification")
        ]

        for i, (text, ntype, message) in enumerate(test_buttons):
            button = QPushButton(f"Test {text}")
            button.setMinimumHeight(40)
            button.clicked.connect(lambda checked, t=ntype, m=message: self.create_test_notification(t, m))
            button_layout.addWidget(button, i // 2, i % 2)

        layout.addLayout(button_layout)

        # Custom notification test
        custom_group = QGroupBox("Custom Notification Test")
        custom_layout = QFormLayout(custom_group)

        self.test_title = QLineEdit("Test Notification")
        custom_layout.addRow("Title:", self.test_title)

        self.test_message = QLineEdit("This is a test notification message")
        custom_layout.addRow("Message:", self.test_message)

        self.test_type = QComboBox()
        self.test_type.addItems(["Info", "Success", "Warning", "Error", "Critical"])
        custom_layout.addRow("Type:", self.test_type)

        self.test_priority = QComboBox()
        self.test_priority.addItems(["Low", "Medium", "High", "Critical"])
        self.test_priority.setCurrentText("Medium")
        custom_layout.addRow("Priority:", self.test_priority)

        send_custom_button = QPushButton("Send Custom Notification")
        send_custom_button.clicked.connect(self.send_custom_test_notification)
        custom_layout.addRow("", send_custom_button)

        layout.addWidget(custom_group)
        layout.addStretch()

        return widget

    def create_test_notification(self, notification_type: NotificationType, message: str):
        """Create a test notification"""
        notification = Notification(
            title=f"{notification_type.value.title()} Test",
            message=message,
            notification_type=notification_type,
            priority=NotificationPriority.MEDIUM
        )
        self.show_notification(notification)

    def send_custom_test_notification(self):
        """Send custom test notification"""
        type_map = {
            "Info": NotificationType.INFO,
            "Success": NotificationType.SUCCESS,
            "Warning": NotificationType.WARNING,
            "Error": NotificationType.ERROR,
            "Critical": NotificationType.CRITICAL
        }

        priority_map = {
            "Low": NotificationPriority.LOW,
            "Medium": NotificationPriority.MEDIUM,
            "High": NotificationPriority.HIGH,
            "Critical": NotificationPriority.CRITICAL
        }

        notification = Notification(
            title=self.test_title.text(),
            message=self.test_message.text(),
            notification_type=type_map[self.test_type.currentText()],
            priority=priority_map[self.test_priority.currentText()]
        )
        self.show_notification(notification)

    def show_notification(self, notification: Notification):
        """Show a notification using all enabled methods"""
        # Add to notification center
        self.notification_center.add_notification(notification)

        # Show toast notification
        if self.should_show_toast():
            toast = ToastNotification(notification)
            toast.show_notification()
            self.active_toasts.append(toast)

            # Clean up finished toasts
            self.cleanup_finished_toasts()

        # Show system tray notification
        if self.should_show_tray():
            self.show_system_tray_notification(notification)

        # Emit signal
        self.notification_created.emit(notification)

    def should_show_toast(self) -> bool:
        """Check if toast notifications should be shown"""
        # Would check settings and DND hours
        return True

    def should_show_tray(self) -> bool:
        """Check if system tray notifications should be shown"""
        # Would check settings and DND hours
        return True

    def show_system_tray_notification(self, notification: Notification):
        """Show system tray notification"""
        # This would integrate with the main application's system tray
        print(f"System Tray: {notification.title} - {notification.message}")

    def cleanup_finished_toasts(self):
        """Clean up finished toast notifications"""
        self.active_toasts = [toast for toast in self.active_toasts if toast.isVisible()]

    def handle_new_notification(self, notification: Notification):
        """Handle new notification signal"""
        logger.info(f"New notification: {notification.title}")

def create_notification_system() -> NotificationManager:
    """Factory function to create notification system"""
    return NotificationManager()
