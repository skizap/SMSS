#!/usr/bin/env python3
"""
Social Media Surveillance System - UI Themes and Styling
Modern styling system with CSS stylesheets, dark/light theme support,
and responsive design across different screen sizes.
"""

import logging
from typing import Dict, Any
from enum import Enum

from PyQt6.QtCore import QSettings, pyqtSignal, QObject
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

class ThemeType(Enum):
    """Available theme types"""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Follow system theme

class ThemeManager(QObject):
    """Manager for application themes and styling"""
    
    theme_changed = pyqtSignal(str)  # theme_name
    
    def __init__(self):
        super().__init__()
        self.current_theme = ThemeType.LIGHT
        self.custom_styles = {}
        
    def get_light_theme(self) -> str:
        """Get light theme stylesheet"""
        return """
        /* Light Theme Stylesheet */
        
        /* Main Application */
        QMainWindow {
            background: #f5f5f5;
            color: #2c3e50;
        }
        
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            background: transparent;
        }
        
        /* Frames and Panels */
        QFrame[frameShape="4"] {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 12px;
        }
        
        QFrame[frameShape="5"] {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
        }
        
        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffffff, stop:1 #f8f9fa);
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
            color: #495057;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f8f9fa, stop:1 #e9ecef);
            border-color: #adb5bd;
        }
        
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e9ecef, stop:1 #dee2e6);
            border-color: #6c757d;
        }
        
        QPushButton:disabled {
            background: #f8f9fa;
            border-color: #dee2e6;
            color: #adb5bd;
        }
        
        /* Primary Buttons */
        QPushButton[class="primary"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a90e2, stop:1 #357abd);
            border: 1px solid #357abd;
            color: white;
            font-weight: bold;
        }
        
        QPushButton[class="primary"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #5ba0f2, stop:1 #4a90e2);
        }
        
        /* Success Buttons */
        QPushButton[class="success"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #27ae60, stop:1 #229954);
            border: 1px solid #229954;
            color: white;
            font-weight: bold;
        }
        
        QPushButton[class="success"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2ecc71, stop:1 #27ae60);
        }
        
        /* Warning Buttons */
        QPushButton[class="warning"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f39c12, stop:1 #e67e22);
            border: 1px solid #e67e22;
            color: white;
            font-weight: bold;
        }
        
        QPushButton[class="warning"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f1c40f, stop:1 #f39c12);
        }
        
        /* Danger Buttons */
        QPushButton[class="danger"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e74c3c, stop:1 #c0392b);
            border: 1px solid #c0392b;
            color: white;
            font-weight: bold;
        }
        
        QPushButton[class="danger"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ec7063, stop:1 #e74c3c);
        }
        
        /* Input Fields */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background: white;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 10pt;
            color: #2c3e50;
        }
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #4a90e2;
            outline: none;
        }
        
        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background: #f8f9fa;
            border-color: #dee2e6;
            color: #6c757d;
        }
        
        /* Combo Boxes */
        QComboBox {
            background: white;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            padding: 8px 12px;
            min-width: 100px;
            color: #2c3e50;
        }
        
        QComboBox:hover {
            border-color: #adb5bd;
        }
        
        QComboBox:focus {
            border-color: #4a90e2;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iIzZjNzU3ZCIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            width: 12px;
            height: 8px;
        }
        
        QComboBox QAbstractItemView {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            selection-background-color: #e3f2fd;
            outline: none;
        }
        
        /* Spin Boxes */
        QSpinBox, QDoubleSpinBox {
            background: white;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            padding: 8px 12px;
            color: #2c3e50;
        }
        
        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #4a90e2;
        }
        
        /* Check Boxes */
        QCheckBox {
            color: #2c3e50;
            font-weight: 500;
        }
        
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #e1e8ed;
            border-radius: 4px;
            background: white;
        }
        
        QCheckBox::indicator:hover {
            border-color: #4a90e2;
        }
        
        QCheckBox::indicator:checked {
            background: #4a90e2;
            border-color: #4a90e2;
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4=);
        }
        
        /* Radio Buttons */
        QRadioButton {
            color: #2c3e50;
            font-weight: 500;
        }
        
        QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #e1e8ed;
            border-radius: 9px;
            background: white;
        }
        
        QRadioButton::indicator:hover {
            border-color: #4a90e2;
        }
        
        QRadioButton::indicator:checked {
            background: #4a90e2;
            border-color: #4a90e2;
        }
        
        QRadioButton::indicator:checked::after {
            content: '';
            width: 8px;
            height: 8px;
            border-radius: 4px;
            background: white;
            margin: 3px;
        }
        
        /* Group Boxes */
        QGroupBox {
            font-weight: bold;
            color: #2c3e50;
            border: 2px solid #e1e8ed;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            background: #f5f5f5;
        }
        
        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            background: white;
            margin-top: -1px;
        }
        
        QTabBar::tab {
            background: #f8f9fa;
            border: 1px solid #e1e8ed;
            padding: 12px 20px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 500;
            color: #6c757d;
        }
        
        QTabBar::tab:selected {
            background: white;
            border-bottom: 1px solid white;
            color: #2c3e50;
            font-weight: bold;
        }
        
        QTabBar::tab:hover:!selected {
            background: #e9ecef;
            color: #495057;
        }
        
        /* Tables */
        QTableWidget {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            gridline-color: #f1f3f4;
            selection-background-color: #e3f2fd;
        }
        
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f1f3f4;
        }
        
        QTableWidget::item:selected {
            background: #e3f2fd;
            color: #1976d2;
        }
        
        QHeaderView::section {
            background: #f8f9fa;
            border: none;
            border-bottom: 2px solid #e1e8ed;
            padding: 12px 8px;
            font-weight: bold;
            color: #495057;
        }
        
        /* List Widgets */
        QListWidget {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            selection-background-color: #e3f2fd;
        }
        
        QListWidget::item {
            padding: 8px;
            border-bottom: 1px solid #f1f3f4;
        }
        
        QListWidget::item:hover {
            background: #f8f9fa;
        }
        
        QListWidget::item:selected {
            background: #e3f2fd;
            color: #1976d2;
        }
        
        /* Scroll Bars */
        QScrollBar:vertical {
            background: #f8f9fa;
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }
        
        QScrollBar::handle:vertical {
            background: #adb5bd;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:vertical:hover {
            background: #6c757d;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        
        QScrollBar:horizontal {
            background: #f8f9fa;
            height: 12px;
            border-radius: 6px;
            margin: 0;
        }
        
        QScrollBar::handle:horizontal {
            background: #adb5bd;
            border-radius: 6px;
            min-width: 20px;
            margin: 2px;
        }
        
        QScrollBar::handle:horizontal:hover {
            background: #6c757d;
        }
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }
        
        /* Progress Bars */
        QProgressBar {
            background: #f8f9fa;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            color: #495057;
        }
        
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a90e2, stop:1 #357abd);
            border-radius: 7px;
        }
        
        /* Menu Bar */
        QMenuBar {
            background: white;
            border-bottom: 1px solid #e1e8ed;
            color: #2c3e50;
        }
        
        QMenuBar::item {
            padding: 8px 12px;
            background: transparent;
        }
        
        QMenuBar::item:selected {
            background: #f8f9fa;
        }
        
        QMenu {
            background: white;
            border: 1px solid #e1e8ed;
            border-radius: 8px;
            padding: 4px;
        }
        
        QMenu::item {
            padding: 8px 16px;
            border-radius: 4px;
        }
        
        QMenu::item:selected {
            background: #e3f2fd;
        }
        
        /* Status Bar */
        QStatusBar {
            background: white;
            border-top: 1px solid #e1e8ed;
            color: #6c757d;
        }
        
        /* Tool Tips */
        QToolTip {
            background: #2c3e50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-size: 9pt;
        }
        """

    def get_dark_theme(self) -> str:
        """Get dark theme stylesheet"""
        return """
        /* Dark Theme Stylesheet */

        /* Main Application */
        QMainWindow {
            background: #1e1e1e;
            color: #ffffff;
        }

        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            background: transparent;
            color: #ffffff;
        }

        /* Frames and Panels */
        QFrame[frameShape="4"] {
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 12px;
        }

        QFrame[frameShape="5"] {
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
        }

        /* Buttons */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #404040, stop:1 #353535);
            border: 1px solid #555555;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 500;
            color: #ffffff;
            min-height: 20px;
        }

        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a4a4a, stop:1 #404040);
            border-color: #666666;
        }

        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #353535, stop:1 #2a2a2a);
            border-color: #777777;
        }

        QPushButton:disabled {
            background: #2a2a2a;
            border-color: #404040;
            color: #666666;
        }

        /* Primary Buttons */
        QPushButton[class="primary"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4a90e2, stop:1 #357abd);
            border: 1px solid #357abd;
            color: white;
            font-weight: bold;
        }

        QPushButton[class="primary"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #5ba0f2, stop:1 #4a90e2);
        }

        /* Input Fields */
        QLineEdit, QTextEdit, QPlainTextEdit {
            background: #2d2d2d;
            border: 2px solid #404040;
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 10pt;
            color: #ffffff;
        }

        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
            border-color: #4a90e2;
            outline: none;
        }

        QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
            background: #1e1e1e;
            border-color: #2a2a2a;
            color: #666666;
        }

        /* Combo Boxes */
        QComboBox {
            background: #2d2d2d;
            border: 2px solid #404040;
            border-radius: 8px;
            padding: 8px 12px;
            min-width: 100px;
            color: #ffffff;
        }

        QComboBox:hover {
            border-color: #555555;
        }

        QComboBox:focus {
            border-color: #4a90e2;
        }

        QComboBox QAbstractItemView {
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
            selection-background-color: #4a90e2;
            color: #ffffff;
            outline: none;
        }

        /* Group Boxes */
        QGroupBox {
            font-weight: bold;
            color: #ffffff;
            border: 2px solid #404040;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 8px 0 8px;
            background: #1e1e1e;
        }

        /* Tab Widget */
        QTabWidget::pane {
            border: 1px solid #404040;
            border-radius: 8px;
            background: #2d2d2d;
            margin-top: -1px;
        }

        QTabBar::tab {
            background: #353535;
            border: 1px solid #404040;
            padding: 12px 20px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 500;
            color: #cccccc;
        }

        QTabBar::tab:selected {
            background: #2d2d2d;
            border-bottom: 1px solid #2d2d2d;
            color: #ffffff;
            font-weight: bold;
        }

        QTabBar::tab:hover:!selected {
            background: #404040;
            color: #ffffff;
        }

        /* Tables */
        QTableWidget {
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
            gridline-color: #404040;
            selection-background-color: #4a90e2;
            color: #ffffff;
        }

        QTableWidget::item:selected {
            background: #4a90e2;
            color: #ffffff;
        }

        QHeaderView::section {
            background: #353535;
            border: none;
            border-bottom: 2px solid #404040;
            padding: 12px 8px;
            font-weight: bold;
            color: #ffffff;
        }

        /* List Widgets */
        QListWidget {
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
            selection-background-color: #4a90e2;
            color: #ffffff;
        }

        QListWidget::item:hover {
            background: #353535;
        }

        QListWidget::item:selected {
            background: #4a90e2;
            color: #ffffff;
        }

        /* Scroll Bars */
        QScrollBar:vertical {
            background: #353535;
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }

        QScrollBar::handle:vertical {
            background: #666666;
            border-radius: 6px;
            min-height: 20px;
            margin: 2px;
        }

        QScrollBar::handle:vertical:hover {
            background: #777777;
        }

        /* Menu Bar */
        QMenuBar {
            background: #2d2d2d;
            border-bottom: 1px solid #404040;
            color: #ffffff;
        }

        QMenuBar::item:selected {
            background: #353535;
        }

        QMenu {
            background: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 4px;
            color: #ffffff;
        }

        QMenu::item:selected {
            background: #4a90e2;
        }

        /* Status Bar */
        QStatusBar {
            background: #2d2d2d;
            border-top: 1px solid #404040;
            color: #cccccc;
        }
        """

    def apply_theme(self, theme_type: ThemeType):
        """Apply the specified theme"""
        try:
            app = QApplication.instance()
            if not app:
                logger.warning("No QApplication instance found")
                return

            if theme_type == ThemeType.LIGHT:
                stylesheet = self.get_light_theme()
            elif theme_type == ThemeType.DARK:
                stylesheet = self.get_dark_theme()
            elif theme_type == ThemeType.AUTO:
                # Detect system theme (simplified)
                stylesheet = self.get_light_theme()  # Default to light for now
            else:
                stylesheet = self.get_light_theme()

            # Apply custom styles
            for selector, style in self.custom_styles.items():
                stylesheet += f"\n{selector} {{ {style} }}"

            app.setStyleSheet(stylesheet)
            self.current_theme = theme_type

            # Save theme preference
            settings = QSettings()
            settings.setValue("ui/theme", theme_type.value)

            self.theme_changed.emit(theme_type.value)
            logger.info(f"Applied {theme_type.value} theme")

        except Exception as e:
            logger.error(f"Error applying theme: {e}")

    def get_current_theme(self) -> ThemeType:
        """Get the current theme"""
        return self.current_theme

    def load_saved_theme(self):
        """Load the saved theme preference"""
        try:
            settings = QSettings()
            theme_name = settings.value("ui/theme", ThemeType.LIGHT.value)

            # Convert string to enum
            for theme_type in ThemeType:
                if theme_type.value == theme_name:
                    self.apply_theme(theme_type)
                    return

            # Default to light theme if invalid
            self.apply_theme(ThemeType.LIGHT)

        except Exception as e:
            logger.error(f"Error loading saved theme: {e}")
            self.apply_theme(ThemeType.LIGHT)

    def add_custom_style(self, selector: str, style: str):
        """Add custom CSS style"""
        self.custom_styles[selector] = style

    def remove_custom_style(self, selector: str):
        """Remove custom CSS style"""
        if selector in self.custom_styles:
            del self.custom_styles[selector]

    def get_theme_colors(self) -> Dict[str, str]:
        """Get color palette for current theme"""
        if self.current_theme == ThemeType.DARK:
            return {
                'background': '#1e1e1e',
                'surface': '#2d2d2d',
                'primary': '#4a90e2',
                'secondary': '#666666',
                'text': '#ffffff',
                'text_secondary': '#cccccc',
                'border': '#404040',
                'success': '#27ae60',
                'warning': '#f39c12',
                'error': '#e74c3c'
            }
        else:  # Light theme
            return {
                'background': '#f5f5f5',
                'surface': '#ffffff',
                'primary': '#4a90e2',
                'secondary': '#6c757d',
                'text': '#2c3e50',
                'text_secondary': '#6c757d',
                'border': '#e1e8ed',
                'success': '#27ae60',
                'warning': '#f39c12',
                'error': '#e74c3c'
            }

# Global theme manager instance
_theme_manager = None

def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance"""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager

def apply_theme(theme_type: ThemeType):
    """Convenience function to apply theme"""
    get_theme_manager().apply_theme(theme_type)

def get_current_theme() -> ThemeType:
    """Convenience function to get current theme"""
    return get_theme_manager().get_current_theme()

def load_saved_theme():
    """Convenience function to load saved theme"""
    get_theme_manager().load_saved_theme()
