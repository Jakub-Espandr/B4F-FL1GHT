"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from core.fl1ght_viewer import FL1GHTViewer
from utils.config import ASSETS_DIR, ICONS_DIR, load_custom_fonts

def get_application_icon():
    """Get the application icon in a cross-platform way"""
    # List of supported icon formats
    icon_names = [
        'icon.png',  # PNG format (universal)
        'icon.ico',  # Windows ICO format
        'icon.icns'  # macOS icon format
    ]
    
    # Try each icon format
    for icon_name in icon_names:
        icon_path = os.path.join(ICONS_DIR, icon_name)
        if os.path.exists(icon_path):
            return QIcon(icon_path)
    
    # If no icon is found, return None
    return None

def set_process_name(name):
    """Set the process name for the application"""
    if sys.platform == 'darwin':  # macOS
        try:
            from ctypes import cdll, byref, create_string_buffer
            libc = cdll.LoadLibrary('libc.dylib')
            buff = create_string_buffer(len(name) + 1)
            buff.value = name.encode('utf-8')
            libc.setprogname(byref(buff))
        except Exception as e:
            print(f"Failed to set process name: {e}")

def main():
    # Set process name first
    set_process_name("B4F: FL1GHT")
    
    # Set application attributes before creating QApplication
    QApplication.setApplicationName("B4F: FL1GHT")
    QApplication.setOrganizationName("Born4Flight")
    
    app = QApplication([])
    
    # Load custom fonts
    loaded_fonts = load_custom_fonts()
    if not loaded_fonts:
        print("Warning: Failed to load custom fonts")
    
    # Set application icon in a cross-platform way
    app_icon = get_application_icon()
    if app_icon:
        app.setWindowIcon(app_icon)
    
    # Set dark theme for the entire application
    app.setStyleSheet("""
        QWidget {
            background-color: #1e1e1e;
            color: white;
        }
        QGroupBox {
            border: 1px solid #3a3a3a;
            border-radius: 5px;
            margin-top: 1ex;
            padding-top: 1ex;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 3px;
        }
        QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #3a3a3a;
            border-radius: 3px;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
        }
        QPushButton:pressed {
            background-color: #4d4d4d;
        }
        QCheckBox {
            spacing: 5px;
        }
        QCheckBox::indicator {
            width: 15px;
            height: 15px;
        }
        QScrollArea {
            border: none;
        }
        QSlider::groove:horizontal {
            border: 1px solid #3a3a3a;
            height: 8px;
            background: #2d2d2d;
            margin: 2px 0;
            border-radius: 4px;
        }
        QSlider::handle:horizontal {
            background: #00bfff;
            border: 2px solid #0080ff;
            width: 16px;
            height: 16px;
            margin: -4px 0;
            border-radius: 8px;
        }
        QSlider::handle:horizontal:hover {
            background: #40dfff;
            border: 2px solid #00bfff;
        }
        QSlider::handle:horizontal:pressed {
            background: #0080ff;
            border: 2px solid #0066cc;
        }
        QProgressBar {
            border: 1px solid #3a3a3a;
            border-radius: 3px;
            text-align: center;
            background-color: #2d2d2d;
        }
        QProgressBar::chunk {
            background-color: #4d4d4d;
            width: 10px;
            margin: 0.5px;
        }
    """)
    
    viewer = FL1GHTViewer()
    # Set window icon if available
    if app_icon:
        viewer.setWindowIcon(app_icon)
    app.exec()

if __name__ == "__main__":
    main() 