#!/usr/bin/env python3
"""
Social Media Surveillance System - Comparison Dashboard
Multi-target comparison dashboard with correlation analysis and competitive insights.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
        QHeaderView, QGroupBox, QScrollArea, QCheckBox, QComboBox,
        QTabWidget, QSplitter, QListWidget, QListWidgetItem
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import numpy as np
    import seaborn as sns
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from core.database import db_manager
from reporting.analytics_service import analytics_service

logger = logging.getLogger(__name__)

class TargetSelectionWidget(QWidget):
    """Widget for selecting multiple targets for comparison"""
    
    selection_changed = pyqtSignal(list)  # Emit list of selected target IDs
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.targets = []
        self.selected_targets = []
        self.setup_ui()
        self.load_targets()
        
    def setup_ui(self):
        """Setup the target selection UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🎯 Select Targets for Comparison")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        layout.addWidget(header)
        
        # Target list with checkboxes
        self.target_list = QScrollArea()
        self.target_list.setWidgetResizable(True)
        self.target_list.setStyleSheet("""
            QScrollArea {
                border: 2px solid #e9ecef;
                border-radius: 10px;
                background: white;
            }
        """)
        
        self.target_widget = QWidget()
        self.target_layout = QVBoxLayout(self.target_widget)
        self.target_list.setWidget(self.target_widget)
        
        layout.addWidget(self.target_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
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
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setStyleSheet("""
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
        clear_all_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_all_btn)
        
        layout.addLayout(button_layout)
        
        # Selected count
        self.count_label = QLabel("0 targets selected")
        self.count_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 5px;")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.count_label)
        
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
                        'follower_count': target.follower_count or 0,
                        'category': target.category
                    }
                    for target in targets
                ]
                
                self.populate_target_list()
                
        except Exception as e:
            logger.error(f"Error loading targets: {e}")
            self.targets = []
    
    def populate_target_list(self):
        """Populate the target list with checkboxes"""
        # Clear existing widgets
        for i in reversed(range(self.target_layout.count())):
            child = self.target_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        # Add target checkboxes
        for target in self.targets:
            checkbox = QCheckBox()
            checkbox.setStyleSheet("""
                QCheckBox {
                    font-size: 11px;
                    padding: 8px;
                }
                QCheckBox::indicator {
                    width: 18px;
                    height: 18px;
                }
                QCheckBox::indicator:unchecked {
                    border: 2px solid #bdc3c7;
                    border-radius: 3px;
                    background: white;
                }
                QCheckBox::indicator:checked {
                    border: 2px solid #3498db;
                    border-radius: 3px;
                    background: #3498db;
                }
            """)
            
            # Create display text
            display_text = f"@{target['username']}"
            if target['display_name']:
                display_text += f" ({target['display_name']})"
            display_text += f" - {target['follower_count']:,} followers"
            if target['category']:
                display_text += f" [{target['category']}]"
            
            checkbox.setText(display_text)
            checkbox.setProperty('target_id', target['id'])
            checkbox.stateChanged.connect(self.on_selection_changed)
            
            self.target_layout.addWidget(checkbox)
        
        self.target_layout.addStretch()
    
    def on_selection_changed(self):
        """Handle target selection change"""
        self.selected_targets = []
        
        for i in range(self.target_layout.count()):
            widget = self.target_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox) and widget.isChecked():
                target_id = widget.property('target_id')
                if target_id:
                    self.selected_targets.append(target_id)
        
        # Update count label
        count = len(self.selected_targets)
        self.count_label.setText(f"{count} target{'s' if count != 1 else ''} selected")
        
        # Emit signal
        self.selection_changed.emit(self.selected_targets)
    
    def select_all(self):
        """Select all targets"""
        for i in range(self.target_layout.count()):
            widget = self.target_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.setChecked(True)
    
    def clear_all(self):
        """Clear all selections"""
        for i in range(self.target_layout.count()):
            widget = self.target_layout.itemAt(i).widget()
            if isinstance(widget, QCheckBox):
                widget.setChecked(False)

class ComparisonChartWidget(QWidget):
    """Widget for displaying comparison charts"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = None
        self.canvas = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the comparison chart UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        if MATPLOTLIB_AVAILABLE:
            self.figure = Figure(figsize=(14, 10), dpi=100)
            self.figure.patch.set_facecolor('white')
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setStyleSheet("""
                background: white; 
                border: 2px solid #3498db; 
                border-radius: 12px;
            """)
            layout.addWidget(self.canvas)
        else:
            placeholder = QLabel("Comparison charts require matplotlib\nPlease install: pip install matplotlib seaborn")
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
    
    def create_comparison_view(self, target_ids: List[int], time_range: str = "30d"):
        """Create comprehensive comparison view"""
        if not MATPLOTLIB_AVAILABLE or not self.figure or not target_ids:
            return
        
        try:
            # Get comparison data
            comparison_data = analytics_service.get_multi_target_comparison(target_ids, time_range)
            
            if 'error' in comparison_data:
                self.show_error_message(comparison_data['error'])
                return
            
            # Clear figure and create subplots
            self.figure.clear()
            
            # Create 2x2 subplot grid
            gs = self.figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
            
            # 1. Performance comparison (top-left)
            ax1 = self.figure.add_subplot(gs[0, 0])
            self.plot_performance_comparison(ax1, comparison_data)
            
            # 2. Growth trends (top-right)
            ax2 = self.figure.add_subplot(gs[0, 1])
            self.plot_growth_trends(ax2, comparison_data)
            
            # 3. Correlation heatmap (bottom-left)
            ax3 = self.figure.add_subplot(gs[1, 0])
            self.plot_correlation_heatmap(ax3, comparison_data)
            
            # 4. Rankings comparison (bottom-right)
            ax4 = self.figure.add_subplot(gs[1, 1])
            self.plot_rankings_comparison(ax4, comparison_data)
            
            # Add main title
            self.figure.suptitle(f'Multi-Target Comparison Analysis ({len(target_ids)} targets)', 
                               fontsize=16, fontweight='bold', y=0.95)
            
            self.canvas.draw()
            
        except Exception as e:
            logger.error(f"Error creating comparison view: {e}")
            self.show_error_message(str(e))
    
    def plot_performance_comparison(self, ax, comparison_data):
        """Plot performance metrics comparison"""
        try:
            targets_data = comparison_data.get('comparison_data', {}).get('targets_data', {})
            
            if not targets_data:
                ax.text(0.5, 0.5, 'No performance data available', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Performance Comparison', fontweight='bold')
                return
            
            # Extract performance metrics
            usernames = []
            engagement_rates = []
            health_scores = []
            
            for target_id, data in targets_data.items():
                target_info = data.get('target_info', {})
                health_summary = data.get('health_summary', {})
                post_metrics = data.get('post_metrics', {})
                
                usernames.append(f"@{target_info.get('username', 'Unknown')}")
                engagement_rates.append(post_metrics.get('avg_engagement_per_post', 0))
                health_scores.append(health_summary.get('current_health_score', 0))
            
            # Create grouped bar chart
            x = np.arange(len(usernames))
            width = 0.35
            
            bars1 = ax.bar(x - width/2, engagement_rates, width, label='Engagement Rate', 
                          color='#3498db', alpha=0.8)
            bars2 = ax.bar(x + width/2, health_scores, width, label='Health Score', 
                          color='#27ae60', alpha=0.8)
            
            # Add value labels
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                           f'{height:.1f}', ha='center', va='bottom', fontsize=8)
            
            ax.set_title('Performance Comparison', fontweight='bold')
            ax.set_xlabel('Targets')
            ax.set_ylabel('Score')
            ax.set_xticks(x)
            ax.set_xticklabels(usernames, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3, axis='y')
            
        except Exception as e:
            logger.error(f"Error plotting performance comparison: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def plot_growth_trends(self, ax, comparison_data):
        """Plot growth trends comparison"""
        try:
            targets_data = comparison_data.get('comparison_data', {}).get('targets_data', {})
            
            # Create sample growth data for demonstration
            days = list(range(30))
            colors = plt.cm.Set3(np.linspace(0, 1, len(targets_data)))
            
            for i, (target_id, data) in enumerate(targets_data.items()):
                target_info = data.get('target_info', {})
                username = target_info.get('username', f'Target {target_id}')
                
                # Generate sample growth data (in real implementation, use actual data)
                base_followers = target_info.get('follower_count', 1000)
                growth_rate = np.random.normal(0.02, 0.01)  # 2% average growth with variation
                growth_data = [base_followers * (1 + growth_rate) ** day for day in days]
                
                ax.plot(days, growth_data, label=f'@{username}', 
                       color=colors[i], linewidth=2, marker='o', markersize=3)
            
            ax.set_title('Follower Growth Trends', fontweight='bold')
            ax.set_xlabel('Days')
            ax.set_ylabel('Followers')
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            logger.error(f"Error plotting growth trends: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def plot_correlation_heatmap(self, ax, comparison_data):
        """Plot correlation heatmap"""
        try:
            correlation_analysis = comparison_data.get('correlation_analysis', {})
            correlation_matrix = correlation_analysis.get('correlation_matrix', {})
            
            if not correlation_matrix:
                ax.text(0.5, 0.5, 'No correlation data available', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Metric Correlations', fontweight='bold')
                return
            
            # Convert correlation matrix to numpy array
            metrics = list(correlation_matrix.keys())
            corr_array = np.zeros((len(metrics), len(metrics)))
            
            for i, metric1 in enumerate(metrics):
                for j, metric2 in enumerate(metrics):
                    corr_array[i, j] = correlation_matrix[metric1].get(metric2, 0)
            
            # Create heatmap
            im = ax.imshow(corr_array, cmap='RdYlBu_r', aspect='auto', vmin=-1, vmax=1)
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, shrink=0.8)
            cbar.set_label('Correlation Coefficient')
            
            # Set ticks and labels
            ax.set_xticks(range(len(metrics)))
            ax.set_yticks(range(len(metrics)))
            ax.set_xticklabels([m.replace('_', ' ').title() for m in metrics], rotation=45, ha='right')
            ax.set_yticklabels([m.replace('_', ' ').title() for m in metrics])
            
            # Add correlation values
            for i in range(len(metrics)):
                for j in range(len(metrics)):
                    text = ax.text(j, i, f'{corr_array[i, j]:.2f}',
                                 ha="center", va="center", color="black", fontsize=8)
            
            ax.set_title('Metric Correlations', fontweight='bold')
            
        except Exception as e:
            logger.error(f"Error plotting correlation heatmap: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def plot_rankings_comparison(self, ax, comparison_data):
        """Plot rankings comparison"""
        try:
            comparative_stats = comparison_data.get('comparison_data', {}).get('comparative_statistics', {})
            
            if not comparative_stats:
                ax.text(0.5, 0.5, 'No ranking data available', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Performance Rankings', fontweight='bold')
                return
            
            # Get rankings for a key metric (e.g., avg_engagement)
            engagement_rankings = comparative_stats.get('avg_engagement', {}).get('rankings', [])
            
            if not engagement_rankings:
                ax.text(0.5, 0.5, 'No engagement rankings available', 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title('Performance Rankings', fontweight='bold')
                return
            
            # Extract data for plotting
            usernames = []
            values = []
            ranks = []
            
            for ranking in engagement_rankings[:10]:  # Top 10
                # Get username from target_id (simplified)
                usernames.append(f"Target {ranking['target_id']}")
                values.append(ranking['value'])
                ranks.append(ranking['rank'])
            
            # Create horizontal bar chart
            colors = plt.cm.viridis(np.linspace(0, 1, len(usernames)))
            bars = ax.barh(range(len(usernames)), values, color=colors)
            
            # Add rank labels
            for i, (bar, rank) in enumerate(zip(bars, ranks)):
                width = bar.get_width()
                ax.text(width + max(values) * 0.01, bar.get_y() + bar.get_height()/2,
                       f'#{rank}', ha='left', va='center', fontweight='bold')
            
            ax.set_title('Engagement Rate Rankings', fontweight='bold')
            ax.set_xlabel('Engagement Rate')
            ax.set_yticks(range(len(usernames)))
            ax.set_yticklabels(usernames)
            ax.grid(True, alpha=0.3, axis='x')
            
        except Exception as e:
            logger.error(f"Error plotting rankings comparison: {e}")
            ax.text(0.5, 0.5, f'Error: {str(e)}', ha='center', va='center', transform=ax.transAxes)
    
    def show_error_message(self, error_msg: str):
        """Show error message on chart"""
        if self.figure:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'Error loading comparison data:\n{error_msg}', 
                   ha='center', va='center', transform=ax.transAxes,
                   fontsize=14, color='#e74c3c')
            ax.axis('off')
            self.canvas.draw()

class ComparisonDashboard(QWidget):
    """Main comparison dashboard widget"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Setup the comparison dashboard UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Left panel - Target selection
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
        left_panel.setMaximumWidth(400)
        left_panel.setMinimumWidth(350)
        
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Target selection
        self.target_selection = TargetSelectionWidget()
        left_layout.addWidget(self.target_selection)
        
        layout.addWidget(left_panel)
        
        # Right panel - Comparison charts
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
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("📊 Multi-Target Comparison Analysis")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; margin-bottom: 15px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(header)
        
        # Comparison chart
        self.comparison_chart = ComparisonChartWidget()
        right_layout.addWidget(self.comparison_chart)
        
        layout.addWidget(right_panel)
        
    def setup_connections(self):
        """Setup signal connections"""
        self.target_selection.selection_changed.connect(self.on_targets_changed)
        
    def on_targets_changed(self, target_ids: List[int]):
        """Handle target selection change"""
        if len(target_ids) >= 2:
            self.comparison_chart.create_comparison_view(target_ids, "30d")
        else:
            # Show message to select more targets
            if self.comparison_chart.figure:
                self.comparison_chart.figure.clear()
                ax = self.comparison_chart.figure.add_subplot(111)
                ax.text(0.5, 0.5, 'Please select at least 2 targets for comparison', 
                       ha='center', va='center', transform=ax.transAxes,
                       fontsize=16, color='#7f8c8d')
                ax.axis('off')
                self.comparison_chart.canvas.draw()

def create_comparison_dashboard() -> ComparisonDashboard:
    """Factory function to create comparison dashboard"""
    return ComparisonDashboard()
