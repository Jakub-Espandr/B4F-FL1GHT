"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QCheckBox, QLabel, QMessageBox, QGroupBox, QScrollArea,
    QSlider, QProgressBar, QSizePolicy, QComboBox, QToolTip, QGridLayout, QSpinBox,
    QDialog, QLineEdit, QListWidget, QApplication, QDoubleSpinBox,
    QDialogButtonBox, QLineEdit, QTextEdit, QScrollArea, QFrame, QSizePolicy,
    QToolTip, QSplitter, QFormLayout, QSpinBox, QDoubleSpinBox, QComboBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QIcon, QImage, QPixmap, QPalette
from PySide6.QtCore import Qt, QMargins, QTimer, QSize, QRect, QPoint, Signal
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries, QCategoryAxis, QLegend
from utils.config import FONT_CONFIG, COLOR_PALETTE, MOTOR_COLORS, ALTERNATIVE_COLOR_PALETTE
from utils.data_processor import get_clean_name
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from utils.step_trace import StepTrace
import os
import matplotlib.cm as cm
from scipy import signal
from scipy.ndimage import gaussian_filter1d, gaussian_filter
from mpl_toolkits.axes_grid1 import make_axes_locatable
from utils.pid_analyzer_noise import plot_all_noise_from_df, plot_noise_from_df, generate_individual_noise_figures
import sys
import json
import tempfile
import warnings
from utils.spectrogram_utils import calculate_spectrogram

class ClickableChartView(QChartView):
    """A QChartView that emits a signal when clicked."""
    clicked = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mousePressEvent(self, event):
        """Emit the clicked signal on a mouse press event."""
        self.clicked.emit()
        super().mousePressEvent(event)

class FeatureSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Initialize settings attributes
        self.author_name = ""
        self.drone_name = ""
        self.export_dir = os.path.expanduser("~/Desktop")
        self.use_drone_in_filename = False
        self.debug_level = "INFO"  # Can be 'INFO', 'DEBUG', 'VERBOSE'
        # Try to load from settings.json in config folder
        try:
            import json
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            config_dir = os.path.join(app_dir, "config")
            settings_path = os.path.join(config_dir, "settings.json")
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    self.author_name = settings.get('author_name', self.author_name)
                    self.drone_name = settings.get('drone_name', self.drone_name)
                    self.export_dir = settings.get('export_dir', self.export_dir)
                    self.use_drone_in_filename = settings.get('use_drone_in_filename', self.use_drone_in_filename)
                    self.debug_level = settings.get('debug_level', self.debug_level)
        except Exception as e:
            print(f"[FeatureSelectionWidget] Failed to load settings: {e}")
        self.loaded_logs = {}  # Dictionary to store loaded logs
        self.loaded_log_paths = {}  # Dictionary to store paths to original .bbl files
        self.selected_logs = []  # List to store selected logs
        self.current_log = None  # Current log being displayed
        self.df = None  # Current dataframe
        self.current_line_width = 1.0  # Default line width
        self.setup_ui()
        self.setup_connections()

    def get_current_tab_index(self):
        """Safely get the current tab index"""
        try:
            # Try to get the tab widget through the parent hierarchy
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, 'tab_widget'):
                    return parent.tab_widget.currentIndex()
                parent = parent.parent()
            return 0  # Default to time domain tab if we can't find the tab widget
        except Exception:
            return 0  # Default to time domain tab if anything goes wrong

    def setup_connections(self):
        # Connect list widget selection change
        self.logs_list.itemSelectionChanged.connect(self.on_logs_selection_changed)
        # Connect combo box selection change
        self.logs_combo.currentIndexChanged.connect(self.on_log_selected)

    def setup_ui(self):
        layout = QVBoxLayout(self)  # Changed back to vertical layout
        layout.setSpacing(10)  # Restore original spacing
        layout.setContentsMargins(0, 0, 0, 0)

        # File selection controls at the top
        file_controls = QVBoxLayout()
        file_controls.setSpacing(10)  # Restore original spacing
        file_controls.setContentsMargins(0, 0, 0, 10)  # Restore original margins

        # File selection label
        self.file_label = QLabel("Select BBL file:")
        self.file_label.setFont(self.create_font('label'))
        file_controls.addWidget(self.file_label)

        # File selection button
        self.select_button = QPushButton("Select File(s)")
        self.select_button.setFont(self.create_font('button'))
        file_controls.addWidget(self.select_button)

        # Add loaded logs combo box
        logs_label = QLabel("Loaded Logs:")
        logs_label.setFont(self.create_font('label'))
        file_controls.addWidget(logs_label)

        # Create logs list widget for multi-selection but make it smaller
        self.logs_list = QListWidget()
        self.logs_list.setFont(self.create_font('label'))
        self.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.logs_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                padding: 5px;
                color: white;
                min-height: 50px;
                max-height: 80px;
            }
            QListWidget::item {
                border: none;
                padding: 2px;
                min-height: 20px;
            }
            QListWidget::item:selected {
                background-color: #4d4d4d;
                border: none;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
                border: none;
            }
            QScrollBar:vertical {
                background: #232323;
                width: 16px;
                margin: 0px 0px 0px 0px;
                border-radius: 8px;
            }
            QScrollBar::handle:vertical {
                background: #888888;
                min-height: 24px;
                border-radius: 8px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.logs_list.itemSelectionChanged.connect(self.on_logs_selection_changed)
        file_controls.addWidget(self.logs_list)

        # Keep the single log combo for compatibility but hide it
        self.logs_combo = QComboBox()
        self.logs_combo.setVisible(False)
        self.logs_combo.currentIndexChanged.connect(self.on_log_selected)
        file_controls.addWidget(self.logs_combo)

        # Plot button - single button for both single and multi-log plotting
        self.plot_button = QPushButton("Show Plot")
        self.plot_button.setFont(self.create_font('button'))
        # Set neon style for plot button
        self.plot_button.setStyleSheet("""
            QPushButton {
                background-color: #00ff00;
                color: black;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #00cc00;
                border-color: #00cc00;
            }
            QPushButton:pressed {
                background-color: #009900;
                border-color: #009900;
            }
        """)
        file_controls.addWidget(self.plot_button)

        # Add file controls to main layout
        layout.addLayout(file_controls)

        # Add title for feature selectors
        selector_title = QLabel("Graph Visualization")
        selector_title.setFont(self.create_font('title'))
        selector_title.setStyleSheet("""
            QLabel {
                color: white;
                padding: 5px;
            }
        """)
        layout.addWidget(selector_title)

        # Create scroll area for features
        self.feature_scroll = QScrollArea()
        self.feature_scroll.setWidgetResizable(True)
        self.feature_scroll.setMaximumWidth(250)
        self.feature_scroll.setFrameShape(QScrollArea.NoFrame)
        
        # Create widget to hold feature checkboxes
        self.feature_widget = QWidget()
        self.feature_layout = QVBoxLayout(self.feature_widget)
        self.feature_layout.setSpacing(10)  # Restore original spacing
        self.feature_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create feature groups
        self.create_gyro_group()
        self.create_pid_group()
        self.create_rc_group()
        self.create_motor_group()
        
        self.feature_scroll.setWidget(self.feature_widget)
        layout.addWidget(self.feature_scroll)
        
        # Add stretch to push legend down
        layout.addStretch(1)
        
        # Add legend area at the bottom
        self.legend_group = QGroupBox("Plot Legend")
        self.legend_group.setFont(self.create_font('title'))
        self.legend_group.setStyleSheet("QGroupBox { background-color: #444; border: none; }")
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setSpacing(10)  # Restore original spacing
        self.legend_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        self.legend_group.setLayout(self.legend_layout)
        layout.addWidget(self.legend_group)

        # Add line width label above the slider/settings row
        self.line_width_label = QLabel("Line Width: 1.0px")
        self.line_width_label.setFont(self.create_font('label'))
        layout.addWidget(self.line_width_label)
        # Add line width controls (slider and settings button in one row, no group box)
        slider_row = QHBoxLayout()
        slider_row.setSpacing(10)
        self.line_width_slider = QSlider(Qt.Horizontal)
        self.line_width_slider.setMinimum(2)  # 1.0 * 2
        self.line_width_slider.setMaximum(4)  # 2.0 * 2
        self.line_width_slider.setValue(2)    # 1.0 * 2
        self.line_width_slider.setTickPosition(QSlider.NoTicks)
        self.line_width_slider.setFixedWidth(100)  # Make slider more narrow
        self.line_width_slider.valueChanged.connect(self.line_width_changed)
        slider_row.addWidget(self.line_width_slider)
        # Settings button as emoji
        self.settings_button = QPushButton('⚙️')
        self.settings_button.setToolTip('Settings')
        self.settings_button.setFixedSize(40, 40)
        font = self.settings_button.font()
        font.setPointSize(20)
        self.settings_button.setFont(font)
        self.settings_button.clicked.connect(self.open_settings_dialog)
        slider_row.addWidget(self.settings_button)
        layout.addLayout(slider_row)

    def create_gyro_group(self):
        self.gyro_group = QGroupBox("Gyro Data")
        self.gyro_group.setFont(self.create_font('sub_group'))
        self.gyro_layout = QVBoxLayout()
        self.gyro_layout.setSpacing(10)  # Restore original spacing
        self.gyro_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        
        self.gyro_unfilt_checkbox = QCheckBox("Gyro (raw)")
        self.gyro_scaled_checkbox = QCheckBox("Gyro (filtered)")
        
        self.gyro_unfilt_checkbox.setFont(self.create_font('checkbox'))
        self.gyro_scaled_checkbox.setFont(self.create_font('checkbox'))
        
        self.gyro_layout.addWidget(self.gyro_unfilt_checkbox)
        self.gyro_layout.addWidget(self.gyro_scaled_checkbox)
        self.gyro_group.setLayout(self.gyro_layout)
        self.feature_layout.addWidget(self.gyro_group)

    def create_pid_group(self):
        self.pid_group = QGroupBox("PID Data")
        self.pid_group.setFont(self.create_font('sub_group'))
        self.pid_layout = QVBoxLayout()
        self.pid_layout.setSpacing(10)  # Restore original spacing
        self.pid_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        
        self.pid_p_checkbox = QCheckBox("P-Term")
        self.pid_i_checkbox = QCheckBox("I-Term")
        self.pid_d_checkbox = QCheckBox("D-Term")
        self.pid_f_checkbox = QCheckBox("FeedForward")
        self.setpoint_checkbox = QCheckBox("Setpoint")
        
        for checkbox in [self.pid_p_checkbox, self.pid_i_checkbox, self.pid_d_checkbox,
                        self.pid_f_checkbox, self.setpoint_checkbox]:
            checkbox.setFont(self.create_font('checkbox'))
            self.pid_layout.addWidget(checkbox)
            
        self.pid_group.setLayout(self.pid_layout)
        self.feature_layout.addWidget(self.pid_group)

    def create_rc_group(self):
        self.rc_group = QGroupBox("RC Data")
        self.rc_group.setFont(self.create_font('sub_group'))
        self.rc_layout = QVBoxLayout()
        self.rc_layout.setSpacing(10)  # Restore original spacing
        self.rc_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        
        self.rc_checkbox = QCheckBox("RC Commands")
        self.throttle_checkbox = QCheckBox("Throttle")
        self.throttle_checkbox.setChecked(True)
        
        self.rc_checkbox.setFont(self.create_font('checkbox'))
        self.throttle_checkbox.setFont(self.create_font('checkbox'))
        
        self.rc_layout.addWidget(self.rc_checkbox)
        self.rc_layout.addWidget(self.throttle_checkbox)
        self.rc_group.setLayout(self.rc_layout)
        self.feature_layout.addWidget(self.rc_group)

    def create_motor_group(self):
        self.motor_group = QGroupBox("Motor Outputs")
        self.motor_group.setFont(self.create_font('sub_group'))
        self.motor_layout = QVBoxLayout()
        self.motor_layout.setSpacing(10)  # Restore original spacing
        self.motor_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        
        self.motor_checkbox = QCheckBox("Motor Outputs")
        self.motor_checkbox.setFont(self.create_font('checkbox'))
        
        self.motor_layout.addWidget(self.motor_checkbox)
        self.motor_group.setLayout(self.motor_layout)
        self.feature_layout.addWidget(self.motor_group)

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font

    def get_selected_features(self):
        """Get list of selected features"""
        selected_features = []
        
        # Handle gyro data
        if self.gyro_unfilt_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'gyrounfilt' in col.lower()])
        if self.gyro_scaled_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'gyroadc' in col.lower() and '(deg/s)' in col])
        
        # Handle PID data
        if self.pid_p_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'axisp' in col.lower()])
        if self.pid_i_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'axisi' in col.lower()])
        if self.pid_d_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'axisd' in col.lower()])
        if self.pid_f_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'axisf' in col.lower()])
        
        # Handle Setpoint data
        if self.setpoint_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'setpoint' in col.lower()])
        
        # Handle RC data
        if self.rc_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'rccommand' in col.lower() and '[3]' not in col])
        
        # Handle Throttle data
        if self.throttle_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'rccommand[3]' in col.lower()])
        
        # Handle Motor Outputs
        if self.motor_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if col.lower().startswith('motor[')])
        
        return selected_features

    def update_legend(self, series_by_category):
        """Update legend items based on the series data (unique label per axis)."""
        # Clear existing legend items
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # If empty, exit early
        if not series_by_category:
            return
            
        # Add new legend items (sorted alphabetically for consistent display)
        for legend_label in sorted(series_by_category.keys()):
            # Special handling for motors
            if legend_label.startswith('Motor'):
                # Skip individual motor entries as they'll be handled separately
                continue
                
            legend_label_widget = QLabel()
            legend_label_widget.setFont(self.create_font('label'))

            # Get color value
            color_value = series_by_category[legend_label]
            if isinstance(color_value, str) and color_value.startswith('#'):
                # Already a color name (like "#ff0000")
                color_name = color_value
            else:
                # Need to determine color from name
                color = QColor(*COLOR_PALETTE.get(legend_label, (128, 128, 128)))
                color_name = color.name()

            # Create a colored dot/square and the label text
            legend_label_widget.setText(f"<span style='color: {color_name}'>●</span> {legend_label}")
            # Remove any background color from the label
            legend_label_widget.setStyleSheet("background: none;")
            self.legend_layout.addWidget(legend_label_widget)
            
        # Handle motors separately
        motor_entries = [(label, color) for label, color in series_by_category.items() if label.startswith('Motor')]
        if motor_entries:
            # Add "Motors:" label
            motor_label = QLabel("Motors:")
            motor_label.setFont(self.create_font('label'))
            motor_label.setStyleSheet("background: transparent;")
            self.legend_layout.addWidget(motor_label)
            
            # Group motors by 4
            for i in range(0, len(motor_entries), 4):
                # Create a row for up to 4 motors
                row_widget = QWidget()
                row_widget.setStyleSheet("background: transparent;")
                row_layout = QHBoxLayout(row_widget)
                row_layout.setSpacing(10)
                row_layout.setContentsMargins(0, 0, 0, 0)
                
                # Add up to 4 motors in this row
                for j in range(4):
                    if i + j < len(motor_entries):
                        label, color_value = motor_entries[i + j]
                        # Extract motor number (1-based)
                        try:
                            motor_num = int(label.split(' ')[1]) + 1
                        except:
                            motor_num = i + j + 1
                        # Create a colored dot
                        dot_label = QLabel("●")
                        if isinstance(color_value, str) and color_value.startswith('#'):
                            color_name = color_value
                        else:
                            color = QColor(*MOTOR_COLORS[(motor_num-1) % len(MOTOR_COLORS)])
                            color_name = color.name()
                        dot_label.setStyleSheet("color: %s; font-size: 14px; background: transparent;" % color_name)
                        # Add motor number
                        motor_num_label = QLabel(f"{motor_num}")
                        motor_num_label.setFont(self.create_font('label'))
                        motor_num_label.setStyleSheet("background: transparent;")
                        # Add dot and number to row
                        row_layout.addWidget(dot_label)
                        row_layout.addWidget(motor_num_label)
                row_layout.addStretch()
                self.legend_layout.addWidget(row_widget)

    def line_width_changed(self, value):
        """Update line width for all series in all charts"""
        # Convert slider value to actual line width (divide by 2)
        line_width = value / 2.0
        
        # Store current line width for later use
        self.current_line_width = line_width
        
        # Get the parent FL1GHTViewer instance
        parent = self.parent()
        if parent and hasattr(parent, 'chart_manager'):
            for chart_view in parent.chart_manager.chart_views:
                if chart_view.chart():
                    for series in chart_view.chart().series():
                        # Skip only the zero reference line (black line at y=0)
                        if series.name() == "Zero" and series.pen().color() == Qt.black:
                            continue
                        pen = series.pen()
                        pen.setWidthF(line_width)  # Use setWidthF for floating point width
                        series.setPen(pen)
                    chart_view.chart().update()
        
        # Also update Step Response plot if that tab is active
        if parent and hasattr(parent, 'tab_widget') and hasattr(parent, 'step_response_widget'):
            if parent.tab_widget.currentIndex() == 2:
                # Update line width for existing series without recreating the plot
                for chart_view in parent.step_response_widget.chart_views:
                    if chart_view.chart():
                        for series in chart_view.chart().series():
                            # Skip the reference line (black line at y=1.0)
                            if series.name() == "Zero" or series.pen().color() == Qt.black:
                                continue
                            pen = series.pen()
                            pen.setWidthF(line_width)
                            series.setPen(pen)
                        chart_view.chart().update()
        
        self.line_width_label.setText(f"Line Width: {line_width:.1f}px")

    def notify_spectral_update(self, _):
        parent = self.parent()
        # Find the main viewer (FL1GHTViewer) in the parent chain
        while parent is not None and not hasattr(parent, 'spectral_widget'):
            parent = parent.parent() if hasattr(parent, 'parent') else None
        if parent and hasattr(parent, 'spectral_widget') and hasattr(parent, 'df'):
            parent.spectral_widget.update_spectrum(parent.df)
            
    def notify_parent_update(self, _):
        """Notify parent (FL1GHTViewer) to update the plot with currently selected features"""
        from PySide6.QtCore import QTimer
        if self.debug('DEBUG'):
            print(f"[DEBUG] notify_parent_update: called, selected_logs={getattr(self, 'selected_logs', None)}")
        # If we already have a pending update, don't schedule another one
        if hasattr(self, 'update_timer') and self.update_timer is not None and self.update_timer.isActive():
            if self.debug('DEBUG'):
                print(f"[DEBUG] notify_parent_update: update_timer is active, skipping")
            return
        # Create a timer for delayed update
        if not hasattr(self, 'update_timer') or self.update_timer is None:
            self.update_timer = QTimer()
            self.update_timer.setSingleShot(True)
            self.update_timer.timeout.connect(self._do_update)
        # Start or restart the timer (300ms delay)
        self.update_timer.start(300)
        if self.debug('DEBUG'):
            print(f"[DEBUG] notify_parent_update: timer started")
    
    def _do_update(self):
        """Actually perform the update after the timer expires"""
        parent = self.parent()
        # Find the main viewer (FL1GHTViewer) in the parent chain
        while parent is not None and not hasattr(parent, 'plot_selected'):
            parent = parent.parent() if hasattr(parent, 'parent') else None
        if self.debug('DEBUG'):
            print(f"[DEBUG] _do_update: parent={parent}, tab={parent.tab_widget.currentIndex() if parent and hasattr(parent, 'tab_widget') else None}")
        # Check if we're in the Time Domain tab (index 0)
        if parent and hasattr(parent, 'tab_widget') and parent.tab_widget.currentIndex() == 0:
            # Call plot_selected to update the chart and legend
            if self.debug('DEBUG'):
                print(f"[DEBUG] _do_update: calling plot_selected() for Time Domain tab")
            parent.plot_selected()

    def uncheck_all_features(self):
        for checkbox in [self.gyro_unfilt_checkbox, self.gyro_scaled_checkbox, 
                         self.pid_p_checkbox, self.pid_i_checkbox, self.pid_d_checkbox,
                         self.pid_f_checkbox, self.setpoint_checkbox, self.rc_checkbox,
                         self.throttle_checkbox, self.motor_checkbox]:
            checkbox.setChecked(False)

    def set_time_domain_mode(self, enabled: bool):
        """Set the widget to time domain mode"""
        self.time_domain_mode = enabled
        # Update selection mode based on current tab
        current_tab = self.get_current_tab_index()
        if current_tab in [0, 3, 4]:  # Time Domain, Noise Analysis, Drone Config
            self.logs_list.setSelectionMode(QListWidget.SingleSelection)
        elif current_tab in [1, 2]:  # Spectral Analysis, Step Response
            self.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
        elif current_tab == 5:  # Export
            self.logs_list.setSelectionMode(QListWidget.SingleSelection)

    def _set_checkboxes_enabled(self, enabled):
        """Enable or disable all feature checkboxes"""
        self.gyro_scaled_checkbox.setEnabled(enabled)
        self.gyro_unfilt_checkbox.setEnabled(enabled)
        self.pid_p_checkbox.setEnabled(enabled)
        self.pid_i_checkbox.setEnabled(enabled)
        self.pid_d_checkbox.setEnabled(enabled)
        self.pid_f_checkbox.setEnabled(enabled)
        self.setpoint_checkbox.setEnabled(enabled)
        self.rc_checkbox.setEnabled(enabled)
        self.throttle_checkbox.setEnabled(enabled)
        self.motor_checkbox.setEnabled(enabled)

    def set_step_response_mode(self, enabled):
        """Enable or disable step response mode"""
        self.step_response_mode = enabled
        
        # Disable checkboxes in step response mode
        self._set_checkboxes_enabled(not enabled)
        
        # Ensure legend is always hidden in step response mode
        self.legend_group.setVisible(not enabled)
        
        # Set selection mode for logs list
        if enabled:
            self.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
            # Connect step response handler
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_spectral_log_selection)
                except (TypeError, RuntimeError):
                    pass
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_step_response_log_selection)
                except (TypeError, RuntimeError):
                    pass
            self.logs_list.itemSelectionChanged.connect(self._handle_step_response_log_selection)
        else:
            self.logs_list.setSelectionMode(QListWidget.SingleSelection)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_step_response_log_selection)
                except (TypeError, RuntimeError):
                    pass

    def set_spectral_mode(self, enabled):
        """Set the widget to frequency domain mode"""
        self.spectral_mode = enabled
        # Update selection mode based on current tab
        current_tab = self.get_current_tab_index()
        if current_tab == 0:  # Time Domain
            self.logs_list.setSelectionMode(QListWidget.SingleSelection)
            # Enable checkboxes for time domain
            self._set_checkboxes_enabled(True)
        elif current_tab == 3:  # Noise Analysis
            self.logs_list.setSelectionMode(QListWidget.SingleSelection)
            # Disable checkboxes for noise analysis
            self._set_checkboxes_enabled(False)
        elif current_tab == 5:  # Drone Config
            self.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
            # Disable checkboxes for drone config tab
            self._set_checkboxes_enabled(False)
        elif current_tab == 1:  # Frequency Domain
            self.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
            # Enable checkboxes for frequency domain
            self._set_checkboxes_enabled(True)
            # Automatically select gyro (raw) and gyro (filtered) for frequency domain analysis
            self.gyro_unfilt_checkbox.setChecked(True)
            self.gyro_scaled_checkbox.setChecked(True)
            # Connect frequency domain handler
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_step_response_log_selection)
                except (TypeError, RuntimeError):
                    pass
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_spectral_log_selection)
                except (TypeError, RuntimeError):
                    pass
            self.logs_list.itemSelectionChanged.connect(self._handle_spectral_log_selection)
        elif current_tab == 2:  # Step Response
            self.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
            # Disable checkboxes for step response
            self._set_checkboxes_enabled(False)
            # Connect step response handler
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_spectral_log_selection)
                except (TypeError, RuntimeError):
                    pass
                try:
                    self.logs_list.itemSelectionChanged.disconnect(self._handle_step_response_log_selection)
                except (TypeError, RuntimeError):
                    pass
            self.logs_list.itemSelectionChanged.connect(self._handle_step_response_log_selection)

    def _handle_step_response_checkbox(self, state):
        """Handle checkbox state changes in step response mode"""
        # Count how many checkboxes are checked
        checked_count = sum(1 for checkbox in [
            self.gyro_scaled_checkbox,
            self.gyro_unfilt_checkbox,
            self.pid_p_checkbox,
            self.pid_i_checkbox,
            self.pid_d_checkbox,
            self.pid_f_checkbox,
            self.setpoint_checkbox,
            self.rc_checkbox,
            self.throttle_checkbox,
            self.motor_checkbox
        ] if checkbox.isChecked())
        
        # If more than 3 are checked, uncheck the last one
        if checked_count > 3:
            sender = self.sender()
            if sender:
                sender.setChecked(False)
            QMessageBox.warning(self, "Warning", "You can only select up to 3 features for step response analysis.")

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.resize(420, 260)  # Make the dialog wider and taller
        layout = QVBoxLayout(dialog)

        # Author name
        author_label = QLabel("Author Name:")
        author_edit = QLineEdit()
        author_edit.setText(self.author_name)
        layout.addWidget(author_label)
        layout.addWidget(author_edit)

        # Drone name
        drone_label = QLabel("Drone Name:")
        drone_edit = QLineEdit()
        drone_edit.setText(self.drone_name)
        layout.addWidget(drone_label)
        layout.addWidget(drone_edit)

        # Checkbox for using drone in filename
        drone_checkbox = QCheckBox("Include drone name in export filename")
        drone_checkbox.setChecked(self.use_drone_in_filename)
        layout.addWidget(drone_checkbox)

        # Debug level selection
        debug_label = QLabel("Debug Level:")
        debug_combo = QComboBox()
        debug_combo.addItems(["INFO", "DEBUG", "VERBOSE"])
        debug_combo.setCurrentText(self.debug_level)
        debug_combo.setStyleSheet("QComboBox { border: 1.5px solid white; border-radius: 4px; }")
        layout.addWidget(debug_label)
        layout.addWidget(debug_combo)

        # Export directory
        dir_label = QLabel("Export Directory:")
        dir_edit = QLineEdit()
        dir_edit.setText(self.export_dir)
        browse_btn = QPushButton("Browse...")
        def browse_dir():
            dir_path = QFileDialog.getExistingDirectory(self, "Select Export Directory", self.export_dir)
            if dir_path:
                dir_edit.setText(dir_path)
        browse_btn.clicked.connect(browse_dir)
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(dir_edit)
        dir_layout.addWidget(browse_btn)
        layout.addWidget(dir_label)
        layout.addLayout(dir_layout)

        # Save/Cancel buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        def save_settings():
            self.author_name = author_edit.text()
            self.export_dir = dir_edit.text()
            self.drone_name = drone_edit.text()
            self.use_drone_in_filename = drone_checkbox.isChecked()
            self.debug_level = debug_combo.currentText()
            # Save to config/settings.json
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            config_dir = os.path.join(app_dir, "config")
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
            config_path = os.path.join(config_dir, "settings.json")
            try:
                with open(config_path, "w") as f:
                    json.dump({
                        "author_name": self.author_name,
                        "export_dir": self.export_dir,
                        "drone_name": self.drone_name,
                        "use_drone_in_filename": self.use_drone_in_filename,
                        "debug_level": self.debug_level
                    }, f, indent=2)
            except Exception as e:
                print(f"[Settings] Failed to save config: {e}")
            dialog.accept()
        save_btn.clicked.connect(save_settings)
        cancel_btn.clicked.connect(dialog.reject)

        dialog.exec()

    def _get_drone_name(self, parent):
        if hasattr(parent, 'feature_widget') and hasattr(parent.feature_widget, 'drone_name'):
            return parent.feature_widget.drone_name
        return ""
    def _use_drone_in_filename(self, parent):
        if hasattr(parent, 'feature_widget') and hasattr(parent.feature_widget, 'use_drone_in_filename'):
            return parent.feature_widget.use_drone_in_filename
        return False

    def on_logs_selection_changed(self):
        """Handle log selection changes in the list widget"""
        selected_items = self.logs_list.selectedItems()
        if self.debug('DEBUG'):
            print(f"[DEBUG] on_logs_selection_changed: selected_items={[item.text() for item in selected_items]}")
        if not selected_items:
            return

        # Get the current tab
        current_tab = self.get_current_tab_index()
        if self.debug('DEBUG'):
            print(f"[DEBUG] on_logs_selection_changed: current_tab={current_tab}")
        
        # Force single selection for Time Domain, Noise Analysis
        if current_tab in [0, 3]:  # Time Domain, Noise Analysis
            if len(selected_items) > 1:
                last_selected = selected_items[-1]
                self.logs_list.clearSelection()
                last_selected.setSelected(True)
                selected_items = [last_selected]
                if self.debug('DEBUG'):
                    print(f"[DEBUG] on_logs_selection_changed: forced single selection, kept {last_selected.text()}")
        elif current_tab == 5:  # Drone Config
            if len(selected_items) > 2:
                # Unselect the last selected item
                selected_items[-1].setSelected(False)
                selected_items = selected_items[:-1]
                QMessageBox.warning(self, "Warning", "You can only select up to 2 logs for drone config comparison.")
                if self.debug('DEBUG'):
                    print(f"[DEBUG] on_logs_selection_changed: forced two selection, kept {[item.text() for item in selected_items]}")
        elif current_tab == 1:  # Frequency Domain
            if len(selected_items) > 2:
                # Unselect the last selected item
                selected_items[-1].setSelected(False)
                selected_items = selected_items[:-1]
                QMessageBox.warning(self, "Warning", "You can only select up to 2 logs for frequency domain analysis.")
                if self.debug('DEBUG'):
                    print(f"[DEBUG] on_logs_selection_changed: forced two selection for frequency domain, kept {[item.text() for item in selected_items]}")
        else:
            # For all other tabs, check if Ctrl/Cmd or Shift key is pressed
            modifiers = QApplication.keyboardModifiers()
            is_ctrl_cmd = modifiers & (Qt.ControlModifier | Qt.MetaModifier)
            is_shift = modifiers & Qt.ShiftModifier
            
            # If not multi-select and more than one item is selected, clear all but the last selected
            if not (is_ctrl_cmd or is_shift) and len(selected_items) > 1:
                last_selected = selected_items[-1]
                self.logs_list.clearSelection()
                last_selected.setSelected(True)
                selected_items = [last_selected]
                if self.debug('DEBUG'):
                    print(f"[DEBUG] on_logs_selection_changed: forced single selection (no multi-select), kept {last_selected.text()}")

        # Update selected_logs list
        self.selected_logs = [item.text() for item in selected_items]
        if self.debug('DEBUG'):
            print(f"[DEBUG] on_logs_selection_changed: self.selected_logs={self.selected_logs}")
        
        # Update current log
        if self.selected_logs:
            self.current_log = self.loaded_logs[self.selected_logs[0]]
            self.df = self.current_log
            if self.debug('DEBUG'):
                print(f"[DEBUG] on_logs_selection_changed: current_log={self.selected_logs[0]}, df shape={self.df.shape if hasattr(self.df, 'shape') else None}")
            
            # Update combo box to match list selection
            if len(self.selected_logs) == 1:
                index = self.logs_combo.findText(self.selected_logs[0])
                if index >= 0:
                    self.logs_combo.setCurrentIndex(index)
                    if self.debug('DEBUG'):
                        print(f"[DEBUG] on_logs_selection_changed: logs_combo set to {self.selected_logs[0]}")
            
            # Only notify parent for non-Time Domain tabs
            if current_tab != 0:  # Don't auto-plot in Time Domain tab
                # For Drone Config tab, pass up to 2 logs
                if current_tab == 5:  # Drone Config (changed from 4 to 5)
                    if self.debug('DEBUG'):
                        print(f"[DEBUG] on_logs_selection_changed: notifying parent for Drone Config tab with logs {self.selected_logs[:2]}")
                    self.notify_parent_update(self.selected_logs[:2])
                else:
                    if self.debug('DEBUG'):
                        print(f"[DEBUG] on_logs_selection_changed: notifying parent for tab {current_tab}")
                    self.notify_parent_update(None)

    def on_log_selected(self, index):
        """Handle log selection changes in the combo box"""
        if index < 0:
            return
            
        log_name = self.logs_combo.currentText()
        if not log_name:
            return
            
        # Update list widget selection
        items = self.logs_list.findItems(log_name, Qt.MatchExactly)
        if items:
            self.logs_list.clearSelection()
            items[0].setSelected(True)
            
        # Update current log
        self.current_log = self.loaded_logs[log_name]
        self.df = self.current_log
        self.selected_logs = [log_name]
        
        # Only notify parent for non-Time Domain tabs
        current_tab = self.get_current_tab_index()
        if current_tab != 0:  # Don't auto-plot in Time Domain tab
            self.notify_parent_update(None)

    def _handle_step_response_log_selection(self):
        """Handle log selection changes in step response mode"""
        if not hasattr(self, 'step_response_mode') or not self.step_response_mode:
            return
            
        selected_items = self.logs_list.selectedItems()
        if len(selected_items) > 5:
            # Unselect the last selected item
            selected_items[-1].setSelected(False)
            QMessageBox.warning(self, "Warning", "You can only select up to 5 flights for step response analysis.")

    def _handle_spectral_log_selection(self):
        """Handle log selection changes in frequency domain mode"""
        if not hasattr(self, 'spectral_mode') or not self.spectral_mode:
            return
            
        selected_items = self.logs_list.selectedItems()
        if len(selected_items) > 2:
            # Unselect the last selected item
            selected_items[-1].setSelected(False)
            QMessageBox.warning(self, "Warning", "You can only select up to 2 flights for frequency domain.")

    def debug(self, level):
        levels = {"INFO": 1, "DEBUG": 2, "VERBOSE": 3}
        return levels.get(getattr(self, 'debug_level', 'INFO'), 1) >= levels.get(level, 1)

    def check_missing_features(self):
        """Check if selected checkboxes have corresponding data in the current log and show warnings"""
        if not hasattr(self, 'df') or self.df is None:
            return
            
        missing_features = []
        
        # Check gyro data
        if self.gyro_unfilt_checkbox.isChecked():
            gyro_unfilt_cols = [col for col in self.df.columns if 'gyrounfilt' in col.lower()]
            if not gyro_unfilt_cols:
                missing_features.append("Gyro (raw)")
                
        if self.gyro_scaled_checkbox.isChecked():
            gyro_scaled_cols = [col for col in self.df.columns if 'gyroadc' in col.lower() and '(deg/s)' in col]
            if not gyro_scaled_cols:
                missing_features.append("Gyro (filtered)")
        
        # Check PID data
        if self.pid_p_checkbox.isChecked():
            pid_p_cols = [col for col in self.df.columns if 'axisp' in col.lower()]
            if not pid_p_cols:
                missing_features.append("P-Term")
                
        if self.pid_i_checkbox.isChecked():
            pid_i_cols = [col for col in self.df.columns if 'axisi' in col.lower()]
            if not pid_i_cols:
                missing_features.append("I-Term")
                
        if self.pid_d_checkbox.isChecked():
            pid_d_cols = [col for col in self.df.columns if 'axisd' in col.lower()]
            if not pid_d_cols:
                missing_features.append("D-Term")
                
        if self.pid_f_checkbox.isChecked():
            pid_f_cols = [col for col in self.df.columns if 'axisf' in col.lower()]
            if not pid_f_cols:
                missing_features.append("FeedForward")
        
        # Check Setpoint data
        if self.setpoint_checkbox.isChecked():
            setpoint_cols = [col for col in self.df.columns if 'setpoint' in col.lower()]
            if not setpoint_cols:
                missing_features.append("Setpoint")
        
        # Check RC data
        if self.rc_checkbox.isChecked():
            rc_cols = [col for col in self.df.columns if 'rccommand' in col.lower() and '[3]' not in col]
            if not rc_cols:
                missing_features.append("RC Commands")
        
        # Check Throttle data
        if self.throttle_checkbox.isChecked():
            throttle_cols = [col for col in self.df.columns if 'rccommand[3]' in col.lower()]
            if not throttle_cols:
                missing_features.append("Throttle")
        
        # Check Motor Outputs
        if self.motor_checkbox.isChecked():
            motor_cols = [col for col in self.df.columns if col.lower().startswith('motor[')]
            if not motor_cols:
                missing_features.append("Motor Outputs")
        
        # Show warning if any features are missing
        if missing_features:
            feature_list = ", ".join(missing_features)
            QMessageBox.warning(
                self, 
                "Missing Data", 
                f"The following selected features are not available in the current log:\n\n{feature_list}\n\nThese features will not be plotted."
            )

class ControlWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar - hidden and not added to layout
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(self.create_font('label'))
        self.progress_bar.setVisible(False)
        # Not adding to layout: layout.addWidget(self.progress_bar)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.setContentsMargins(10, 0, 10, 0)  # Add horizontal margins
        zoom_label = QLabel("Zoom:")
        zoom_label.setFont(self.create_font('label'))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(0)
        self.zoom_slider.setMaximum(1000)
        self.zoom_slider.setValue(0)
        self.zoom_slider.setTickPosition(QSlider.NoTicks)
        self.zoom_ratio_label = QLabel("1.0x")
        self.zoom_ratio_label.setFont(self.create_font('label'))
        self.reset_zoom_button = QPushButton("Reset Zoom")
        self.reset_zoom_button.setFont(self.create_font('button'))
        
        zoom_layout.addWidget(zoom_label)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_ratio_label)
        zoom_layout.addWidget(self.reset_zoom_button)
        layout.addLayout(zoom_layout)

        # Scroll controls
        scroll_layout = QHBoxLayout()
        scroll_layout.setContentsMargins(10, 0, 10, 0)  # Add horizontal margins
        scroll_label = QLabel("Scroll:")
        scroll_label.setFont(self.create_font('label'))
        self.scroll_slider = QSlider(Qt.Horizontal)
        self.scroll_slider.setMinimum(0)
        self.scroll_slider.setMaximum(1000)
        self.scroll_slider.setValue(500)
        self.scroll_slider.setTickPosition(QSlider.NoTicks)
        
        scroll_layout.addWidget(scroll_label)
        scroll_layout.addWidget(self.scroll_slider)
        layout.addLayout(scroll_layout)

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font 

