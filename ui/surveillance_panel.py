#!/usr/bin/env python3
"""
Social Media Surveillance System - Surveillance Panel
Advanced surveillance panel for real-time Instagram monitoring and control.
Provides target management, monitoring controls, and live data visualization.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QGroupBox, QScrollArea, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox, QDialog, QLineEdit, QDateTimeEdit
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QDateTime
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon
)

# Import project modules
from core.data_manager import DataManager
from core.browser_engine import InstagramBrowser
from models.instagram_models import SurveillanceTarget, Post, Follower
from scrapers.instagram_profile_scraper import InstagramProfileScraper

logger = logging.getLogger(__name__)

class MonitoringControlWidget(QWidget):
    """Widget for surveillance monitoring controls"""
    
    monitoring_started = pyqtSignal(int)  # target_id
    monitoring_stopped = pyqtSignal(int)  # target_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_target_id = None
        self.is_monitoring = False
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the monitoring controls UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🔍 Monitoring Controls")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ Start Monitoring")
        self.start_button.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2ecc71;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.start_button.clicked.connect(self.start_monitoring)
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ Stop Monitoring")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
            QPushButton:disabled {
                background: #95a5a6;
            }
        """)
        self.stop_button.clicked.connect(self.stop_monitoring)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        # Monitoring settings
        settings_group = QGroupBox("Monitoring Settings")
        settings_layout = QFormLayout(settings_group)
        
        # Refresh interval
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(30, 3600)  # 30 seconds to 1 hour
        self.refresh_interval.setValue(300)  # 5 minutes default
        self.refresh_interval.setSuffix(" seconds")
        settings_layout.addRow("Refresh Interval:", self.refresh_interval)
        
        # Monitor posts
        self.monitor_posts = QCheckBox("Monitor new posts")
        self.monitor_posts.setChecked(True)
        settings_layout.addRow("", self.monitor_posts)
        
        # Monitor followers
        self.monitor_followers = QCheckBox("Monitor followers")
        self.monitor_followers.setChecked(True)
        settings_layout.addRow("", self.monitor_followers)
        
        # Monitor stories
        self.monitor_stories = QCheckBox("Monitor stories")
        self.monitor_stories.setChecked(True)
        settings_layout.addRow("", self.monitor_stories)
        
        layout.addWidget(settings_group)
        
        # Status display
        self.status_label = QLabel("Status: Ready")
        self.status_label.setStyleSheet("""
            QLabel {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
    def set_target(self, target_id: int):
        """Set the current target for monitoring"""
        self.current_target_id = target_id
        self.start_button.setEnabled(True and not self.is_monitoring)
        self.status_label.setText(f"Status: Target {target_id} selected")
        
    def start_monitoring(self):
        """Start monitoring the current target"""
        if self.current_target_id:
            self.is_monitoring = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.status_label.setText("Status: Monitoring active")
            self.monitoring_started.emit(self.current_target_id)
            
    def stop_monitoring(self):
        """Stop monitoring the current target"""
        if self.current_target_id:
            self.is_monitoring = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.status_label.setText("Status: Monitoring stopped")
            self.monitoring_stopped.emit(self.current_target_id)

class RecentActivityWidget(QWidget):
    """Widget displaying recent surveillance activity"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_manager = DataManager()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the recent activity UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("📋 Recent Activity")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        refresh_button = QPushButton("🔄")
        refresh_button.setFixedSize(30, 30)
        refresh_button.setToolTip("Refresh activity")
        refresh_button.clicked.connect(self.refresh_activity)
        header_layout.addWidget(refresh_button)
        
        layout.addLayout(header_layout)
        
        # Activity table
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(4)
        self.activity_table.setHorizontalHeaderLabels([
            "Time", "Target", "Activity", "Details"
        ])
        
        # Configure table
        header = self.activity_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.activity_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                gridline-color: #eee;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QTableWidget::item:selected {
                background: #e3f2fd;
            }
            QHeaderView::section {
                background: #f8f9fa;
                border: none;
                border-bottom: 1px solid #ddd;
                padding: 8px;
                font-weight: bold;
            }
        """)
        
        layout.addWidget(self.activity_table)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_activity)
        self.refresh_timer.start(60000)  # Refresh every minute
        
        # Initial load
        self.refresh_activity()
        
    def refresh_activity(self):
        """Refresh the activity table"""
        try:
            # Get recent activities from database
            activities = self.data_manager.get_recent_activities(limit=50)
            
            self.activity_table.setRowCount(len(activities))
            
            for row, activity in enumerate(activities):
                # Time
                time_item = QTableWidgetItem(activity.get('timestamp', '').strftime('%H:%M:%S'))
                self.activity_table.setItem(row, 0, time_item)
                
                # Target
                target_item = QTableWidgetItem(activity.get('target_username', 'Unknown'))
                self.activity_table.setItem(row, 1, target_item)
                
                # Activity type
                activity_item = QTableWidgetItem(activity.get('activity_type', 'Unknown'))
                self.activity_table.setItem(row, 2, activity_item)
                
                # Details
                details_item = QTableWidgetItem(activity.get('details', ''))
                self.activity_table.setItem(row, 3, details_item)
                
        except Exception as e:
            logger.error(f"Error refreshing activity: {e}")

class TargetDetailsWidget(QWidget):
    """Widget displaying detailed information about selected target"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_target = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the target details UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        self.header_label = QLabel("👤 Target Details")
        self.header_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.header_label.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(self.header_label)
        
        # Scroll area for details
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
            }
        """)
        
        # Details widget
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        
        # Placeholder content
        placeholder = QLabel("Select a target to view details")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #7f8c8d; font-style: italic; margin: 50px;")
        self.details_layout.addWidget(placeholder)
        
        scroll_area.setWidget(self.details_widget)
        layout.addWidget(scroll_area)
        
    def update_target_details(self, target_id: int):
        """Update the target details display"""
        try:
            data_manager = DataManager()
            target = data_manager.get_target_by_id(target_id)
            
            if target:
                self.current_target = target
                self.header_label.setText(f"👤 @{target.instagram_username}")
                self.populate_details(target)
            else:
                self.show_no_target()
                
        except Exception as e:
            logger.error(f"Error updating target details: {e}")
            self.show_error(str(e))
            
    def populate_details(self, target):
        """Populate the details widget with target information"""
        # Clear existing content
        for i in reversed(range(self.details_layout.count())):
            self.details_layout.itemAt(i).widget().setParent(None)
            
        # Basic info
        info_group = QGroupBox("Basic Information")
        info_layout = QFormLayout(info_group)
        
        info_layout.addRow("Username:", QLabel(f"@{target.instagram_username}"))
        info_layout.addRow("Display Name:", QLabel(target.display_name or "Not set"))
        info_layout.addRow("Status:", QLabel(target.status.title()))
        info_layout.addRow("Added:", QLabel(target.created_at.strftime('%Y-%m-%d %H:%M')))
        
        self.details_layout.addWidget(info_group)
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QFormLayout(stats_group)
        
        stats_layout.addRow("Followers:", QLabel(str(target.follower_count or 0)))
        stats_layout.addRow("Following:", QLabel(str(target.following_count or 0)))
        stats_layout.addRow("Posts:", QLabel(str(target.post_count or 0)))
        
        self.details_layout.addWidget(stats_group)
        
        self.details_layout.addStretch()
        
    def show_no_target(self):
        """Show no target selected message"""
        for i in reversed(range(self.details_layout.count())):
            self.details_layout.itemAt(i).widget().setParent(None)
            
        placeholder = QLabel("No target selected")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #7f8c8d; font-style: italic; margin: 50px;")
        self.details_layout.addWidget(placeholder)
        
    def show_error(self, error_message: str):
        """Show error message"""
        for i in reversed(range(self.details_layout.count())):
            self.details_layout.itemAt(i).widget().setParent(None)
            
        error_label = QLabel(f"Error loading target details:\n{error_message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("color: #e74c3c; margin: 50px;")
        self.details_layout.addWidget(error_label)

class MonitoringWorker(QThread):
    """Background worker for surveillance monitoring"""

    activity_detected = pyqtSignal(dict)  # Activity data
    error_occurred = pyqtSignal(str)      # Error message
    status_updated = pyqtSignal(str)      # Status message

    def __init__(self, target_id: int, settings: dict):
        super().__init__()
        self.target_id = target_id
        self.settings = settings
        self.is_running = False
        self.data_manager = DataManager()

    def run(self):
        """Main monitoring loop"""
        self.is_running = True
        self.status_updated.emit("Initializing monitoring...")

        try:
            # Initialize browser and scraper
            browser = InstagramBrowser()
            scraper = InstagramProfileScraper(browser)

            self.status_updated.emit("Browser initialized")

            while self.is_running:
                try:
                    # Get target info
                    target = self.data_manager.get_target_by_id(self.target_id)
                    if not target:
                        self.error_occurred.emit("Target not found")
                        break

                    self.status_updated.emit(f"Monitoring @{target.instagram_username}")

                    # Check for new posts
                    if self.settings.get('monitor_posts', True):
                        self.check_new_posts(scraper, target)

                    # Check for follower changes
                    if self.settings.get('monitor_followers', True):
                        self.check_follower_changes(scraper, target)

                    # Check for stories
                    if self.settings.get('monitor_stories', True):
                        self.check_new_stories(scraper, target)

                    # Wait for next check
                    interval = self.settings.get('refresh_interval', 300)
                    self.msleep(interval * 1000)  # Convert to milliseconds

                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    self.error_occurred.emit(str(e))
                    self.msleep(30000)  # Wait 30 seconds before retry

        except Exception as e:
            logger.error(f"Fatal error in monitoring worker: {e}")
            self.error_occurred.emit(f"Fatal error: {str(e)}")
        finally:
            self.is_running = False
            self.status_updated.emit("Monitoring stopped")

    def stop(self):
        """Stop the monitoring worker"""
        self.is_running = False

    def check_new_posts(self, scraper, target):
        """Check for new posts"""
        try:
            # Get recent posts from Instagram
            posts = scraper.scrape_recent_posts(target.instagram_username, limit=5)

            for post_data in posts:
                # Check if post already exists in database
                existing_post = self.data_manager.get_post_by_instagram_id(
                    post_data.get('instagram_post_id')
                )

                if not existing_post:
                    # New post detected
                    self.activity_detected.emit({
                        'type': 'new_post',
                        'target_id': self.target_id,
                        'target_username': target.instagram_username,
                        'data': post_data,
                        'timestamp': datetime.now()
                    })

        except Exception as e:
            logger.error(f"Error checking new posts: {e}")

    def check_follower_changes(self, scraper, target):
        """Check for follower changes"""
        try:
            # Get current follower count
            profile_data = scraper.scrape_profile_info(target.instagram_username)
            current_count = profile_data.get('follower_count', 0)

            if target.follower_count and current_count != target.follower_count:
                # Follower count changed
                change = current_count - target.follower_count
                self.activity_detected.emit({
                    'type': 'follower_change',
                    'target_id': self.target_id,
                    'target_username': target.instagram_username,
                    'data': {
                        'old_count': target.follower_count,
                        'new_count': current_count,
                        'change': change
                    },
                    'timestamp': datetime.now()
                })

                # Update target in database
                self.data_manager.update_target_stats(self.target_id, {
                    'follower_count': current_count
                })

        except Exception as e:
            logger.error(f"Error checking follower changes: {e}")

    def check_new_stories(self, scraper, target):
        """Check for new stories"""
        try:
            # Get recent stories
            stories = scraper.scrape_stories(target.instagram_username)

            for story_data in stories:
                # Check if story already exists
                existing_story = self.data_manager.get_story_by_instagram_id(
                    story_data.get('story_id')
                )

                if not existing_story:
                    # New story detected
                    self.activity_detected.emit({
                        'type': 'new_story',
                        'target_id': self.target_id,
                        'target_username': target.instagram_username,
                        'data': story_data,
                        'timestamp': datetime.now()
                    })

        except Exception as e:
            logger.error(f"Error checking new stories: {e}")

class SurveillancePanel(QWidget):
    """Main surveillance panel widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_target_id = None
        self.monitoring_worker = None
        self.setup_ui()

    def setup_ui(self):
        """Setup the surveillance panel UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Left panel - Controls and target details
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
        """)
        left_panel.setMaximumWidth(350)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Monitoring controls
        self.monitoring_controls = MonitoringControlWidget()
        self.monitoring_controls.monitoring_started.connect(self.start_monitoring)
        self.monitoring_controls.monitoring_stopped.connect(self.stop_monitoring)
        left_layout.addWidget(self.monitoring_controls, 1)

        # Target details
        self.target_details = TargetDetailsWidget()
        left_layout.addWidget(self.target_details, 2)

        layout.addWidget(left_panel)

        # Right panel - Activity and monitoring data
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        right_panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
        """)

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Recent activity
        self.recent_activity = RecentActivityWidget()
        right_layout.addWidget(self.recent_activity)

        layout.addWidget(right_panel)

    def set_target(self, target_id: int):
        """Set the current surveillance target"""
        self.current_target_id = target_id

        # Update controls and details
        self.monitoring_controls.set_target(target_id)
        self.target_details.update_target_details(target_id)

        # Refresh activity for this target
        self.recent_activity.refresh_activity()

    def start_monitoring(self, target_id: int):
        """Start monitoring the specified target"""
        if self.monitoring_worker and self.monitoring_worker.isRunning():
            self.stop_monitoring(target_id)

        # Get monitoring settings
        settings = {
            'refresh_interval': self.monitoring_controls.refresh_interval.value(),
            'monitor_posts': self.monitoring_controls.monitor_posts.isChecked(),
            'monitor_followers': self.monitoring_controls.monitor_followers.isChecked(),
            'monitor_stories': self.monitoring_controls.monitor_stories.isChecked()
        }

        # Start monitoring worker
        self.monitoring_worker = MonitoringWorker(target_id, settings)
        self.monitoring_worker.activity_detected.connect(self.handle_activity_detected)
        self.monitoring_worker.error_occurred.connect(self.handle_monitoring_error)
        self.monitoring_worker.status_updated.connect(self.handle_status_update)
        self.monitoring_worker.start()

        logger.info(f"Started monitoring target {target_id}")

    def stop_monitoring(self, target_id: int):
        """Stop monitoring the specified target"""
        if self.monitoring_worker and self.monitoring_worker.isRunning():
            self.monitoring_worker.stop()
            self.monitoring_worker.wait(5000)  # Wait up to 5 seconds

            if self.monitoring_worker.isRunning():
                self.monitoring_worker.terminate()

            self.monitoring_worker = None

        logger.info(f"Stopped monitoring target {target_id}")

    def handle_activity_detected(self, activity_data: dict):
        """Handle detected surveillance activity"""
        try:
            # Log the activity
            logger.info(f"Activity detected: {activity_data['type']} for @{activity_data['target_username']}")

            # Save to database
            data_manager = DataManager()
            data_manager.save_activity(activity_data)

            # Refresh activity display
            self.recent_activity.refresh_activity()

            # Show notification (would integrate with notification system)
            self.show_activity_notification(activity_data)

        except Exception as e:
            logger.error(f"Error handling detected activity: {e}")

    def handle_monitoring_error(self, error_message: str):
        """Handle monitoring errors"""
        logger.error(f"Monitoring error: {error_message}")

        # Update status
        self.monitoring_controls.status_label.setText(f"Status: Error - {error_message}")

    def handle_status_update(self, status_message: str):
        """Handle monitoring status updates"""
        self.monitoring_controls.status_label.setText(f"Status: {status_message}")

    def show_activity_notification(self, activity_data: dict):
        """Show notification for detected activity"""
        activity_type = activity_data['type']
        username = activity_data['target_username']

        if activity_type == 'new_post':
            message = f"New post detected from @{username}"
        elif activity_type == 'follower_change':
            change = activity_data['data']['change']
            if change > 0:
                message = f"@{username} gained {change} followers"
            else:
                message = f"@{username} lost {abs(change)} followers"
        elif activity_type == 'new_story':
            message = f"New story posted by @{username}"
        else:
            message = f"Activity detected from @{username}"

        # This would integrate with the main dashboard's notification system
        print(f"🔔 {message}")  # Placeholder for actual notification
