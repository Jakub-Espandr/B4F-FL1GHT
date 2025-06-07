"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import os
import subprocess
import pandas as pd
import glob
import tempfile
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy,
    QFileDialog, QTabWidget
)
from PySide6.QtGui import QFont, QPainter
from PySide6.QtCore import Qt, QMargins
from PySide6.QtCharts import QChart
from ui.widgets import FeatureSelectionWidget, ControlWidget, SpectralAnalyzerWidget, StepResponseWidget, FrequencyAnalyzerWidget, PlotExportWidget
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
        self.current_file = None
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
        
        # Step response tab
        self.step_response_widget = StepResponseWidget(self.feature_widget)
        
        # Frequency analyzer tab
        self.frequency_analyzer_widget = FrequencyAnalyzerWidget(self.feature_widget)
        
        # Export tab
        self.export_widget = PlotExportWidget()
        
        # Add tabs
        self.tab_widget.addTab(time_domain_widget, "Time Domain")
        self.tab_widget.addTab(self.spectral_widget, "Spectral Analysis")
        self.tab_widget.addTab(self.step_response_widget, "Step Response")
        self.tab_widget.addTab(self.frequency_analyzer_widget, "Frequency Analyzer")
        self.tab_widget.addTab(self.export_widget, "Export Plots")
        
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
            
        # Store the current file path
        self.current_file = file_path
        
        # --- NEW: Parse PID values from .bbl header ---
        pid_vals = {'roll': None, 'pitch': None, 'yaw': None}
        try:
            with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                for i, line in enumerate(f):
                    if 'rollPID:' in line:
                        pid_vals['roll'] = line.split('rollPID:')[1].strip().split()[0]
                    if 'pitchPID:' in line:
                        pid_vals['pitch'] = line.split('pitchPID:')[1].strip().split()[0]
                    if 'yawPID:' in line:
                        pid_vals['yaw'] = line.split('yawPID:')[1].strip().split()[0]
                    if i > 100:
                        break
            print(f"[DEBUG] Parsed PID values from .bbl: {pid_vals}")
        except Exception as e:
            print(f"[DEBUG] Could not parse PID from .bbl: {e}")
        
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

            # DEBUG: Print the first 20 lines of the CSV (header)
            print("[DEBUG] First 20 lines of CSV header:")
            with open(temp_file_path, 'r') as f:
                for i, line in enumerate(f):
                    print(line.strip())
                    if i >= 19:
                        break

            # Load the CSV data
            self.df = pd.read_csv(temp_file_path)

            # Inject PID values as columns if found
            if pid_vals['roll']:
                self.df['rollPID'] = pid_vals['roll']
            if pid_vals['pitch']:
                self.df['pitchPID'] = pid_vals['pitch']
            if pid_vals['yaw']:
                self.df['yawPID'] = pid_vals['yaw']
            
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
            
            # Update spectral analysis after loading data
            self.spectral_widget.update_spectrum(self.df)
            
            # Clear existing frequency analyzer plots but don't update with new data
            # Let user click "Show Plot" button instead
            self.frequency_analyzer_widget.clear_all_plots()
            
            # If we're on the Time Domain tab, update the plot
            if self.tab_widget.currentIndex() == 0:
                self.plot_selected()
            
            QMessageBox.information(self, "Success", f"Successfully loaded: {os.path.basename(file_path)}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
            return

    def plot_selected(self):
        if not hasattr(self, 'df') or self.df is None:
            QMessageBox.warning(self, "Warning", "Please load a data file first.")
            return

        # Only plot for the active tab
        current_tab = self.tab_widget.currentIndex()
        # 0 = Time Domain, 1 = Spectral Analysis, 2 = Step Response, 3 = Frequency Analyzer
        if current_tab == 0:
            try:
                self.control_widget.progress_bar.setVisible(True)
                self.control_widget.progress_bar.setValue(0)
                
                # Get selected features from the feature widget
                selected_features = self.feature_widget.get_selected_features()
                if not selected_features:
                    QMessageBox.warning(self, "Warning", "Please select at least one feature to plot.")
                    self.control_widget.progress_bar.setVisible(False)
                    return
                
                # Get the current line width from feature widget
                line_width = getattr(self.feature_widget, 'current_line_width', 1.0)
                
                # Plot selected features with the current line width
                self.chart_manager.plot_features(self.df, selected_features, self.control_widget.progress_bar, line_width=line_width)
                self.control_widget.progress_bar.setValue(100)
                self.control_widget.progress_bar.setVisible(False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to plot data: {str(e)}")
                self.control_widget.progress_bar.setVisible(False)
        elif current_tab == 1:
            # Spectral analysis tab
            self.update_spectral_analysis()
        elif current_tab == 2:
            # Step response tab
            # Update step response analysis
            line_width = getattr(self.feature_widget, 'current_line_width', 1.0)
            self.step_response_widget.update_step_response(self.df, line_width=line_width)
        elif current_tab == 3:
            # Frequency analyzer tab
            try:
                # Calculate the Nyquist frequency (half of the sampling rate)
                time_data = self.df['time'].values.astype(float)
                if time_data.max() > 1e6:
                    time_data = time_data / 1_000_000.0
                elif time_data.max() > 1e3:
                    time_data = time_data / 1_000.0
                time_data = time_data - time_data.min()
                
                # Calculate sampling rate and Nyquist frequency
                dt = np.mean(np.diff(time_data))
                fs = 1.0 / dt if dt > 0 else 0.0
                nyquist_freq = fs / 2.0
                
                # Round up to the nearest 50Hz for cleaner display
                max_freq = int(min(1000, nyquist_freq))
                if max_freq % 50 != 0:
                    max_freq = ((max_freq // 50) + 1) * 50
                
                # Force a complete refresh of the plots
                self.frequency_analyzer_widget.clear_all_plots()
                # Update with new data, using the calculated max frequency
                self.frequency_analyzer_widget.update_frequency_plots(self.df, max_freq=max_freq)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update frequency plots: {str(e)}")

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

    def set_step_response_defaults(self):
        # Select gyro filtered and RC command for step response analysis
        self.feature_widget.throttle_checkbox.setChecked(False)
        self.feature_widget.gyro_scaled_checkbox.setChecked(True)
        self.feature_widget.gyro_unfilt_checkbox.setChecked(False)
        self.feature_widget.pid_p_checkbox.setChecked(False)
        self.feature_widget.pid_i_checkbox.setChecked(False)
        self.feature_widget.pid_d_checkbox.setChecked(False)
        self.feature_widget.setpoint_checkbox.setChecked(False)
        self.feature_widget.rc_checkbox.setChecked(True)
        self.feature_widget.motor_checkbox.setChecked(False)

    def set_frequency_analyzer_defaults(self):
        # Select gyro filtered and unfiltered for frequency analysis
        if hasattr(self.feature_widget, 'gyro_unfilt_checkbox'):
            self.feature_widget.gyro_unfilt_checkbox.setChecked(True)
        if hasattr(self.feature_widget, 'gyro_scaled_checkbox'):
            self.feature_widget.gyro_scaled_checkbox.setChecked(True)
        if hasattr(self.feature_widget, 'pid_p_checkbox'):
            self.feature_widget.pid_p_checkbox.setChecked(False)
        if hasattr(self.feature_widget, 'pid_i_checkbox'):
            self.feature_widget.pid_i_checkbox.setChecked(False)
        if hasattr(self.feature_widget, 'pid_d_checkbox'):
            self.feature_widget.pid_d_checkbox.setChecked(False)
        if hasattr(self.feature_widget, 'setpoint_checkbox'):
            self.feature_widget.setpoint_checkbox.setChecked(False)
        if hasattr(self.feature_widget, 'rc_checkbox'):
            self.feature_widget.rc_checkbox.setChecked(False)
        if hasattr(self.feature_widget, 'throttle_checkbox'):
            self.feature_widget.throttle_checkbox.setChecked(True)

    def on_tab_changed(self, index):
        # 0 = Time Domain, 1 = Spectral Analysis, 2 = Step Response, 3 = Frequency Analyzer, 4 = Export
        
        # Store previous tab index when switching to export tab
        if index == 4:  # Export tab
            # Store the previous tab index (we need to look at the previously active tab)
            previous_index = getattr(self, '_previous_tab_index', 0)
            # Set it in the export widget
            if hasattr(self, 'export_widget'):
                self.export_widget.set_previous_tab(previous_index)
                self.export_widget.export_plots()
            return
        
        # Remember the current tab index for the next tab change
        self._previous_tab_index = index
        
        if index == 0:
            self.set_time_domain_defaults()
            self.feature_widget.set_time_domain_mode(True)
            self.feature_widget.legend_group.setVisible(True)
            # Update plot for time domain if we have data
            if hasattr(self, 'df') and self.df is not None:
                self.plot_selected()
        elif index == 1:
            self.set_spectral_defaults()
            self.feature_widget.set_time_domain_mode(True)
            self.feature_widget.throttle_checkbox.setEnabled(False)
            self.feature_widget.motor_checkbox.setEnabled(False)
            self.feature_widget.legend_group.setVisible(True)
        elif index == 2:
            self.set_step_response_defaults()
            self.feature_widget.set_time_domain_mode(False)
            self.feature_widget.legend_group.setVisible(False)
        elif index == 3:
            self.set_frequency_analyzer_defaults()
            self.feature_widget.set_time_domain_mode(False)
            self.feature_widget.legend_group.setVisible(False)
            # No longer auto-update frequency analyzer plots
            # Let user click "Show Plot" button instead 