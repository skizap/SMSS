#!/usr/bin/env python3
"""
Social Media Surveillance System - Data Exploration Widget
Interactive data exploration with filtering, drill-down, and export capabilities.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
        QHeaderView, QGroupBox, QScrollArea, QComboBox, QSpinBox,
        QDateEdit, QLineEdit, QCheckBox, QTabWidget, QSplitter,
        QTreeWidget, QTreeWidgetItem, QTextEdit, QProgressBar,
        QSlider, QDialog, QDialogButtonBox, QFormLayout, QFileDialog,
        QMessageBox
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QDate, QThread
    from PyQt6.QtGui import QFont, QColor, QAction, QIcon
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from core.database import db_manager
from reporting.analytics_service import analytics_service
from reporting.statistical_analysis_engine import data_aggregation_engine

logger = logging.getLogger(__name__)

class DataFilterWidget(QWidget):
    """Widget for setting up data filters"""
    
    filters_changed = pyqtSignal(dict)  # Emit filter configuration
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the data filter UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🔍 Data Filters")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #34495e; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # Filter form
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #ecf0f1;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        form_layout = QFormLayout(form_frame)
        
        # Date range filter
        date_group = QGroupBox("Date Range")
        date_layout = QVBoxLayout(date_group)
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet("padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px;")
        date_layout.addWidget(QLabel("Start Date:"))
        date_layout.addWidget(self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet("padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px;")
        date_layout.addWidget(QLabel("End Date:"))
        date_layout.addWidget(self.end_date)
        
        form_layout.addRow(date_group)
        
        # Metric type filter
        self.metric_type = QComboBox()
        self.metric_type.addItems([
            "All Metrics",
            "Follower Count",
            "Engagement Rate", 
            "Health Score",
            "Post Frequency",
            "Scraping Performance"
        ])
        self.metric_type.setStyleSheet("padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px;")
        form_layout.addRow("Metric Type:", self.metric_type)
        
        # Target category filter
        self.category_filter = QComboBox()
        self.category_filter.addItems([
            "All Categories",
            "Influencer",
            "Brand",
            "Celebrity",
            "Organization",
            "Other"
        ])
        self.category_filter.setStyleSheet("padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px;")
        form_layout.addRow("Category:", self.category_filter)
        
        # Follower range filter
        follower_group = QGroupBox("Follower Range")
        follower_layout = QVBoxLayout(follower_group)
        
        self.min_followers = QSpinBox()
        self.min_followers.setRange(0, 10000000)
        self.min_followers.setValue(0)
        self.min_followers.setSuffix(" followers")
        self.min_followers.setStyleSheet("padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px;")
        follower_layout.addWidget(QLabel("Minimum:"))
        follower_layout.addWidget(self.min_followers)
        
        self.max_followers = QSpinBox()
        self.max_followers.setRange(0, 10000000)
        self.max_followers.setValue(10000000)
        self.max_followers.setSuffix(" followers")
        self.max_followers.setStyleSheet("padding: 5px; border: 1px solid #bdc3c7; border-radius: 4px;")
        follower_layout.addWidget(QLabel("Maximum:"))
        follower_layout.addWidget(self.max_followers)
        
        form_layout.addRow(follower_group)
        
        # Health score filter
        health_group = QGroupBox("Health Score Range")
        health_layout = QVBoxLayout(health_group)
        
        self.health_slider = QSlider(Qt.Orientation.Horizontal)
        self.health_slider.setRange(0, 100)
        self.health_slider.setValue(0)
        self.health_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #bdc3c7;
                height: 8px;
                background: #ecf0f1;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #2980b9;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """)
        
        self.health_label = QLabel("Minimum Health Score: 0")
        health_layout.addWidget(self.health_label)
        health_layout.addWidget(self.health_slider)
        
        self.health_slider.valueChanged.connect(
            lambda v: self.health_label.setText(f"Minimum Health Score: {v}")
        )
        
        form_layout.addRow(health_group)
        
        layout.addWidget(form_frame)
        
        # Apply filters button
        apply_btn = QPushButton("🔍 Apply Filters")
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        apply_btn.clicked.connect(self.apply_filters)
        layout.addWidget(apply_btn)
        
        # Reset filters button
        reset_btn = QPushButton("🔄 Reset Filters")
        reset_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #7f8c8d;
            }
        """)
        reset_btn.clicked.connect(self.reset_filters)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
    def apply_filters(self):
        """Apply current filter settings"""
        filters = {
            'start_date': self.start_date.date().toPython(),
            'end_date': self.end_date.date().toPython(),
            'metric_type': self.metric_type.currentText(),
            'category': self.category_filter.currentText(),
            'min_followers': self.min_followers.value(),
            'max_followers': self.max_followers.value(),
            'min_health_score': self.health_slider.value()
        }
        
        self.filters_changed.emit(filters)
        
    def reset_filters(self):
        """Reset all filters to default values"""
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.end_date.setDate(QDate.currentDate())
        self.metric_type.setCurrentIndex(0)
        self.category_filter.setCurrentIndex(0)
        self.min_followers.setValue(0)
        self.max_followers.setValue(10000000)
        self.health_slider.setValue(0)
        
        self.apply_filters()

class DataTableWidget(QWidget):
    """Widget for displaying filtered data in table format"""
    
    row_selected = pyqtSignal(dict)  # Emit selected row data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_data = []
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the data table UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header with controls
        header_layout = QHBoxLayout()
        
        header = QLabel("📊 Data Explorer")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #34495e;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Export button
        export_btn = QPushButton("📤 Export")
        export_btn.setStyleSheet("""
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
        export_btn.clicked.connect(self.export_data)
        header_layout.addWidget(export_btn)
        
        layout.addLayout(header_layout)
        
        # Data table
        self.table = QTableWidget()
        self.table.setStyleSheet("""
            QTableWidget {
                border: 2px solid #ecf0f1;
                border-radius: 10px;
                background: white;
                gridline-color: #ecf0f1;
                selection-background-color: #3498db;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTableWidget::item:hover {
                background: #ebf3fd;
            }
            QHeaderView::section {
                background: #34495e;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        # Enable sorting
        self.table.setSortingEnabled(True)
        
        # Set selection behavior
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        
        # Connect selection signal
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        
        layout.addWidget(self.table)
        
        # Status label
        self.status_label = QLabel("No data loaded")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
    def update_data(self, filters: Dict[str, Any]):
        """Update table data based on filters"""
        try:
            # Clear existing data
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.current_data = []
            
            # Get filtered data
            data = self.fetch_filtered_data(filters)
            
            if not data:
                self.status_label.setText("No data matches the current filters")
                return
            
            # Setup table structure
            self.setup_table_structure(data)
            
            # Populate table
            self.populate_table(data)
            
            # Update status
            self.status_label.setText(f"Showing {len(data)} records")
            
        except Exception as e:
            logger.error(f"Error updating data table: {e}")
            self.status_label.setText(f"Error loading data: {str(e)}")
    
    def fetch_filtered_data(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch data based on applied filters"""
        try:
            # Get targets that match filters
            with db_manager.get_session() as session:
                from models.instagram_models import SurveillanceTarget
                
                query = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                )
                
                # Apply category filter
                if filters.get('category') and filters['category'] != "All Categories":
                    query = query.filter(SurveillanceTarget.category == filters['category'])
                
                # Apply follower range filter
                if filters.get('min_followers', 0) > 0:
                    query = query.filter(SurveillanceTarget.follower_count >= filters['min_followers'])
                
                if filters.get('max_followers', 10000000) < 10000000:
                    query = query.filter(SurveillanceTarget.follower_count <= filters['max_followers'])
                
                targets = query.all()
                
                # Get analytics data for each target
                data = []
                for target in targets:
                    try:
                        # Get dashboard data
                        dashboard_data = analytics_service.get_target_analytics_dashboard(
                            target.id, "30d"
                        )
                        
                        if 'error' not in dashboard_data:
                            target_info = dashboard_data.get('target_info', {})
                            health_summary = dashboard_data.get('health_summary', {})
                            performance_metrics = dashboard_data.get('performance_metrics', {})
                            
                            # Apply health score filter
                            health_score = health_summary.get('current_health_score', 0)
                            if health_score >= filters.get('min_health_score', 0):
                                
                                record = {
                                    'target_id': target.id,
                                    'username': target_info.get('username', ''),
                                    'display_name': target_info.get('display_name', ''),
                                    'category': target_info.get('category', ''),
                                    'follower_count': target_info.get('follower_count', 0),
                                    'following_count': target_info.get('following_count', 0),
                                    'post_count': target_info.get('post_count', 0),
                                    'health_score': health_score,
                                    'engagement_rate': health_summary.get('avg_engagement_rate', 0),
                                    'success_rate': performance_metrics.get('avg_success_rate', 0),
                                    'quality_score': performance_metrics.get('avg_quality_score', 0),
                                    'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M')
                                }
                                
                                data.append(record)
                                
                    except Exception as e:
                        logger.error(f"Error getting data for target {target.id}: {e}")
                        continue
                
                return data
                
        except Exception as e:
            logger.error(f"Error fetching filtered data: {e}")
            return []
    
    def setup_table_structure(self, data: List[Dict[str, Any]]):
        """Setup table columns based on data structure"""
        if not data:
            return
        
        # Define column headers
        headers = [
            'Username', 'Display Name', 'Category', 'Followers', 'Following',
            'Posts', 'Health Score', 'Engagement Rate', 'Success Rate',
            'Quality Score', 'Last Updated'
        ]
        
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
    
    def populate_table(self, data: List[Dict[str, Any]]):
        """Populate table with data"""
        self.current_data = data
        self.table.setRowCount(len(data))
        
        for row, record in enumerate(data):
            # Username
            self.table.setItem(row, 0, QTableWidgetItem(f"@{record.get('username', '')}"))
            
            # Display Name
            self.table.setItem(row, 1, QTableWidgetItem(record.get('display_name', '')))
            
            # Category
            self.table.setItem(row, 2, QTableWidgetItem(record.get('category', '')))
            
            # Followers
            followers = record.get('follower_count', 0)
            self.table.setItem(row, 3, QTableWidgetItem(f"{followers:,}"))
            
            # Following
            following = record.get('following_count', 0)
            self.table.setItem(row, 4, QTableWidgetItem(f"{following:,}"))
            
            # Posts
            posts = record.get('post_count', 0)
            self.table.setItem(row, 5, QTableWidgetItem(f"{posts:,}"))
            
            # Health Score
            health_score = record.get('health_score', 0)
            health_item = QTableWidgetItem(f"{health_score:.1f}%")
            if health_score >= 80:
                health_item.setBackground(QColor("#d5f4e6"))  # Light green
            elif health_score >= 60:
                health_item.setBackground(QColor("#fff3cd"))  # Light yellow
            else:
                health_item.setBackground(QColor("#f8d7da"))  # Light red
            self.table.setItem(row, 6, health_item)
            
            # Engagement Rate
            engagement = record.get('engagement_rate', 0)
            self.table.setItem(row, 7, QTableWidgetItem(f"{engagement:.2f}%"))
            
            # Success Rate
            success_rate = record.get('success_rate', 0)
            self.table.setItem(row, 8, QTableWidgetItem(f"{success_rate:.1f}%"))
            
            # Quality Score
            quality_score = record.get('quality_score', 0)
            self.table.setItem(row, 9, QTableWidgetItem(f"{quality_score:.2f}"))
            
            # Last Updated
            self.table.setItem(row, 10, QTableWidgetItem(record.get('last_updated', '')))
    
    def on_row_selected(self):
        """Handle row selection"""
        current_row = self.table.currentRow()
        if 0 <= current_row < len(self.current_data):
            selected_data = self.current_data[current_row]
            self.row_selected.emit(selected_data)
    
    def export_data(self):
        """Export current data to CSV"""
        if not self.current_data:
            QMessageBox.information(self, "Export", "No data to export")
            return
        
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Data", f"analytics_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "CSV Files (*.csv)"
            )
            
            if file_path:
                import csv
                
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    if self.current_data:
                        fieldnames = self.current_data[0].keys()
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(self.current_data)
                
                QMessageBox.information(self, "Export", f"Data exported successfully to:\n{file_path}")
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            QMessageBox.critical(self, "Export Error", f"Failed to export data:\n{str(e)}")

class DataExplorationWidget(QWidget):
    """Main data exploration widget combining filters and data display"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the data exploration UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Left panel - Filters
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #e9ecef;
                border-radius: 15px;
            }
        """)
        left_panel.setMaximumWidth(350)
        left_panel.setMinimumWidth(300)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Data filters
        self.data_filter = DataFilterWidget()
        left_layout.addWidget(self.data_filter)
        
        layout.addWidget(left_panel)
        
        # Right panel - Data table
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        right_panel.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 15px;
            }
        """)
        
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Data table
        self.data_table = DataTableWidget()
        right_layout.addWidget(self.data_table)
        
        layout.addWidget(right_panel)
        
    def setup_connections(self):
        """Setup signal connections"""
        self.data_filter.filters_changed.connect(self.data_table.update_data)
        
        # Apply initial filters
        self.data_filter.apply_filters()

def create_data_exploration_widget() -> DataExplorationWidget:
    """Factory function to create data exploration widget"""
    return DataExplorationWidget()
