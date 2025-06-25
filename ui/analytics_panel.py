#!/usr/bin/env python3
"""
Social Media Surveillance System - Analytics Panel
Advanced analytics panel with data visualization, charts, and statistical analysis.
Provides comprehensive insights into surveillance data and trends.
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import json

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QFrame, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QGroupBox, QScrollArea, QTextEdit,
    QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QListWidget,
    QListWidgetItem, QMessageBox, QDialog, QLineEdit, QDateTimeEdit,
    QCalendarWidget, QDateEdit
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QDateTime, QDate
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QPen, QBrush
)

# Import matplotlib for charts
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    import pandas as pd
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("Matplotlib not available - charts will be disabled")

# Import project modules
from core.data_manager import DataManager
from models.instagram_models import SurveillanceTarget, Post, Follower
from reporting.analytics_service import analytics_service
from reporting.metrics_collector import metrics_collector
from reporting.account_health_monitor import account_health_monitor

logger = logging.getLogger(__name__)

class ChartWidget(QWidget):
    """Base widget for displaying charts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = None
        self.canvas = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the chart widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        if MATPLOTLIB_AVAILABLE:
            # Create matplotlib figure and canvas
            self.figure = Figure(figsize=(8, 6), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setStyleSheet("background: white; border: 1px solid #ddd; border-radius: 8px;")
            layout.addWidget(self.canvas)
        else:
            # Fallback placeholder
            placeholder = QLabel("Charts require matplotlib\nPlease install: pip install matplotlib")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    background: #f8f9fa;
                    border: 2px dashed #dee2e6;
                    border-radius: 8px;
                    color: #6c757d;
                    font-size: 14px;
                    padding: 40px;
                }
            """)
            layout.addWidget(placeholder)
            
    def clear_chart(self):
        """Clear the current chart"""
        if self.figure:
            self.figure.clear()
            if self.canvas:
                self.canvas.draw()
                
    def update_chart(self, chart_type: str, data: dict, title: str = ""):
        """Update the chart with new data"""
        if not MATPLOTLIB_AVAILABLE or not self.figure:
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        try:
            if chart_type == "line":
                self.create_line_chart(ax, data, title)
            elif chart_type == "bar":
                self.create_bar_chart(ax, data, title)
            elif chart_type == "pie":
                self.create_pie_chart(ax, data, title)
            elif chart_type == "scatter":
                self.create_scatter_chart(ax, data, title)
            else:
                ax.text(0.5, 0.5, f"Chart type '{chart_type}' not supported", 
                       ha='center', va='center', transform=ax.transAxes)
                
            self.figure.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            ax.text(0.5, 0.5, f"Error creating chart:\n{str(e)}", 
                   ha='center', va='center', transform=ax.transAxes)
            self.canvas.draw()
            
    def create_line_chart(self, ax, data: dict, title: str):
        """Create a line chart"""
        x_data = data.get('x', [])
        y_data = data.get('y', [])
        
        if x_data and y_data:
            ax.plot(x_data, y_data, marker='o', linewidth=2, markersize=6)
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(data.get('xlabel', 'X'))
            ax.set_ylabel(data.get('ylabel', 'Y'))
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels if they're dates
            if x_data and isinstance(x_data[0], (datetime, str)):
                ax.tick_params(axis='x', rotation=45)
                
    def create_bar_chart(self, ax, data: dict, title: str):
        """Create a bar chart"""
        x_data = data.get('x', [])
        y_data = data.get('y', [])
        
        if x_data and y_data:
            bars = ax.bar(x_data, y_data, color='#4a90e2', alpha=0.8)
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(data.get('xlabel', 'Categories'))
            ax.set_ylabel(data.get('ylabel', 'Values'))
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}', ha='center', va='bottom')
                       
            ax.tick_params(axis='x', rotation=45)
            
    def create_pie_chart(self, ax, data: dict, title: str):
        """Create a pie chart"""
        labels = data.get('labels', [])
        values = data.get('values', [])
        
        if labels and values:
            colors = ['#4a90e2', '#50c878', '#ffa500', '#ff6b6b', '#9b59b6']
            ax.pie(values, labels=labels, autopct='%1.1f%%', 
                  colors=colors[:len(values)], startangle=90)
            ax.set_title(title, fontsize=14, fontweight='bold')
            
    def create_scatter_chart(self, ax, data: dict, title: str):
        """Create a scatter chart"""
        x_data = data.get('x', [])
        y_data = data.get('y', [])
        
        if x_data and y_data:
            ax.scatter(x_data, y_data, alpha=0.6, s=50, color='#4a90e2')
            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel(data.get('xlabel', 'X'))
            ax.set_ylabel(data.get('ylabel', 'Y'))
            ax.grid(True, alpha=0.3)

class AnalyticsControlWidget(QWidget):
    """Widget for analytics controls and filters"""
    
    filters_changed = pyqtSignal(dict)  # Emit when filters change
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the analytics controls UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("📊 Analytics Controls")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Filters group
        filters_group = QGroupBox("Filters")
        filters_layout = QFormLayout(filters_group)
        
        # Target selection
        self.target_combo = QComboBox()
        self.target_combo.addItem("All Targets", "all")
        self.target_combo.currentTextChanged.connect(self.on_filters_changed)
        filters_layout.addRow("Target:", self.target_combo)
        
        # Date range
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.on_filters_changed)
        filters_layout.addRow("From:", self.date_from)
        
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.on_filters_changed)
        filters_layout.addRow("To:", self.date_to)
        
        # Metric selection
        self.metric_combo = QComboBox()
        self.metric_combo.addItems([
            "Follower Growth",
            "Post Engagement",
            "Story Views",
            "Activity Timeline",
            "Engagement Rate"
        ])
        self.metric_combo.currentTextChanged.connect(self.on_filters_changed)
        filters_layout.addRow("Metric:", self.metric_combo)
        
        layout.addWidget(filters_group)
        
        # Chart type selection
        chart_group = QGroupBox("Chart Type")
        chart_layout = QVBoxLayout(chart_group)
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Line Chart", "Bar Chart", "Pie Chart", "Scatter Plot"])
        self.chart_type_combo.currentTextChanged.connect(self.on_filters_changed)
        chart_layout.addWidget(self.chart_type_combo)
        
        layout.addWidget(chart_group)
        
        # Action buttons
        button_layout = QVBoxLayout()
        
        refresh_button = QPushButton("🔄 Refresh Data")
        refresh_button.setStyleSheet("""
            QPushButton {
                background: #4a90e2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        refresh_button.clicked.connect(self.on_filters_changed)
        button_layout.addWidget(refresh_button)
        
        export_button = QPushButton("📊 Export Chart")
        export_button.setStyleSheet("""
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
        export_button.clicked.connect(self.export_chart)
        button_layout.addWidget(export_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def populate_targets(self, targets: List[dict]):
        """Populate the target combo box"""
        self.target_combo.clear()
        self.target_combo.addItem("All Targets", "all")
        
        for target in targets:
            self.target_combo.addItem(
                f"@{target['username']}", 
                target['id']
            )
            
    def get_current_filters(self) -> dict:
        """Get current filter settings"""
        # Convert QDate to Python date properly
        date_from = self.date_from.date()
        date_to = self.date_to.date()

        # Convert QDate to Python date
        if hasattr(date_from, 'toPython'):
            date_from = date_from.toPython()
        else:
            # For newer PyQt6 versions, use toPyDate()
            date_from = date_from.toPyDate() if hasattr(date_from, 'toPyDate') else date(date_from.year(), date_from.month(), date_from.day())

        if hasattr(date_to, 'toPython'):
            date_to = date_to.toPython()
        else:
            # For newer PyQt6 versions, use toPyDate()
            date_to = date_to.toPyDate() if hasattr(date_to, 'toPyDate') else date(date_to.year(), date_to.month(), date_to.day())

        return {
            'target_id': self.target_combo.currentData(),
            'date_from': date_from,
            'date_to': date_to,
            'metric': self.metric_combo.currentText(),
            'chart_type': self.chart_type_combo.currentText().lower().replace(' ', '_')
        }
        
    def on_filters_changed(self):
        """Handle filter changes"""
        filters = self.get_current_filters()
        self.filters_changed.emit(filters)
        
    def export_chart(self):
        """Export current chart"""
        QMessageBox.information(self, "Export", "Chart export functionality will be implemented")

class StatsSummaryWidget(QWidget):
    """Widget displaying summary statistics"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the stats summary UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("📈 Summary Statistics")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Stats grid
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        self.stats_layout = QGridLayout(self.stats_frame)
        
        # Initialize with placeholder stats
        self.update_stats({
            'total_targets': 0,
            'total_posts': 0,
            'total_followers': 0,
            'avg_engagement': 0.0
        })
        
        layout.addWidget(self.stats_frame)
        layout.addStretch()
        
    def update_stats(self, stats: dict):
        """Update the statistics display"""
        # Clear existing widgets
        for i in reversed(range(self.stats_layout.count())):
            self.stats_layout.itemAt(i).widget().setParent(None)
            
        # Create stat items
        stat_items = [
            ("🎯", "Targets", stats.get('total_targets', 0)),
            ("📝", "Posts", stats.get('total_posts', 0)),
            ("👥", "Followers", stats.get('total_followers', 0)),
            ("💝", "Avg Engagement", f"{stats.get('avg_engagement', 0):.1f}%")
        ]
        
        for i, (icon, label, value) in enumerate(stat_items):
            stat_widget = self.create_stat_item(icon, label, str(value))
            row = i // 2
            col = i % 2
            self.stats_layout.addWidget(stat_widget, row, col)
            
    def create_stat_item(self, icon: str, label: str, value: str) -> QWidget:
        """Create a single stat item widget"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 10px;
            }
            QFrame:hover {
                background: #e9ecef;
            }
        """)
        widget.setMinimumHeight(80)
        
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 20))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet("color: #2c3e50;")
        layout.addWidget(value_label)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Segoe UI", 9))
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_widget.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(label_widget)
        
        return widget

