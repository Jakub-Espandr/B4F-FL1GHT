"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import os
import subprocess
import pandas as pd
import glob
import tempfile
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy,
    QFileDialog, QTabWidget
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QMargins
from PySide6.QtCharts import QChart
from ui.widgets import FeatureSelectionWidget, ControlWidget, SpectralAnalyzerWidget
from .chart_manager import ChartManager
from utils.data_processor import normalize_time_data, get_clean_name, decimate_data
from utils.config import FONT_CONFIG

class FL1GHTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B4F: FL1GHT")
        self.setMinimumSize(400, 400)
        
        # Initialize components
        self.chart_manager = ChartManager()
        self.setup_ui()
        self.setup_connections()
        
        # Show fullscreen
        self.showFullScreen()

    def setup_ui(self):
        # Main layout
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Left side - Feature selection
        self.feature_widget = FeatureSelectionWidget()
        main_layout.addWidget(self.feature_widget, stretch=0)

        # Right side - Controls and charts
        right_widget = QWidget()
        right_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(self.create_font('tab'))
        self.tab_widget.setStyleSheet("""
            QTabBar::tab {
                background-color: #4a4a4a;
                color: white;
                padding: 6px 12px;
                border: 1px solid #555;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffa500;
                color: black;
            }
            QTabBar::tab:hover {
                background-color: #5a5a5a;
            }
        """)
        
        # Time domain tab
        time_domain_widget = QWidget()
        time_domain_layout = QVBoxLayout(time_domain_widget)
        time_domain_layout.setSpacing(10)
        time_domain_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add controls to time domain tab
        self.control_widget = ControlWidget()
        time_domain_layout.addWidget(self.control_widget)
        
        # Add charts to time domain tab
        min_chart_height = max((self.minimumHeight() - 200) // 2, 150)
        chart_views = self.chart_manager.create_chart_views(self, min_chart_height)
        for chart_view in chart_views:
            time_domain_layout.addWidget(chart_view, stretch=2)
        
        # Spectral analyzer tab
        self.spectral_widget = SpectralAnalyzerWidget(self.feature_widget)
        
        # Add tabs
        self.tab_widget.addTab(time_domain_widget, "Time Domain")
        self.tab_widget.addTab(self.spectral_widget, "Spectral Analysis")
        
        right_layout.addWidget(self.tab_widget)
        main_layout.addWidget(right_widget, stretch=1)

        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        # Set initial selection for time domain tab
        self.set_time_domain_defaults()

    def setup_connections(self):
        # Connect control widget signals
        self.feature_widget.select_button.clicked.connect(self.load_bbl)
        self.feature_widget.plot_button.clicked.connect(self.plot_selected)
        self.control_widget.zoom_slider.valueChanged.connect(self.zoom_slider_changed)
        self.control_widget.scroll_slider.valueChanged.connect(self.scroll_slider_changed)
        self.control_widget.reset_zoom_button.clicked.connect(self.reset_zoom)

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font

    def load_bbl(self):
        """Load a BBL file and convert it to CSV."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select BBL file",
            "",
            "BBL Files (*.bbl);;All Files (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            # Get the path to the blackbox decoder tool
            decoder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "blackbox_decode")
            
            # Run blackbox decoder with stdout output
            result = subprocess.run(
                [decoder_path, '--stdout', '--unit-rotation', 'deg/s', file_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                QMessageBox.critical(self, "Error", f"Failed to decode BBL file: {result.stderr}")
                return
                
            # Create a temporary file to store the CSV data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                temp_file.write(result.stdout)
                temp_file_path = temp_file.name
            
            # Load the CSV data
            self.df = pd.read_csv(temp_file_path)
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            # Strip leading/trailing spaces from all column names
            self.df.columns = self.df.columns.str.strip()
            
            if self.df.empty:
                QMessageBox.warning(self, "Warning", "No valid data found in the file")
                return
                
            # Find time column
            time_col = next((col for col in self.df.columns if 'time' in col.lower()), None)
            if time_col is None:
                QMessageBox.critical(self, "Error", "No time column found in the data")
                return
                
            # Rename time column to 'time' for consistency
            self.df = self.df.rename(columns={time_col: 'time'})
            
            # Normalize time data
            self.df['time'] = (self.df['time'] - self.df['time'].iloc[0]) / 1_000_000.0
            
            # Update actual time range
            self.actual_time_range = (self.df['time'].min(), self.df['time'].max())
            self.chart_manager.actual_time_max = float(self.df['time'].max())
            
            # Update feature widget with dataframe
            self.feature_widget.df = self.df
            
            # Update available features for spectral analysis
            # Exclude time column from available features
            # self.spectral_widget.update_inputs(available_features)  # No longer needed
            
            # Update spectral analysis after loading data
            self.spectral_widget.update_spectrum(self.df)
            
            QMessageBox.information(self, "Success", f"Successfully loaded: {os.path.basename(file_path)}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            return

    def plot_selected(self):
        if not hasattr(self, "df") or self.df.empty:
            QMessageBox.warning(self, "Warning", "Please load a data file first.")
            return

        # Only plot for the active tab
        current_tab = self.tab_widget.currentIndex()
        # 0 = Time Domain, 1 = Spectral Analysis
        if current_tab == 0:
            try:
                self.control_widget.progress_bar.setVisible(True)
                self.control_widget.progress_bar.setValue(0)
                # Existing time domain plotting code
                current_line_width = self.feature_widget.line_width_slider.value() / 2.0
                for chart_view in self.chart_manager.chart_views:
                    if chart_view.chart():
                        for series in chart_view.chart().series():
                            chart_view.chart().removeSeries(series)
                            series.deleteLater()
                        new_chart = QChart()
                        new_chart.setTitle(chart_view.chart().title())
                        new_chart.setAnimationOptions(QChart.NoAnimation)
                        new_chart.setTheme(QChart.ChartThemeLight)
                        new_chart.setMargins(QMargins(10, 10, 10, 10))
                        new_chart.legend().setVisible(False)
                        chart_view.setChart(new_chart)
                selected_features = self.feature_widget.get_selected_features()
                if not selected_features:
                    QMessageBox.warning(self, "Warning", "Please select at least one data column.")
                    return
                time_min = 0.0
                time_max = float(self.chart_manager.actual_time_max)
                margin = time_max * 0.02
                self.chart_manager.full_time_range = (time_min, time_max + margin)
                series_by_category = {}
                axis_names = ['Roll', 'Pitch', 'Yaw', 'Throttle']
                # --- Begin: Compute global min/max for Roll, Pitch, Yaw ---
                global_min = None
                global_max = None
                axis_feature_values = [[], [], []]  # For Roll, Pitch, Yaw
                for axis in range(3):
                    axis_features = [f for f in selected_features if f'[{axis}]' in f and not f.lower().startswith('motor[')]
                    for feature in axis_features:
                        if feature in self.df.columns:
                            _, value_data = decimate_data(
                                self.df['time'].values,
                                self.df[feature].values
                            )
                            axis_feature_values[axis].append(value_data)
                # Flatten and compute global min/max
                all_values = []
                for axis_vals in axis_feature_values:
                    for arr in axis_vals:
                        all_values.extend(arr)
                if all_values:
                    min_val = min(all_values)
                    max_val = max(all_values)
                    abs_max = max(abs(min_val), abs(max_val))
                    symmetric_min = -abs_max
                    symmetric_max = abs_max
                else:
                    symmetric_min = None
                    symmetric_max = None
                # --- End: Compute global min/max for Roll, Pitch, Yaw ---
                for axis in range(4):
                    if axis < 3:
                        axis_features = [f for f in selected_features if f'[{axis}]' in f and not f.lower().startswith('motor[')]
                    else:
                        axis_features = [f for f in selected_features if any(name in f.lower() for name in ['throttle', 'rc[3]', 'rc3', 'rc_command[3]', 'rccommand[3]'])]
                        axis_features += [f for f in selected_features if f.lower().startswith('motor[')]
                    if not axis_features:
                        continue
                    series_data = []
                    for feature in axis_features:
                        if feature in self.df.columns:
                            time_data, value_data = decimate_data(
                                self.df['time'].values,
                                self.df[feature].values
                            )
                            clean_name = get_clean_name(feature)
                            series_data.append({
                                'name': clean_name,
                                'time': time_data,
                                'values': value_data
                            })
                    if axis < 3:
                        self.chart_manager.update_chart(
                            self.chart_manager.chart_views[axis],
                            series_data,
                            time_min,
                            time_max,
                            symmetric_min,
                            symmetric_max,
                            line_width=current_line_width
                        )
                    else:
                        has_motors = any(f.lower().startswith('motor[') for f in axis_features)
                        has_throttle = any(name in f.lower() for f in axis_features for name in ['throttle', 'rc[3]', 'rc3', 'rc_command[3]', 'rccommand[3]'])
                        if has_motors and has_throttle:
                            y_range = (0, 2100)
                        elif has_motors:
                            y_range = (0, 2100)
                        else:
                            y_range = (995, 2005)
                        self.chart_manager.update_chart(
                            self.chart_manager.chart_views[axis],
                            series_data,
                            time_min,
                            time_max,
                            *y_range,
                            line_width=current_line_width
                        )
                    for data in series_data:
                        if data['name'] not in series_by_category:
                            series_by_category[data['name']] = self.chart_manager.chart_views[axis].chart().series()[-1]
                self.feature_widget.update_legend(series_by_category)
                self.control_widget.zoom_slider.setValue(0)
                self.control_widget.zoom_ratio_label.setText("1.0x")
                self.control_widget.progress_bar.setValue(100)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error during plotting:\n{e}")
            finally:
                self.control_widget.progress_bar.setVisible(False)
        elif current_tab == 1:
            # Only update the spectral analyzer
            self.spectral_widget.update_spectrum(self.df)

    def update_spectral_analysis(self):
        """Update the spectral analysis when inputs change"""
        if hasattr(self, 'df') and not self.df.empty:
            self.spectral_widget.update_spectrum(self.df)

    def zoom_slider_changed(self, value):
        # Calculate zoom factor
        if value <= 800:
            zoom_factor = 1.0 + (value / 800.0) * 9.0
        else:
            remaining = value - 800
            zoom_factor = 10.0 * (100.0 ** (remaining / 200.0))
        
        # Update zoom ratio label
        self.control_widget.zoom_ratio_label.setText(f"{zoom_factor:.1f}x")
        
        # Update charts
        self.chart_manager.update_zoom(
            zoom_factor,
            self.control_widget.scroll_slider.value() / 1000.0
        )
        
        # Ensure rounded 5-second increments when zoomed out to 1.0x
        if zoom_factor == 1.0:
            self.chart_manager.reset_zoom()

    def scroll_slider_changed(self, value):
        # Trigger a zoom update to apply the new scroll position
        self.zoom_slider_changed(self.control_widget.zoom_slider.value())

    def reset_zoom(self):
        self.chart_manager.reset_zoom()
        self.control_widget.zoom_slider.setValue(0)
        self.control_widget.zoom_ratio_label.setText("1.0x")
        self.control_widget.scroll_slider.setValue(500)

    def set_time_domain_defaults(self):
        # Select throttle and gyro filtered, deselect others
        self.feature_widget.throttle_checkbox.setChecked(True)
        self.feature_widget.gyro_scaled_checkbox.setChecked(True)
        self.feature_widget.gyro_unfilt_checkbox.setChecked(False)
        self.feature_widget.pid_p_checkbox.setChecked(False)
        self.feature_widget.pid_i_checkbox.setChecked(False)
        self.feature_widget.pid_d_checkbox.setChecked(False)
        self.feature_widget.setpoint_checkbox.setChecked(False)
        self.feature_widget.rc_checkbox.setChecked(False)
        self.feature_widget.motor_checkbox.setChecked(False)

    def set_spectral_defaults(self):
        # Select gyro filtered and gyro raw, deselect others
        self.feature_widget.throttle_checkbox.setChecked(False)
        self.feature_widget.gyro_scaled_checkbox.setChecked(True)
        self.feature_widget.gyro_unfilt_checkbox.setChecked(True)
        self.feature_widget.pid_p_checkbox.setChecked(False)
        self.feature_widget.pid_i_checkbox.setChecked(False)
        self.feature_widget.pid_d_checkbox.setChecked(False)
        self.feature_widget.setpoint_checkbox.setChecked(False)
        self.feature_widget.rc_checkbox.setChecked(False)
        self.feature_widget.motor_checkbox.setChecked(False)

    def on_tab_changed(self, index):
        # 0 = Time Domain, 1 = Spectral Analysis
        if index == 0:
            self.feature_widget.set_time_domain_mode(True)
            self.set_time_domain_defaults()
        else:
            self.feature_widget.set_time_domain_mode(False)
            self.set_spectral_defaults() 