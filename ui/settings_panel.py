#!/usr/bin/env python3
"""
Social Media Surveillance System - Settings Panel
Comprehensive settings panel for system configuration, user preferences,
API settings, and surveillance parameters.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QGroupBox, QScrollArea, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox, QDialog, QLineEdit, QDateTimeEdit,
    QFileDialog, QDialogButtonBox, QPlainTextEdit
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QDateTime, QSettings
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon
)

# Import project modules
from core.config import config
from core.data_manager import DataManager

logger = logging.getLogger(__name__)

class CredentialsWidget(QWidget):
    """Widget for managing Instagram credentials"""
    
    credentials_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_credentials()
        
    def setup_ui(self):
        """Setup the credentials UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🔐 Instagram Credentials")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Credentials form
        form_group = QGroupBox("Account Credentials")
        form_layout = QFormLayout(form_group)
        
        # Username
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Enter Instagram username")
        form_layout.addRow("Username:", self.username_edit)
        
        # Password
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("Enter Instagram password")
        form_layout.addRow("Password:", self.password_edit)
        
        # Show password checkbox
        self.show_password_check = QCheckBox("Show password")
        self.show_password_check.toggled.connect(self.toggle_password_visibility)
        form_layout.addRow("", self.show_password_check)
        
        # 2FA settings
        self.enable_2fa_check = QCheckBox("Enable 2FA support")
        form_layout.addRow("", self.enable_2fa_check)
        
        layout.addWidget(form_group)
        
        # Proxy settings
        proxy_group = QGroupBox("Proxy Settings (Optional)")
        proxy_layout = QFormLayout(proxy_group)
        
        self.enable_proxy_check = QCheckBox("Use proxy")
        proxy_layout.addRow("", self.enable_proxy_check)
        
        self.proxy_host_edit = QLineEdit()
        self.proxy_host_edit.setPlaceholderText("proxy.example.com")
        self.proxy_host_edit.setEnabled(False)
        proxy_layout.addRow("Host:", self.proxy_host_edit)
        
        self.proxy_port_spin = QSpinBox()
        self.proxy_port_spin.setRange(1, 65535)
        self.proxy_port_spin.setValue(8080)
        self.proxy_port_spin.setEnabled(False)
        proxy_layout.addRow("Port:", self.proxy_port_spin)
        
        self.proxy_username_edit = QLineEdit()
        self.proxy_username_edit.setPlaceholderText("Proxy username (if required)")
        self.proxy_username_edit.setEnabled(False)
        proxy_layout.addRow("Username:", self.proxy_username_edit)
        
        self.proxy_password_edit = QLineEdit()
        self.proxy_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.proxy_password_edit.setPlaceholderText("Proxy password (if required)")
        self.proxy_password_edit.setEnabled(False)
        proxy_layout.addRow("Password:", self.proxy_password_edit)
        
        # Connect proxy checkbox to enable/disable fields
        self.enable_proxy_check.toggled.connect(self.toggle_proxy_fields)
        
        layout.addWidget(proxy_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        test_button = QPushButton("🧪 Test Connection")
        test_button.setStyleSheet("""
            QPushButton {
                background: #f39c12;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e67e22;
            }
        """)
        test_button.clicked.connect(self.test_credentials)
        button_layout.addWidget(test_button)
        
        button_layout.addStretch()
        
        save_button = QPushButton("💾 Save Credentials")
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
        save_button.clicked.connect(self.save_credentials)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def toggle_password_visibility(self, checked: bool):
        """Toggle password visibility"""
        if checked:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
            
    def toggle_proxy_fields(self, enabled: bool):
        """Toggle proxy fields based on checkbox"""
        self.proxy_host_edit.setEnabled(enabled)
        self.proxy_port_spin.setEnabled(enabled)
        self.proxy_username_edit.setEnabled(enabled)
        self.proxy_password_edit.setEnabled(enabled)
        
    def load_credentials(self):
        """Load saved credentials"""
        try:
            settings = QSettings()
            
            # Load Instagram credentials (encrypted in real implementation)
            username = settings.value("instagram/username", "")
            password = settings.value("instagram/password", "")
            enable_2fa = settings.value("instagram/enable_2fa", False, type=bool)
            
            self.username_edit.setText(username)
            self.password_edit.setText(password)
            self.enable_2fa_check.setChecked(enable_2fa)
            
            # Load proxy settings
            enable_proxy = settings.value("proxy/enabled", False, type=bool)
            proxy_host = settings.value("proxy/host", "")
            proxy_port = settings.value("proxy/port", 8080, type=int)
            proxy_username = settings.value("proxy/username", "")
            proxy_password = settings.value("proxy/password", "")
            
            self.enable_proxy_check.setChecked(enable_proxy)
            self.proxy_host_edit.setText(proxy_host)
            self.proxy_port_spin.setValue(proxy_port)
            self.proxy_username_edit.setText(proxy_username)
            self.proxy_password_edit.setText(proxy_password)
            
            self.toggle_proxy_fields(enable_proxy)
            
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            
    def save_credentials(self):
        """Save credentials to settings"""
        try:
            settings = QSettings()
            
            # Save Instagram credentials (should be encrypted in real implementation)
            settings.setValue("instagram/username", self.username_edit.text())
            settings.setValue("instagram/password", self.password_edit.text())
            settings.setValue("instagram/enable_2fa", self.enable_2fa_check.isChecked())
            
            # Save proxy settings
            settings.setValue("proxy/enabled", self.enable_proxy_check.isChecked())
            settings.setValue("proxy/host", self.proxy_host_edit.text())
            settings.setValue("proxy/port", self.proxy_port_spin.value())
            settings.setValue("proxy/username", self.proxy_username_edit.text())
            settings.setValue("proxy/password", self.proxy_password_edit.text())
            
            # Emit signal
            credentials = {
                'username': self.username_edit.text(),
                'password': self.password_edit.text(),
                'enable_2fa': self.enable_2fa_check.isChecked(),
                'proxy_enabled': self.enable_proxy_check.isChecked(),
                'proxy_host': self.proxy_host_edit.text(),
                'proxy_port': self.proxy_port_spin.value(),
                'proxy_username': self.proxy_username_edit.text(),
                'proxy_password': self.proxy_password_edit.text()
            }
            
            self.credentials_updated.emit(credentials)
            
            QMessageBox.information(self, "Success", "Credentials saved successfully!")
            
        except Exception as e:
            logger.error(f"Error saving credentials: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save credentials: {str(e)}")
            
    def test_credentials(self):
        """Test Instagram credentials"""
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Warning", "Please enter both username and password")
            return
            
        # This would test actual login in real implementation
        QMessageBox.information(self, "Test", "Credential testing functionality will be implemented")

class MonitoringSettingsWidget(QWidget):
    """Widget for monitoring and surveillance settings"""
    
    settings_updated = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup the monitoring settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("⚙️ Monitoring Settings")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # General settings
        general_group = QGroupBox("General Settings")
        general_layout = QFormLayout(general_group)
        
        # Default refresh interval
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(30, 3600)
        self.refresh_interval_spin.setValue(300)
        self.refresh_interval_spin.setSuffix(" seconds")
        general_layout.addRow("Default Refresh Interval:", self.refresh_interval_spin)
        
        # Max concurrent targets
        self.max_targets_spin = QSpinBox()
        self.max_targets_spin.setRange(1, 50)
        self.max_targets_spin.setValue(10)
        general_layout.addRow("Max Concurrent Targets:", self.max_targets_spin)
        
        # Auto-start monitoring
        self.auto_start_check = QCheckBox("Auto-start monitoring on startup")
        general_layout.addRow("", self.auto_start_check)
        
        layout.addWidget(general_group)
        
        # Data collection settings
        data_group = QGroupBox("Data Collection")
        data_layout = QFormLayout(data_group)
        
        # What to monitor by default
        self.monitor_posts_check = QCheckBox("Monitor posts by default")
        self.monitor_posts_check.setChecked(True)
        data_layout.addRow("", self.monitor_posts_check)
        
        self.monitor_followers_check = QCheckBox("Monitor followers by default")
        self.monitor_followers_check.setChecked(True)
        data_layout.addRow("", self.monitor_followers_check)
        
        self.monitor_stories_check = QCheckBox("Monitor stories by default")
        self.monitor_stories_check.setChecked(True)
        data_layout.addRow("", self.monitor_stories_check)
        
        # Data retention
        self.data_retention_spin = QSpinBox()
        self.data_retention_spin.setRange(7, 365)
        self.data_retention_spin.setValue(90)
        self.data_retention_spin.setSuffix(" days")
        data_layout.addRow("Data Retention Period:", self.data_retention_spin)
        
        layout.addWidget(data_group)
        
        # Performance settings
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout(performance_group)
        
        # Browser instances
        self.browser_instances_spin = QSpinBox()
        self.browser_instances_spin.setRange(1, 5)
        self.browser_instances_spin.setValue(2)
        performance_layout.addRow("Browser Instances:", self.browser_instances_spin)
        
        # Memory limit
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(512, 8192)
        self.memory_limit_spin.setValue(2048)
        self.memory_limit_spin.setSuffix(" MB")
        performance_layout.addRow("Memory Limit:", self.memory_limit_spin)
        
        layout.addWidget(performance_group)
        
        # Save button
        save_button = QPushButton("💾 Save Settings")
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
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        layout.addStretch()
        
    def load_settings(self):
        """Load monitoring settings"""
        try:
            settings = QSettings()
            
            # General settings
            refresh_interval = settings.value("monitoring/refresh_interval", 300, type=int)
            max_targets = settings.value("monitoring/max_targets", 10, type=int)
            auto_start = settings.value("monitoring/auto_start", False, type=bool)
            
            self.refresh_interval_spin.setValue(refresh_interval)
            self.max_targets_spin.setValue(max_targets)
            self.auto_start_check.setChecked(auto_start)
            
            # Data collection settings
            monitor_posts = settings.value("monitoring/monitor_posts", True, type=bool)
            monitor_followers = settings.value("monitoring/monitor_followers", True, type=bool)
            monitor_stories = settings.value("monitoring/monitor_stories", True, type=bool)
            data_retention = settings.value("monitoring/data_retention", 90, type=int)
            
            self.monitor_posts_check.setChecked(monitor_posts)
            self.monitor_followers_check.setChecked(monitor_followers)
            self.monitor_stories_check.setChecked(monitor_stories)
            self.data_retention_spin.setValue(data_retention)
            
            # Performance settings
            browser_instances = settings.value("performance/browser_instances", 2, type=int)
            memory_limit = settings.value("performance/memory_limit", 2048, type=int)
            
            self.browser_instances_spin.setValue(browser_instances)
            self.memory_limit_spin.setValue(memory_limit)
            
        except Exception as e:
            logger.error(f"Error loading monitoring settings: {e}")
            
    def save_settings(self):
        """Save monitoring settings"""
        try:
            settings = QSettings()
            
            # General settings
            settings.setValue("monitoring/refresh_interval", self.refresh_interval_spin.value())
            settings.setValue("monitoring/max_targets", self.max_targets_spin.value())
            settings.setValue("monitoring/auto_start", self.auto_start_check.isChecked())
            
            # Data collection settings
            settings.setValue("monitoring/monitor_posts", self.monitor_posts_check.isChecked())
            settings.setValue("monitoring/monitor_followers", self.monitor_followers_check.isChecked())
            settings.setValue("monitoring/monitor_stories", self.monitor_stories_check.isChecked())
            settings.setValue("monitoring/data_retention", self.data_retention_spin.value())
            
            # Performance settings
            settings.setValue("performance/browser_instances", self.browser_instances_spin.value())
            settings.setValue("performance/memory_limit", self.memory_limit_spin.value())
            
            # Emit signal
            monitoring_settings = {
                'refresh_interval': self.refresh_interval_spin.value(),
                'max_targets': self.max_targets_spin.value(),
                'auto_start': self.auto_start_check.isChecked(),
                'monitor_posts': self.monitor_posts_check.isChecked(),
                'monitor_followers': self.monitor_followers_check.isChecked(),
                'monitor_stories': self.monitor_stories_check.isChecked(),
                'data_retention': self.data_retention_spin.value(),
                'browser_instances': self.browser_instances_spin.value(),
                'memory_limit': self.memory_limit_spin.value()
            }
            
            self.settings_updated.emit(monitoring_settings)
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            logger.error(f"Error saving monitoring settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

class APISettingsWidget(QWidget):
    """Widget for API settings and configurations"""

    api_settings_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.load_api_settings()

    def setup_ui(self):
        """Setup the API settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("🤖 AI & API Settings")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)

        # DeepSeek API settings
        deepseek_group = QGroupBox("DeepSeek AI Configuration")
        deepseek_layout = QFormLayout(deepseek_group)

        # API Key
        self.deepseek_api_key_edit = QLineEdit()
        self.deepseek_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_api_key_edit.setPlaceholderText("Enter DeepSeek API key")
        deepseek_layout.addRow("API Key:", self.deepseek_api_key_edit)

        # Show API key checkbox
        self.show_api_key_check = QCheckBox("Show API key")
        self.show_api_key_check.toggled.connect(self.toggle_api_key_visibility)
        deepseek_layout.addRow("", self.show_api_key_check)

        # Model selection
        self.deepseek_model_combo = QComboBox()
        self.deepseek_model_combo.addItems(["deepseek-chat", "deepseek-coder"])
        deepseek_layout.addRow("Model:", self.deepseek_model_combo)

        # Enable AI analysis
        self.enable_ai_analysis_check = QCheckBox("Enable AI content analysis")
        self.enable_ai_analysis_check.setChecked(True)
        deepseek_layout.addRow("", self.enable_ai_analysis_check)

        # Analysis frequency
        self.analysis_frequency_combo = QComboBox()
        self.analysis_frequency_combo.addItems([
            "Real-time", "Every 5 minutes", "Every 15 minutes",
            "Every hour", "Daily"
        ])
        deepseek_layout.addRow("Analysis Frequency:", self.analysis_frequency_combo)

        layout.addWidget(deepseek_group)

        # Rate limiting settings
        rate_limit_group = QGroupBox("Rate Limiting")
        rate_limit_layout = QFormLayout(rate_limit_group)

        # API requests per minute
        self.api_requests_per_minute_spin = QSpinBox()
        self.api_requests_per_minute_spin.setRange(1, 100)
        self.api_requests_per_minute_spin.setValue(10)
        rate_limit_layout.addRow("API Requests/Minute:", self.api_requests_per_minute_spin)

        # Instagram requests per hour
        self.instagram_requests_per_hour_spin = QSpinBox()
        self.instagram_requests_per_hour_spin.setRange(10, 1000)
        self.instagram_requests_per_hour_spin.setValue(200)
        rate_limit_layout.addRow("Instagram Requests/Hour:", self.instagram_requests_per_hour_spin)

        layout.addWidget(rate_limit_group)

        # Test and save buttons
        button_layout = QHBoxLayout()

        test_api_button = QPushButton("🧪 Test API Connection")
        test_api_button.setStyleSheet("""
            QPushButton {
                background: #f39c12;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e67e22;
            }
        """)
        test_api_button.clicked.connect(self.test_api_connection)
        button_layout.addWidget(test_api_button)

        button_layout.addStretch()

        save_api_button = QPushButton("💾 Save API Settings")
        save_api_button.setStyleSheet("""
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
        save_api_button.clicked.connect(self.save_api_settings)
        button_layout.addWidget(save_api_button)

        layout.addLayout(button_layout)
        layout.addStretch()

    def toggle_api_key_visibility(self, checked: bool):
        """Toggle API key visibility"""
        if checked:
            self.deepseek_api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.deepseek_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def load_api_settings(self):
        """Load API settings"""
        try:
            settings = QSettings()

            # DeepSeek settings
            api_key = settings.value("deepseek/api_key", "")
            model = settings.value("deepseek/model", "deepseek-chat")
            enable_analysis = settings.value("deepseek/enable_analysis", True, type=bool)
            analysis_frequency = settings.value("deepseek/analysis_frequency", "Real-time")

            self.deepseek_api_key_edit.setText(api_key)
            self.deepseek_model_combo.setCurrentText(model)
            self.enable_ai_analysis_check.setChecked(enable_analysis)
            self.analysis_frequency_combo.setCurrentText(analysis_frequency)

            # Rate limiting
            api_requests_per_minute = settings.value("rate_limit/api_requests_per_minute", 10, type=int)
            instagram_requests_per_hour = settings.value("rate_limit/instagram_requests_per_hour", 200, type=int)

            self.api_requests_per_minute_spin.setValue(api_requests_per_minute)
            self.instagram_requests_per_hour_spin.setValue(instagram_requests_per_hour)

        except Exception as e:
            logger.error(f"Error loading API settings: {e}")

    def save_api_settings(self):
        """Save API settings"""
        try:
            settings = QSettings()

            # DeepSeek settings
            settings.setValue("deepseek/api_key", self.deepseek_api_key_edit.text())
            settings.setValue("deepseek/model", self.deepseek_model_combo.currentText())
            settings.setValue("deepseek/enable_analysis", self.enable_ai_analysis_check.isChecked())
            settings.setValue("deepseek/analysis_frequency", self.analysis_frequency_combo.currentText())

            # Rate limiting
            settings.setValue("rate_limit/api_requests_per_minute", self.api_requests_per_minute_spin.value())
            settings.setValue("rate_limit/instagram_requests_per_hour", self.instagram_requests_per_hour_spin.value())

            # Emit signal
            api_settings = {
                'deepseek_api_key': self.deepseek_api_key_edit.text(),
                'deepseek_model': self.deepseek_model_combo.currentText(),
                'enable_ai_analysis': self.enable_ai_analysis_check.isChecked(),
                'analysis_frequency': self.analysis_frequency_combo.currentText(),
                'api_requests_per_minute': self.api_requests_per_minute_spin.value(),
                'instagram_requests_per_hour': self.instagram_requests_per_hour_spin.value()
            }

            self.api_settings_updated.emit(api_settings)

            QMessageBox.information(self, "Success", "API settings saved successfully!")

        except Exception as e:
            logger.error(f"Error saving API settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save API settings: {str(e)}")

    def test_api_connection(self):
        """Test API connection"""
        api_key = self.deepseek_api_key_edit.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Warning", "Please enter an API key")
            return

        # This would test actual API connection in real implementation
        QMessageBox.information(self, "Test", "API connection testing functionality will be implemented")

class SettingsPanel(QWidget):
    """Main settings panel widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the settings panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("⚙️ System Settings")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 20px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        # Settings tabs
        self.settings_tabs = QTabWidget()
        self.settings_tabs.setStyleSheet("""
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

        # Add settings tabs
        self.add_settings_tabs()

        layout.addWidget(self.settings_tabs)

    def add_settings_tabs(self):
        """Add settings tabs"""
        # Credentials tab
        self.credentials_widget = CredentialsWidget()
        self.credentials_widget.credentials_updated.connect(self.on_credentials_updated)
        self.settings_tabs.addTab(self.credentials_widget, "🔐 Credentials")

        # Monitoring settings tab
        self.monitoring_widget = MonitoringSettingsWidget()
        self.monitoring_widget.settings_updated.connect(self.on_monitoring_settings_updated)
        self.settings_tabs.addTab(self.monitoring_widget, "📊 Monitoring")

        # API settings tab
        self.api_widget = APISettingsWidget()
        self.api_widget.api_settings_updated.connect(self.on_api_settings_updated)
        self.settings_tabs.addTab(self.api_widget, "🤖 API Settings")

        # System info tab (placeholder)
        system_info_widget = QWidget()
        system_info_layout = QVBoxLayout(system_info_widget)

        info_label = QLabel("📋 System Information")
        info_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        info_label.setStyleSheet("color: #2c3e50; margin: 20px;")
        system_info_layout.addWidget(info_label)

        info_text = QPlainTextEdit()
        info_text.setReadOnly(True)
        info_text.setPlainText("""
System Information:
- Version: 1.0.0 (Phase 5)
- Python Version: 3.x
- PyQt6 Version: 6.6.0
- Database: SQLite
- Browser Engine: Chromium WebDriver

Features:
✅ Browser Automation
✅ Database Management
✅ Instagram Scraping
✅ AI Analysis Engine
✅ PyQt6 Dashboard

Status: Phase 5 Implementation Complete
        """.strip())
        info_text.setStyleSheet("""
            QPlainTextEdit {
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        system_info_layout.addWidget(info_text)

        self.settings_tabs.addTab(system_info_widget, "ℹ️ System Info")

    def on_credentials_updated(self, credentials: dict):
        """Handle credentials update"""
        logger.info("Credentials updated")

    def on_monitoring_settings_updated(self, settings: dict):
        """Handle monitoring settings update"""
        logger.info("Monitoring settings updated")

    def on_api_settings_updated(self, settings: dict):
        """Handle API settings update"""
        logger.info("API settings updated")

def create_settings_panel() -> SettingsPanel:
    """Factory function to create settings panel"""
    return SettingsPanel()
