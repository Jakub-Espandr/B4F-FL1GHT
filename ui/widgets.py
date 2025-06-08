"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QCheckBox, QLabel, QMessageBox, QGroupBox, QScrollArea,
    QSlider, QProgressBar, QSizePolicy, QComboBox, QToolTip, QGridLayout, QSpinBox,
    QDialog, QLineEdit, QListWidget
)
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QIcon
from PySide6.QtCore import Qt, QMargins, QTimer
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QAreaSeries, QCategoryAxis
from utils.config import FONT_CONFIG, COLOR_PALETTE, MOTOR_COLORS
from utils.data_processor import get_clean_name
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from utils.step_response import StepResponseCalculator
from utils.step_trace import StepTrace
import os
import matplotlib.cm as cm
from scipy import signal
from scipy.ndimage import gaussian_filter1d
from mpl_toolkits.axes_grid1 import make_axes_locatable
from utils.pid_analyzer_noise import plot_all_noise_from_df, plot_noise_from_df, generate_individual_noise_figures
import sys
import json

class FeatureSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.update_timer = None
        self.current_line_width = 1.0  # Default line width (stored here)
        self.author_name = ""  # Default author name
        self.drone_name = ""  # Default drone name
        self.use_drone_in_filename = False
        self.loaded_logs = {}  # Dictionary to store loaded logs {filename: dataframe}
        self.current_log = None  # Currently selected log
        self.selected_logs = []  # List of selected logs for multi-plotting
        # Set default export directory to app_dir/export
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        default_export_dir = os.path.join(app_dir, "export")
        self.export_dir = default_export_dir
        # Try to load settings from config/settings.json
        config_dir = os.path.join(app_dir, "config")
        config_path = os.path.join(config_dir, "settings.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.author_name = data.get("author_name", self.author_name)
                    loaded_export_dir = data.get("export_dir", self.export_dir)
                    if not loaded_export_dir:
                        self.export_dir = default_export_dir
                    else:
                        self.export_dir = loaded_export_dir
                    self.drone_name = data.get("drone_name", self.drone_name)
                    self.use_drone_in_filename = data.get("use_drone_in_filename", self.use_drone_in_filename)
            except Exception as e:
                print(f"[Settings] Failed to load config: {e}")
        self.setup_ui()

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
                        # Skip the zero reference line (black line at y=0)
                        if series.name() == "Zero" or series.pen().color() == Qt.black:
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
        
        # If we already have a pending update, don't schedule another one
        if hasattr(self, 'update_timer') and self.update_timer is not None and self.update_timer.isActive():
            return
            
        # Create a timer for delayed update
        if not hasattr(self, 'update_timer') or self.update_timer is None:
            self.update_timer = QTimer()
            self.update_timer.setSingleShot(True)
            self.update_timer.timeout.connect(self._do_update)
            
        # Start or restart the timer (300ms delay)
        self.update_timer.start(300)
    
    def _do_update(self):
        """Actually perform the update after the timer expires"""
        parent = self.parent()
        # Find the main viewer (FL1GHTViewer) in the parent chain
        while parent is not None and not hasattr(parent, 'plot_selected'):
            parent = parent.parent() if hasattr(parent, 'parent') else None
        
        # Check if we're in the Time Domain tab (index 0)
        if parent and hasattr(parent, 'tab_widget') and parent.tab_widget.currentIndex() == 0:
            # Call plot_selected to update the chart and legend
            parent.plot_selected()

    def uncheck_all_features(self):
        for checkbox in [self.gyro_unfilt_checkbox, self.gyro_scaled_checkbox, 
                         self.pid_p_checkbox, self.pid_i_checkbox, self.pid_d_checkbox,
                         self.pid_f_checkbox, self.setpoint_checkbox, self.rc_checkbox,
                         self.throttle_checkbox, self.motor_checkbox]:
            checkbox.setChecked(False)

    def set_time_domain_mode(self, enabled: bool):
        # List of all checkboxes
        all_checkboxes = [self.gyro_unfilt_checkbox, self.gyro_scaled_checkbox, 
                          self.pid_p_checkbox, self.pid_i_checkbox, self.pid_d_checkbox,
                          self.pid_f_checkbox, self.setpoint_checkbox, self.rc_checkbox,
                          self.throttle_checkbox, self.motor_checkbox]
        if enabled:
            for checkbox in all_checkboxes:
                checkbox.setEnabled(True)
            self.throttle_checkbox.setEnabled(True)
            self.motor_checkbox.setEnabled(True)
        else:
            for checkbox in all_checkboxes:
                checkbox.setEnabled(False)
        # Disconnect all checkbox signals
        for checkbox in all_checkboxes:
            try:
                checkbox.stateChanged.disconnect()
            except TypeError:
                pass
        # Do NOT reconnect stateChanged to notify_parent_update in time domain mode
        # Only the Show Plot button will trigger plot updates

    def open_settings_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.resize(420, 220)  # Make the dialog wider and taller
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
                        "use_drone_in_filename": self.use_drone_in_filename
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
        """Handle selection changes in the logs list widget"""
        selected_items = self.logs_list.selectedItems()
        self.selected_logs = [item.text() for item in selected_items]
        
        # If only one log is selected, update current_log for compatibility
        if len(self.selected_logs) == 1:
            self.current_log = self.loaded_logs[self.selected_logs[0]]
            self.df = self.current_log
            
            # Update combo box for compatibility
            index = self.logs_combo.findText(self.selected_logs[0])
            if index >= 0:
                self.logs_combo.setCurrentIndex(index)
                
        print(f"Selected logs: {self.selected_logs}")

    def on_log_selected(self, index):
        """Handle log selection from the combo box"""
        if index >= 0:  # Check if a valid item is selected
            filename = self.logs_combo.currentText()
            if filename in self.loaded_logs:
                self.current_log = self.loaded_logs[filename]
                self.df = self.current_log  # Update the dataframe for plotting
                
                # Update the logs list selection to match
                for i in range(self.logs_list.count()):
                    item = self.logs_list.item(i)
                    if item.text() == filename:
                        self.logs_list.setCurrentItem(item)
                        break
                
                # Update the feature widget with the new dataframe
                if hasattr(self, 'feature_widget'):
                    self.feature_widget.df = self.df

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
        self.setup_ui()

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
            chart_view_full = QChartView()
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
            row_layout.addWidget(chart_view_full, stretch=3)  # Make full plot wider
            # Zoomed plot (0-100 Hz)
            chart_view_zoom = QChartView()
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
            row_layout.addWidget(chart_view_zoom, stretch=1)  # Make zoomed plot narrower
            # Store both views as a tuple
            self.chart_views.append((chart_view_full, chart_view_zoom))
            charts_layout.addLayout(row_layout)
        layout.addWidget(self.charts_container)

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
        if df is not None:
            self.df = df
        df = self.df
        if df is None or df.empty:
            print("[SpectralAnalyzer] DataFrame is empty or None.")
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
            print("[SpectralAnalyzer] No types selected, nothing will be plotted.")
            return
        print(f"[SpectralAnalyzer] Selected types: {selected_types}")

        # Map type to column patterns, legend, and color
        type_to_pattern = {
            'raw': ('gyroUnfilt[{}]', 'Gyro (raw)', QColor(255, 0, 255)),
            'filtered': ('gyroADC[{}] (deg/s)', 'Gyro (filtered)', QColor(0, 255, 255)),
            'pterm': ('axisP[{}]', 'P-Term', QColor(255, 200, 0)),
            'iterm': ('axisI[{}]', 'I-Term', QColor(255, 128, 0)),
            'dterm': ('axisD[{}]', 'D-Term', QColor(128, 0, 255)),
            'setpoint': ('setpoint[{}]', 'Setpoint', QColor(0, 0, 0)),
            'rc': ('rcCommand[{}]', 'RC Command', QColor(128, 128, 0)),
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
        print(f"[SpectralAnalyzer] Sampling rate: {fs:.2f} Hz")

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
                        series_name = f"{label} ({log_label})"
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
                    # For the legend, only use the feature name (label), not the log name
                    legend_labels.add((label, color.name()))
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
            while legend_layout.count():
                item = legend_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            # Only show legend entries for types that were actually plotted
            for label, color_name in legend_labels:
                legend_label = QLabel()
                legend_label.setFont(self.create_font('label'))
                legend_label.setText(f"<span style='color: {color_name}'>●</span> {label}")
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
        self.setup_ui()

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)
        self.charts_container = QWidget()
        charts_layout = QVBoxLayout(self.charts_container)
        charts_layout.setSpacing(10)
        self.chart_views = []
        for axis in ['Roll', 'Pitch', 'Yaw']:
            chart_view = QChartView()
            chart_view.setRenderHint(QPainter.Antialiasing)
            chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            chart_view.setMinimumHeight(200)
            chart = QChart()
            chart.setTitle(f"{axis} Step Response")
            title_font = QFont()
            title_font.setPointSize(10)
            chart.setTitleFont(title_font)
            chart.legend().setVisible(False)  # Hide legend
            chart.setMargins(QMargins(10, 10, 10, 10))
            chart_view.setChart(chart)
            # Connect mouse move event for tooltips
            chart_view.setMouseTracking(True)
            chart_view.mouseMoveEvent = lambda event, cv=chart_view: self.show_tooltip(event, cv)
            chart_view.setCursor(Qt.CrossCursor)  # Add crosshair cursor
            self.chart_views.append(chart_view)
            charts_layout.addWidget(chart_view)
        layout.addWidget(self.charts_container)

    def update_step_response(self, df, line_width=None, log_name=None, clear_charts=True):
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
        for i, axis_name in enumerate(axes_names):
            chart_view = self.charts_container.layout().itemAt(i).widget() if hasattr(self, 'charts_container') else self.chart_views[i]
            chart = chart_view.chart()
            if clear_charts:
                chart.legend().setVisible(False)  # Hide legend
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
            for pid_key in [f'{axis_name}pid', f'{axis_name.upper()}PID', f'{axis_name[0]}pid']:
                pid_col = [col for col in df.columns if pid_key in col.lower()]
                if pid_col:
                    pid_val = df[pid_col[0]].iloc[0]
                    break

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
                color = QColor(*COLOR_PALETTE.get('Gyro (filtered)', (0, 255, 255)))
                series = QLineSeries()
                t_ms = [float(x) * 1000 for x in t]
                t_ms = [x - t_ms[0] for x in t_ms]  # Ensure starts at 0
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
                        pid_text = f"{p:.0f}; {i:.0f}; {d:.0f}"
                    except:
                        pid_text = f"PID: {pid_val}"
                else:
                    pid_text = "PID: N/A"
                chart.legend().markers(series)[0].setLabel(f"{log_name}\n{pid_text}")
                # Only add annotation for the first log (clear_charts=True)
                if clear_charts:
                    chart.legend().setVisible(True)
                    chart.legend().setLabelColor(Qt.black)
                    chart.legend().setFont(QFont("Arial", 9))
                    chart.update()
                    # Compute max Y and time to reach 0.5 (in ms)
                    max_y = float(np.max(mean))
                    max_idx = int(np.argmax(mean))
                    max_t = float(t_ms[max_idx]) if max_idx < len(t_ms) else 0.0
                    t_05 = next((float(ti) for ti, yi in zip(t_ms, mean) if yi >= 0.5), None)
                    # Prepare annotation text in ms
                    annotation = f"Max: {max_y:.2f} at t={max_t:.0f}ms  Response: {t_05:.0f}ms" if t_05 is not None else f"Max: {max_y:.2f} at t={max_t:.0f}ms  Response: N/A"
                    label = QLabel(annotation)
                    label.setStyleSheet("background: rgba(255,255,255,0.8); color: black; font-size: 11px; padding: 2px;")
                    label.setAlignment(Qt.AlignRight | Qt.AlignTop)
                    proxy = chart_view.scene().addWidget(label)
                    proxy.setZValue(100)
                    proxy.setPos(chart_view.width() - 300, 30)
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
        self.gain_slider.setMaximum(50) # Max gain 50x
        self.gain_slider.setValue(5)    # Default 5x
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
            print("[FrequencyAnalyzer] DataFrame is empty or None.")
            return
        # Debug: print columns and sample data
        print("[FrequencyAnalyzer] DataFrame columns:", self.df.columns.tolist())
        print("[FrequencyAnalyzer] DataFrame head:")
        print(self.df.head())
        
        # Check for key columns
        has_gyro = any('gyro' in col.lower() for col in self.df.columns)
        has_debug = any('debug' in col.lower() for col in self.df.columns)
        has_throttle = any('throttle' in col.lower() or 'rccommand[3]' in col.lower() for col in self.df.columns)
        
        print(f"[FrequencyAnalyzer] Has gyro: {has_gyro}, debug: {has_debug}, throttle: {has_throttle}")
        print(f"[FrequencyAnalyzer] Using gain: {self.gain}x, max_freq: {max_freq}Hz")
        
        # Try to print gyro, debug, and throttle columns
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
        info_label = QLabel("This tab exports the previously viewed plots to your desktop.")
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
        self.status_label.setText("Exporting plots...")
        
        # Find the parent FL1GHTViewer to access the tab widget
        parent = self.parent()
        while parent is not None and not hasattr(parent, 'tab_widget'):
            parent = parent.parent()
        
        if not parent or not hasattr(parent, 'tab_widget'):
            self.status_label.setText("Error: Could not find parent viewer.")
            return
        
        # Export based on the previous tab
        if self.previous_tab_index == 0:  # Time Domain
            self._export_time_domain_plots(parent)
        elif self.previous_tab_index == 1:  # Spectral Analysis
            self._export_spectral_plots(parent)
        elif self.previous_tab_index == 2:  # Step Response
            self._export_step_response_plots(parent)
        elif self.previous_tab_index == 3:  # Frequency Analyzer
            self._export_frequency_analyzer_plots(parent)
        else:
            self.status_label.setText("Error: Unknown tab type.")
    
    def _get_export_dir(self, parent):
        # Try to get export_dir from feature_widget
        if hasattr(parent, 'feature_widget') and hasattr(parent.feature_widget, 'export_dir'):
            return parent.feature_widget.export_dir
        return self.export_path

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
                self.status_label.setText("No Time Domain plots to export.")
                return
            # Use export_dir from settings
            export_dir = self._get_export_dir(parent)
            import os
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            # Generate timestamp for filenames
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = os.path.basename(parent.current_file) if hasattr(parent, 'current_file') and parent.current_file else "LogFile"
            log_name = os.path.splitext(log_name)[0]
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            # Stack plots into a single high-resolution image
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect
            scale_factor = 3.0
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
                author_name = self._get_author_name(parent)
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
                settings_text = f"Line Width: {parent.feature_widget.current_line_width:.1f}px | Zoom: {1.0:.1f}x"
                settings_rect = QRect(0, int(header_height/2), width, int(header_height/2))
                painter.drawText(settings_rect, Qt.AlignCenter | Qt.AlignTop, settings_text)
                # Legend drawing code ...
                legend_items = []
                legend_layout = getattr(parent.feature_widget, 'legend_layout', None)
                if legend_layout is not None:
                    for i in range(legend_layout.count()):
                        item = legend_layout.itemAt(i)
                        widget = item.widget()
                        if widget:
                            import re
                            html = widget.text()
                            match = re.search(r"color: ([^']+).*?>(.*?)<.*?>(.*)", html)
                            if match:
                                color = match.group(1)
                                label = match.group(3)
                                legend_items.append((color, label))
                            else:
                                legend_items.append(("#000000", widget.text()))
                if legend_items:
                    legend_font = QFont("fccTYPO", int(32 * scale_factor / 3.0))
                    legend_font.setBold(False)
                    painter.setFont(legend_font)
                    y = int(header_height * 0.85)
                    x = 40
                    dot_radius = int(18 * scale_factor / 3.0)
                    spacing = int(60 * scale_factor / 3.0)
                    for color, label in legend_items:
                        painter.setPen(QColor(color))
                        painter.setBrush(QColor(color))
                        painter.drawEllipse(x, y, dot_radius, dot_radius)
                        painter.setPen(QColor(0, 0, 0))
                        painter.drawText(x + dot_radius + 12, y + dot_radius, label)
                        x += spacing + painter.fontMetrics().horizontalAdvance(label)
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
                filename = f"{drone_name_filename}-{log_name}-TimeDomain-{timestamp}.jpg"
            else:
                filename = f"{log_name}-TimeDomain-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            combined_image.save(filepath, "JPG", quality=99)
            self.status_label.setText(f"Exported ultra-high-resolution stacked Time Domain plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting Time Domain plots: {str(e)}")
    
    def _export_spectral_plots(self, parent):
        try:
            spectral_widget = parent.spectral_widget
            if not hasattr(spectral_widget, 'chart_views') or not spectral_widget.chart_views:
                self.status_label.setText("No Spectral Analysis plots to export.")
                return
            export_dir = self._get_export_dir(parent)
            import os
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = os.path.basename(parent.current_file) if hasattr(parent, 'current_file') and parent.current_file else "LogFile"
            log_name = os.path.splitext(log_name)[0]
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            chart_pairs = spectral_widget.chart_views
            row_height = max(full.height() for full, zoom in chart_pairs)
            scale_factor = 3.0
            header_height = int(100 * scale_factor)
            chart_height = int(row_height * len(chart_pairs) * scale_factor)
            row_width = chart_pairs[0][0].width() + chart_pairs[0][1].width()
            width = int(row_width * scale_factor)
            total_height = chart_height + header_height
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect
            combined_image = QImage(width, total_height, QImage.Format_ARGB32)
            combined_image.fill(Qt.white)
            painter = QPainter(combined_image)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                author_name = self._get_author_name(parent)
                header_font = QFont("fccTYPO", int(32 * scale_factor / 3.0))
                header_font.setBold(True)
                painter.setFont(header_font)
                painter.setPen(QColor(0, 0, 0))
                header_text = f"Log: {log_name} | Spectral Analysis | Date: {current_date}"
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
                settings_text = f"Smoothing Window Size: {spectral_widget.window_sizes[spectral_widget.window_size_slider.value()]}"
                settings_rect = QRect(0, int(header_height/2), width, int(header_height/2))
                painter.drawText(settings_rect, Qt.AlignCenter | Qt.AlignTop, settings_text)
                legend_items = []
                legend_layout = getattr(parent.feature_widget, 'legend_layout', None)
                if legend_layout is not None:
                    for i in range(legend_layout.count()):
                        item = legend_layout.itemAt(i)
                        widget = item.widget()
                        if widget:
                            import re
                            html = widget.text()
                            match = re.search(r"color: ([^']+).*?>(.*?)<.*?>(.*)", html)
                            if match:
                                color = match.group(1)
                                label = match.group(3)
                                legend_items.append((color, label))
                            else:
                                legend_items.append(("#000000", widget.text()))
                if legend_items:
                    legend_font = QFont("fccTYPO", int(32 * scale_factor / 3.0))
                    legend_font.setBold(False)
                    painter.setFont(legend_font)
                    y = int(header_height * 0.85)
                    x = 40
                    dot_radius = int(18 * scale_factor / 3.0)
                    spacing = int(60 * scale_factor / 3.0)
                    for color, label in legend_items:
                        painter.setPen(QColor(color))
                        painter.setBrush(QColor(color))
                        painter.drawEllipse(x, y, dot_radius, dot_radius)
                        painter.setPen(QColor(0, 0, 0))
                        painter.drawText(x + dot_radius + 12, y + dot_radius, label)
                        x += spacing + painter.fontMetrics().horizontalAdvance(label)
                painter.setPen(QColor(180, 180, 180))
                current_y = header_height
                for chart_view_full, chart_view_zoom in chart_pairs:
                    full_width = int(chart_view_full.width() * scale_factor)
                    full_height = int(chart_view_full.height() * scale_factor)
                    zoom_width = int(chart_view_zoom.width() * scale_factor)
                    zoom_height = int(chart_view_zoom.height() * scale_factor)
                    full_pixmap = QPixmap(full_width, full_height)
                    full_pixmap.fill(Qt.white)
                    temp_painter = QPainter(full_pixmap)
                    temp_painter.setRenderHint(QPainter.Antialiasing, True)
                    chart_view_full.render(temp_painter, target=full_pixmap.rect(), source=chart_view_full.rect())
                    temp_painter.end()
                    zoom_pixmap = QPixmap(zoom_width, zoom_height)
                    zoom_pixmap.fill(Qt.white)
                    temp_painter = QPainter(zoom_pixmap)
                    temp_painter.setRenderHint(QPainter.Antialiasing, True)
                    chart_view_zoom.render(temp_painter, target=zoom_pixmap.rect(), source=chart_view_zoom.rect())
                    temp_painter.end()
                    painter.drawPixmap(0, current_y, full_pixmap)
                    painter.drawPixmap(full_width, current_y, zoom_pixmap)
                    current_y += max(full_height, zoom_height)
            finally:
                painter.end()
            if use_drone and drone_name:
                filename = f"{drone_name_filename}-{log_name}-SpectralAnalysis-{timestamp}.jpg"
            else:
                filename = f"{log_name}-SpectralAnalysis-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            combined_image.save(filepath, "JPG", quality=99)
            self.status_label.setText(f"Exported ultra-high-resolution stacked Spectral Analysis plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting Spectral plots: {str(e)}")
    
    def _export_step_response_plots(self, parent):
        try:
            step_widget = parent.step_response_widget
            if not hasattr(step_widget, 'chart_views') or not step_widget.chart_views:
                self.status_label.setText("No Step Response plots to export.")
                return
            export_dir = self._get_export_dir(parent)
            import os
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_name = os.path.basename(parent.current_file) if hasattr(parent, 'current_file') and parent.current_file else "LogFile"
            log_name = os.path.splitext(log_name)[0]
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            scale_factor = 3.0
            header_height = int(100 * scale_factor)
            chart_height = int(sum(view.height() for view in step_widget.chart_views) * scale_factor)
            width = int(step_widget.chart_views[0].width() * scale_factor)
            total_height = chart_height + header_height
            from PySide6.QtGui import QImage, QPainter, QPixmap, QFont, QColor
            from PySide6.QtCore import QSize, Qt, QRect
            combined_image = QImage(width, total_height, QImage.Format_ARGB32)
            combined_image.fill(Qt.white)
            painter = QPainter(combined_image)
            try:
                painter.setRenderHint(QPainter.Antialiasing, True)
                painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
                author_name = self._get_author_name(parent)
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
                pid_values = parent.pid_values if hasattr(parent, 'pid_values') else {}
                pid_text = ""
                if 'roll' in pid_values:
                    pid_text = f"Roll PID: {pid_values['roll']}, Pitch PID: {pid_values['pitch']}, Yaw PID: {pid_values['yaw']}"
                settings_font = QFont("fccTYPO", int(28 * scale_factor / 3.0))
                settings_font.setBold(True)
                painter.setFont(settings_font)
                settings_rect = QRect(0, int(header_height/2), width, int(header_height/2))
                painter.drawText(settings_rect, Qt.AlignCenter | Qt.AlignTop, pid_text)
                painter.setPen(QColor(180, 180, 180))
                current_y = header_height
                for chart_view in step_widget.chart_views:
                    chart_height = int(chart_view.height() * scale_factor)
                    chart_width = int(chart_view.width() * scale_factor)
                    pixmap = QPixmap(chart_width, chart_height)
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
            combined_image.save(filepath, "JPG", quality=99)
            self.status_label.setText(f"Exported ultra-high-resolution stacked Step Response plots to {export_dir} as {filename}")
        except Exception as e:
            self.status_label.setText(f"Error exporting Step Response plots: {str(e)}")
    
    def _export_frequency_analyzer_plots(self, parent):
        try:
            freq_widget = parent.frequency_analyzer_widget
            if not hasattr(freq_widget, 'canvas_list') or not freq_widget.canvas_list:
                self.status_label.setText("No Frequency Analyzer plots to export.")
                return
            
            # Create export directory if it doesn't exist
            export_dir = self._get_export_dir(parent)
            import os
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
            
            # Generate timestamp for filenames
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Get log name (without extension)
            log_name = os.path.basename(parent.current_file) if hasattr(parent, 'current_file') and parent.current_file else "LogFile"
            log_name = os.path.splitext(log_name)[0]
            drone_name = self._get_drone_name(parent)
            drone_name_filename = drone_name.replace(' ', '_') if drone_name else ''
            use_drone = self._use_drone_in_filename(parent)
            
            # For matplotlib figures, we need a different approach
            # If it's a single figure with subplots, just save it directly at high resolution
            if len(freq_widget.canvas_list) == 1 and hasattr(freq_widget.canvas_list[0], 'figure'):
                fig = freq_widget.canvas_list[0].figure
                if len(fig.axes) > 3:  # If it's a multi-axis figure
                    # Set figure background color to match other exports
                    fig.patch.set_facecolor('#E6E6F0')  # Same color as other exports
                    
                    # Resize figure to add more space at top
                    fig.set_size_inches(fig.get_size_inches()[0], fig.get_size_inches()[1] * 1.3)  # Make figure 30% taller
                    
                    # Add title with info using fccTYPO font
                    fig.suptitle(f"Log: {log_name} | Frequency Analysis | Date: {current_date}", 
                               fontsize=9, y=0.98, fontfamily='fccTYPO', weight='bold')
                    
                    # Add gain text separately with smaller font
                    fig.text(0.5, 0.95, f"Gain: {freq_widget.gain}x", 
                           fontsize=8, fontfamily='fccTYPO', weight='bold', ha='center')
                    
                    # Add much more space above the plot
                    fig.subplots_adjust(top=0.50)  # Increased space above plot significantly
                    
                    # Move colorbars down and add more space
                    for ax in fig.axes:
                        if hasattr(ax, 'get_label') and ax.get_label() == 'colorbar':
                            # Get current position
                            pos = ax.get_position()
                            # Move down by 15% of the figure height
                            ax.set_position([pos.x0, pos.y0 - 0.15, pos.width, pos.height])
                    
                    # Add more space at the bottom of the figure
                    fig.subplots_adjust(bottom=0.2)  # Increased space at bottom
                    
                    if use_drone and drone_name:
                        filename = f"{drone_name_filename}-{log_name}-FrequencyAnalyzer-{timestamp}.jpg"
                    else:
                        filename = f"{log_name}-FrequencyAnalyzer-{timestamp}.jpg"
                    filepath = os.path.join(export_dir, filename)
                    # Save at higher DPI for better resolution - no quality arg for matplotlib
                    fig.savefig(filepath, dpi=1200, bbox_inches='tight', format='jpg')
                    self.status_label.setText(f"Exported ultra-high-resolution combined Frequency Analyzer plot to {export_dir} as {filename}")
                    # Clear and regenerate Frequency Analyzer plot
                    freq_widget.clear_all_plots()
                    if hasattr(freq_widget, 'df') and freq_widget.df is not None:
                        freq_widget.update_frequency_plots(freq_widget.df, max_freq=1000)
                    return
            
            # If we have multiple separate figures, stack them using matplotlib with high resolution
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Get all figures from the canvases
            figures = [canvas.figure for canvas in freq_widget.canvas_list if hasattr(canvas, 'figure')]
            if not figures:
                self.status_label.setText("No valid Frequency Analyzer plots to export.")
                return
                
            # Create a new tall figure to stack all plots with higher resolution
            n_plots = len(figures)
            fig_height = 8 * n_plots  # 8 inches per plot (increased for better quality)
            fig_width = 12  # Wider for better resolution
            
            # Get log name and gain value
            log_name = os.path.basename(parent.current_file) if hasattr(parent, 'current_file') and parent.current_file else "Log File"
            gain = freq_widget.gain
            
            fig, axes = plt.subplots(nrows=n_plots, figsize=(fig_width, fig_height), dpi=1200)
            
            # Add title with info
            fig.suptitle(f"Log: {log_name} | Frequency Analysis | Date: {current_date} | Gain: {gain}x", 
                       fontsize=32, y=0.99)
            
            if n_plots == 1:
                axes = [axes]  # Make it a list if there's only one subplot
            
            # Define plot types and axis names for better labels
            axis_names = ['Roll', 'Pitch', 'Yaw']
            plot_types = ['Gyro', 'Debug', 'DTerm']
            
            # Copy content from each figure to the stacked figure
            for i, (source_fig, ax) in enumerate(zip(figures, axes)):
                # Calculate the axis and plot type based on index
                axis_idx = i // 3
                plot_type_idx = i % 3
                
                axis_name = axis_names[axis_idx] if axis_idx < len(axis_names) else f"Axis{axis_idx}"
                plot_type = plot_types[plot_type_idx] if plot_type_idx < len(plot_types) else f"Type{plot_type_idx}"
                
                # Get the content from the source figure's first axis
                if source_fig.axes:
                    source_ax = source_fig.axes[0]
                    
                    # Copy all artists from the source axis to the target axis
                    for artist in source_ax.get_children():
                        if hasattr(artist, 'get_array') and hasattr(artist, 'get_cmap'):  # For pcolormesh
                            data = artist.get_array()
                            x = artist.get_offsets()[:, 0] if hasattr(artist, 'get_offsets') else np.linspace(0, 100, data.shape[1])
                            y = artist.get_offsets()[:, 1] if hasattr(artist, 'get_offsets') else np.linspace(0, 1000, data.shape[0])
                            
                            # Create new pcolormesh
                            pcm = ax.pcolormesh(x, y, data, cmap=artist.get_cmap(), norm=artist.norm)
                    
                    # Copy axis limits and labels
                    ax.set_xlim(source_ax.get_xlim())
                    ax.set_ylim(source_ax.get_ylim())
                    ax.set_xlabel(source_ax.get_xlabel(), fontsize=22)  # Larger font
                    ax.set_ylabel(source_ax.get_ylabel(), fontsize=22)  # Larger font
                    ax.set_title(f"{axis_name} {plot_type}", fontsize=32)  # Larger font
                    ax.grid(True, color='white', alpha=0.3)
                    # Increase tick label size for better readability
                    ax.tick_params(axis='both', labelsize=12)  # Larger font
            
            # Adjust layout and save at high resolution
            plt.tight_layout(rect=[0, 0, 1, 0.97])  # Leave room for the title
            if use_drone and drone_name:
                filename = f"{drone_name_filename}-{log_name}-FrequencyAnalyzer-{timestamp}.jpg"
            else:
                filename = f"{log_name}-FrequencyAnalyzer-{timestamp}.jpg"
            filepath = os.path.join(export_dir, filename)
            # Save without quality arg (not supported by matplotlib)
            plt.savefig(filepath, dpi=1200, bbox_inches='tight', format='jpg')
            plt.close(fig)
            
            self.status_label.setText(f"Exported ultra-high-resolution stacked Frequency Analyzer plots to {export_dir} as {filename}")
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            self.status_label.setText(f"Error exporting Frequency Analyzer plots: {str(e)}")