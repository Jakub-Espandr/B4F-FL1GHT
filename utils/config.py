"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import os
from PySide6.QtGui import QFontDatabase

# Define paths for assets
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets')
ICONS_DIR = os.path.join(ASSETS_DIR, 'icons')
FONTS_DIR = os.path.join(ASSETS_DIR, 'fonts')

# Font configurations
FONT_CONFIG = {
    'title': {
        'size': 16,
        'weight': 'bold',
        'family': 'fccTYPO'
    },
    'sub_group': {
        'size': 14,
        'weight': 'normal',
        'family': 'fccTYPO'
    },
    'label': {
        'size': 14,
        'weight': 'normal',
        'family': 'fccTYPO'
    },
    'button': {
        'size': 14,
        'weight': 'normal',
        'family': 'fccTYPO'
    },
    'checkbox': {
        'size': 14,
        'weight': 'normal',
        'family': 'fccTYPO'
    },
    'tab': {
        'size': 14,
        'weight': 'normal',
        'family': 'fccTYPO'
    },
    'combo': {
        'size': 14,
        'weight': 'normal',
        'family': 'fccTYPO'
    }
}

def load_custom_fonts():
    """Load custom fonts from the assets directory"""
    font_files = {
        'regular': 'fccTYPO-Regular.ttf',
        'bold': 'fccTYPO-Bold.ttf'
    }
    
    loaded_fonts = {}
    for font_type, font_file in font_files.items():
        font_path = os.path.join(FONTS_DIR, font_file)
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            if font_id != -1:
                font_families = QFontDatabase.applicationFontFamilies(font_id)
                if font_families:
                    loaded_fonts[font_type] = font_families[0]
    
    return loaded_fonts

# Color palette for different data types
COLOR_PALETTE = {
    'Gyro (raw)': (255, 0, 255),      # Neon Pink
    'Gyro (filtered)': (0, 255, 255),  # Neon Cyan
    'P-Term': (255, 200, 0),          # Darker Yellow
    'I-Term': (255, 128, 0),          # Neon Orange
    'D-Term': (128, 0, 255),          # Neon Purple
    'FeedForward': (0, 255, 128),     # Neon Green
    'Setpoint': (0, 0, 0),            # Black
    'RC Command': (128, 128, 0),      # Olive
    'Throttle': (128, 128, 128),      # Gray
}

# Alternative color palette for comparing two logs
ALTERNATIVE_COLOR_PALETTE = {
    'Gyro (raw)': (180, 0, 180),      # Darker Pink
    'Gyro (filtered)': (0, 180, 180), # Darker Cyan
    'P-Term': (180, 140, 0),          # Darker Gold
    'I-Term': (180, 90, 0),           # Darker Orange
    'D-Term': (90, 0, 180),           # Darker Purple
    'FeedForward': (0, 180, 90),      # Darker Green
    'Setpoint': (70, 70, 70),         # Dark Gray
    'RC Command': (90, 90, 0),        # Darker Olive
    'Throttle': (90, 90, 90),         # Darker Gray
}

# Colors for motors
MOTOR_COLORS = [
    (255, 100, 100),    # Light Red
    (100, 255, 100),    # Light Green
    (100, 100, 255),    # Light Blue
    (255, 200, 100),    # Light Orange
    (200, 100, 255),    # Light Purple
    (100, 255, 200),    # Light Teal
    (255, 100, 200),    # Light Pink
    (200, 255, 100),    # Light Lime
]

# Alternative colors for motors in second log
ALTERNATIVE_MOTOR_COLORS = [
    (180, 70, 70),      # Darker Red
    (70, 180, 70),      # Darker Green
    (70, 70, 180),      # Darker Blue
    (180, 140, 70),     # Darker Orange
    (140, 70, 180),     # Darker Purple
    (70, 180, 140),     # Darker Teal
    (180, 70, 140),     # Darker Pink
    (140, 180, 70),     # Darker Lime
]

# Chart configurations
CHART_CONFIG = {
    'margins': (10, 10, 10, 10),
    'animation': False,
    'theme': 'light',
    'legend_visible': False
}

# Data processing configurations
DATA_CONFIG = {
    'max_points': 4000,  # Maximum points for decimation (reduced for better performance)
    'time_column': 'time',  # Default time column name
    'time_scale': 1_000_000.0  # Convert microseconds to seconds
} 