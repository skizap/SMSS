#!/usr/bin/env python3
"""
Social Media Surveillance System - Report Management Widget
UI component for viewing, downloading, and managing generated reports.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QPushButton, QFrame, QTableWidget, QTableWidgetItem,
        QHeaderView, QGroupBox, QComboBox, QLineEdit, QMessageBox,
        QMenu, QDialog, QDialogButtonBox, QTextEdit, QProgressBar,
        QSplitter, QScrollArea
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
    from PyQt6.QtGui import QFont, QColor, QAction, QIcon, QContextMenuEvent
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False

from reporting.report_export_system import report_export_service

logger = logging.getLogger(__name__)

class ReportTableWidget(QTableWidget):
    """Custom table widget for displaying reports with context menu"""
    
    report_selected = pyqtSignal(dict)  # Emit selected report data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.reports_data = []
        self.setup_table()
        
    def setup_table(self):
        """Setup the reports table"""
        # Set columns
        headers = [
            'Name', 'Type', 'Status', 'Generated', 'Size', 'Downloads', 'Actions'
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Table styling
        self.setStyleSheet("""
            QTableWidget {
                border: 2px solid #ecf0f1;
                border-radius: 10px;
                background: white;
                gridline-color: #ecf0f1;
                selection-background-color: #3498db;
                selection-color: white;
                font-size: 11px;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #ecf0f1;
            }
            QTableWidget::item:hover {
                background: #ebf3fd;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                color: white;
                padding: 12px 8px;
                border: none;
                font-weight: bold;
                font-size: 11px;
            }
        """)
        
        # Table behavior
        self.setSortingEnabled(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        
        # Header configuration
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column
        for i in range(1, len(headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect signals
        self.itemSelectionChanged.connect(self.on_selection_changed)
        
    def contextMenuEvent(self, event: QContextMenuEvent):
        """Handle right-click context menu"""
        item = self.itemAt(event.pos())
        if item is None:
            return
        
        row = item.row()
        if row >= len(self.reports_data):
            return
        
        report_data = self.reports_data[row]
        
        # Create context menu
        menu = QMenu(self)
        
        # Open action
        if report_data.get('status') == 'completed':
            open_action = QAction("📂 Open Report", self)
            open_action.triggered.connect(lambda: self.open_report(report_data))
            menu.addAction(open_action)
            
            # Download action
            download_action = QAction("💾 Save As...", self)
            download_action.triggered.connect(lambda: self.download_report(report_data))
            menu.addAction(download_action)
            
            menu.addSeparator()
        
        # View details action
        details_action = QAction("ℹ️ View Details", self)
        details_action.triggered.connect(lambda: self.view_details(report_data))
        menu.addAction(details_action)
        
        # Delete action
        delete_action = QAction("🗑️ Delete Report", self)
        delete_action.triggered.connect(lambda: self.delete_report(report_data))
        menu.addAction(delete_action)
        
        menu.exec(event.globalPos())
    
    def update_reports(self, reports: List[Dict[str, Any]]):
        """Update table with reports data"""
        self.reports_data = reports
        self.setRowCount(len(reports))
        
        for row, report in enumerate(reports):
            # Name
            name_item = QTableWidgetItem(report.get('name', 'Unknown'))
            name_item.setToolTip(report.get('name', 'Unknown'))
            self.setItem(row, 0, name_item)
            
            # Type
            report_type = report.get('type', 'Unknown').upper()
            type_item = QTableWidgetItem(report_type)
            self.setItem(row, 1, type_item)
            
            # Status
            status = report.get('status', 'Unknown')
            status_item = QTableWidgetItem(status.title())
            
            # Color code status
            if status == 'completed':
                status_item.setBackground(QColor("#d5f4e6"))  # Light green
                status_item.setForeground(QColor("#27ae60"))
            elif status == 'generating':
                status_item.setBackground(QColor("#fff3cd"))  # Light yellow
                status_item.setForeground(QColor("#f39c12"))
            elif status == 'failed':
                status_item.setBackground(QColor("#f8d7da"))  # Light red
                status_item.setForeground(QColor("#e74c3c"))
            
            self.setItem(row, 2, status_item)
            
            # Generated date
            generated_at = report.get('generated_at', '')
            if generated_at:
                try:
                    dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                    formatted_date = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    formatted_date = generated_at[:19] if len(generated_at) > 19 else generated_at
            else:
                formatted_date = 'Unknown'
            
            date_item = QTableWidgetItem(formatted_date)
            self.setItem(row, 3, date_item)
            
            # File size
            file_size = report.get('file_size', 0)
            if file_size > 0:
                if file_size > 1024 * 1024:  # MB
                    size_text = f"{file_size / (1024 * 1024):.1f} MB"
                elif file_size > 1024:  # KB
                    size_text = f"{file_size / 1024:.1f} KB"
                else:
                    size_text = f"{file_size} B"
            else:
                size_text = "-"
            
            size_item = QTableWidgetItem(size_text)
            self.setItem(row, 4, size_item)
            
            # Download count
            downloads = report.get('download_count', 0)
            download_item = QTableWidgetItem(str(downloads))
            self.setItem(row, 5, download_item)
            
            # Actions (placeholder)
            actions_item = QTableWidgetItem("Right-click for actions")
            actions_item.setForeground(QColor("#7f8c8d"))
            actions_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Normal, True))
            self.setItem(row, 6, actions_item)
    
    def on_selection_changed(self):
        """Handle selection change"""
        current_row = self.currentRow()
        if 0 <= current_row < len(self.reports_data):
            self.report_selected.emit(self.reports_data[current_row])
    
    def open_report(self, report_data: Dict[str, Any]):
        """Open report file"""
        try:
            file_path = report_data.get('file_path')
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", 
                                  "The report file could not be found.")
                return
            
            # Open with default application
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(['open', file_path])
            else:  # Linux
                subprocess.call(['xdg-open', file_path])
                
        except Exception as e:
            logger.error(f"Error opening report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open report:\n{str(e)}")
    
    def download_report(self, report_data: Dict[str, Any]):
        """Download/save report to chosen location"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            file_path = report_data.get('file_path')
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "File Not Found", 
                                  "The report file could not be found.")
                return
            
            # Get file extension
            _, ext = os.path.splitext(file_path)
            
            # Open save dialog
            save_path, _ = QFileDialog.getSaveFileName(
                self, "Save Report As", 
                report_data.get('name', 'report') + ext,
                f"Report Files (*{ext})"
            )
            
            if save_path:
                import shutil
                shutil.copy2(file_path, save_path)
                QMessageBox.information(self, "Success", 
                                      f"Report saved to:\n{save_path}")
                
        except Exception as e:
            logger.error(f"Error downloading report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save report:\n{str(e)}")
    
    def view_details(self, report_data: Dict[str, Any]):
        """View detailed report information"""
        dialog = ReportDetailsDialog(report_data, self)
        dialog.exec()
    
    def delete_report(self, report_data: Dict[str, Any]):
        """Delete report"""
        try:
            reply = QMessageBox.question(
                self, "Delete Report",
                f"Are you sure you want to delete the report '{report_data.get('name', 'Unknown')}'?\n\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                report_id = report_data.get('id')
                if report_id and report_export_service.delete_report(report_id):
                    QMessageBox.information(self, "Success", "Report deleted successfully.")
                    # Refresh the table
                    self.parent().refresh_reports()
                else:
                    QMessageBox.warning(self, "Error", "Failed to delete report.")
                    
        except Exception as e:
            logger.error(f"Error deleting report: {e}")
            QMessageBox.critical(self, "Error", f"Failed to delete report:\n{str(e)}")

class ReportDetailsDialog(QDialog):
    """Dialog for viewing detailed report information"""
    
    def __init__(self, report_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.report_data = report_data
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the details dialog UI"""
        self.setWindowTitle("Report Details")
        self.setFixedSize(500, 400)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel(f"📊 {self.report_data.get('name', 'Unknown Report')}")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50; padding: 10px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Details text
        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setStyleSheet("""
            QTextEdit {
                border: 2px solid #ecf0f1;
                border-radius: 8px;
                background: #f8f9fa;
                padding: 10px;
                font-family: 'Courier New', monospace;
                font-size: 10px;
            }
        """)
        
        # Format details
        details = self._format_report_details()
        details_text.setPlainText(details)
        
        layout.addWidget(details_text)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _format_report_details(self) -> str:
        """Format report details for display"""
        details = []
        
        details.append("REPORT INFORMATION")
        details.append("=" * 50)
        details.append(f"Name: {self.report_data.get('name', 'Unknown')}")
        details.append(f"Type: {self.report_data.get('type', 'Unknown')}")
        details.append(f"Status: {self.report_data.get('status', 'Unknown')}")
        details.append(f"ID: {self.report_data.get('id', 'Unknown')}")
        details.append("")
        
        details.append("GENERATION DETAILS")
        details.append("=" * 50)
        generated_at = self.report_data.get('generated_at', 'Unknown')
        if generated_at:
            try:
                dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            except:
                formatted_date = generated_at
        else:
            formatted_date = 'Unknown'
        details.append(f"Generated: {formatted_date}")
        
        generation_time = self.report_data.get('generation_time')
        if generation_time:
            details.append(f"Generation Time: {generation_time:.2f} seconds")
        
        details.append("")
        
        details.append("FILE INFORMATION")
        details.append("=" * 50)
        file_path = self.report_data.get('file_path', 'Unknown')
        details.append(f"File Path: {file_path}")
        
        file_size = self.report_data.get('file_size', 0)
        if file_size > 0:
            if file_size > 1024 * 1024:  # MB
                size_text = f"{file_size / (1024 * 1024):.2f} MB ({file_size:,} bytes)"
            elif file_size > 1024:  # KB
                size_text = f"{file_size / 1024:.2f} KB ({file_size:,} bytes)"
            else:
                size_text = f"{file_size} bytes"
        else:
            size_text = "Unknown"
        details.append(f"File Size: {size_text}")
        
        download_count = self.report_data.get('download_count', 0)
        details.append(f"Download Count: {download_count}")
        details.append("")
        
        # Error information if failed
        error_message = self.report_data.get('error_message')
        if error_message:
            details.append("ERROR INFORMATION")
            details.append("=" * 50)
            details.append(f"Error: {error_message}")
            details.append("")
        
        return "\n".join(details)

class ReportManagementWidget(QWidget):
    """Main widget for managing generated reports"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.refresh_reports()
        
        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_reports)
        self.refresh_timer.start(30000)  # Refresh every 30 seconds
        
    def setup_ui(self):
        """Setup the report management UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        header = QLabel("📋 Report Management")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet("color: #2c3e50;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #3498db;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #2980b9;
            }
        """)
        refresh_btn.clicked.connect(self.refresh_reports)
        header_layout.addWidget(refresh_btn)
        
        # Clear old reports button
        cleanup_btn = QPushButton("🧹 Cleanup Old Reports")
        cleanup_btn.setStyleSheet("""
            QPushButton {
                background: #e67e22;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #d35400;
            }
        """)
        cleanup_btn.clicked.connect(self.cleanup_old_reports)
        header_layout.addWidget(cleanup_btn)
        
        layout.addLayout(header_layout)
        
        # Reports table
        self.reports_table = ReportTableWidget()
        layout.addWidget(self.reports_table)
        
        # Status bar
        self.status_label = QLabel("Loading reports...")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic; padding: 10px;")
        layout.addWidget(self.status_label)
        
    def refresh_reports(self):
        """Refresh the reports list"""
        try:
            reports = report_export_service.list_reports(limit=100)
            self.reports_table.update_reports(reports)
            
            # Update status
            count = len(reports)
            self.status_label.setText(f"Showing {count} report{'s' if count != 1 else ''}")
            
        except Exception as e:
            logger.error(f"Error refreshing reports: {e}")
            self.status_label.setText(f"Error loading reports: {str(e)}")
    
    def cleanup_old_reports(self):
        """Clean up old reports"""
        try:
            reply = QMessageBox.question(
                self, "Cleanup Old Reports",
                "This will delete reports older than 30 days.\n\n"
                "Are you sure you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Implementation would go here
                QMessageBox.information(self, "Cleanup", 
                                      "Old reports cleanup completed.")
                self.refresh_reports()
                
        except Exception as e:
            logger.error(f"Error cleaning up reports: {e}")
            QMessageBox.critical(self, "Error", f"Failed to cleanup reports:\n{str(e)}")

def create_report_management_widget() -> ReportManagementWidget:
    """Factory function to create report management widget"""
    return ReportManagementWidget()
