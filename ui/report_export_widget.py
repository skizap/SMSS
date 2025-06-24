#!/usr/bin/env python3
"""
Social Media Surveillance System - Report Export Widget
UI component for configuring and generating reports with multiple format support.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QFrame, QGroupBox, QComboBox, QSpinBox,
        QDateEdit, QLineEdit, QCheckBox, QTextEdit, QProgressBar,
        QListWidget, QListWidgetItem, QMessageBox, QFileDialog,
        QDialog, QDialogButtonBox, QTabWidget, QScrollArea
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QDate, QThread
    from PyQt6.QtGui import QFont, QColor, QIcon
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from core.database import db_manager
from reporting.report_export_system import (
    ReportExportService, ReportConfiguration, ReportFormat, ReportType,
    report_export_service
)

logger = logging.getLogger(__name__)

class ReportConfigurationWidget(QWidget):
    """Widget for configuring report generation parameters"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_targets = []
        self.setup_ui()
        self.load_templates()
        
    def setup_ui(self):
        """Setup the report configuration UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # Header
        header = QLabel("📊 Report Configuration")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Configuration form
        config_frame = QFrame()
        config_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #ecf0f1;
                border-radius: 12px;
                padding: 20px;
            }
        """)
        config_layout = QFormLayout(config_frame)
        config_layout.setSpacing(15)
        
        # Report type selection
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Dashboard Summary",
            "Multi-Target Comparison", 
            "Health Analysis",
            "Performance Summary",
            "Trend Analysis",
            "Anomaly Report"
        ])
        self.report_type_combo.setStyleSheet(self._get_combo_style())
        config_layout.addRow("Report Type:", self.report_type_combo)
        
        # Format selection
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PDF", "Excel", "CSV", "JSON"])
        self.format_combo.setStyleSheet(self._get_combo_style())
        config_layout.addRow("Export Format:", self.format_combo)
        
        # Template selection
        self.template_combo = QComboBox()
        self.template_combo.setStyleSheet(self._get_combo_style())
        config_layout.addRow("Template:", self.template_combo)
        
        # Date range
        date_group = QGroupBox("Date Range")
        date_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #34495e;
            }
        """)
        date_layout = QHBoxLayout(date_group)
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet(self._get_date_style())
        date_layout.addWidget(QLabel("From:"))
        date_layout.addWidget(self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet(self._get_date_style())
        date_layout.addWidget(QLabel("To:"))
        date_layout.addWidget(self.end_date)
        
        config_layout.addRow(date_group)
        
        # Options
        options_group = QGroupBox("Options")
        options_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #34495e;
            }
        """)
        options_layout = QVBoxLayout(options_group)
        
        self.include_charts_cb = QCheckBox("Include Charts and Visualizations")
        self.include_charts_cb.setChecked(True)
        self.include_charts_cb.setStyleSheet("font-weight: normal; padding: 5px;")
        options_layout.addWidget(self.include_charts_cb)
        
        self.include_raw_data_cb = QCheckBox("Include Raw Data Tables")
        self.include_raw_data_cb.setStyleSheet("font-weight: normal; padding: 5px;")
        options_layout.addWidget(self.include_raw_data_cb)
        
        config_layout.addRow(options_group)
        
        layout.addWidget(config_frame)
        
        # Target selection
        target_group = QGroupBox("Target Selection")
        target_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #3498db;
            }
        """)
        target_layout = QVBoxLayout(target_group)
        
        # Target selection buttons
        target_buttons = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All Active")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_targets)
        target_buttons.addWidget(select_all_btn)
        
        clear_btn = QPushButton("Clear Selection")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #7f8c8d;
            }
        """)
        clear_btn.clicked.connect(self.clear_target_selection)
        target_buttons.addWidget(clear_btn)
        
        target_buttons.addStretch()
        target_layout.addLayout(target_buttons)
        
        # Target list
        self.target_list = QListWidget()
        self.target_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                background: white;
                padding: 5px;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background: #ebf3fd;
            }
            QListWidget::item:selected {
                background: #3498db;
                color: white;
            }
        """)
        self.target_list.setMaximumHeight(150)
        self.target_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        target_layout.addWidget(self.target_list)
        
        # Selected count
        self.selected_count_label = QLabel("0 targets selected")
        self.selected_count_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 5px;")
        target_layout.addWidget(self.selected_count_label)
        
        layout.addWidget(target_group)
        
        # Generate button
        self.generate_btn = QPushButton("🚀 Generate Report")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #27ae60, stop:1 #229954);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px 30px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #229954, stop:1 #1e8449);
            }
            QPushButton:pressed {
                background: #1e8449;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_report)
        layout.addWidget(self.generate_btn)
        
        # Load targets
        self.load_targets()
        
        # Connect signals
        self.target_list.itemSelectionChanged.connect(self.update_selected_count)
        
    def _get_combo_style(self) -> str:
        """Get combo box style"""
        return """
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
                background: white;
            }
            QComboBox:focus {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border: 2px solid #7f8c8d;
                width: 6px;
                height: 6px;
                border-top: none;
                border-right: none;
                transform: rotate(-45deg);
            }
        """
    
    def _get_date_style(self) -> str:
        """Get date edit style"""
        return """
            QDateEdit {
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                background: white;
            }
            QDateEdit:focus {
                border-color: #3498db;
            }
        """
    
    def load_templates(self):
        """Load available report templates"""
        try:
            templates = report_export_service.get_available_templates()
            
            self.template_combo.clear()
            for template in templates:
                display_name = template['name']
                if template['type'] == 'custom':
                    display_name += " (Custom)"
                
                self.template_combo.addItem(display_name, template['id'])
                
        except Exception as e:
            logger.error(f"Error loading templates: {e}")
    
    def load_targets(self):
        """Load surveillance targets"""
        try:
            with db_manager.get_session() as session:
                from models.instagram_models import SurveillanceTarget
                targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).all()
                
                self.target_list.clear()
                for target in targets:
                    display_text = f"@{target.instagram_username}"
                    if target.display_name:
                        display_text += f" ({target.display_name})"
                    display_text += f" - {target.follower_count or 0:,} followers"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, target.id)
                    self.target_list.addItem(item)
                    
        except Exception as e:
            logger.error(f"Error loading targets: {e}")
    
    def select_all_targets(self):
        """Select all targets"""
        for i in range(self.target_list.count()):
            item = self.target_list.item(i)
            item.setSelected(True)
    
    def clear_target_selection(self):
        """Clear target selection"""
        self.target_list.clearSelection()
    
    def update_selected_count(self):
        """Update selected targets count"""
        selected_items = self.target_list.selectedItems()
        count = len(selected_items)
        self.selected_count_label.setText(f"{count} target{'s' if count != 1 else ''} selected")
        
        # Update selected targets list
        self.selected_targets = []
        for item in selected_items:
            target_id = item.data(Qt.ItemDataRole.UserRole)
            if target_id:
                self.selected_targets.append(target_id)
    
    def generate_report(self):
        """Generate report with current configuration"""
        try:
            # Validate configuration
            if not self.selected_targets:
                QMessageBox.warning(self, "No Targets Selected", 
                                  "Please select at least one target for the report.")
                return
            
            # Create configuration
            report_type_map = {
                "Dashboard Summary": ReportType.DASHBOARD,
                "Multi-Target Comparison": ReportType.COMPARISON,
                "Health Analysis": ReportType.HEALTH_SUMMARY,
                "Performance Summary": ReportType.PERFORMANCE_SUMMARY,
                "Trend Analysis": ReportType.TREND_ANALYSIS,
                "Anomaly Report": ReportType.ANOMALY_REPORT
            }
            
            format_map = {
                "PDF": ReportFormat.PDF,
                "Excel": ReportFormat.EXCEL,
                "CSV": ReportFormat.CSV,
                "JSON": ReportFormat.JSON
            }
            
            config = ReportConfiguration(
                report_type=report_type_map[self.report_type_combo.currentText()],
                format=format_map[self.format_combo.currentText()],
                target_ids=self.selected_targets,
                date_range_start=self.start_date.date().toPython(),
                date_range_end=self.end_date.date().toPython(),
                template_id=self.template_combo.currentData(),
                include_charts=self.include_charts_cb.isChecked(),
                include_raw_data=self.include_raw_data_cb.isChecked()
            )
            
            # Show progress dialog
            progress_dialog = ReportProgressDialog(config, self)
            progress_dialog.exec()
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            QMessageBox.critical(self, "Report Generation Error", 
                               f"Failed to generate report:\n{str(e)}")

class ReportProgressDialog(QDialog):
    """Dialog showing report generation progress"""
    
    def __init__(self, config: ReportConfiguration, parent=None):
        super().__init__(parent)
        self.config = config
        self.report_id = None
        self.setup_ui()
        self.start_generation()
        
    def setup_ui(self):
        """Setup progress dialog UI"""
        self.setWindowTitle("Generating Report")
        self.setFixedSize(400, 200)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Status label
        self.status_label = QLabel("Initializing report generation...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 12px; color: #2c3e50;")
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                text-align: center;
                background: #ecf0f1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498db, stop:1 #2980b9);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e74c3c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #c0392b;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.open_btn = QPushButton("Open Report")
        self.open_btn.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #229954;
            }
        """)
        self.open_btn.clicked.connect(self.open_report)
        self.open_btn.setEnabled(False)
        button_layout.addWidget(self.open_btn)
        
        layout.addLayout(button_layout)
        
        # Timer for checking progress
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_progress)
        
    def start_generation(self):
        """Start report generation"""
        try:
            self.status_label.setText("Starting report generation...")
            self.report_id = report_export_service.generate_report_async(self.config)
            
            # Start checking progress
            self.check_timer.start(2000)  # Check every 2 seconds
            
        except Exception as e:
            logger.error(f"Error starting report generation: {e}")
            self.status_label.setText(f"Error: {str(e)}")
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
    
    def check_progress(self):
        """Check report generation progress"""
        try:
            if self.report_id:
                status = report_export_service.get_report_status(self.report_id)
                
                if status.get('status') == 'completed':
                    self.status_label.setText("Report generated successfully!")
                    self.progress_bar.setRange(0, 1)
                    self.progress_bar.setValue(1)
                    self.open_btn.setEnabled(True)
                    self.cancel_btn.setText("Close")
                    self.check_timer.stop()
                    
                elif status.get('status') == 'failed':
                    error_msg = status.get('error_message', 'Unknown error')
                    self.status_label.setText(f"Report generation failed: {error_msg}")
                    self.progress_bar.setRange(0, 1)
                    self.progress_bar.setValue(0)
                    self.check_timer.stop()
                    
                else:
                    self.status_label.setText("Generating report...")
                    
        except Exception as e:
            logger.error(f"Error checking progress: {e}")
            self.status_label.setText(f"Error checking progress: {str(e)}")
            self.check_timer.stop()
    
    def open_report(self):
        """Open the generated report"""
        try:
            if self.report_id:
                status = report_export_service.get_report_status(self.report_id)
                file_path = status.get('file_path')
                
                if file_path and os.path.exists(file_path):
                    # Open file with default application
                    import subprocess
                    import platform
                    
                    if platform.system() == 'Windows':
                        os.startfile(file_path)
                    elif platform.system() == 'Darwin':  # macOS
                        subprocess.call(['open', file_path])
                    else:  # Linux
                        subprocess.call(['xdg-open', file_path])
                    
                    self.accept()
                else:
                    QMessageBox.warning(self, "File Not Found", 
                                      "The generated report file could not be found.")
                    
        except Exception as e:
            logger.error(f"Error opening report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open report:\n{str(e)}")

def create_report_export_widget() -> ReportConfigurationWidget:
    """Factory function to create report export widget"""
    return ReportConfigurationWidget()