class SpectralAnalyzerWidget(QWidget):
    def __init__(self, feature_widget, parent=None):
        super().__init__(parent)
        self.df = None
        self.feature_widget = feature_widget
        self.expanded_chart = None
        self.original_heights = {}  # Store original heights for restoration
        self.setup_ui()
        self.log_count = 0  # Track number of logs plotted

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Smoothing setup controls
        smoothing_group = QGroupBox()
        smoothing_group.setStyleSheet("QGroupBox { border: none; }")
        smoothing_layout = QHBoxLayout()
        self.window_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768]
        self.window_size_slider = QSlider(Qt.Horizontal)
        self.window_size_slider.setMinimum(0)
        self.window_size_slider.setMaximum(len(self.window_sizes) - 1)
        self.window_size_slider.setValue(5)  # Default to 8192
        self.window_size_slider.setTickInterval(1)
        self.window_size_slider.setTickPosition(QSlider.TicksBelow)
        self.window_size_slider.setSingleStep(1)
        # Smoothing labels
        max_label = QLabel("Smoothing: Max")
        max_label.setFont(self.create_font('label'))
        min_label = QLabel("Smoothing: Min")
        min_label.setFont(self.create_font('label'))
        smoothing_layout.addWidget(max_label)
        smoothing_layout.addWidget(self.window_size_slider)
        smoothing_layout.addWidget(min_label)
        self.window_size_slider.valueChanged.connect(lambda _: self.update_spectrum(self.df))
        smoothing_group.setLayout(smoothing_layout)
        layout.addWidget(smoothing_group)

        # Charts container
        self.charts_container = QWidget()
        charts_layout = QVBoxLayout(self.charts_container)
        charts_layout.setSpacing(10)
        self.chart_views = []  # Will now hold tuples: (full_range_view, zoomed_view)
        for axis in ['Roll', 'Pitch', 'Yaw']:
            row_layout = QHBoxLayout()
            # Full range plot
            chart_view_full = ClickableChartView()
            chart_view_full.setRenderHint(QPainter.Antialiasing)
            chart_view_full.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            chart_view_full.setMinimumHeight(200)
            chart_full = QChart()
            chart_full.setTitle(f"{axis} Spectrum (Full)")
            title_font = QFont()
            title_font.setPointSize(10)
            chart_full.setTitleFont(title_font)
            chart_full.legend().setVisible(True)
            chart_full.setMargins(QMargins(10, 10, 10, 10))
            chart_view_full.setChart(chart_full)
            chart_view_full.setMouseTracking(True)
            chart_view_full.mouseMoveEvent = lambda event, cv=chart_view_full: self.show_tooltip(event, cv)
            chart_view_full.setCursor(Qt.CrossCursor)  # Add crosshair cursor
            chart_view_full.clicked.connect(lambda cv=chart_view_full: self.on_chart_clicked(cv))
            row_layout.addWidget(chart_view_full, stretch=3)  # Make full plot wider
            # Zoomed plot (0-100 Hz)
            chart_view_zoom = ClickableChartView()
            chart_view_zoom.setRenderHint(QPainter.Antialiasing)
            chart_view_zoom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            chart_view_zoom.setMinimumHeight(200)
            chart_view_zoom.setMaximumWidth(400)  # Make zoomed plot even wider
            chart_zoom = QChart()
            chart_zoom.setTitle(f"{axis} Spectrum (0-100 Hz)")
            chart_zoom.setTitleFont(title_font)
            chart_zoom.legend().setVisible(True)
            chart_zoom.setMargins(QMargins(10, 10, 10, 10))
            chart_view_zoom.setChart(chart_zoom)
            chart_view_zoom.setMouseTracking(True)
            chart_view_zoom.mouseMoveEvent = lambda event, cv=chart_view_zoom: self.show_tooltip(event, cv)
            chart_view_zoom.setCursor(Qt.CrossCursor)  # Add crosshair cursor
            chart_view_zoom.clicked.connect(lambda cv=chart_view_zoom: self.on_chart_clicked(cv))
            row_layout.addWidget(chart_view_zoom, stretch=1)  # Make zoomed plot narrower
            # Store both views as a tuple
            self.chart_views.append((chart_view_full, chart_view_zoom))
            charts_layout.addLayout(row_layout)
        layout.addWidget(self.charts_container)

    def on_chart_clicked(self, clicked_chart_view):
        """Handle chart click to expand or restore."""
        # If the clicked chart is already expanded, restore all
        if self.expanded_chart is clicked_chart_view:
            self.restore_all_charts()
        else:
            # If another chart is expanded, or no chart is expanded
            self.expand_chart(clicked_chart_view)

    def expand_chart(self, chart_view):
        """Expand a single chart and hide others."""
        # Store original heights if not already stored
        if not self.original_heights:
            for full_view, zoom_view in self.chart_views:
                self.original_heights[full_view] = full_view.height()
                self.original_heights[zoom_view] = zoom_view.height()
        
        # Hide all charts except the clicked one
        for full_view, zoom_view in self.chart_views:
            full_view.hide()
            zoom_view.hide()
        
        # Show only the clicked chart
        chart_view.show()
        
        # Remove maximum width constraint for the expanded chart
        chart_view.setMaximumWidth(16777215)  # Qt's default maximum width
        
        self.expanded_chart = chart_view

    def restore_all_charts(self):
        """Restore all charts to their original visibility and heights."""
        for full_view, zoom_view in self.chart_views:
            full_view.show()
            zoom_view.show()
            # Restore original heights if available
            if full_view in self.original_heights:
                full_view.setMinimumHeight(self.original_heights[full_view])
            if zoom_view in self.original_heights:
                zoom_view.setMinimumHeight(self.original_heights[zoom_view])
            # Restore maximum width constraint for zoomed charts
            zoom_view.setMaximumWidth(400)
        
        self.expanded_chart = None

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font

    def update_spectrum(self, df, log_label=None, clear_charts=True):
        # Always clear all series before plotting new spectra (fix caching on smoothing change)
        if clear_charts:
            for (chart_view_full, chart_view_zoom) in self.chart_views:
                chart_view_full.chart().removeAllSeries()
                chart_view_zoom.chart().removeAllSeries()
            self.log_count = 0  # Reset log count when clearing charts
        else:
            self.log_count += 1  # Increment log count for additional logs
            
        # Determine if we should use alternative colors for second log
        use_alternative_colors = (self.log_count > 0)
            
        if df is not None:
            self.df = df
        df = self.df
        if df is None or df.empty:
            print("[INFO][SpectralAnalyzer] DataFrame is empty or None.")
            return
        # Welch parameters from user controls
        window_size = self.window_sizes[self.window_size_slider.value()]
        window_type = 'hann'  # Fixed
        overlap = 0.5        # Fixed (50%)

        # Determine which types are selected (Gyro raw, Gyro filtered, PID, Setpoint, RC Command)
        selected_types = []
        fw = self.feature_widget
        if hasattr(fw, 'gyro_unfilt_checkbox') and fw.gyro_unfilt_checkbox.isChecked():
            selected_types.append('raw')
        if hasattr(fw, 'gyro_scaled_checkbox') and fw.gyro_scaled_checkbox.isChecked():
            selected_types.append('filtered')
        if hasattr(fw, 'pid_p_checkbox') and fw.pid_p_checkbox.isChecked():
            selected_types.append('pterm')
        if hasattr(fw, 'pid_i_checkbox') and fw.pid_i_checkbox.isChecked():
            selected_types.append('iterm')
        if hasattr(fw, 'pid_d_checkbox') and fw.pid_d_checkbox.isChecked():
            selected_types.append('dterm')
        if hasattr(fw, 'setpoint_checkbox') and fw.setpoint_checkbox.isChecked():
            selected_types.append('setpoint')
        if hasattr(fw, 'rc_checkbox') and fw.rc_checkbox.isChecked():
            selected_types.append('rc')
        if not selected_types:
            print("[INFO][SpectralAnalyzer] No types selected, nothing will be plotted.")
            return
        if self.feature_widget.debug('INFO'):
            print(f"[INFO][SpectralAnalyzer] Selected types: {selected_types}")

        # Select color palette based on whether to use alternative colors
        color_palette = ALTERNATIVE_COLOR_PALETTE if use_alternative_colors else COLOR_PALETTE

        # Map type to column patterns, legend, and color
        type_to_pattern = {
            'raw': ('gyroUnfilt[{}]', 'Gyro (raw)', QColor(*color_palette.get('Gyro (raw)', (255, 0, 255)))),
            'filtered': ('gyroADC[{}] (deg/s)', 'Gyro (filtered)', QColor(*color_palette.get('Gyro (filtered)', (0, 255, 255)))),
            'pterm': ('axisP[{}]', 'P-Term', QColor(*color_palette.get('P-Term', (255, 200, 0)))),
            'iterm': ('axisI[{}]', 'I-Term', QColor(*color_palette.get('I-Term', (255, 128, 0)))),
            'dterm': ('axisD[{}]', 'D-Term', QColor(*color_palette.get('D-Term', (128, 0, 255)))),
            'setpoint': ('setpoint[{}]', 'Setpoint', QColor(*color_palette.get('Setpoint', (0, 0, 0)))),
            'rc': ('rcCommand[{}]', 'RC Command', QColor(*color_palette.get('RC Command', (128, 128, 0)))),
        }
        axis_names = ['Roll', 'Pitch', 'Yaw']
        axis_indices = [0, 1, 2]

        time_data = df['time'].values.astype(float)
        if time_data.max() > 1e6:
            time_data = time_data / 1_000_000.0
        elif time_data.max() > 1e3:
            time_data = time_data / 1_000.0
        time_data = time_data - time_data.min()
        dt = np.mean(np.diff(time_data))
        fs = 1.0 / dt if dt > 0 else 0.0
        if self.feature_widget.debug('INFO'):
            print(f"[INFO][SpectralAnalyzer] Sampling rate: {fs:.2f} Hz")

        from scipy import signal

        legend_labels = set()
        plotted_types = set()
        for axis_idx, axis_name in enumerate(['Roll', 'Pitch', 'Yaw']):
            chart_full = self.chart_views[axis_idx][0].chart()
            chart_zoom = self.chart_views[axis_idx][1].chart()
            chart_full.legend().setVisible(False)
            chart_zoom.legend().setVisible(False)
            series_list = []
            for t in selected_types:
                pattern, label, color = type_to_pattern[t]
                col_name = pattern.format(axis_idx)
                if col_name in df.columns:
                    axis_data = df[col_name].values
                    if len(axis_data) < 2:
                        continue
                    nperseg = window_size
                    noverlap = int(window_size * overlap)
                    freqs, psd = signal.welch(axis_data, fs=fs, nperseg=nperseg, window=window_type, noverlap=noverlap, scaling='density')
                    psd_db = 10 * np.log10(psd + 1e-10)
                    # Full range series
                    series_full = QLineSeries()
                    # Add log label to series name if provided
                    series_name = label
                    if log_label:
                        series_name = f"{label} [{log_label}]"
                    series_full.setName(series_name)
                    for f, p in zip(freqs, psd_db):
                        series_full.append(f, p)
                    pen = series_full.pen()
                    pen.setColor(color)
                    pen.setWidthF(1.5)
                    series_full.setPen(pen)
                    chart_full.addSeries(series_full)
                    # Zoomed series (0-100 Hz)
                    series_zoom = QLineSeries()
                    series_zoom.setName(series_name)
                    for f, p in zip(freqs, psd_db):
                        if f <= 100:
                            series_zoom.append(f, p)
                    pen_zoom = series_zoom.pen()
                    pen_zoom.setColor(color)
                    pen_zoom.setWidthF(1.5)
                    series_zoom.setPen(pen_zoom)
                    chart_zoom.addSeries(series_zoom)
                    series_list.append(series_full)
                    # For the legend, include the log name and label
                    if log_label:
                        legend_labels.add((label, color.name(), log_label))
                    else:
                        legend_labels.add((label, color.name(), None))
                    plotted_types.add(t)
            # Axes for full range
            chart_full.createDefaultAxes()
            axes_x_full = chart_full.axes(Qt.Horizontal)
            axes_y_full = chart_full.axes(Qt.Vertical)
            if axes_x_full and axes_y_full:
                axis_x = axes_x_full[0]
                axis_y = axes_y_full[0]
                axis_x.setTitleText("Frequency (Hz)")
                axis_x.setTitleVisible(True)
                axis_x.setLabelsVisible(True)
                axis_x.setGridLineVisible(True)
                axis_x.setRange(0, int(fs/2))
                axis_x.setTickCount(int(fs/2 / 50) + 1)
                axis_x.setLabelFormat("%.0f")
                axis_x.setTickInterval(50)
                axis_x.setTickAnchor(0)
                axis_x.setTickType(QValueAxis.TicksDynamic)
                small_font = self.create_font('label')
                small_font.setPointSize(8)
                axis_x.setLabelsFont(small_font)
                axis_y.setTitleText("Spectral Power (dB)")
                axis_y.setTitleVisible(True)
                axis_y.setLabelsVisible(True)
                axis_y.setGridLineVisible(True)
                axis_y.setRange(-50, 20)
            # Axes for zoomed (0-100 Hz)
            chart_zoom.createDefaultAxes()
            axes_x_zoom = chart_zoom.axes(Qt.Horizontal)
            axes_y_zoom = chart_zoom.axes(Qt.Vertical)
            if axes_x_zoom and axes_y_zoom:
                axis_xz = axes_x_zoom[0]
                axis_yz = axes_y_zoom[0]
                axis_xz.setTitleText("Frequency (Hz)")
                axis_xz.setTitleVisible(True)
                axis_xz.setLabelsVisible(True)
                axis_xz.setGridLineVisible(True)
                axis_xz.setRange(0, 100)
                axis_xz.setTickCount(5)
                axis_xz.setTickInterval(25)
                axis_xz.setTickAnchor(0)
                axis_xz.setTickType(QValueAxis.TicksDynamic)
                axis_xz.setLabelsFont(small_font)  # Using the same small FONT_CONFIG font
                axis_yz.setTitleText("Spectral Power (dB)")
                axis_yz.setTitleVisible(True)
                axis_yz.setLabelsVisible(True)
                axis_yz.setGridLineVisible(True)
                axis_yz.setRange(-50, 20)
            chart_full.update()
            chart_zoom.update()
        
        # Update the left legend area (legend_group/legend_layout)
        legend_layout = getattr(self.feature_widget, 'legend_layout', None)
        if legend_layout is not None:
            # Only clear legend if we're on the first log
            if clear_charts:
                while legend_layout.count():
                    item = legend_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
            # Sort legend entries by label then by log_label for consistent display
            sorted_labels = sorted(legend_labels, key=lambda x: (x[0], str(x[2]) if x[2] else ""))
            # Determine if we are plotting multiple logs
            num_logs = getattr(self.feature_widget, 'selected_logs', None)
            if num_logs is not None and isinstance(num_logs, list):
                multi_log = len(num_logs) > 1
            else:
                multi_log = False
            # Only show legend entries for types that were actually plotted
            for label, color_name, log_label in sorted_labels:
                legend_label = QLabel()
                legend_label.setFont(self.create_font('label'))
                # Add log name to legend label only if multi_log is True
                if multi_log and log_label:
                    legend_text = f"<span style='color: {color_name}'>●</span> {label} [{log_label}]"
                else:
                    legend_text = f"<span style='color: {color_name}'>●</span> {label}"
                legend_label.setText(legend_text)
                legend_label.setStyleSheet("background: none;")
                legend_layout.addWidget(legend_label)

    def show_tooltip(self, event, chart_view):
        chart = chart_view.chart()
        if not chart:
            return
        # Get axes
        axes_x = chart.axes(Qt.Horizontal)
        axes_y = chart.axes(Qt.Vertical)
        if not axes_x or not axes_y:
            return
        axis_x = axes_x[0]
        axis_y = axes_y[0]
        # Get axis ranges
        x_min = axis_x.min()
        x_max = axis_x.max()
        y_min = axis_y.min()
        y_max = axis_y.max()
        # Get plot area geometry
        plot_area = chart.plotArea()
        left = plot_area.left()
        right = plot_area.right()
        top = plot_area.top()
        bottom = plot_area.bottom()
        # Map pixel to axis value
        if right - left == 0 or bottom - top == 0:
            return
        freq_val = x_min + (x_max - x_min) * (event.position().x() - left) / (right - left)
        
        # Update all charts with the same frequency line
        for full_view, zoom_view in self.chart_views:
            for view in [full_view, zoom_view]:
                view_chart = view.chart()
                if not view_chart:
                    continue
                    
                # Get plot area for this chart
                view_plot_area = view_chart.plotArea()
                view_left = view_plot_area.left()
                view_right = view_plot_area.right()
                view_top = view_plot_area.top()
                view_bottom = view_plot_area.bottom()
                
                # Calculate X position in scene coordinates for this chart
                view_x_scene = view.mapToScene(view.mapFromGlobal(event.globalPos())).x()
                
                # Draw or update vertical line
                scene = view.scene()
                if not hasattr(view, '_track_line'):
                    from PySide6.QtWidgets import QGraphicsLineItem
                    view._track_line = QGraphicsLineItem()
                    view._track_line.setZValue(1000)
                    pen = view._track_line.pen()
                    pen.setColor(QColor(255, 0, 0, 128))
                    pen.setWidth(1)
                    view._track_line.setPen(pen)
                    scene.addItem(view._track_line)
                
                # Show/hide line based on whether we're in the plot area
                if view_left <= view_x_scene <= view_right:
                    view._track_line.setLine(view_x_scene, view_top, view_x_scene, view_bottom)
                    view._track_line.setVisible(True)
                else:
                    view._track_line.setVisible(False)
        
        # Get all series data at the current frequency point
        tooltip_lines = [f"Frequency: {freq_val:.2f} Hz"]
        all_series = chart.series()
        for series in all_series:
            # Find closest point to current frequency
            closest_point = None
            closest_dist = float('inf')
            for i in range(series.count()):
                point = series.at(i)
                dist = abs(point.x() - freq_val)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_point = point
            if closest_point and closest_dist < (x_max - x_min) / 100:  # Only show if reasonably close
                name = series.name()
                value = closest_point.y()
                tooltip_lines.append(f"{name}: {value:.2f} dB")
        tooltip = "\n".join(tooltip_lines)
        if left <= event.position().x() <= right:
            QToolTip.showText(event.globalPos(), tooltip, chart_view)
        else:
            QToolTip.hideText()

