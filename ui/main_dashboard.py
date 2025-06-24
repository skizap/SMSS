#!/usr/bin/env python3
"""
Social Media Surveillance System - Main Dashboard
PyQt6-based main dashboard interface for the surveillance system.
Provides real-time monitoring, analytics, and system management.
"""

import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QMenuBar, QStatusBar, QToolBar, QLabel, QPushButton,
    QFrame, QSplitter, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QSystemTrayIcon, QMenu, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QGroupBox, QGridLayout, QScrollArea, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPoint, QRect,
    QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QFont, QColor, QPalette, QAction,
    QLinearGradient, QPainter, QPen, QBrush
)

# Import project modules
from core.config import config
from core.data_manager import DataManager
from models.instagram_models import SurveillanceTarget, Post, Follower
from analysis.deepseek_analyzer import DeepSeekAnalyzer

logger = logging.getLogger(__name__)

class ModernButton(QPushButton):
    """Custom modern-styled button with hover effects"""
    
    def __init__(self, text: str, icon_path: str = None, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self.setFont(QFont("Segoe UI", 10))
        
        if icon_path and Path(icon_path).exists():
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(20, 20))
        
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a90e2, stop:1 #357abd);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5ba0f2, stop:1 #4a90e2);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #357abd, stop:1 #2968a3);
            }
            QPushButton:disabled {
                background: #cccccc;
                color: #666666;
            }
        """)

class StatusIndicator(QWidget):
    """Custom status indicator widget with colored dot and text"""
    
    def __init__(self, status: str = "offline", text: str = "", parent=None):
        super().__init__(parent)
        self.status = status
        self.text = text
        self.setFixedSize(120, 30)
        
    def set_status(self, status: str, text: str = ""):
        """Update status and text"""
        self.status = status
        self.text = text
        self.update()
        
    def paintEvent(self, event):
        """Custom paint event for status indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Status colors
        colors = {
            "online": QColor(46, 204, 113),    # Green
            "offline": QColor(231, 76, 60),    # Red
            "warning": QColor(241, 196, 15),   # Yellow
            "processing": QColor(52, 152, 219) # Blue
        }
        
        # Draw status dot
        color = colors.get(self.status, colors["offline"])
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(color.darker(120), 2))
        painter.drawEllipse(5, 10, 12, 12)
        
        # Draw text
        painter.setPen(QPen(QColor(60, 60, 60)))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(25, 20, self.text)

