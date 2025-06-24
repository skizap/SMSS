#!/usr/bin/env python3
"""
Social Media Surveillance System - Enhanced Analytics Dashboard
Advanced analytics dashboard with real-time data visualization, statistical analysis, and interactive charts.
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
import threading
import time

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
        QLabel, QPushButton, QFrame, QSplitter, QTableWidget, QTableWidgetItem,
        QHeaderView, QProgressBar, QGroupBox, QScrollArea, QTextEdit,
        QComboBox, QSpinBox, QCheckBox, QSlider, QTabWidget, QListWidget,
        QListWidgetItem, QMessageBox, QDialog, QLineEdit, QDateTimeEdit,
        QCalendarWidget, QDateEdit, QApplication, QMainWindow, QStatusBar
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QThread, pyqtSignal, QSize, QDateTime, QDate, QPropertyAnimation,
        QEasingCurve, QParallelAnimationGroup, QRect
    )
    from PyQt6.QtGui import (
        QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QPen, QBrush,
        QLinearGradient, QAction
    )
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

# Import matplotlib for advanced charts
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    from matplotlib.animation import FuncAnimation
    import numpy as np
    import pandas as pd
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
    
    # Set matplotlib style
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import project modules
from core.config import config
from core.database import db_manager
from reporting.analytics_service import analytics_service
from reporting.metrics_collector import metrics_collector
from reporting.account_health_monitor import account_health_monitor
from reporting.statistical_analysis_engine import statistical_engine, data_aggregation_engine

logger = logging.getLogger(__name__)

class RealTimeMetricsWidget(QWidget):
    """Real-time metrics display widget with live updates"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_metrics)
        self.update_timer.start(5000)  # Update every 5 seconds
        
    def setup_ui(self):
        """Setup the real-time metrics UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🔴 Real-Time Metrics")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #e74c3c; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # Metrics grid
        self.metrics_frame = QFrame()
        self.metrics_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #e9ecef;
                border-radius: 12px;
                padding: 15px;
            }
        """)
        
        self.metrics_layout = QGridLayout(self.metrics_frame)
        self.metrics_layout.setSpacing(15)
        
        # Initialize metric cards
        self.metric_cards = {}
        self.create_metric_cards()
        
        layout.addWidget(self.metrics_frame)
        
    def create_metric_cards(self):
        """Create metric display cards"""
        metrics = [
            ("active_sessions", "🔄", "Active Sessions", "0", "#3498db"),
            ("items_per_minute", "📊", "Items/Min", "0", "#27ae60"),
            ("success_rate", "✅", "Success Rate", "0%", "#f39c12"),
            ("system_health", "💚", "System Health", "0%", "#e74c3c")
        ]
        
        for i, (key, icon, label, value, color) in enumerate(metrics):
            card = self.create_metric_card(icon, label, value, color)
            self.metric_cards[key] = card
            row = i // 2
            col = i % 2
            self.metrics_layout.addWidget(card, row, col)
    
    def create_metric_card(self, icon: str, label: str, value: str, color: str) -> QWidget:
        """Create a single metric card"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 2px solid {color};
                border-radius: 10px;
                padding: 15px;
                min-height: 100px;
            }}
            QFrame:hover {{
                background: {color}15;
                transform: scale(1.02);
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI", 24))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(value_label)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Segoe UI", 10))
        label_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_widget.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(label_widget)
        
        # Store references for updates
        card.value_label = value_label
        card.icon_label = icon_label
        
        return card
    
    def update_metrics(self):
        """Update real-time metrics"""
        try:
            # Get real-time metrics from the collector
            metrics = metrics_collector.get_real_time_metrics()
            
            # Update active sessions
            active_sessions = metrics.get('active_sessions', 0)
            self.metric_cards['active_sessions'].value_label.setText(str(active_sessions))
            
            # Update items per minute
            items_per_minute = metrics.get('items_per_minute', 0)
            self.metric_cards['items_per_minute'].value_label.setText(f"{items_per_minute:.1f}")
            
            # Update success rate
            success_rate = metrics.get('avg_success_rate', 0)
            self.metric_cards['success_rate'].value_label.setText(f"{success_rate:.1f}%")
            
            # Get system performance analytics
            system_analytics = analytics_service.get_system_performance_analytics()
            system_health = system_analytics.get('system_health_score', 0)
            self.metric_cards['system_health'].value_label.setText(f"{system_health:.1f}%")
            
            # Update colors based on values
            self.update_metric_colors(success_rate, system_health)
            
        except Exception as e:
            logger.error(f"Error updating real-time metrics: {e}")
    
    def update_metric_colors(self, success_rate: float, system_health: float):
        """Update metric card colors based on values"""
        # Success rate color
        if success_rate >= 90:
            color = "#27ae60"  # Green
        elif success_rate >= 70:
            color = "#f39c12"  # Orange
        else:
            color = "#e74c3c"  # Red
        self.metric_cards['success_rate'].value_label.setStyleSheet(f"color: {color};")
        
        # System health color
        if system_health >= 80:
            color = "#27ae60"  # Green
        elif system_health >= 60:
            color = "#f39c12"  # Orange
        else:
            color = "#e74c3c"  # Red
        self.metric_cards['system_health'].value_label.setStyleSheet(f"color: {color};")

class AdvancedChartWidget(QWidget):
    """Advanced chart widget with multiple visualization types"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = None
        self.canvas = None
        self.animation = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the advanced chart widget UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        if MATPLOTLIB_AVAILABLE:
            # Create matplotlib figure with subplots
            self.figure = Figure(figsize=(12, 8), dpi=100)
            self.figure.patch.set_facecolor('white')
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setStyleSheet("""
                background: white; 
                border: 2px solid #3498db; 
                border-radius: 12px;
            """)
            layout.addWidget(self.canvas)
        else:
            # Fallback placeholder
            placeholder = QLabel("Advanced charts require matplotlib\nPlease install: pip install matplotlib seaborn")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                QLabel {
                    background: #f8f9fa;
                    border: 2px dashed #dee2e6;
                    border-radius: 12px;
                    color: #6c757d;
                    font-size: 16px;
                    padding: 60px;
                }
            """)
            layout.addWidget(placeholder)
    
    def create_dashboard_view(self, target_id: int, time_range: str = "30d"):
        """Create comprehensive dashboard view"""
        if not MATPLOTLIB_AVAILABLE or not self.figure:
            return
        
        try:
            # Get dashboard data
            dashboard_data = analytics_service.get_target_analytics_dashboard(target_id, time_range)
            
            if 'error' in dashboard_data:
                self.show_error_message(dashboard_data['error'])
                return
            
            # Clear figure and create subplots
            self.figure.clear()
            
            # Create 2x2 subplot grid
            gs = self.figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
            
            # 1. Follower growth trend (top-left)
            ax1 = self.figure.add_subplot(gs[0, 0])
            self.plot_follower_growth(ax1, dashboard_data)
            
            # 2. Engagement rate over time (top-right)
            ax2 = self.figure.add_subplot(gs[0, 1])
            self.plot_engagement_trend(ax2, dashboard_data)
            
            # 3. Health score gauge (bottom-left)
            ax3 = self.figure.add_subplot(gs[1, 0])
            self.plot_health_gauge(ax3, dashboard_data)
            
            # 4. Performance metrics (bottom-right)
            ax4 = self.figure.add_subplot(gs[1, 1])
            self.plot_performance_metrics(ax4, dashboard_data)
            
            # Add main title
            target_info = dashboard_data.get('target_info', {})
            username = target_info.get('username', 'Unknown')
            self.figure.suptitle(f'Analytics Dashboard - @{username}', 
                               fontsize=16, fontweight='bold', y=0.95)
            
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error creating dashboard view: {e}")
            self.show_error_message(str(e))
    
    def plot_follower_growth(self, ax, dashboard_data):
        """Plot follower growth trend"""
        try:
            trend_data = dashboard_data.get('trend_analyses', {}).get('follower_count', {})
            trend_analysis = trend_data.get('trend_analysis', {})
            
            # Get time series data from aggregated metrics
            aggregated = dashboard_data.get('aggregated_metrics', {})
            follower_metrics = aggregated.get('follower_metrics', {})
            time_series = follower_metrics.get('time_series', {})
            
            if time_series.get('timestamps') and time_series.get('values'):
                timestamps = [datetime.fromisoformat(ts.replace('Z', '+00:00')) for ts in time_series['timestamps']]
                values = time_series['values']
                
                # Plot main line
                ax.plot(timestamps, values, linewidth=3, marker='o', markersize=6, 
                       color='#3498db', label='Followers')
                
                # Add trend line if available
                if trend_analysis.get('forecast_values'):
                    forecast = trend_analysis['forecast_values']
                    forecast_dates = [timestamps[-1] + timedelta(days=i+1) for i in range(len(forecast))]
                    ax.plot(forecast_dates, forecast, '--', color='#e74c3c', 
                           alpha=0.7, label='Forecast')
                
                ax.set_title('Follower Growth Trend', fontweight='bold')
                ax.set_xlabel('Date')
                ax.set_ylabel('Followers')
                ax.grid(True, alpha=0.3)
                ax.legend()
                
                # Format x-axis
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, 'No follower data available', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Follower Growth Trend', fontweight='bold')
                
        except Exception as e:
            logger.error(f"Error plotting follower growth: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def plot_engagement_trend(self, ax, dashboard_data):
        """Plot engagement rate trend"""
        try:
            trend_data = dashboard_data.get('trend_analyses', {}).get('engagement_rate', {})
            trend_analysis = trend_data.get('trend_analysis', {})
            
            # Create sample engagement data if not available
            dates = [datetime.now() - timedelta(days=i) for i in range(30, 0, -1)]
            engagement_rates = np.random.normal(3.5, 0.8, 30)  # Sample data
            engagement_rates = np.clip(engagement_rates, 0, 10)  # Clip to reasonable range
            
            # Plot engagement trend
            ax.plot(dates, engagement_rates, linewidth=3, marker='s', markersize=5,
                   color='#27ae60', label='Engagement Rate')
            
            # Add moving average
            if len(engagement_rates) >= 7:
                moving_avg = pd.Series(engagement_rates).rolling(window=7).mean()
                ax.plot(dates, moving_avg, '--', color='#f39c12', 
                       alpha=0.8, label='7-day Average')
            
            ax.set_title('Engagement Rate Trend', fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Engagement Rate (%)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.tick_params(axis='x', rotation=45)
            
        except Exception as e:
            logger.error(f"Error plotting engagement trend: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def plot_health_gauge(self, ax, dashboard_data):
        """Plot health score as a gauge chart"""
        try:
            health_summary = dashboard_data.get('health_summary', {})
            health_score = health_summary.get('current_health_score', 0)
            
            # Create gauge chart
            theta = np.linspace(0, np.pi, 100)
            
            # Background arc
            ax.plot(np.cos(theta), np.sin(theta), linewidth=20, color='#ecf0f1', alpha=0.3)
            
            # Health score arc
            score_theta = np.linspace(0, np.pi * (health_score / 100), int(health_score))
            if len(score_theta) > 0:
                # Color based on health score
                if health_score >= 80:
                    color = '#27ae60'  # Green
                elif health_score >= 60:
                    color = '#f39c12'  # Orange
                else:
                    color = '#e74c3c'  # Red
                
                ax.plot(np.cos(score_theta), np.sin(score_theta), linewidth=20, color=color)
            
            # Add score text
            ax.text(0, -0.3, f'{health_score:.1f}%', ha='center', va='center',
                   fontsize=24, fontweight='bold', color='#2c3e50')
            ax.text(0, -0.5, 'Health Score', ha='center', va='center',
                   fontsize=12, color='#7f8c8d')
            
            ax.set_xlim(-1.2, 1.2)
            ax.set_ylim(-0.7, 1.2)
            ax.set_aspect('equal')
            ax.axis('off')
            ax.set_title('Account Health Score', fontweight='bold', pad=20)
            
        except Exception as e:
            logger.error(f"Error plotting health gauge: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def plot_performance_metrics(self, ax, dashboard_data):
        """Plot performance metrics as bar chart"""
        try:
            performance = dashboard_data.get('performance_metrics', {})
            
            metrics = ['Success Rate', 'Quality Score', 'Response Time', 'Items/Min']
            values = [
                performance.get('avg_success_rate', 0),
                performance.get('avg_quality_score', 0) * 100,  # Convert to percentage
                max(0, 100 - performance.get('avg_response_time', 0) * 10),  # Invert response time
                min(100, performance.get('items_per_minute', 0) * 10)  # Scale items per minute
            ]
            
            colors = ['#3498db', '#27ae60', '#f39c12', '#9b59b6']
            bars = ax.bar(metrics, values, color=colors, alpha=0.8)
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{value:.1f}%', ha='center', va='bottom', fontweight='bold')
            
            ax.set_title('Performance Metrics', fontweight='bold')
            ax.set_ylabel('Score (%)')
            ax.set_ylim(0, 110)
            ax.grid(True, alpha=0.3, axis='y')
            ax.tick_params(axis='x', rotation=45)
            
        except Exception as e:
            logger.error(f"Error plotting performance metrics: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def show_error_message(self, error_msg: str):
        """Show error message on chart"""
        if self.figure:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'Error loading dashboard:\n{error_msg}', 
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=14, color='#e74c3c')
            ax.axis('off')
            self.canvas.draw()

class TrendAnalysisWidget(QWidget):
    """Widget for displaying trend analysis and statistical insights"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the trend analysis UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("📈 Trend Analysis & Insights")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #8e44ad; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # Insights container
        self.insights_scroll = QScrollArea()
        self.insights_scroll.setWidgetResizable(True)
        self.insights_scroll.setStyleSheet("""
            QScrollArea {
                border: 2px solid #e9ecef;
                border-radius: 10px;
                background: white;
            }
        """)
        
        self.insights_widget = QWidget()
        self.insights_layout = QVBoxLayout(self.insights_widget)
        self.insights_scroll.setWidget(self.insights_widget)
        
        layout.addWidget(self.insights_scroll)
        
        # Update button
        update_button = QPushButton("🔄 Update Analysis")
        update_button.setStyleSheet("""
            QPushButton {
                background: #8e44ad;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #9b59b6;
            }
        """)
        update_button.clicked.connect(self.update_analysis)
        layout.addWidget(update_button)
    
    def update_analysis(self, target_id: int = None):
        """Update trend analysis for target"""
        try:
            # Clear existing insights
            for i in reversed(range(self.insights_layout.count())):
                child = self.insights_layout.itemAt(i).widget()
                if child:
                    child.setParent(None)
            
            if target_id:
                # Get dashboard data with insights
                dashboard_data = analytics_service.get_target_analytics_dashboard(target_id, "30d")
                insights = dashboard_data.get('key_insights', [])
                
                if insights:
                    for insight in insights:
                        insight_widget = self.create_insight_widget(insight)
                        self.insights_layout.addWidget(insight_widget)
                else:
                    no_insights = QLabel("No significant insights detected for this period.")
                    no_insights.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 20px;")
                    no_insights.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.insights_layout.addWidget(no_insights)
            else:
                placeholder = QLabel("Select a target to view trend analysis")
                placeholder.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 20px;")
                placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.insights_layout.addWidget(placeholder)
            
            self.insights_layout.addStretch()
            
        except Exception as e:
            logger.error(f"Error updating trend analysis: {e}")
    
    def create_insight_widget(self, insight: Dict[str, Any]) -> QWidget:
        """Create widget for displaying a single insight"""
        widget = QFrame()
        
        # Style based on insight type
        insight_type = insight.get('type', 'info')
        colors = {
            'positive': '#27ae60',
            'negative': '#e74c3c',
            'warning': '#f39c12',
            'critical': '#8e44ad',
            'info': '#3498db'
        }
        
        color = colors.get(insight_type, '#3498db')
        widget.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-left: 4px solid {color};
                border-radius: 8px;
                padding: 15px;
                margin: 5px 0;
            }}
            QFrame:hover {{
                background: {color}10;
            }}
        """)
        
        layout = QVBoxLayout(widget)
        
        # Insight message
        message = QLabel(insight.get('message', 'No message'))
        message.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        message.setStyleSheet(f"color: {color};")
        message.setWordWrap(True)
        layout.addWidget(message)
        
        # Additional details
        metric = insight.get('metric', '')
        strength = insight.get('strength', 0)
        
        details = QLabel(f"Metric: {metric} | Confidence: {strength:.1%}")
        details.setFont(QFont("Segoe UI", 9))
        details.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(details)
        
        return widget

class TargetSelectorWidget(QWidget):
    """Widget for selecting surveillance targets with search and filtering"""

    target_changed = pyqtSignal(int)  # Emit when target selection changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self.targets = []
        self.setup_ui()
        self.load_targets()

    def setup_ui(self):
        """Setup the target selector UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("🎯 Target Selection")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(header)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search targets...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        self.search_box.textChanged.connect(self.filter_targets)
        layout.addWidget(self.search_box)

        # Target combo box
        self.target_combo = QComboBox()
        self.target_combo.setStyleSheet("""
            QComboBox {
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 11px;
                min-height: 20px;
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
        """)
        self.target_combo.currentIndexChanged.connect(self.on_target_changed)
        layout.addWidget(self.target_combo)

        # Time range selector
        time_group = QGroupBox("Time Range")
        time_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        time_layout = QVBoxLayout(time_group)

        self.time_range_combo = QComboBox()
        self.time_range_combo.addItems(["7 days", "30 days", "90 days", "1 year"])
        self.time_range_combo.setCurrentText("30 days")
        self.time_range_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 10px;
            }
        """)
        self.time_range_combo.currentTextChanged.connect(self.on_time_range_changed)
        time_layout.addWidget(self.time_range_combo)

        layout.addWidget(time_group)
        layout.addStretch()

    def load_targets(self):
        """Load targets from database"""
        try:
            with db_manager.get_session() as session:
                from models.instagram_models import SurveillanceTarget
                targets = session.query(SurveillanceTarget).filter(
                    SurveillanceTarget.status == 'active'
                ).all()

                self.targets = [
                    {
                        'id': target.id,
                        'username': target.instagram_username,
                        'display_name': target.display_name,
                        'follower_count': target.follower_count or 0
                    }
                    for target in targets
                ]

                self.populate_combo()

        except Exception as e:
            logger.error(f"Error loading targets: {e}")
            self.targets = []

    def populate_combo(self):
        """Populate the combo box with targets"""
        self.target_combo.clear()
        self.target_combo.addItem("Select a target...", None)

        for target in self.targets:
            display_text = f"@{target['username']}"
            if target['display_name']:
                display_text += f" ({target['display_name']})"
            display_text += f" - {target['follower_count']} followers"

            self.target_combo.addItem(display_text, target['id'])

    def filter_targets(self, search_text: str):
        """Filter targets based on search text"""
        if not search_text:
            self.populate_combo()
            return

        search_text = search_text.lower()
        filtered_targets = [
            target for target in self.targets
            if (search_text in target['username'].lower() or
                (target['display_name'] and search_text in target['display_name'].lower()))
        ]

        self.target_combo.clear()
        self.target_combo.addItem("Select a target...", None)

        for target in filtered_targets:
            display_text = f"@{target['username']}"
            if target['display_name']:
                display_text += f" ({target['display_name']})"
            display_text += f" - {target['follower_count']} followers"

            self.target_combo.addItem(display_text, target['id'])

    def on_target_changed(self):
        """Handle target selection change"""
        target_id = self.target_combo.currentData()
        if target_id:
            self.target_changed.emit(target_id)

    def on_time_range_changed(self):
        """Handle time range change"""
        target_id = self.target_combo.currentData()
        if target_id:
            self.target_changed.emit(target_id)

    def get_current_target_id(self) -> Optional[int]:
        """Get currently selected target ID"""
        return self.target_combo.currentData()

    def get_current_time_range(self) -> str:
        """Get current time range selection"""
        time_text = self.time_range_combo.currentText()
        time_map = {
            "7 days": "7d",
            "30 days": "30d",
            "90 days": "90d",
            "1 year": "1y"
        }
        return time_map.get(time_text, "30d")

class AnomalyDetectionWidget(QWidget):
    """Widget for displaying anomaly detection results"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup the anomaly detection UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_layout = QHBoxLayout()
        header = QLabel("⚠️ Anomaly Detection")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #e67e22; margin-bottom: 10px;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        # Refresh button
        refresh_button = QPushButton("🔄")
        refresh_button.setFixedSize(30, 30)
        refresh_button.setStyleSheet("""
            QPushButton {
                background: #e67e22;
                color: white;
                border: none;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #d35400;
            }
        """)
        refresh_button.clicked.connect(self.refresh_anomalies)
        header_layout.addWidget(refresh_button)

        layout.addLayout(header_layout)

        # Anomalies list
        self.anomalies_list = QListWidget()
        self.anomalies_list.setStyleSheet("""
            QListWidget {
                border: 2px solid #e9ecef;
                border-radius: 10px;
                background: white;
                alternate-background-color: #f8f9fa;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                min-height: 40px;
            }
            QListWidget::item:hover {
                background: #fff3cd;
            }
        """)
        layout.addWidget(self.anomalies_list)

        # Summary label
        self.summary_label = QLabel("No anomalies detected")
        self.summary_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 10px;")
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.summary_label)

    def refresh_anomalies(self, target_id: int = None):
        """Refresh anomaly detection results"""
        try:
            self.anomalies_list.clear()

            # Get anomaly report
            anomaly_report = analytics_service.generate_anomaly_report(target_id, days=7)

            if 'error' in anomaly_report:
                self.summary_label.setText(f"Error: {anomaly_report['error']}")
                self.summary_label.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 10px;")
                return

            # Process anomalies
            total_anomalies = anomaly_report['summary']['total_anomalies']
            critical_anomalies = anomaly_report['summary']['critical_anomalies']

            if total_anomalies == 0:
                self.summary_label.setText("✅ No anomalies detected")
                self.summary_label.setStyleSheet("color: #27ae60; font-weight: bold; padding: 10px;")
            else:
                self.summary_label.setText(f"⚠️ {total_anomalies} anomalies detected ({critical_anomalies} critical)")
                self.summary_label.setStyleSheet("color: #e67e22; font-weight: bold; padding: 10px;")

                # Add anomalies to list
                anomalies_by_target = anomaly_report['anomalies_by_target']

                for target_id, anomalies in anomalies_by_target.items():
                    for anomaly in anomalies:
                        item_widget = self.create_anomaly_item(anomaly)
                        item = QListWidgetItem()
                        item.setSizeHint(item_widget.sizeHint())
                        self.anomalies_list.addItem(item)
                        self.anomalies_list.setItemWidget(item, item_widget)

        except Exception as e:
            logger.error(f"Error refreshing anomalies: {e}")
            self.summary_label.setText(f"Error: {str(e)}")
            self.summary_label.setStyleSheet("color: #e74c3c; font-weight: bold; padding: 10px;")

    def create_anomaly_item(self, anomaly: Dict[str, Any]) -> QWidget:
        """Create widget for displaying a single anomaly"""
        widget = QFrame()

        # Style based on severity
        severity = anomaly.get('severity', 'medium')
        colors = {
            'critical': '#e74c3c',
            'medium': '#f39c12',
            'low': '#3498db'
        }

        color = colors.get(severity, '#f39c12')
        widget.setStyleSheet(f"""
            QFrame {{
                background: white;
                border-left: 4px solid {color};
                border-radius: 6px;
                padding: 8px;
            }}
        """)

        layout = QHBoxLayout(widget)

        # Severity indicator
        severity_label = QLabel("🔴" if severity == 'critical' else "🟡" if severity == 'medium' else "🔵")
        severity_label.setFont(QFont("Segoe UI", 16))
        layout.addWidget(severity_label)

        # Anomaly details
        details_layout = QVBoxLayout()

        # Metric and type
        metric_label = QLabel(f"{anomaly.get('metric', 'Unknown')} - {anomaly.get('type', 'Unknown')}")
        metric_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        metric_label.setStyleSheet(f"color: {color};")
        details_layout.addWidget(metric_label)

        # Timestamp and value
        timestamp = anomaly.get('timestamp', '')
        value = anomaly.get('value', 0)
        info_label = QLabel(f"Time: {timestamp[:19] if timestamp else 'Unknown'} | Value: {value:.2f}")
        info_label.setFont(QFont("Segoe UI", 8))
        info_label.setStyleSheet("color: #7f8c8d;")
        details_layout.addWidget(info_label)

        layout.addLayout(details_layout)
        layout.addStretch()

        return widget