class StepResponseWidget(QWidget):
    def __init__(self, feature_widget, parent=None):
        super().__init__(parent)
        self.feature_widget = feature_widget
        self.df = None
        self.expanded_chart = None
        self.original_heights = {}  # Store original heights for restoration
        self.setup_ui()

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font

    def get_detailed_window_stats(self, trace):
        """Get detailed window statistics for debugging and analysis."""
        max_inputs = trace.max_in
        low_mask_sum = int(np.sum(trace.low_mask))
        toolow_mask_sum = int(np.sum(trace.toolow_mask))
        useful_windows = int(np.sum(trace.low_mask * trace.toolow_mask))
        
        return {
            'total_windows': len(max_inputs),
            'useful_windows': useful_windows,
            'low_amplitude_windows': len(max_inputs) - toolow_mask_sum,  # max input <= 20
            'high_amplitude_windows': len(max_inputs) - low_mask_sum,    # max input > 500
            'optimal_windows': useful_windows,                           # 20 < max input <= 500
            'min_max_input': float(np.min(max_inputs)),
            'max_max_input': float(np.max(max_inputs)),
            'mean_max_input': float(np.mean(max_inputs)),
            'sufficient_for_analysis': useful_windows >= 10
        }

    def calculate_sample_stats(self, trace):
        """Calculate sample statistics for the step response analysis."""
        # Calculate sampling frequency
        dt = abs(trace.dt)  # Time step between samples
        sampling_freq = 1.0 / dt if dt > 0 else 1000.0  # Default to 1kHz if dt is invalid
        
        # Calculate samples per window
        flen_samples = trace.flen  # Frame length in samples
        rlen_samples = trace.rlen  # Response length in samples
        
        # Calculate total windows created
        total_time_samples = len(trace.data['time'])
        shift_samples = int(flen_samples / trace.superpos)
        total_windows_created = int(total_time_samples / shift_samples) - trace.superpos if shift_samples > 0 else 0
        
        # Calculate useful windows (those that contribute to the step response)
        # The system uses: low_mask * toolow_mask
        # low_mask: windows with max input <= threshold (500)
        # toolow_mask: windows with max input > 20 (not too low)
        useful_windows = int(np.sum(trace.low_mask * trace.toolow_mask))
        
        # Determine if there are sufficient windows
        sufficient_windows = useful_windows >= 100  # Minimum threshold for reliable analysis (changed from 10 to 100)
        
        # Calculate total samples processed (only useful windows)
        total_samples_processed = useful_windows * flen_samples if useful_windows > 0 else 0
        
        # Calculate final plot resolution
        final_plot_points = rlen_samples * 1000  # 1000 vertical bins from weighted_mode_avr
        
        return {
            'sampling_freq': sampling_freq,
            'flen_samples': flen_samples,
            'rlen_samples': rlen_samples,
            'total_windows_created': total_windows_created,
            'useful_windows': useful_windows,
            'sufficient_windows': sufficient_windows,
            'total_samples_processed': total_samples_processed,
            'final_plot_points': final_plot_points,
            'shift_samples': shift_samples
        }

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        self.charts_container = QWidget()
        charts_layout = QVBoxLayout(self.charts_container)
        charts_layout.setSpacing(10)
        self.chart_views = []
        for axis in ['Roll', 'Pitch', 'Yaw']:
            chart_view = ClickableChartView()
            chart_view.setRenderHint(QPainter.Antialiasing)
            chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            chart_view.setMinimumHeight(200)
            chart = QChart()
            chart.setTitle(f"{axis} Step Response")
            title_font = QFont()
            title_font.setPointSize(10)
            chart.setTitleFont(title_font)
            chart.legend().setVisible(False)  # Hide legend by default
            chart.setMargins(QMargins(10, 10, 10, 10))
            chart_view.setChart(chart)
            # Connect mouse move event for tooltips
            chart_view.setMouseTracking(True)
            chart_view.mouseMoveEvent = lambda event, cv=chart_view: self.show_tooltip(event, cv)
            chart_view.setCursor(Qt.CrossCursor)  # Add crosshair cursor
            # Connect resize event for responsive annotations
            chart_view.resizeEvent = lambda event, cv=chart_view: self.on_chart_resize(event, cv)
            # Connect click event for expand functionality
            chart_view.clicked.connect(lambda cv=chart_view: self.on_chart_clicked(cv))
            self.chart_views.append(chart_view)
            charts_layout.addWidget(chart_view)
        layout.addWidget(self.charts_container)

    def on_chart_clicked(self, clicked_chart_view):
        """Handle chart click to expand or restore."""
        # If the clicked chart is already expanded, restore all
        if self.expanded_chart is clicked_chart_view:
            self.restore_all_charts()
        else:
            # If another chart is expanded, or no chart is expanded
            self.expand_chart(clicked_chart_view)

    def expand_chart(self, chart_view):
        """Expand a single chart and hide others."""
        # Store original heights if not already stored
        if not self.original_heights:
            for chart_view_item in self.chart_views:
                self.original_heights[chart_view_item] = chart_view_item.height()
        
        # Hide all charts except the clicked one
        for chart_view_item in self.chart_views:
            chart_view_item.hide()
        
        # Show only the clicked chart
        chart_view.show()
        
        self.expanded_chart = chart_view

    def restore_all_charts(self):
        """Restore all charts to their original visibility and heights."""
        for chart_view_item in self.chart_views:
            chart_view_item.show()
            # Restore original heights if available
            if chart_view_item in self.original_heights:
                chart_view_item.setMinimumHeight(self.original_heights[chart_view_item])
        
        self.expanded_chart = None

    def on_chart_resize(self, event, chart_view):
        """Handle chart resize events to reposition annotations."""
        # Call the original resize event
        QChartView.resizeEvent(chart_view, event)
        
        # Reposition all annotations for this chart
        if hasattr(chart_view, '_annotation_labels'):
            for i, proxy in enumerate(chart_view._annotation_labels):
                if proxy is not None:
                    y_offset = 20 + (15 * i)
                    proxy.setPos(chart_view.width() - 400, y_offset)

    def update_step_response(self, df, line_width=None, log_name=None, clear_charts=True, log_index=0):
        if df is None or df.empty:
            print('[StepResponseWidget] DataFrame is empty or None.')
            return
        self.df = df
        axes_names = ['roll', 'pitch', 'yaw']
        # Only clear all series and annotation labels if clear_charts is True
        if clear_charts:
            for chart_view in self.chart_views:
                chart = chart_view.chart()
                chart.removeAllSeries()
                if hasattr(chart_view, '_annotation_labels'):
                    for label_proxy in chart_view._annotation_labels:
                        try:
                            if label_proxy is not None:
                                label_proxy.deleteLater()
                        except Exception:
                            pass
                    chart_view._annotation_labels = []
                else:
                    chart_view._annotation_labels = []
        # Use provided log_name or fallback to old method
        if log_name is None:
            log_name = "Log"
            parent = self.parent()
            while parent is not None and not hasattr(parent, 'current_file'):
                parent = parent.parent()
            if parent and hasattr(parent, 'current_file') and parent.current_file:
                log_name = os.path.basename(parent.current_file)
        # Optional: Decimate data for speed if very large
        if len(df) > 20000:
            df = df.iloc[::2].reset_index(drop=True)
        from utils.config import MOTOR_COLORS
        for i, axis_name in enumerate(axes_names):
            chart_view = self.charts_container.layout().itemAt(i).widget() if hasattr(self, 'charts_container') else self.chart_views[i]
            chart = chart_view.chart()
            if clear_charts:
                chart.legend().setVisible(True)  # Show legend
                chart.setTitle(f"{axis_name.capitalize()} Step Response")
                # Remove all existing axes before adding new ones (only if clear_charts)
                for axis in chart.axes():
                    chart.removeAxis(axis)
                # Set up axes
                axis_x = QValueAxis()
                axis_x.setTitleText('Time (ms)')
                axis_x.setRange(0, 500)
                axis_x.setLabelFormat('%d')
                axis_x.setTickCount(6)
                axis_x.setTitleVisible(True)
                axis_x.setLabelsVisible(True)
                axis_x.setGridLineVisible(True)
                axis_x.setLinePenColor(Qt.black)
                axis_x.setLabelsColor(Qt.black)
                axis_x.setTitleFont(self.create_font('label'))
                axis_x.setLabelsFont(self.create_font('label'))
                # Use QCategoryAxis for Y axis to guarantee ticks at 0, 0.25, ..., 1.75
                axis_y = QCategoryAxis()
                axis_y.setTitleText('Response')
                axis_y.setRange(0., 1.75)
                axis_y.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
                for v in [0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75]:
                    axis_y.append(f'{v:.2f}', v)
                axis_y.setTitleVisible(True)
                axis_y.setLabelsVisible(True)
                axis_y.setGridLineVisible(True)
                axis_y.setLinePenColor(Qt.black)
                axis_y.setLabelsColor(Qt.black)
                axis_y.setTitleFont(self.create_font('label'))
                axis_y.setLabelsFont(self.create_font('label'))
                chart.addAxis(axis_x, Qt.AlignBottom)
                chart.addAxis(axis_y, Qt.AlignLeft)
                chart_view._step_axis_x = axis_x
                chart_view._step_axis_y = axis_y
            else:
                axis_x = getattr(chart_view, '_step_axis_x', None)
                axis_y = getattr(chart_view, '_step_axis_y', None)
                if axis_x is None or axis_y is None:
                    continue

            # Find columns
            gyro_col = f'gyroADC[{i}] (deg/s)'
            p_err_col = f'axisP[{i}]'
            throttle_col = 'rcCommand[3]'
            pid_val = None
            ff_val = None
            for pid_key in [f'{axis_name}pid', f'{axis_name.upper()}PID', f'{axis_name[0]}pid']:
                pid_col = [col for col in df.columns if pid_key in col.lower()]
                if pid_col:
                    pid_val = df[pid_col[0]].iloc[0]
                    break

            # Get feed forward value from FF column
            ff_col = f'{axis_name}FF'
            if ff_col in df.columns:
                ff_val = df[ff_col].iloc[0]
                if self.feature_widget.debug('DEBUG'):
                    print(f"[DEBUG] Feed forward value for {axis_name} from {ff_col}: {ff_val}")
            else:
                if self.feature_widget.debug('DEBUG'):
                    print(f"[DEBUG] Feed forward column {ff_col} not found in DataFrame")
                ff_val = 0.0

            # Get d_min value from DMin column
            dmin_col = f'{axis_name}DMin'
            if dmin_col in df.columns:
                dmin_val = df[dmin_col].iloc[0]
                if self.feature_widget.debug('DEBUG'):
                    print(f"[DEBUG] d_min value for {axis_name} from {dmin_col}: {dmin_val}")
            else:
                if self.feature_widget.debug('DEBUG'):
                    print(f"[DEBUG] d_min column {dmin_col} not found in DataFrame")
                dmin_val = 0.0

            if gyro_col in df.columns and p_err_col in df.columns and throttle_col in df.columns:
                time = df['time'].values
                gyro = df[gyro_col].values
                p_err = df[p_err_col].values
                throttle = df[throttle_col].values
                try:
                    pid_p = float(str(pid_val).split(',')[0]) if pid_val is not None and pid_val != 'N/A' else 1.0
                except Exception:
                    pid_p = 1.0
                axis_data = {
                    'name': axis_name,
                    'time': time,
                    'p_err': p_err,
                    'gyro': gyro,
                    'P': pid_p,
                    'throttle': throttle
                }
                trace = StepTrace(axis_data)
                t = trace.time_resp
                mean, std, _ = trace.resp_low

                # Calculate sample statistics
                sample_stats = self.calculate_sample_stats(trace)

                # Reference line at y=1.0 (add first, so it's behind the data)
                if clear_charts and len(t) > 1:
                    ref_line = QLineSeries()
                    ref_line.append(0, 1.0)
                    ref_line.append(500, 1.0)
                    ref_pen = QPen(Qt.black)
                    ref_pen.setWidthF(1.7)
                    ref_line.setPen(ref_pen)
                    chart.addSeries(ref_line)
                    # Prevent double-attaching axes
                    if axis_x not in ref_line.attachedAxes():
                        ref_line.attachAxis(axis_x)
                    if axis_y not in ref_line.attachedAxes():
                        ref_line.attachAxis(axis_y)
                    for marker in chart.legend().markers(ref_line):
                        marker.setVisible(False)

                # Step response mean line (add after, so it's on top)
                color = QColor(*MOTOR_COLORS[log_index % len(MOTOR_COLORS)])
                series = QLineSeries()
                t_ms = [float(x) * 1000 for x in t]
                t_ms = [x - t_ms[0] for x in t_ms]
                mean = list(mean)
                for x, y in zip(t_ms, mean):
                    series.append(x, y)
                series.setName(f"{log_name}")
                pen = series.pen()
                pen.setColor(color)
                pen.setWidthF(line_width if line_width is not None else 1.5)
                series.setPen(pen)
                chart.addSeries(series)
                # Prevent double-attaching axes
                if axis_x not in series.attachedAxes():
                    series.attachAxis(axis_x)
                if axis_y not in series.attachedAxes():
                    series.attachAxis(axis_y)
                # Legend: PID values
                if pid_val and pid_val != 'N/A':
                    try:
                        p, i, d = map(float, str(pid_val).split(','))
                        ff = float(ff_val) if ff_val is not None else 0.0
                        dmin = float(dmin_val) if dmin_val is not None else 0.0
                        pid_text = f"<b>P:</b> {p:.0f}; <b>I:</b> {i:.0f}; <b>D:</b> {dmin:.0f}; <b>Dmax:</b> {d:.0f}; <b>FF:</b> {ff:.0f};"
                    except:
                        pid_text = f"PID: {pid_val}"
                else:
                    pid_text = "PID: N/A"
                # Set legend text with log name and PID values
                chart.legend().markers(series)[0].setLabel(f"{log_name}\n{pid_text}")
                # Configure legend
                chart.legend().setVisible(True)  # Always show legend
                chart.legend().setLabelColor(Qt.black)
                legend_font = QFont("fccTYPO", 9)
                legend_font.setBold(False)  # Ensure normal weight
                chart.legend().setFont(legend_font)
                # Set marker to circle
                for marker in chart.legend().markers(series):
                    marker.setShape(QLegend.MarkerShapeCircle)
                chart.update()
                # Compute max Y and time to reach 0.5 (in ms)
                max_y = float(np.max(mean))
                max_idx = int(np.argmax(mean))
                max_t = float(t_ms[max_idx]) if max_idx < len(t_ms) else 0.0
                t_05 = next((float(ti) for ti, yi in zip(t_ms, mean) if yi >= 0.5), None)
                
                # Prepare annotation text with sample statistics
                if sample_stats['sufficient_windows']:
                    sample_info = f"<b>Useful windows:</b> {sample_stats['useful_windows']} | <b>Samples:</b> {sample_stats['total_samples_processed']}"
                else:
                    sample_info = f"<b>Insufficient for reliable analysis</b>"
                
                annotation = f"<b>Max:</b> {max_y:.2f} at t={max_t:.0f}ms | <b>Response:</b> {t_05:.0f}ms" if t_05 is not None else f"<b>Max:</b> {max_y:.2f} at t={max_t:.0f}ms | <b>Response:</b> N/A"
                full_annotation = f"{annotation} | {sample_info}"
                
                label = QLabel(full_annotation)
                label.setStyleSheet(f"color: {color.name()}; font-size: 9px; font-family: fccTYPO; padding: 1px; background: transparent;")
                label.setAttribute(Qt.WA_TranslucentBackground)
                label.setAlignment(Qt.AlignRight | Qt.AlignTop)
                proxy = chart_view.scene().addWidget(label)
                proxy.setZValue(100)
                # Position annotations vertically for each log with smaller spacing
                y_offset = 20 + (15 * log_index)  # Reduced spacing
                proxy.setPos(chart_view.width() - 400, y_offset)  # Moved more to the left
                if not hasattr(chart_view, '_annotation_labels'):
                    chart_view._annotation_labels = []
                chart_view._annotation_labels.append(proxy)

    def show_tooltip(self, event, chart_view):
        chart = chart_view.chart()
        if not chart:
            return
        # Get axes
        axes_x = chart.axes(Qt.Horizontal)
        axes_y = chart.axes(Qt.Vertical)
        if not axes_x or not axes_y:
            return
        axis_x = axes_x[0]
        axis_y = axes_y[0]
        # Get axis ranges
        x_min = axis_x.min()
        x_max = axis_x.max()
        y_min = axis_y.min()
        y_max = axis_y.max()
        # Get plot area geometry
        plot_area = chart.plotArea()
        left = plot_area.left()
        right = plot_area.right()
        top = plot_area.top()
        bottom = plot_area.bottom()
        # Map pixel to axis value
        if right - left == 0 or bottom - top == 0:
            return
        t_val = x_min + (x_max - x_min) * (event.position().x() - left) / (right - left)
        
        # Update all charts with the same time line
        for view in self.chart_views:
            view_chart = view.chart()
            if not view_chart:
                continue
                
            # Get plot area for this chart
            view_plot_area = view_chart.plotArea()
            view_left = view_plot_area.left()
            view_right = view_plot_area.right()
            view_top = view_plot_area.top()
            view_bottom = view_plot_area.bottom()
            
            # Calculate X position in scene coordinates for this chart
            view_x_scene = view.mapToScene(view.mapFromGlobal(event.globalPos())).x()
            
            # Draw or update vertical line
            scene = view.scene()
            if not hasattr(view, '_track_line'):
                from PySide6.QtWidgets import QGraphicsLineItem
                view._track_line = QGraphicsLineItem()
                view._track_line.setZValue(1000)
                pen = view._track_line.pen()
                pen.setColor(QColor(255, 0, 0, 128))
                pen.setWidth(1)
                view._track_line.setPen(pen)
                scene.addItem(view._track_line)
            
            # Show/hide line based on whether we're in the plot area
            if view_left <= view_x_scene <= view_right:
                view._track_line.setLine(view_x_scene, view_top, view_x_scene, view_bottom)
                view._track_line.setVisible(True)
            else:
                view._track_line.setVisible(False)
        
        # Get all series data at the current time point
        tooltip_lines = [f"Time: {t_val:.1f} ms"]
        all_series = chart.series()
        for series in all_series:
            # Find closest point to current time
            closest_point = None
            closest_dist = float('inf')
            for i in range(series.count()):
                point = series.at(i)
                dist = abs(point.x() - t_val)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_point = point
            if closest_point and closest_dist < (x_max - x_min) / 100:  # Only show if reasonably close
                name = series.name()
                value = closest_point.y()
                tooltip_lines.append(f"{name}: {value:.2f}")
        tooltip = "\n".join(tooltip_lines)
        if left <= event.position().x() <= right:
            QToolTip.showText(event.globalPos(), tooltip, chart_view)
        else:
            QToolTip.hideText()

    def clear_all_charts_and_annotations(self):
        for chart_view in self.chart_views:
            chart = chart_view.chart()
            chart.removeAllSeries()
            if hasattr(chart_view, '_annotation_labels'):
                for label_proxy in chart_view._annotation_labels:
                    try:
                        if label_proxy is not None:
                            label_proxy.deleteLater()
                    except Exception:
                        pass
                chart_view._annotation_labels = []
            else:
                chart_view._annotation_labels = []

    def clear_all_legends(self):
        """Clear all legends from the step response charts"""
        for chart_view in self.chart_views:
            if chart_view.chart():
                chart_view.chart().legend().setVisible(False)
                chart_view.chart().update()

