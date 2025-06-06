"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QCheckBox, QLabel, QMessageBox, QGroupBox, QScrollArea,
    QSlider, QProgressBar, QSizePolicy, QComboBox, QToolTip
)
from PySide6.QtGui import QFont, QColor, QPainter
from PySide6.QtCore import Qt, QMargins
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from utils.config import FONT_CONFIG, COLOR_PALETTE, MOTOR_COLORS
from utils.data_processor import get_clean_name
import numpy as np

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

    def notify_spectral_update(self, _):
        parent = self.parent()
        # Find the main viewer (FL1GHTViewer) in the parent chain
        while parent is not None and not hasattr(parent, 'spectral_widget'):
            parent = parent.parent() if hasattr(parent, 'parent') else None
        if parent and hasattr(parent, 'spectral_widget') and hasattr(parent, 'df'):
            parent.spectral_widget.update_spectrum(parent.df)

    def set_time_domain_mode(self, enabled: bool):
        # Enable throttle and motor outputs only in time domain mode
        self.throttle_checkbox.setEnabled(enabled)
        self.motor_checkbox.setEnabled(enabled)

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
        smoothing_group = QGroupBox("Smoothing Setup")
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
        smoothing_layout.addWidget(QLabel("Smoothing: Max"))
        smoothing_layout.addWidget(self.window_size_slider)
        smoothing_layout.addWidget(QLabel("Smoothing: Min"))
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

    def update_spectrum(self, df):
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
            chart_full.removeAllSeries()
            chart_zoom.removeAllSeries()
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
                    series_full.setName(label)
                    for f, p in zip(freqs, psd_db):
                        series_full.append(f, p)
                    pen = series_full.pen()
                    pen.setColor(color)
                    pen.setWidthF(1.5)
                    series_full.setPen(pen)
                    chart_full.addSeries(series_full)
                    # Zoomed series (0-100 Hz)
                    series_zoom = QLineSeries()
                    series_zoom.setName(label)
                    for f, p in zip(freqs, psd_db):
                        if f <= 100:
                            series_zoom.append(f, p)
                    pen_zoom = series_zoom.pen()
                    pen_zoom.setColor(color)
                    pen_zoom.setWidthF(1.5)
                    series_zoom.setPen(pen_zoom)
                    chart_zoom.addSeries(series_zoom)
                    series_list.append(series_full)
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
                axis_x.setLabelsFont(QFont("Arial", 8))
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
                axis_xz.setLabelsFont(QFont("Arial", 8))
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
            for t in selected_types:
                if t in plotted_types:
                    pattern, label, color = type_to_pattern[t]
                    legend_label = QLabel()
                    legend_label.setFont(self.create_font('label'))
                    legend_label.setText(f"<span style='color: {color.name()}'>{label}</span>")
                    legend_layout.addWidget(legend_label)

    def show_tooltip(self, event, chart_view):
        """Show tooltip with frequency and power spectral density values"""
        chart = chart_view.chart()
        if not chart:
            return

        # Convert mouse position to chart coordinates
        pos = chart_view.mapToScene(event.pos())
        chart_pos = chart.mapFromScene(pos)

        # Get axes
        axis_x = chart.axes(Qt.Horizontal)[0]
        axis_y = chart.axes(Qt.Vertical)[0]

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
        freq = x_min + (x_max - x_min) * (chart_pos.x() - left) / (right - left)
        psd = y_max - (y_max - y_min) * (chart_pos.y() - top) / (bottom - top)

        # Format tooltip text
        tooltip = f"Frequency: {freq:.1f} Hz\nPSD: {psd:.1f} dB/Hz"

        # Show tooltip
        QToolTip.showText(event.globalPos(), tooltip, chart_view) 