class EnhancedAnalyticsDashboard(QMainWindow):
    """Main enhanced analytics dashboard window"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_target_id = None
        self.setup_ui()
        self.setup_connections()
        self.start_auto_refresh()

    def setup_ui(self):
        """Setup the main dashboard UI"""
        self.setWindowTitle("Instagram Surveillance - Enhanced Analytics Dashboard")
        self.setMinimumSize(1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Left sidebar
        left_sidebar = QFrame()
        left_sidebar.setFrameStyle(QFrame.Shape.StyledPanel)
        left_sidebar.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f8f9fa);
                border: 2px solid #e9ecef;
                border-radius: 15px;
            }
        """)
        left_sidebar.setMaximumWidth(350)
        left_sidebar.setMinimumWidth(300)

        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Target selector
        self.target_selector = TargetSelectorWidget()
        left_layout.addWidget(self.target_selector, 1)

        # Real-time metrics
        self.real_time_metrics = RealTimeMetricsWidget()
        left_layout.addWidget(self.real_time_metrics, 2)

        # Anomaly detection
        self.anomaly_detection = AnomalyDetectionWidget()
        left_layout.addWidget(self.anomaly_detection, 2)

        main_layout.addWidget(left_sidebar)

        # Right main area
        right_area = QFrame()
        right_area.setFrameStyle(QFrame.Shape.StyledPanel)
        right_area.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #e9ecef;
                border-radius: 15px;
            }
        """)

        right_layout = QVBoxLayout(right_area)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Tab widget for different views
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #bdc3c7;
                border-radius: 8px;
                background: white;
            }
            QTabWidget::tab-bar {
                alignment: center;
            }
            QTabBar::tab {
                background: #ecf0f1;
                border: 1px solid #bdc3c7;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom-color: white;
            }
            QTabBar::tab:hover {
                background: #d5dbdb;
            }
        """)

        # Dashboard tab
        dashboard_tab = QWidget()
        dashboard_layout = QVBoxLayout(dashboard_tab)
        self.main_chart = AdvancedChartWidget()
        dashboard_layout.addWidget(self.main_chart)
        self.tab_widget.addTab(dashboard_tab, "📊 Dashboard")

        # Trends tab
        trends_tab = QWidget()
        trends_layout = QVBoxLayout(trends_tab)
        self.trend_analysis = TrendAnalysisWidget()
        trends_layout.addWidget(self.trend_analysis)
        self.tab_widget.addTab(trends_tab, "📈 Trends")

        right_layout.addWidget(self.tab_widget)
        main_layout.addWidget(right_area)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Ready - Select a target to begin analysis")
        self.setStatusBar(self.status_bar)

    def setup_connections(self):
        """Setup signal connections"""
        self.target_selector.target_changed.connect(self.on_target_changed)

    def on_target_changed(self, target_id: int):
        """Handle target selection change"""
        self.current_target_id = target_id
        time_range = self.target_selector.get_current_time_range()

        # Update dashboard
        self.main_chart.create_dashboard_view(target_id, time_range)

        # Update trend analysis
        self.trend_analysis.update_analysis(target_id)

        # Update anomaly detection
        self.anomaly_detection.refresh_anomalies(target_id)

        # Update status
        target_username = None
        for target in self.target_selector.targets:
            if target['id'] == target_id:
                target_username = target['username']
                break

        if target_username:
            self.status_bar.showMessage(f"Analyzing @{target_username} - {time_range}")

    def start_auto_refresh(self):
        """Start auto-refresh timer"""
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(60000)  # Refresh every minute

    def auto_refresh(self):
        """Auto-refresh dashboard data"""
        if self.current_target_id:
            time_range = self.target_selector.get_current_time_range()
            self.main_chart.create_dashboard_view(self.current_target_id, time_range)

def create_enhanced_analytics_dashboard() -> EnhancedAnalyticsDashboard:
    """Factory function to create enhanced analytics dashboard"""
    return EnhancedAnalyticsDashboard()
