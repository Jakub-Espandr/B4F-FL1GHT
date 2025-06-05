"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QCheckBox, QLabel, QMessageBox, QGroupBox, QScrollArea,
    QSlider, QProgressBar, QSizePolicy
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt
from utils.config import FONT_CONFIG, COLOR_PALETTE, MOTOR_COLORS

class FeatureSelectionWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.select_button = QPushButton("Select File")
        self.select_button.setFont(self.create_font('button'))
        file_controls.addWidget(self.select_button)

        # Plot button
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
        self.legend_layout = QVBoxLayout()
        self.legend_layout.setSpacing(10)  # Restore original spacing
        self.legend_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        self.legend_group.setLayout(self.legend_layout)
        layout.addWidget(self.legend_group)

        # Add line width controls under the legend
        line_width_group = QGroupBox("Line Width")
        line_width_group.setFont(self.create_font('sub_group'))
        line_width_layout = QVBoxLayout()
        line_width_layout.setSpacing(10)  # Restore original spacing
        line_width_layout.setContentsMargins(10, 10, 10, 10)  # Restore original margins
        
        # Create horizontal layout for slider and label
        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(10)  # Restore original spacing
        
        self.line_width_slider = QSlider(Qt.Horizontal)
        self.line_width_slider.setMinimum(2)  # 1.0 * 2
        self.line_width_slider.setMaximum(4)  # 2.0 * 2
        self.line_width_slider.setValue(2)    # 1.0 * 2
        self.line_width_slider.setTickPosition(QSlider.NoTicks)
        self.line_width_slider.valueChanged.connect(self.line_width_changed)
        slider_layout.addWidget(self.line_width_slider)
        
        self.line_width_label = QLabel("1.0px")
        self.line_width_label.setMinimumWidth(40)
        self.line_width_label.setFont(self.create_font('label'))
        slider_layout.addWidget(self.line_width_label)
        
        line_width_layout.addLayout(slider_layout)
        line_width_group.setLayout(line_width_layout)
        layout.addWidget(line_width_group)

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
            selected_features.extend([col for col in self.df.columns if '(deg/s)' in col])
        
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
            selected_features.extend([col for col in self.df.columns if 'rccommand' in col.lower()])
        
        # Handle Throttle data
        if self.throttle_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if 'rccommand[3]' in col.lower()])
        
        # Handle Motor Outputs
        if self.motor_checkbox.isChecked():
            selected_features.extend([col for col in self.df.columns if col.lower().startswith('motor[')])
        
        return selected_features

    def update_legend(self, series_by_category):
        """Update legend items based on the series data"""
        # Clear existing legend items
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new legend items
        for clean_name, series in series_by_category.items():
            legend_label = QLabel()
            legend_label.setFont(self.create_font('label'))
            
            # Get color from COLOR_PALETTE or MOTOR_COLORS
            if clean_name.startswith('Motor'):
                # For motors, use the motor number to get a color
                motor_num = int(clean_name.split(' ')[1])
                color = QColor(*MOTOR_COLORS[motor_num % len(MOTOR_COLORS)])
            else:
                # For other data types, use the predefined colors
                color = QColor(*COLOR_PALETTE.get(clean_name, (128, 128, 128)))  # Default to gray if not found
            
            legend_label.setText(f"<span style='color: {color.name()}'>{clean_name}</span>")
            self.legend_layout.addWidget(legend_label)

    def line_width_changed(self, value):
        """Update line width for all series in all charts"""
        # Convert slider value to actual line width (divide by 2)
        line_width = value / 2.0
        
        # Get the parent FL1GHTViewer instance
        parent = self.parent()
        if parent and hasattr(parent, 'chart_manager'):
            for chart_view in parent.chart_manager.chart_views:
                if chart_view.chart():
                    for series in chart_view.chart().series():
                        pen = series.pen()
                        pen.setWidthF(line_width)  # Use setWidthF for floating point width
                        series.setPen(pen)
                    chart_view.chart().update()
        
        self.line_width_label.setText(f"{line_width:.1f}px")

class ControlWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(0, 0, 0, 0)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFont(self.create_font('label'))
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Zoom controls
        zoom_layout = QHBoxLayout()
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