class AnalyticsDataProcessor:
    """Processes data for analytics visualization"""

    def __init__(self):
        self.data_manager = DataManager()

    def get_follower_growth_data(self, target_id: str, date_from: datetime, date_to: datetime) -> dict:
        """Get follower growth data for visualization"""
        try:
            if target_id == "all":
                # Get data for all targets
                data = self.data_manager.get_follower_growth_all_targets(date_from, date_to)
            else:
                # Get data for specific target
                data = self.data_manager.get_follower_growth_by_target(target_id, date_from, date_to)

            if not data:
                return {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Followers'}

            # Process data for chart
            dates = [item['date'] for item in data]
            counts = [item['follower_count'] for item in data]

            return {
                'x': dates,
                'y': counts,
                'xlabel': 'Date',
                'ylabel': 'Followers'
            }

        except Exception as e:
            logger.error(f"Error getting follower growth data: {e}")
            return {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Followers'}

    def get_engagement_data(self, target_id: str, date_from: datetime, date_to: datetime) -> dict:
        """Get engagement data for visualization"""
        try:
            if target_id == "all":
                data = self.data_manager.get_engagement_data_all_targets(date_from, date_to)
            else:
                data = self.data_manager.get_engagement_data_by_target(target_id, date_from, date_to)

            if not data:
                return {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Engagement Rate (%)'}

            # Process data
            dates = [item['date'] for item in data]
            rates = [item['engagement_rate'] * 100 for item in data]  # Convert to percentage

            return {
                'x': dates,
                'y': rates,
                'xlabel': 'Date',
                'ylabel': 'Engagement Rate (%)'
            }

        except Exception as e:
            logger.error(f"Error getting engagement data: {e}")
            return {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Engagement Rate (%)'}

    def get_post_type_distribution(self, target_id: str, date_from: datetime, date_to: datetime) -> dict:
        """Get post type distribution for pie chart"""
        try:
            if target_id == "all":
                data = self.data_manager.get_post_type_distribution_all_targets(date_from, date_to)
            else:
                data = self.data_manager.get_post_type_distribution_by_target(target_id, date_from, date_to)

            if not data:
                return {'labels': [], 'values': []}

            labels = [item['post_type'].title() for item in data]
            values = [item['count'] for item in data]

            return {
                'labels': labels,
                'values': values
            }

        except Exception as e:
            logger.error(f"Error getting post type distribution: {e}")
            return {'labels': [], 'values': []}

    def get_activity_timeline(self, target_id: str, date_from: datetime, date_to: datetime) -> dict:
        """Get activity timeline data"""
        try:
            if target_id == "all":
                data = self.data_manager.get_activity_timeline_all_targets(date_from, date_to)
            else:
                data = self.data_manager.get_activity_timeline_by_target(target_id, date_from, date_to)

            if not data:
                return {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Activity Count'}

            dates = [item['date'] for item in data]
            counts = [item['activity_count'] for item in data]

            return {
                'x': dates,
                'y': counts,
                'xlabel': 'Date',
                'ylabel': 'Activity Count'
            }

        except Exception as e:
            logger.error(f"Error getting activity timeline: {e}")
            return {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Activity Count'}

    def get_summary_stats(self, target_id: str, date_from: datetime, date_to: datetime) -> dict:
        """Get summary statistics"""
        try:
            if target_id == "all":
                stats = self.data_manager.get_summary_stats_all_targets(date_from, date_to)
            else:
                stats = self.data_manager.get_summary_stats_by_target(target_id, date_from, date_to)

            return stats or {
                'total_targets': 0,
                'total_posts': 0,
                'total_followers': 0,
                'avg_engagement': 0.0
            }

        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return {
                'total_targets': 0,
                'total_posts': 0,
                'total_followers': 0,
                'avg_engagement': 0.0
            }

class AnalyticsPanel(QWidget):
    """Main analytics panel widget"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_processor = AnalyticsDataProcessor()
        self.setup_ui()
        self.load_initial_data()

    def setup_ui(self):
        """Setup the analytics panel UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Left panel - Controls and stats
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.Shape.StyledPanel)
        left_panel.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 10px;
                border: 1px solid #ddd;
            }
        """)
        left_panel.setMaximumWidth(300)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Analytics controls
        self.analytics_controls = AnalyticsControlWidget()
        self.analytics_controls.filters_changed.connect(self.update_analytics)
        left_layout.addWidget(self.analytics_controls, 2)

        # Summary stats
        self.stats_summary = StatsSummaryWidget()
        left_layout.addWidget(self.stats_summary, 1)

        layout.addWidget(left_panel)

        # Right panel - Charts and visualizations
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
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Chart title
        self.chart_title = QLabel("📊 Analytics Visualization")
        self.chart_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.chart_title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        right_layout.addWidget(self.chart_title)

        # Main chart
        self.main_chart = ChartWidget()
        right_layout.addWidget(self.main_chart)

        layout.addWidget(right_panel)

    def load_initial_data(self):
        """Load initial data for the analytics panel"""
        try:
            # Load targets for the combo box
            data_manager = DataManager()
            targets = data_manager.get_all_targets()

            target_data = [
                {'id': target.id, 'username': target.instagram_username}
                for target in targets
            ]

            self.analytics_controls.populate_targets(target_data)

            # Load initial analytics
            self.update_analytics()

        except Exception as e:
            logger.error(f"Error loading initial data: {e}")

    def update_analytics(self):
        """Update analytics based on current filters"""
        try:
            filters = self.analytics_controls.get_current_filters()

            # Convert dates to datetime
            date_from = datetime.combine(filters['date_from'], datetime.min.time())
            date_to = datetime.combine(filters['date_to'], datetime.max.time())

            # Get data based on selected metric
            metric = filters['metric']
            target_id = filters['target_id']
            chart_type = filters['chart_type'].replace('_chart', '').replace('_plot', '')

            if metric == "Follower Growth":
                data = self.data_processor.get_follower_growth_data(target_id, date_from, date_to)
                title = "Follower Growth Over Time"
                chart_type = "line"  # Force line chart for growth

            elif metric == "Post Engagement":
                data = self.data_processor.get_engagement_data(target_id, date_from, date_to)
                title = "Engagement Rate Over Time"
                chart_type = "line"  # Force line chart for engagement

            elif metric == "Story Views":
                # Placeholder for story views data
                data = {'x': [], 'y': [], 'xlabel': 'Date', 'ylabel': 'Story Views'}
                title = "Story Views Over Time"

            elif metric == "Activity Timeline":
                data = self.data_processor.get_activity_timeline(target_id, date_from, date_to)
                title = "Activity Timeline"
                chart_type = "bar"  # Force bar chart for activity

            elif metric == "Engagement Rate":
                data = self.data_processor.get_post_type_distribution(target_id, date_from, date_to)
                title = "Post Type Distribution"
                chart_type = "pie"  # Force pie chart for distribution

            else:
                data = {'x': [], 'y': []}
                title = "No Data Available"

            # Update chart
            self.main_chart.update_chart(chart_type, data, title)
            self.chart_title.setText(f"📊 {title}")

            # Update summary stats
            stats = self.data_processor.get_summary_stats(target_id, date_from, date_to)
            self.stats_summary.update_stats(stats)

        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
            self.main_chart.clear_chart()
            self.chart_title.setText("📊 Error Loading Analytics")

def create_analytics_panel() -> AnalyticsPanel:
    """Factory function to create analytics panel"""
    return AnalyticsPanel()