class ActivityFeedWidget(QWidget):
    """Real-time activity feed widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.activities = []
        
    def setup_ui(self):
        """Setup the activity feed UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🔴 Live Activity Feed")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Activity list
        self.activity_list = QListWidget()
        self.activity_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                alternate-background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background: #e3f2fd;
            }
        """)
        layout.addWidget(self.activity_list)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_activities)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def add_activity(self, activity_type: str, message: str, timestamp: datetime = None):
        """Add new activity to the feed"""
        if timestamp is None:
            timestamp = datetime.now()
            
        # Activity icons
        icons = {
            "new_post": "📝",
            "new_follower": "👤",
            "story_posted": "📸",
            "bio_changed": "✏️",
            "engagement_spike": "📈",
            "error": "⚠️",
            "system": "⚙️"
        }
        
        icon = icons.get(activity_type, "📋")
        time_str = timestamp.strftime("%H:%M:%S")
        
        item_text = f"{icon} {time_str} - {message}"
        item = QListWidgetItem(item_text)
        
        # Color coding based on activity type
        if activity_type == "error":
            item.setBackground(QColor(255, 235, 235))
        elif activity_type in ["new_post", "new_follower"]:
            item.setBackground(QColor(235, 255, 235))
        elif activity_type == "engagement_spike":
            item.setBackground(QColor(235, 245, 255))
            
        self.activity_list.insertItem(0, item)
        
        # Keep only last 100 activities
        if self.activity_list.count() > 100:
            self.activity_list.takeItem(100)
            
    def refresh_activities(self):
        """Refresh activities from database"""
        try:
            # This would typically fetch from database
            # For now, we'll add a system heartbeat
            self.add_activity("system", "System heartbeat - All services operational")
        except Exception as e:
            logger.error(f"Error refreshing activities: {e}")
            self.add_activity("error", f"Failed to refresh activities: {str(e)}")

class SystemStatsWidget(QWidget):
    """System statistics and health monitoring widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(10000)  # Update every 10 seconds
        
    def setup_ui(self):
        """Setup the system stats UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("📊 System Status")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Stats container
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)
        
        # Status indicators
        self.browser_status = StatusIndicator("offline", "Browser: Disconnected")
        self.database_status = StatusIndicator("offline", "Database: Offline")
        self.ai_status = StatusIndicator("offline", "AI Analysis: Inactive")
        
        stats_layout.addWidget(self.browser_status)
        stats_layout.addWidget(self.database_status)
        stats_layout.addWidget(self.ai_status)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #ddd;")
        stats_layout.addWidget(separator)
        
        # Performance metrics
        self.memory_label = QLabel("Memory Usage: --")
        self.cpu_label = QLabel("CPU Usage: --")
        self.uptime_label = QLabel("Uptime: --")
        
        for label in [self.memory_label, self.cpu_label, self.uptime_label]:
            label.setFont(QFont("Segoe UI", 9))
            label.setStyleSheet("color: #555; margin: 2px 0;")
            stats_layout.addWidget(label)
            
        layout.addWidget(stats_frame)
        layout.addStretch()
        
    def update_stats(self):
        """Update system statistics"""
        try:
            import psutil
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.memory_label.setText(f"Memory Usage: {memory.percent:.1f}%")
            
            # CPU usage
            cpu = psutil.cpu_percent(interval=1)
            self.cpu_label.setText(f"CPU Usage: {cpu:.1f}%")
            
            # Update status indicators (would be based on actual system checks)
            self.browser_status.set_status("online", "Browser: Connected")
            self.database_status.set_status("online", "Database: Operational")
            self.ai_status.set_status("processing", "AI Analysis: Active")
            
        except ImportError:
            # psutil not available
            self.memory_label.setText("Memory Usage: N/A")
            self.cpu_label.setText("CPU Usage: N/A")
        except Exception as e:
            logger.error(f"Error updating stats: {e}")

class TargetListWidget(QWidget):
    """Widget for displaying and managing surveillance targets"""

    target_selected = pyqtSignal(int)  # Emits target ID when selected

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.data_manager = DataManager()
        self.refresh_targets()

    def setup_ui(self):
        """Setup the target list UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with add button
        header_layout = QHBoxLayout()
        header = QLabel("🎯 Surveillance Targets")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        add_button = ModernButton("+ Add Target")
        add_button.setMaximumWidth(120)
        add_button.clicked.connect(self.add_target)
        header_layout.addWidget(add_button)

        layout.addLayout(header_layout)

        # Target list
        self.target_list = QListWidget()
        self.target_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                alternate-background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 12px;
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
        self.target_list.itemClicked.connect(self.on_target_selected)
        layout.addWidget(self.target_list)

        # Refresh button
        refresh_button = ModernButton("🔄 Refresh")
        refresh_button.clicked.connect(self.refresh_targets)
        layout.addWidget(refresh_button)

    def refresh_targets(self):
        """Refresh the target list from database"""
        try:
            self.target_list.clear()

            # Get targets from database
            targets = self.data_manager.get_all_targets()

            for target in targets:
                item_widget = self.create_target_item(target)
                item = QListWidgetItem()
                item.setSizeHint(item_widget.sizeHint())
                item.setData(Qt.ItemDataRole.UserRole, target.id)

                self.target_list.addItem(item)
                self.target_list.setItemWidget(item, item_widget)

        except Exception as e:
            logger.error(f"Error refreshing targets: {e}")

    def create_target_item(self, target) -> QWidget:
        """Create a custom widget for target list item"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        # Profile picture placeholder
        profile_pic = QLabel("👤")
        profile_pic.setFixedSize(40, 40)
        profile_pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        profile_pic.setStyleSheet("""
            QLabel {
                background: #f0f0f0;
                border-radius: 20px;
                font-size: 20px;
            }
        """)
        layout.addWidget(profile_pic)

        # Target info
        info_layout = QVBoxLayout()

        username_label = QLabel(f"@{target.instagram_username}")
        username_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        username_label.setStyleSheet("color: #2c3e50;")
        info_layout.addWidget(username_label)

        stats_text = f"👥 {target.follower_count or 0} | 📝 {target.post_count or 0} posts"
        stats_label = QLabel(stats_text)
        stats_label.setFont(QFont("Segoe UI", 8))
        stats_label.setStyleSheet("color: #7f8c8d;")
        info_layout.addWidget(stats_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Status indicator
        status = "online" if target.status == "active" else "offline"
        status_indicator = StatusIndicator(status, target.status.title())
        layout.addWidget(status_indicator)

        return widget

    def on_target_selected(self, item):
        """Handle target selection"""
        target_id = item.data(Qt.ItemDataRole.UserRole)
        if target_id:
            self.target_selected.emit(target_id)

    def add_target(self):
        """Show add target dialog"""
        dialog = AddTargetDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_targets()

class AddTargetDialog(QDialog):
    """Dialog for adding new surveillance targets"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Surveillance Target")
        self.setModal(True)
        self.setFixedSize(400, 300)
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)

        # Form
        form_layout = QFormLayout()

        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter Instagram username (without @)")
        form_layout.addRow("Username:", self.username_edit)

        self.display_name_edit = QLineEdit()
        self.display_name_edit.setPlaceholderText("Optional display name")
        form_layout.addRow("Display Name:", self.display_name_edit)

        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High", "Critical"])
        self.priority_combo.setCurrentText("Medium")
        form_layout.addRow("Priority:", self.priority_combo)

        self.notifications_check = QCheckBox("Enable notifications")
        self.notifications_check.setChecked(True)
        form_layout.addRow("", self.notifications_check)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        add_button = ModernButton("Add Target")
        add_button.clicked.connect(self.accept_target)
        button_layout.addWidget(add_button)

        layout.addLayout(button_layout)

    def accept_target(self):
        """Accept and add the target"""
        username = self.username_edit.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Please enter a username")
            return

        try:
            data_manager = DataManager()
            target_id = data_manager.add_target(
                instagram_username=username,
                display_name=self.display_name_edit.text().strip() or None,
                priority=self.priority_combo.currentText().lower(),
                notifications_enabled=self.notifications_check.isChecked()
            )

            if target_id:
                QMessageBox.information(self, "Success", f"Target @{username} added successfully!")
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Failed to add target")

        except Exception as e:
            logger.error(f"Error adding target: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add target: {str(e)}")