class FrequencyAnalyzerWidget(QWidget):
    def __init__(self, feature_widget, parent=None):
        super().__init__(parent)
        self.feature_widget = feature_widget
        self.df = None
        self.canvas = None
        self.gain = 5.0  # Default gain value
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Add gain control slider
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(10, 0, 10, 0)  # Add horizontal margins
        gain_label = QLabel("Gain:")
        gain_label.setFont(self.create_font('label'))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setMinimum(1)  # Min gain 1x
        self.gain_slider.setMaximum(50)
        self.gain_slider.setValue(5)
        self.gain_slider.setTickInterval(5)
        self.gain_slider.setTickPosition(QSlider.TicksBelow)
        self.gain_value_label = QLabel(f"{self.gain}x")
        self.gain_value_label.setFont(self.create_font('label'))
        
        self.gain_slider.valueChanged.connect(self.on_gain_changed)
        
        control_layout.addWidget(gain_label)
        control_layout.addWidget(self.gain_slider)
        control_layout.addWidget(self.gain_value_label)
        
        layout.addLayout(control_layout)
        
        self.plot_container = QWidget()
        self.plot_layout = QGridLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_container)
        layout.addStretch(1)  # Push everything up so gain slider stays at the top

    def on_gain_changed(self, value):
        self.gain = value
        self.gain_value_label.setText(f"{self.gain}x")
        # No longer automatically update plots when gain changes
        # User needs to click "Show Plot" button to see the changes

    def clear_all_plots(self):
        # Remove all canvases from the layout
        if hasattr(self, 'canvas_list'):
            for canvas in self.canvas_list:
                self.plot_layout.removeWidget(canvas)
                canvas.setParent(None)
                canvas.deleteLater()
            self.canvas_list = []
        else:
            self.canvas_list = []
        if self.canvas is not None:
            self.plot_layout.removeWidget(self.canvas)
            self.canvas.setParent(None)
            self.canvas.deleteLater()
            self.canvas = None

    def update_frequency_plots(self, df, max_freq=1000):
        if df is not None:
            self.df = df
        if self.df is None or self.df.empty:
            if self.feature_widget.debug('DEBUG'):
                print("[FrequencyAnalyzer] DataFrame is empty or None.")
            return
        # Debug: print columns and sample data
        if self.feature_widget.debug('DEBUG'):
            print("[FrequencyAnalyzer] DataFrame columns:", self.df.columns.tolist())
            print("[FrequencyAnalyzer] DataFrame head:")
            print(self.df.head())
        # Check for key columns
        has_gyro = any('gyro' in col.lower() for col in self.df.columns)
        has_debug = any('debug' in col.lower() for col in self.df.columns)
        has_throttle = any('throttle' in col.lower() or 'rccommand[3]' in col.lower() for col in self.df.columns)
        if self.feature_widget.debug('DEBUG'):
            print(f"[FrequencyAnalyzer] Has gyro: {has_gyro}, debug: {has_debug}, throttle: {has_throttle}")
            print(f"[FrequencyAnalyzer] Using gain: {self.gain}x, max_freq: {max_freq}Hz")
        # Try to print gyro, debug, and throttle columns
        if self.feature_widget.debug('DEBUG'):
            for col in self.df.columns:
                if 'gyro' in col.lower() or 'debug' in col.lower() or 'throttle' in col.lower() or 'rccommand[3]' in col.lower():
                    values = self.df[col].head().to_list()
                    if all(v == 0 for v in values):
                        print(f"[FrequencyAnalyzer] WARNING: {col} has all zeros in first rows")
                    else:
                        print(f"[FrequencyAnalyzer] Sample data for {col}:", values)
        self.clear_all_plots()
        try:
            figures = generate_individual_noise_figures(self.df, gain=self.gain, max_freq=max_freq)
            self.canvas_list = []
            # Arrange in 3x3 grid: rows=roll/pitch/yaw, cols=gyro/debug
            for i, fig in enumerate(figures):
                canvas = FigureCanvas(fig)
                # Set cursor to crosshair for better precision
                canvas.setCursor(Qt.CrossCursor)
                row = i // 3
                if i % 3 == 0:
                    col = 0  # Gyro
                elif i % 3 == 1:
                    col = 1  # Debug
                else:
                    col = 2  # D-term
                self.plot_layout.addWidget(canvas, row, col)
                self.canvas_list.append(canvas)
                # Add tooltip support
                def make_motion_event_handler(canvas, fig):
                    def on_motion(event):
                        # Get figure dimensions
                        fig_height = fig.get_figheight() * fig.dpi
                        # If position is near the bottom of the figure (where colorbar is), hide tooltip
                        # Colorbar is in the bottom ~5% of the figure
                        if event.y < fig_height * 0.05:
                            QToolTip.hideText()
                            return
                        # Hide tooltip if over colorbar or if no data coordinates
                        if (event.inaxes is None or
                            event.xdata is None or event.ydata is None or
                            (hasattr(event.inaxes, 'get_label') and event.inaxes.get_label() == 'colorbar')):
                            QToolTip.hideText()
                            return
                        x, y = event.xdata, event.ydata
                        tooltip = f"Throttle: {x:.1f}%\nFrequency: {y:.1f} Hz"
                        QToolTip.showText(canvas.mapToGlobal(event.guiEvent.pos()), tooltip, canvas)
                    return on_motion
                # Add statistics annotation to the plot
                for ax in fig.axes:
                    # Skip if this is a colorbar axis
                    if ax.get_label() == 'colorbar':
                        continue
                    for artist in ax.get_children():
                        if hasattr(artist, 'get_array') and hasattr(artist, 'get_facecolor'):  # QuadMesh
                            arr = artist.get_array()
                            if arr is not None and hasattr(arr, 'shape'):
                                # Get frequency values from the plot
                                y_lims = ax.get_ylim()
                                y_data = np.linspace(y_lims[0], y_lims[1], arr.shape[0])
                                # Create mask for frequencies above 15Hz
                                freq_mask = y_data >= 15
                                # Calculate statistics only for frequencies above 15Hz
                                # Remove any padding/background values (1e-6)
                                noise_values = arr[freq_mask][arr[freq_mask] > 1e-6]
                                if len(noise_values) > 0:
                                    mean_val = np.mean(noise_values)
                                    peak_val = np.max(noise_values)
                                    # Add text annotation
                                    ax.text(0.98, 0.98, 
                                           f"Mean: {mean_val:.2f}\nPeak: {peak_val:.2f}",
                                           transform=ax.transAxes,
                                           verticalalignment='top',
                                           horizontalalignment='right',
                                           color='white',
                                           fontsize=9)
                canvas.mpl_connect('motion_notify_event', make_motion_event_handler(canvas, fig))
            if self.feature_widget.debug('DEBUG'):
                print(f"[FrequencyAnalyzer] Individual plots generated successfully in 3x3 grid (max freq: {max_freq}Hz)")
        except Exception as e:
            import traceback
            print(f"[FrequencyAnalyzer] Error plotting: {e}")
            print(traceback.format_exc())

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font 

class PlotExportWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.export_path = "/Users/jakubespandr/Desktop"
        self.previous_tab_index = 0  # Default to Time Domain
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create info label
        info_label = QLabel("This tab exports the previously viewed plots to selected directory.")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setFont(self.create_font('title'))
        layout.addWidget(info_label)
        
        # Create status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFont(self.create_font('label'))
        layout.addWidget(self.status_label)
        
        # Create return button
        self.return_button = QPushButton("Return to Previous Tab")
        self.return_button.setFont(self.create_font('button'))
        self.return_button.clicked.connect(self.return_to_previous_tab)
        layout.addWidget(self.return_button)
        
        # Add stretch to push everything to the top
        layout.addStretch(1)
    
    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font
    
    def set_previous_tab(self, tab_index):
        """Set the previous tab index to return to"""
        self.previous_tab_index = tab_index
    
    def return_to_previous_tab(self):
        """Return to the previous tab"""
        parent = self.parent()
        while parent is not None and not hasattr(parent, 'tab_widget'):
            parent = parent.parent()
        
        if parent and hasattr(parent, 'tab_widget'):
            parent.tab_widget.setCurrentIndex(self.previous_tab_index)
    
    def export_plots(self):
        """Export plots based on the previous tab"""
        parent = self.parent()
        while parent is not None and not hasattr(parent, 'tab_widget'):
            parent = parent.parent()
        
        if not parent:
            self.status_label.setText("Error: Could not find parent widget")
            return
        
        try:
            if self.previous_tab_index == 0:  # Time Domain
                self._export_time_domain_plots(parent)
            elif self.previous_tab_index == 1:  # Frequency Domain
                self._export_spectral_plots(parent)
            elif self.previous_tab_index == 2:  # Step Response
                self._export_step_response_plots(parent)
            elif self.previous_tab_index == 3:  # Noise Analysis
                self._export_frequency_analyzer_plots(parent)
            elif self.previous_tab_index == 4:  # Frequency Evolution
                self._export_spectrogram_plots(parent)
            else:
                self.status_label.setText("Invalid tab index for export")
        except Exception as e:
            self.status_label.setText(f"Error during export: {str(e)}")
    
    def _get_export_dir(self, parent):
        # Try to get export_dir from settings.json in config folder
        try:
            import json
            import os
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            config_dir = os.path.join(app_dir, "config")
            settings_path = os.path.join(config_dir, "settings.json")
            export_dir = None
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    export_dir = settings.get('export_dir', None)
            # Use export_dir from settings only if it is set and non-empty
            if export_dir and isinstance(export_dir, str) and export_dir.strip():
                os.makedirs(export_dir, exist_ok=True)
                return export_dir
        except Exception as e:
            print(f"[PlotExportWidget] Failed to load export_dir from settings: {e}")
        # Fallback: use <project_root>/export
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_export_dir = os.path.join(project_dir, 'export')
        os.makedirs(default_export_dir, exist_ok=True)
        return default_export_dir

    def _get_author_name(self, parent):
        if hasattr(parent, 'feature_widget') and hasattr(parent.feature_widget, 'author_name'):
            return parent.feature_widget.author_name
        return ""
    
    def _get_drone_name(self, parent):
        if hasattr(parent, 'feature_widget') and hasattr(parent.feature_widget, 'drone_name'):
            return parent.feature_widget.drone_name
        return ""
    
    def _use_drone_in_filename(self, parent):
        if hasattr(parent, 'feature_widget') and hasattr(parent.feature_widget, 'use_drone_in_filename'):
            return parent.feature_widget.use_drone_in_filename
        return False

    def _export_time_domain_plots(self, parent):
        try:
            chart_views = parent.chart_manager.chart_views
            if not chart_views:
                self.status_label.setText("No plots to export")
                return
            export_dir = self._get_export_dir(parent)
            import os
            os.makedirs(export_dir, exist_ok=True)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = parent.feature_widget.selected_logs[0] if hasattr(parent.feature_widget, 'selected_logs') and parent.feature_widget.selected_logs else "LogFile"
            log_name = os.path.splitext(log_name)[0]  # Remove .bbl extension
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            author_name = self._get_author_name(parent)
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect
            scale_factor = 3.5
            header_height = int(100 * scale_factor)
            legend_height = int(60 * scale_factor)
            width = int(chart_views[0].width() * scale_factor)
            chart_height = int(sum(view.height() for view in chart_views) * scale_factor)
            total_height = chart_height + header_height + legend_height
            combined_image = QImage(width, total_height, QImage.Format_ARGB32)
            combined_image.fill(Qt.white)
            painter = QPainter(combined_image)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                header_font = QFont("fccTYPO", int(32 * scale_factor / 3.0))
                header_font.setBold(True)
                painter.setFont(header_font)
                painter.setPen(QColor(0, 0, 0))
                header_text = f"Log: {log_name} | Time Domain | Date: {current_date}"
                if author_name:
                    header_text += f" | Author: {author_name}"
                if drone_name:
                    header_text += f" | Drone: {drone_name}"
                header_rect = QRect(0, 0, width, header_height)
                painter.fillRect(header_rect, QColor(230, 230, 240))
                painter.drawText(header_rect, Qt.AlignCenter | Qt.AlignTop, header_text)
                settings_font = QFont("fccTYPO", int(28 * scale_factor / 3.0))
                settings_font.setBold(True)
                painter.setFont(settings_font)
                # Get zoom and line width info
                zoom_info = ""
                if hasattr(parent, 'control_widget') and hasattr(parent.control_widget, 'zoom_ratio_label'):
                    zoom_info = f"Zoom: {parent.control_widget.zoom_ratio_label.text()}"
                line_width = getattr(parent.feature_widget, 'current_line_width', 1.0)
                settings_text = f"Line Width: {line_width} | {zoom_info}"
                settings_rect = QRect(0, int(header_height/2), width, int(header_height/2))
                painter.drawText(settings_rect, Qt.AlignCenter | Qt.AlignTop, settings_text)
                # Draw legend preview
                legend_layout = getattr(parent.feature_widget, 'legend_layout', None)
                if legend_layout is not None and legend_layout.count() > 0:
                    legend_font = QFont("fccTYPO", int(28 * scale_factor / 3.0))
                    legend_font.setBold(False)
                    painter.setFont(legend_font)
                    y = header_height + int(legend_height * 0.3)
                    x = 40
                    dot_radius = int(18 * scale_factor / 3.0)
                    spacing = int(60 * scale_factor / 3.0)
                    for i in range(legend_layout.count()):
                        item = legend_layout.itemAt(i)
                        widget = item.widget()
                        if widget:
                            from PySide6.QtWidgets import QLabel
                            if isinstance(widget, QLabel):
                                import re
                                html = widget.text()
                                match = re.search(r"color: ([^']+).*?>(.*?)<.*?>(.*)", html)
                                if match:
                                    color = match.group(1)
                                    label = match.group(3)
                                else:
                                    color = "#000000"
                                    label = widget.text()
                                if label.strip() == "Motors:":
                                    # Just draw the label, no dot
                                    painter.setPen(QColor(0, 0, 0))
                                    painter.drawText(x, y + dot_radius, label)
                                    x += painter.fontMetrics().horizontalAdvance(label) + spacing // 2
                                else:
                                    painter.setPen(QColor(color))
                                    painter.setBrush(QColor(color))
                                    painter.drawEllipse(x, y, dot_radius, dot_radius)
                                    painter.setPen(QColor(0, 0, 0))
                                    painter.drawText(x + dot_radius + 12, y + dot_radius, label)
                                    x += spacing + painter.fontMetrics().horizontalAdvance(label)
                            else:
                                # Handle motor row widget
                                # Find all QLabel children (dots and numbers)
                                child_labels = widget.findChildren(QLabel)
                                cx = x
                                for child in child_labels:
                                    text = child.text()
                                    style = child.styleSheet()
                                    if "color:" in style:
                                        # This is a dot
                                        color = style.split("color:")[1].split(";")[0].strip()
                                        painter.setPen(QColor(color))
                                        painter.setBrush(QColor(color))
                                        painter.drawEllipse(cx, y, dot_radius, dot_radius)
                                        cx += dot_radius + 4
                                    else:
                                        # This is a number
                                        painter.setPen(QColor(0, 0, 0))
                                        painter.drawText(cx, y + dot_radius, text)
                                        cx += painter.fontMetrics().horizontalAdvance(text) + spacing // 2
                                x = cx + spacing // 2
                painter.setPen(QColor(180, 180, 180))
                current_y = header_height + legend_height
                for chart_view in chart_views:
                    original_size = chart_view.size()
                    scaled_size = QSize(int(original_size.width() * scale_factor), int(original_size.height() * scale_factor))
                    pixmap = QPixmap(scaled_size)
                    pixmap.fill(Qt.white)
                    temp_painter = QPainter(pixmap)
                    temp_painter.setRenderHint(QPainter.Antialiasing, True)
                    chart_view.render(temp_painter, target=pixmap.rect(), source=chart_view.rect())
                    temp_painter.end()
                    painter.drawPixmap(0, current_y, pixmap)
                    current_y += pixmap.height()
            finally:
                painter.end()
            if use_drone and drone_name:
                filename = f"{drone_name_filename}-{log_name}-TimeDomain-{timestamp}.jpg"
            else:
                filename = f"{log_name}-TimeDomain-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            combined_image.save(filepath, "JPG", quality=100)
            self.status_label.setText(f"Exported stacked Time Domain plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting time domain plots: {str(e)}")

    # Repeat similar stacking logic for _export_spectral_plots and _export_step_response_plots
    
    def _export_spectral_plots(self, parent):
        try:
            chart_views = parent.spectral_widget.chart_views
            if not chart_views:
                self.status_label.setText("No spectral plots to export")
                return
            export_dir = self._get_export_dir(parent)
            import os
            os.makedirs(export_dir, exist_ok=True)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = parent.feature_widget.selected_logs[0] if hasattr(parent.feature_widget, 'selected_logs') and parent.feature_widget.selected_logs else "LogFile"
            log_name = os.path.splitext(log_name)[0]  # Remove .bbl extension
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            author_name = self._get_author_name(parent)
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect
            scale_factor = 3.5
            header_height = int(100 * scale_factor)
            legend_height = int(60 * scale_factor)
            nrows = 3
            # Calculate left and right column widths separately
            left_col_width = int(max(full.width() for full, _ in chart_views) * scale_factor)
            right_col_width = int(max(zoom.width() for _, zoom in chart_views) * scale_factor)
            cell_height = int(max(max(full.height(), zoom.height()) for full, zoom in chart_views) * scale_factor)
            width = left_col_width + right_col_width
            chart_height = cell_height * nrows
            total_height = header_height + legend_height + chart_height
            combined_image = QImage(width, total_height, QImage.Format_ARGB32)
            combined_image.fill(Qt.white)
            painter = QPainter(combined_image)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                header_font = QFont("fccTYPO", int(32 * scale_factor / 3.0))
                header_font.setBold(True)
                painter.setFont(header_font)
                painter.setPen(QColor(0, 0, 0))
                header_text = f"Log: {log_name} | Frequency Domain | Date: {current_date}"
                if author_name:
                    header_text += f" | Author: {author_name}"
                if drone_name:
                    header_text += f" | Drone: {drone_name}"
                header_rect = QRect(0, 0, width, header_height)
                painter.fillRect(header_rect, QColor(230, 230, 240))
                painter.drawText(header_rect, Qt.AlignCenter | Qt.AlignTop, header_text)
                settings_font = QFont("fccTYPO", int(28 * scale_factor / 3.0))
                settings_font.setBold(True)
                painter.setFont(settings_font)
                settings_text = f"Smoothing: {parent.spectral_widget.window_sizes[parent.spectral_widget.window_size_slider.value()]}"
                settings_rect = QRect(0, int(header_height/2), width, int(header_height/2))
                painter.drawText(settings_rect, Qt.AlignCenter | Qt.AlignTop, settings_text)
                # Draw legend preview (reuse logic from time domain if desired)
                legend_layout = getattr(parent.feature_widget, 'legend_layout', None)
                if legend_layout is not None and legend_layout.count() > 0:
                    legend_font = QFont("fccTYPO", int(28 * scale_factor / 3.0))
                    legend_font.setBold(False)
                    painter.setFont(legend_font)
                    y = header_height + int(legend_height * 0.3)
                    x = 40
                    dot_radius = int(18 * scale_factor / 3.0)
                    spacing = int(60 * scale_factor / 3.0)
                    for i in range(legend_layout.count()):
                        item = legend_layout.itemAt(i)
                        widget = item.widget()
                        if widget:
                            from PySide6.QtWidgets import QLabel
                            if isinstance(widget, QLabel):
                                import re
                                html = widget.text()
                                match = re.search(r"color: ([^']+).*?>(.*?)<.*?>(.*)", html)
                                if match:
                                    color = match.group(1)
                                    label = match.group(3)
                                else:
                                    color = "#000000"
                                    label = widget.text()
                                if label.strip() == "Motors:":
                                    painter.setPen(QColor(0, 0, 0))
                                    painter.drawText(x, y + dot_radius, label)
                                    x += painter.fontMetrics().horizontalAdvance(label) + spacing // 2
                                else:
                                    painter.setPen(QColor(color))
                                    painter.setBrush(QColor(color))
                                    painter.drawEllipse(x, y, dot_radius, dot_radius)
                                    painter.setPen(QColor(0, 0, 0))
                                    painter.drawText(x + dot_radius + 12, y + dot_radius, label)
                                    x += spacing + painter.fontMetrics().horizontalAdvance(label)
                            else:
                                child_labels = widget.findChildren(QLabel)
                                cx = x
                                for child in child_labels:
                                    text = child.text()
                                    style = child.styleSheet()
                                    if "color:" in style:
                                        color = style.split("color:")[1].split(";")[0].strip()
                                        painter.setPen(QColor(color))
                                        painter.setBrush(QColor(color))
                                        painter.drawEllipse(cx, y, dot_radius, dot_radius)
                                        cx += dot_radius + 4
                                    else:
                                        painter.setPen(QColor(0, 0, 0))
                                        painter.drawText(cx, y + dot_radius, text)
                                        cx += painter.fontMetrics().horizontalAdvance(text) + spacing // 2
                                x = cx + spacing // 2
                painter.setPen(QColor(180, 180, 180))
                # Draw charts in 3x2 grid with correct column widths
                for row, (chart_view_full, chart_view_zoom) in enumerate(chart_views):
                    # Left column (full)
                    original_size_full = chart_view_full.size()
                    scaled_size_full = QSize(int(original_size_full.width() * scale_factor), int(original_size_full.height() * scale_factor))
                    pixmap_full = QPixmap(scaled_size_full)
                    pixmap_full.fill(Qt.white)
                    temp_painter = QPainter(pixmap_full)
                    temp_painter.setRenderHint(QPainter.Antialiasing, True)
                    chart_view_full.render(temp_painter, target=pixmap_full.rect(), source=chart_view_full.rect())
                    temp_painter.end()
                    x_offset_full = 0
                    y_offset = header_height + legend_height + row * cell_height
                    painter.drawPixmap(x_offset_full, y_offset, pixmap_full)
                    # Right column (zoomed)
                    original_size_zoom = chart_view_zoom.size()
                    scaled_size_zoom = QSize(int(original_size_zoom.width() * scale_factor), int(original_size_zoom.height() * scale_factor))
                    pixmap_zoom = QPixmap(scaled_size_zoom)
                    pixmap_zoom.fill(Qt.white)
                    temp_painter = QPainter(pixmap_zoom)
                    temp_painter.setRenderHint(QPainter.Antialiasing, True)
                    chart_view_zoom.render(temp_painter, target=pixmap_zoom.rect(), source=chart_view_zoom.rect())
                    temp_painter.end()
                    x_offset_zoom = left_col_width
                    painter.drawPixmap(x_offset_zoom, y_offset, pixmap_zoom)
            finally:
                painter.end()
            if use_drone and drone_name:
                filename = f"{drone_name_filename}-{log_name}-FrequencyDomain-{timestamp}.jpg"
            else:
                filename = f"{log_name}-FrequencyDomain-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            combined_image.save(filepath, "JPG", quality=100)
            self.status_label.setText(f"Exported stacked Spectral plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting spectral plots: {str(e)}")
    
    def _export_step_response_plots(self, parent):
        try:
            chart_views = parent.step_response_widget.chart_views
            if not chart_views:
                self.status_label.setText("No step response plots to export")
                return
            export_dir = self._get_export_dir(parent)
            import os
            os.makedirs(export_dir, exist_ok=True)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = parent.feature_widget.selected_logs[0] if hasattr(parent.feature_widget, 'selected_logs') and parent.feature_widget.selected_logs else "LogFile"
            log_name = os.path.splitext(log_name)[0]  # Remove .bbl extension
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            author_name = self._get_author_name(parent)
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect
            scale_factor = 3.5
            header_height = int(100 * scale_factor)
            width = int(chart_views[0].width() * scale_factor)
            chart_height = int(sum(view.height() for view in chart_views) * scale_factor)
            total_height = chart_height + header_height
            combined_image = QImage(width, total_height, QImage.Format_ARGB32)
            combined_image.fill(Qt.white)
            painter = QPainter(combined_image)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                header_font = QFont("fccTYPO", int(32 * scale_factor / 3.0))
                header_font.setBold(True)
                painter.setFont(header_font)
                painter.setPen(QColor(0, 0, 0))
                header_text = f"Log: {log_name} | Step Response | Date: {current_date}"
                if author_name:
                    header_text += f" | Author: {author_name}"
                if drone_name:
                    header_text += f" | Drone: {drone_name}"
                header_rect = QRect(0, 0, width, header_height)
                painter.fillRect(header_rect, QColor(230, 230, 240))
                painter.drawText(header_rect, Qt.AlignCenter | Qt.AlignTop, header_text)
                painter.setPen(QColor(180, 180, 180))
                current_y = header_height
                for chart_view in chart_views:
                    original_size = chart_view.size()
                    scaled_size = QSize(int(original_size.width() * scale_factor), int(original_size.height() * scale_factor))
                    pixmap = QPixmap(scaled_size)
                    pixmap.fill(Qt.white)
                    temp_painter = QPainter(pixmap)
                    temp_painter.setRenderHint(QPainter.Antialiasing, True)
                    chart_view.render(temp_painter, target=pixmap.rect(), source=chart_view.rect())
                    temp_painter.end()
                    painter.drawPixmap(0, current_y, pixmap)
                    current_y += pixmap.height()
            finally:
                painter.end()
            if use_drone and drone_name:
                filename = f"{drone_name_filename}-{log_name}-StepResponse-{timestamp}.jpg"
            else:
                filename = f"{log_name}-StepResponse-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            combined_image.save(filepath, "JPG", quality=100)
            self.status_label.setText(f"Exported stacked Step Response plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting step response plots: {str(e)}")
    
    def _export_frequency_analyzer_plots(self, parent):
        try:
            freq_widget = parent.frequency_analyzer_widget
            if not hasattr(freq_widget, 'canvas_list') or not freq_widget.canvas_list:
                self.status_label.setText("No Noise Analysis plots to export.")
                return
            export_dir = self._get_export_dir(parent)
            import os
            os.makedirs(export_dir, exist_ok=True)
            import datetime
            import tempfile
            from PySide6.QtGui import QImage, QPainter, QFont, QColor, QPixmap
            from PySide6.QtCore import Qt, QRect
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = parent.feature_widget.selected_logs[0] if hasattr(parent.feature_widget, 'selected_logs') and parent.feature_widget.selected_logs else "LogFile"
            log_name = os.path.splitext(log_name)[0]  # Remove .bbl extension
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            author_name = self._get_author_name(parent)
            gain = freq_widget.gain if hasattr(freq_widget, 'gain') else 1.0
            figures = [canvas.figure for canvas in freq_widget.canvas_list if hasattr(canvas, 'figure')]
            if not figures:
                self.status_label.setText("No valid Noise Analysis plots to export.")
                return
            for i, fig in enumerate(figures):
                # Save the matplotlib figure to a temporary PNG file at high DPI
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpfile:
                    fig.savefig(tmpfile.name, dpi=350, bbox_inches='tight')
                    tmpfile.flush()
                    # Load the plot image
                    plot_img = QImage(tmpfile.name)
                # Calculate header height
                scale_factor = plot_img.devicePixelRatioF() if hasattr(plot_img, 'devicePixelRatioF') else 1.0
                header_height = int(100 * scale_factor)
                width = plot_img.width()
                total_height = header_height + plot_img.height()
                # Create the final image
                final_img = QImage(width, total_height, QImage.Format_ARGB32)
                final_img.fill(Qt.white)
                painter = QPainter(final_img)
                try:
                    painter.setRenderHint(QPainter.Antialiasing, True)
                    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                    # Draw header
                    header_font = QFont("fccTYPO", int(94 * scale_factor / 3.0))
                    header_font.setBold(True)
                    painter.setFont(header_font)
                    painter.setPen(QColor(0, 0, 0))
                    header_text = f"Log: {log_name} - Noise Analysis - {timestamp}"
                    if author_name:
                        header_text += f" - {author_name}"
                    if use_drone and drone_name:
                        header_text += f" - {drone_name}"
                    painter.drawText(QRect(0, 0, width, header_height), Qt.AlignCenter | Qt.AlignTop, header_text)
                    # Draw gain info with more space below header
                    gain_font = QFont("fccTYPO", int(82 * scale_factor / 3.0))
                    gain_font.setBold(True)
                    painter.setFont(gain_font)
                    gain_text = f"Gain: {gain}x"
                    gain_rect = QRect(0, int(header_height * 0.75), width, int(header_height * 0.25))
                    painter.drawText(gain_rect, Qt.AlignCenter | Qt.AlignTop, gain_text)
                    # Draw the plot image below the header
                    painter.drawImage(0, header_height, plot_img)
                finally:
                    painter.end()
                if use_drone and drone_name_filename:
                    filename = f"{log_name}_{drone_name_filename}_NoiseAnalysis_{i+1}_{timestamp}.jpg"
                else:
                    filename = f"{log_name}_NoiseAnalysis_{i+1}_{timestamp}.jpg"
                final_img.save(os.path.join(export_dir, filename), "JPG", quality=100)
            self.status_label.setText(f"Exported stacked Noise Analysis plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting frequency plots: {str(e)}")

    def _export_spectrogram_plots(self, parent):
        try:
            import datetime
            import os
            spectrogram_widget = parent.spectrogram_widget
            if not hasattr(spectrogram_widget, 'canvas_list') or not spectrogram_widget.canvas_list:
                self.status_label.setText("No Frequency Evolution plots to export.")
                return

            import io
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect, QPoint

            # 1. Render all canvases to in-memory pixmaps to correctly calculate dimensions
            pixmaps = []
            for canvas in spectrogram_widget.canvas_list:
                try:
                    buf = io.BytesIO()
                    # Use savefig with bbox_inches='tight' to remove whitespace around the figure
                    canvas.figure.savefig(buf, format='png', dpi=300, bbox_inches='tight', pad_inches=0.1)
                    buf.seek(0)
                    pixmap = QPixmap()
                    pixmap.loadFromData(buf.read())
                    pixmaps.append(pixmap)
                except Exception as e:
                    print(f"Error rendering spectrogram canvas to pixmap: {e}")
                    continue
            
            if not pixmaps:
                self.status_label.setText("Failed to render spectrogram plots for export.")
                return

            # 2. Calculate final image dimensions from the rendered pixmaps
            # Scale all plots to the width of the widest plot for consistency
            max_width = max(p.width() for p in pixmaps)
            
            scaled_pixmaps = []
            total_chart_height = 0
            for p in pixmaps:
                scaled_p = p.scaledToWidth(max_width, Qt.SmoothTransformation)
                scaled_pixmaps.append(scaled_p)
                total_chart_height += scaled_p.height()

            export_dir = self._get_export_dir(parent)
            os.makedirs(export_dir, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = parent.feature_widget.selected_logs[0] if hasattr(parent.feature_widget, 'selected_logs') and parent.feature_widget.selected_logs else "LogFile"
            log_name = os.path.splitext(log_name)[0]
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            author_name = self._get_author_name(parent)

            # Define header height, but no legend height for frequency evolution
            header_font_scale = 3.5
            header_height = int(100 * header_font_scale)
            
            width = max_width
            total_height = header_height + total_chart_height

            # 3. Create the combined image
            combined_image = QImage(width, total_height, QImage.Format_ARGB32)
            combined_image.fill(Qt.white)
            painter = QPainter(combined_image)

            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

                # Draw header
                header_font = QFont("fccTYPO", int(32 * header_font_scale / 3.0))
                header_font.setBold(True)
                painter.setFont(header_font)
                painter.setPen(QColor(0, 0, 0))
                header_text = f"Log: {log_name} | Frequency Evolution | Date: {current_date}"
                if author_name:
                    header_text += f" | Author: {author_name}"
                if drone_name:
                    header_text += f" | Drone: {drone_name}"
                header_rect = QRect(0, 0, width, header_height)
                painter.fillRect(header_rect, QColor(230, 230, 240))
                painter.drawText(header_rect, Qt.AlignCenter | Qt.AlignTop, header_text)
                
                settings_font = QFont("fccTYPO", int(28 * header_font_scale / 3.0))
                settings_font.setBold(True)
                painter.setFont(settings_font)
                window_size = 2 ** spectrogram_widget.window_slider.value()
                gain_value = spectrogram_widget.gain
                settings_text = f"Window Size: {window_size} | Gain: {gain_value}x"
                settings_rect = QRect(0, int(header_height/2), width, int(header_height/2))
                painter.drawText(settings_rect, Qt.AlignCenter | Qt.AlignTop, settings_text)

                # 4. Draw the tightly cropped pixmaps onto the combined image
                current_y = header_height
                for pixmap in scaled_pixmaps:
                    painter.drawPixmap(0, current_y, pixmap)
                    current_y += pixmap.height()
            finally:
                painter.end()

            # 5. Save the final image
            if use_drone and drone_name:
                filename = f"{drone_name_filename}-{log_name}-FrequencyEvolution-{timestamp}.jpg"
            else:
                filename = f"{log_name}-FrequencyEvolution-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            combined_image.save(filepath, "JPG", quality=100)
            self.status_label.setText(f"Exported stacked Frequency Evolution plots to {export_dir} as {filename}")
        except Exception as e:
            import traceback
            print(f"Error exporting frequency evolution plots: {e}\n{traceback.format_exc()}")
            self.status_label.setText(f"Error exporting frequency evolution plots: {str(e)}")

class ParametersWidget(QWidget):
    def __init__(self, feature_widget, parent=None):
        super().__init__(parent)
        self.feature_widget = feature_widget
        self.highlight_differences = False
        self.show_only_differences = False
        self.value_labels = []  # Store references to value QLabel widgets for highlighting
        self.difference_rows = set()  # Store row indices that are different
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create a horizontal layout for the two buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        
        # Add highlight differences button (hidden by default)
        self.highlight_button = QPushButton("Highlight Differences")
        self.highlight_button.setCheckable(True)
        self.highlight_button.setVisible(False)
        self.highlight_button.clicked.connect(self.toggle_highlight_differences)
        self.highlight_button.setFont(QFont("fccTYPO"))
        self.set_highlight_button_style(False)
        button_row.addWidget(self.highlight_button)

        # Add show only differences button (hidden by default)
        self.show_diff_button = QPushButton("Show Only Differences")
        self.show_diff_button.setCheckable(True)
        self.show_diff_button.setVisible(False)
        self.show_diff_button.clicked.connect(self.toggle_show_only_differences)
        self.show_diff_button.setFont(QFont("fccTYPO"))
        self.set_show_diff_button_style(False)
        button_row.addWidget(self.show_diff_button)

        layout.addLayout(button_row)
        
        # Create scroll area for parameters
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #1e1e1e;
            }
            QScrollBar:vertical {
                background: #232323;
                width: 16px;
                margin: 0px 0px 0px 0px;
                border-radius: 8px;
            }
            QScrollBar::handle:vertical {
                background: #888888;
                min-height: 24px;
                border-radius: 8px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        # Create widget to hold parameters
        self.parameters_widget = QWidget()
        self.parameters_layout = QVBoxLayout(self.parameters_widget)
        self.parameters_layout.setSpacing(10)
        self.parameters_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.parameters_widget)
        layout.addWidget(scroll_area)
        
    def set_highlight_button_style(self, active):
        if active:
            self.highlight_button.setStyleSheet("background-color: #00ff66; color: black; font-weight: bold;")
        else:
            self.highlight_button.setStyleSheet("")

    def set_show_diff_button_style(self, active):
        if active:
            self.show_diff_button.setStyleSheet("background-color: #3399ff; color: white; font-weight: bold;")
        else:
            self.show_diff_button.setStyleSheet("")

    def toggle_highlight_differences(self):
        self.highlight_differences = not self.highlight_differences
        self.highlight_button.setChecked(self.highlight_differences)
        self.set_highlight_button_style(self.highlight_differences)
        self.apply_highlighting()

    def toggle_show_only_differences(self):
        self.show_only_differences = not self.show_only_differences
        self.show_diff_button.setChecked(self.show_only_differences)
        self.set_show_diff_button_style(self.show_only_differences)
        # Re-render the parameters with the current filter
        self.update_parameters(self.current_log_names)

    def apply_highlighting(self):
        # Only highlight if there are two logs and value_labels is populated
        if not self.value_labels or len(self.value_labels) != 2:
            return
        for row in range(len(self.value_labels[0])):
            label1 = self.value_labels[0][row]
            label2 = self.value_labels[1][row]
            val1 = label1.text()
            val2 = label2.text()
            if self.highlight_differences and val1 != val2:
                label1.setStyleSheet("color: #222; background: #fff9b1;")
                label2.setStyleSheet("color: #222; background: #fff9b1;")
            else:
                label1.setStyleSheet("color: #00bfff;")
                label2.setStyleSheet("color: #00bfff;")

    def update_parameters(self, log_names=None):
        self.clear_parameters()
        self.value_labels = []
        self.difference_rows = set()
        self.current_log_names = log_names
        if not log_names or not hasattr(self.feature_widget, 'loaded_log_paths'):
            self.highlight_button.setVisible(False)
            self.show_diff_button.setVisible(False)
            return
        if isinstance(log_names, str):
            log_names = [log_names]
        log_names = log_names[:2]  # Only allow up to 2 logs
        bbl_paths = [self.feature_widget.loaded_log_paths.get(name) for name in log_names]
        sections_list = [self.parse_bbl_header(path) if path else {} for path in bbl_paths]

        # Collect all unique parameter keys in order
        all_keys = []
        key_to_section = {}
        section_order = [
            'Firmware', 'Craft', 'PID', 'RC', 'TPA', 'D', 'I', 'Anti', 'Feed', 'Acc', 'Other', 'Hardware'
        ]
        for idx, sections in enumerate(sections_list):
            for section in section_order:
                if section in sections:
                    for key, _ in sections[section]:
                        if key not in all_keys:
                            all_keys.append(key)
                            key_to_section[key] = section
            for section, items in sections.items():
                if section == 'Field':
                    continue
                for key, _ in items:
                    if key not in all_keys:
                        all_keys.append(key)
                        key_to_section[key] = section

        # Create a grid layout: col 0 = key, col 1 = log1, col 2 = log2
        grid_layout = QGridLayout()
        grid_layout.setSpacing(5)
        grid_layout.setHorizontalSpacing(10)
        grid_layout.setContentsMargins(10, 10, 10, 10)

        # Header row
        grid_layout.addWidget(QLabel("Parameter"), 0, 0)
        grid_layout.addWidget(QLabel(log_names[0] if len(log_names) > 0 else ""), 0, 1)
        grid_layout.addWidget(QLabel(log_names[1] if len(log_names) > 1 else ""), 0, 2)

        row = 1
        value_labels_1 = []
        value_labels_2 = []
        for key in all_keys:
            label = QLabel(key)
            label.setStyleSheet("color: white;")
            # Get values for both logs
            values = []
            for col, sections in enumerate(sections_list):
                value = ""
                section = key_to_section.get(key, None)
                if section and section in sections:
                    for k, v in sections[section]:
                        if k == key:
                            value = v
                            break
                values.append(value if value.strip() else "")
            # If show_only_differences is enabled, skip rows that are the same
            if self.show_only_differences and len(values) == 2 and values[0] == values[1]:
                continue
            # Track difference rows for highlighting
            if len(values) == 2 and values[0] != values[1]:
                self.difference_rows.add(row-1)  # row-1 because header is row 0
            grid_layout.addWidget(label, row, 0)
            for col, value in enumerate(values):
                value_label = QLabel(value)
                value_label.setStyleSheet("color: #00bfff;")
                grid_layout.addWidget(value_label, row, col + 1)
                if col == 0:
                    value_labels_1.append(value_label)
                elif col == 1:
                    value_labels_2.append(value_label)
            row += 1

        # Store references for highlighting
        if len(log_names) == 2:
            self.value_labels = [value_labels_1, value_labels_2]
            self.highlight_button.setVisible(True)
            self.show_diff_button.setVisible(True)
            self.set_highlight_button_style(self.highlight_differences)
            self.set_show_diff_button_style(self.show_only_differences)
            self.apply_highlighting()
        else:
            self.value_labels = []
            self.highlight_button.setVisible(False)
            self.show_diff_button.setVisible(False)

        self.parameters_layout.addLayout(grid_layout)
        self.parameters_layout.addStretch(1)

    def clear_parameters(self):
        """Clear all parameters from the display, including layouts"""
        while self.parameters_layout.count():
            item = self.parameters_layout.takeAt(0)
            widget = item.widget()
            layout = item.layout()
            if widget is not None:
                widget.deleteLater()
            elif layout is not None:
                self._delete_layout(layout)

    def _delete_layout(self, layout):
        """Recursively delete all items in a layout"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                child_layout = item.layout()
                if widget is not None:
                    widget.deleteLater()
                elif child_layout is not None:
                    self._delete_layout(child_layout)
            layout.deleteLater()

    def parse_bbl_header(self, bbl_path):
        """Parse the header of a .bbl file and return a dict of sections to key-value pairs."""
        if not bbl_path or not os.path.exists(bbl_path):
            return {}
        sections = {}
        seen_params = set()  # Keep track of parameters we've already seen
        try:
            with open(bbl_path, 'r', encoding='latin-1', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('H '):
                        continue
                    # Remove the leading 'H '
                    line = line[2:]
                    # Only process lines with a colon
                    if ':' not in line:
                        continue
                    # Try to split into section and value
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    # Skip if we've already seen this parameter
                    if key in seen_params:
                        continue
                    seen_params.add(key)
                    # Group by the part before the first space (e.g., 'Field I', 'Firmware', etc.)
                    section = key.split(' ')[0] if ' ' in key else key
                    if section not in sections:
                        sections[section] = []
                    sections[section].append((key, value))
            return sections
        except Exception as e:
            print(f"[ParametersWidget] Failed to parse .bbl header: {e}")
            return {}

    # Add a helper for debug level checks
    def debug(self, level):
        levels = {"INFO": 1, "DEBUG": 2, "VERBOSE": 3}
        return levels.get(getattr(self, 'debug_level', 'INFO'), 1) >= levels.get(level, 1)

class SpectrogramWidget(QWidget):
    def __init__(self, feature_widget, parent=None):
        super().__init__(parent)
        self.feature_widget = feature_widget
        self.df = None
        self.gain = 5.0  # Default gain value
        self.canvas_list = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Add gain control slider
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(10, 0, 10, 0)
        gain_label = QLabel("Gain:")
        gain_label.setFont(self.feature_widget.create_font('label'))
        self.gain_slider = QSlider(Qt.Horizontal)
        self.gain_slider.setMinimum(1)
        self.gain_slider.setMaximum(50)
        self.gain_slider.setValue(5)
        self.gain_slider.setTickInterval(5)
        self.gain_slider.setTickPosition(QSlider.TicksBelow)
        self.gain_value_label = QLabel(f"{self.gain}x")
        self.gain_value_label.setFont(self.feature_widget.create_font('label'))
        self.gain_slider.valueChanged.connect(self.on_gain_changed)
        control_layout.addWidget(gain_label)
        control_layout.addWidget(self.gain_slider)
        control_layout.addWidget(self.gain_value_label)
        # Add window size slider
        window_label = QLabel("Window Size:")
        window_label.setFont(self.feature_widget.create_font('label'))
        self.window_slider = QSlider(Qt.Horizontal)
        self.window_slider.setMinimum(6)   # 2**6 = 64
        self.window_slider.setMaximum(11)  # 2**11 = 2048
        self.window_slider.setValue(8)     # 2**8 = 256
        self.window_slider.setTickInterval(1)
        self.window_slider.setTickPosition(QSlider.TicksBelow)
        self.window_slider.valueChanged.connect(self.on_window_size_changed)
        self.window_value_label = QLabel("256")
        self.window_value_label.setFont(self.feature_widget.create_font('label'))
        control_layout.addWidget(window_label)
        control_layout.addWidget(self.window_slider)
        control_layout.addWidget(self.window_value_label)
        layout.addLayout(control_layout)

        self.plot_container = QWidget()
        self.plot_layout = QGridLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_container)
        layout.addStretch(1)

    def on_gain_changed(self, value):
        self.gain = value
        self.gain_value_label.setText(f"{self.gain}x")
        # Update the plot with the new gain
        self.update_spectrogram(self.df)

    def clear_all_plots(self):
        for canvas in self.canvas_list:
            self.plot_layout.removeWidget(canvas)
            canvas.setParent(None)
            canvas.deleteLater()
        self.canvas_list = []

    def update_spectrogram(self, df, max_freq=None):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib import colors
        from scipy.ndimage import gaussian_filter

        # Set plot style for consistency
        plt.style.use('default')
        plt.rcParams['font.family'] = 'fccTYPO'
        plt.rcParams['font.size'] = 10
        
        if df is not None:
            self.df = df
        if self.df is None or self.df.empty:
            if self.feature_widget.debug('DEBUG'):
                print("[SpectrogramWidget] DataFrame is empty or None.")
            return
        self.clear_all_plots()
        axis_labels = ['Roll', 'Pitch', 'Yaw']
        # Determine which gyro type is selected
        gyro_type = None
        if hasattr(self.feature_widget, 'gyro_unfilt_checkbox') and self.feature_widget.gyro_unfilt_checkbox.isChecked():
            gyro_type = 'raw'
        elif hasattr(self.feature_widget, 'gyro_scaled_checkbox') and self.feature_widget.gyro_scaled_checkbox.isChecked():
            gyro_type = 'filtered'
        else:
            gyro_type = 'filtered'
        vmin = 0.01  # Fixed noise floor value
        
        # Calculate Nyquist frequency from data
        time = self.df['time'].values.astype(float)
        if time.max() > 1e6:
            time = time / 1_000_000.0
        elif time.max() > 1e3:
            time = time / 1_000.0
        time = time - time.min()
        dt = np.mean(np.diff(time))
        fs = 1.0 / dt if dt > 0 else 0.0
        nyquist = fs / 2
        nperseg = 2 ** self.window_slider.value()
        noverlap = int(nperseg * 0.75)
        
        # First pass: calculate all spectrograms to find global min/max values
        all_results = []
        global_vmax = vmin
        global_f_max = 0
        
        for axis_idx, axis_name in enumerate(axis_labels):
            result = calculate_spectrogram(self.df, axis_idx, gyro_type=gyro_type, max_freq=nyquist, gain=self.gain, clip_seconds=1.0, nperseg=nperseg, noverlap=noverlap)
            if result is not None:
                t, f, Sxx = result['t'], result['f'], result['Sxx']
                Sxx_smooth = gaussian_filter(Sxx, sigma=1)
                local_vmax = np.max(Sxx_smooth) + 1e-6
                global_vmax = max(global_vmax, local_vmax)
                global_f_max = max(global_f_max, f.max())
                all_results.append({
                    'axis_idx': axis_idx,
                    'axis_name': axis_name,
                    't': t,
                    'f': f,
                    'Sxx_smooth': Sxx_smooth
                })
        
        # Ensure we have a valid vmax
        if vmin >= global_vmax:
            global_vmax = vmin * 10 if vmin > 0 else 1e-5
        
        # Second pass: create plots with consistent limits
        for result_data in all_results:
            axis_idx = result_data['axis_idx']
            axis_name = result_data['axis_name']
            t = result_data['t']
            f = result_data['f']
            Sxx_smooth = result_data['Sxx_smooth']
            
            # Use constrained_layout to prevent label cropping
            fig, ax = plt.subplots(figsize=(8, 5.5), constrained_layout=True)
            plot_label = f'Gyro (raw) {axis_name}' if gyro_type == 'raw' else f'Gyro (filtered) {axis_name}'
            extent = [t.min(), t.max(), f.min(), f.max()]
            im = ax.imshow(Sxx_smooth + 1e-12, aspect='auto', origin='lower',
                          extent=extent,
                          norm=colors.LogNorm(vmin=vmin, vmax=global_vmax),
                          cmap='inferno', interpolation='bilinear')
            ax.set_title(f"Frequency Evolution {plot_label}", color='black', loc='left', pad=5)
            ax.set_ylabel('Frequency (Hz)', color='black')
            ax.set_xlabel('Time (s)', color='black')
            # Use consistent y-axis limits for all plots
            ax.set_ylim(0, global_f_max)
            ax.set_facecolor('white')
            ax.grid(True, color='gray', alpha=0.5, linestyle='-')
            ax.tick_params(axis='x', colors='black')
            ax.tick_params(axis='y', colors='black')
            for spine in ax.spines.values():
                spine.set_color('black')
            
            canvas = FigureCanvas(fig)
            canvas.setCursor(Qt.CrossCursor)

            # Add tooltip functionality
            def make_motion_event_handler(canvas, fig, t_data, f_data, sxx_data):
                def on_motion(event):
                    if event.inaxes:
                        try:
                            # Map mouse coordinates to data indices
                            time_val = event.xdata
                            freq_val = event.ydata
                            
                            time_idx = np.argmin(np.abs(t_data - time_val))
                            freq_idx = np.argmin(np.abs(f_data - freq_val))
                            
                            intensity = sxx_data[freq_idx, time_idx]
                            
                            # Format the tooltip text
                            tooltip_text = (
                                f"Time: {time_val:.3f} s\n"
                                f"Frequency: {freq_val:.1f} Hz\n"
                                f"Intensity: {intensity:.4f}"
                            )
                            
                            # Use the event's GUI coordinates to position the tooltip
                            QToolTip.showText(event.guiEvent.globalPos(), tooltip_text, canvas)
                        except (ValueError, IndexError):
                            # Hide tooltip if there's an error or mouse is out of data bounds
                            QToolTip.hideText()
                    else:
                        QToolTip.hideText()
                return on_motion

            # Connect the event handler to the canvas
            canvas.mpl_connect(
                'motion_notify_event', 
                make_motion_event_handler(canvas, fig, t, f, Sxx_smooth)
            )
            
            self.plot_layout.addWidget(canvas, axis_idx, 0)
            self.canvas_list.append(canvas)

    def on_window_size_changed(self, value):
        nperseg = 2 ** value
        self.window_value_label.setText(str(nperseg))
        self.update_spectrogram(self.df)