class MainDashboard(QMainWindow):
    """Main dashboard window for the surveillance system"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Media Surveillance System - Dashboard")
        self.setMinimumSize(1200, 800)
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_system_tray()
        self.center_window()

        # Initialize data manager
        self.data_manager = DataManager()

        # Start background updates
        self.start_background_updates()

    def setup_ui(self):
        """Setup the main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left sidebar
        left_sidebar = self.create_left_sidebar()
        main_layout.addWidget(left_sidebar, 1)

        # Main content area
        main_content = self.create_main_content()
        main_layout.addWidget(main_content, 3)

        # Right sidebar
        right_sidebar = self.create_right_sidebar()
        main_layout.addWidget(right_sidebar, 1)

        # Apply modern styling
        self.setStyleSheet("""
            QMainWindow {
                background: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)

    def create_left_sidebar(self) -> QWidget:
        """Create the left sidebar with targets and controls"""
        sidebar = QFrame()
        sidebar.setFrameStyle(QFrame.Shape.StyledPanel)
        sidebar.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)

        # Target list
        self.target_list_widget = TargetListWidget()
        self.target_list_widget.target_selected.connect(self.on_target_selected)
        layout.addWidget(self.target_list_widget)

        return sidebar

    def create_main_content(self) -> QWidget:
        """Create the main content area with tabs"""
        content_frame = QFrame()
        content_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        content_frame.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
        """)

        layout = QVBoxLayout(content_frame)
        layout.setContentsMargins(10, 10, 10, 10)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f8f9fa;
                border: 1px solid #ddd;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background: #e9ecef;
            }
        """)

        # Add tabs (will be implemented in separate files)
        self.add_dashboard_tabs()

        layout.addWidget(self.tab_widget)
        return content_frame

    def create_right_sidebar(self) -> QWidget:
        """Create the right sidebar with activity feed and stats"""
        sidebar = QFrame()
        sidebar.setFrameStyle(QFrame.Shape.StyledPanel)
        sidebar.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)

        # Activity feed
        self.activity_feed = ActivityFeedWidget()
        layout.addWidget(self.activity_feed, 2)

        # System stats
        self.system_stats = SystemStatsWidget()
        layout.addWidget(self.system_stats, 1)

        return sidebar

    def add_dashboard_tabs(self):
        """Add tabs to the main content area"""
        # Overview tab
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)

        welcome_label = QLabel("📊 Dashboard Overview")
        welcome_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: #2c3e50; margin: 20px;")
        overview_layout.addWidget(welcome_label)

        # Quick stats
        stats_layout = QGridLayout()

        # Create stat cards
        stat_cards = [
            ("Active Targets", "0", "🎯"),
            ("Total Posts", "0", "📝"),
            ("New Followers", "0", "👤"),
            ("Alerts Today", "0", "🔔")
        ]

        for i, (title, value, icon) in enumerate(stat_cards):
            card = self.create_stat_card(title, value, icon)
            stats_layout.addWidget(card, i // 2, i % 2)

        overview_layout.addLayout(stats_layout)
        overview_layout.addStretch()

        self.tab_widget.addTab(overview_widget, "📊 Overview")

        # Placeholder tabs for other panels
        self.tab_widget.addTab(QLabel("Surveillance panel will be implemented here"), "🔍 Surveillance")
        self.tab_widget.addTab(QLabel("Analytics panel will be implemented here"), "📈 Analytics")
        self.tab_widget.addTab(QLabel("Settings panel will be implemented here"), "⚙️ Settings")

    def create_stat_card(self, title: str, value: str, icon: str) -> QWidget:
        """Create a statistics card widget"""
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 1px solid #e9ecef;
                border-radius: 12px;
                padding: 15px;
            }
            QFrame:hover {
                border: 1px solid #4a90e2;
                box-shadow: 0 2px 8px rgba(74, 144, 226, 0.2);
            }
        """)
        card.setMinimumHeight(120)

        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 24))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(value_label)

        # Title
        title_label = QLabel(title)
        title_label.setFont(QFont("Segoe UI", 10))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(title_label)

        return card

    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_target_action = QAction("&New Target", self)
        new_target_action.setShortcut("Ctrl+N")
        new_target_action.triggered.connect(self.add_new_target)
        file_menu.addAction(new_target_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        view_menu.addAction(refresh_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Tools")

        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup the status bar"""
        self.status_bar = self.statusBar()

        # Status message
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # Connection status
        self.connection_status = QLabel("🔴 Disconnected")
        self.status_bar.addPermanentWidget(self.connection_status)

    def setup_system_tray(self):
        """Setup system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)

            # Create tray menu
            tray_menu = QMenu()

            show_action = tray_menu.addAction("Show Dashboard")
            show_action.triggered.connect(self.show)

            tray_menu.addSeparator()

            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(QApplication.instance().quit)

            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)

            # Set icon (would use actual icon file)
            self.tray_icon.setToolTip("Social Media Surveillance System")
            self.tray_icon.show()

    def center_window(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen().geometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def start_background_updates(self):
        """Start background update timers"""
        # Update dashboard stats every 30 seconds
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_dashboard_stats)
        self.update_timer.start(30000)

        # Initial update
        self.update_dashboard_stats()

    def update_dashboard_stats(self):
        """Update dashboard statistics"""
        try:
            # Get current stats from database
            stats = self.data_manager.get_dashboard_stats()

            # Update status bar
            self.status_label.setText(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
            self.connection_status.setText("🟢 Connected")

            # Add activity
            self.activity_feed.add_activity("system", "Dashboard stats updated")

        except Exception as e:
            logger.error(f"Error updating dashboard stats: {e}")
            self.connection_status.setText("🔴 Error")
            self.activity_feed.add_activity("error", f"Failed to update stats: {str(e)}")

    def on_target_selected(self, target_id: int):
        """Handle target selection"""
        try:
            # Switch to surveillance tab
            self.tab_widget.setCurrentIndex(1)

            # Update activity feed
            self.activity_feed.add_activity("system", f"Selected target ID: {target_id}")

        except Exception as e:
            logger.error(f"Error selecting target: {e}")

    def add_new_target(self):
        """Show add new target dialog"""
        self.target_list_widget.add_target()

    def refresh_all(self):
        """Refresh all data"""
        try:
            self.target_list_widget.refresh_targets()
            self.update_dashboard_stats()
            self.activity_feed.add_activity("system", "All data refreshed")

        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to refresh data: {str(e)}")

    def show_settings(self):
        """Show settings dialog"""
        QMessageBox.information(self, "Settings", "Settings panel will be implemented in the next phase")

    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>Social Media Surveillance System</h2>
        <p><b>Version:</b> 1.0.0 (Phase 5)</p>
        <p><b>Description:</b> AI-powered Instagram monitoring and surveillance system</p>
        <p><b>Features:</b></p>
        <ul>
            <li>Real-time Instagram monitoring</li>
            <li>AI-powered content analysis</li>
            <li>Advanced analytics and reporting</li>
            <li>Stealth browser automation</li>
        </ul>
        <p><b>Developed by:</b> Social Media Surveillance Team</p>
        """

        QMessageBox.about(self, "About", about_text)

    def tray_icon_activated(self, reason):
        """Handle system tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def closeEvent(self, event):
        """Handle window close event"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            # Minimize to tray instead of closing
            self.hide()
            event.ignore()
        else:
            # Actually close the application
            event.accept()

    def show_notification(self, title: str, message: str, icon_type: str = "info"):
        """Show system notification"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            icon = QSystemTrayIcon.MessageIcon.Information
            if icon_type == "warning":
                icon = QSystemTrayIcon.MessageIcon.Warning
            elif icon_type == "critical":
                icon = QSystemTrayIcon.MessageIcon.Critical

            self.tray_icon.showMessage(title, message, icon, 5000)

def main():
    """Main entry point for the dashboard"""
    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Social Media Surveillance System")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SMSS Team")

    # Set application icon (would use actual icon file)
    # app.setWindowIcon(QIcon("icons/app_icon.png"))

    # Create and show main dashboard
    dashboard = MainDashboard()
    dashboard.show()

    # Show welcome notification
    dashboard.show_notification(
        "SMSS Dashboard",
        "Social Media Surveillance System is now running",
        "info"
    )

    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
