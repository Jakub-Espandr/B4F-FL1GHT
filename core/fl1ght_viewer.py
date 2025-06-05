"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import os
import subprocess
import pandas as pd
import glob
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QSizePolicy,
    QFileDialog
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt, QMargins
from PySide6.QtCharts import QChart
from ui.widgets import FeatureSelectionWidget, ControlWidget
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

        # Add controls
        self.control_widget = ControlWidget()
        right_layout.addWidget(self.control_widget)

        # Add charts
        min_chart_height = max((self.minimumHeight() - 200) // 2, 150)
        chart_views = self.chart_manager.create_chart_views(self, min_chart_height)
        for chart_view in chart_views:
            right_layout.addWidget(chart_view, stretch=2)

        main_layout.addWidget(right_widget, stretch=1)

    def setup_connections(self):
        # Connect control widget signals
        self.feature_widget.select_button.clicked.connect(self.load_bbl)
        self.feature_widget.plot_button.clicked.connect(self.plot_selected)
        self.control_widget.zoom_slider.valueChanged.connect(self.zoom_slider_changed)
        self.control_widget.scroll_slider.valueChanged.connect(self.scroll_slider_changed)
        self.control_widget.reset_zoom_button.clicked.connect(self.reset_zoom)

    def load_bbl(self):
        bbl_path, _ = QFileDialog.getOpenFileName(
            self, "Select Blackbox log", "", "Blackbox log (*.bbl)"
        )
        if not bbl_path:
            return

        self.bbl_path = bbl_path
        self.bbl_dir = os.path.dirname(bbl_path)
        self.base = os.path.splitext(os.path.basename(bbl_path))[0]
        DECODER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "blackbox_decode")

        # Run decoder
        try:
            result = subprocess.run(
                [DECODER, "--unit-rotation", "deg/s", bbl_path],
                check=True,
                capture_output=True,
                text=True
            )
            if "failed to decode" in result.stdout or "failed to decode" in result.stderr:
                QMessageBox.warning(self, "Warning", 
                    "Some errors occurred during decoding. Data may be incomplete.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Decoding failed:\n{e}")
            return

        # Find CSV
        candidates = sorted(
            glob.glob(os.path.join(self.bbl_dir, self.base + "*.csv")),
            reverse=True
        )
        if not candidates:
            QMessageBox.critical(self, "Error", "CSV file not found.")
            return

        # If we have multiple files, prefer the main data file over GPS files
        if len(candidates) > 1:
            latest_time = max(os.stat(f).st_mtime for f in candidates)
            main_files = [f for f in candidates 
                         if 'gps' not in f.lower() 
                         and latest_time - os.stat(f).st_mtime < 1.0]
            if main_files:
                self.csv_path = sorted(main_files, key=lambda f: os.stat(f).st_size, reverse=True)[0]
            else:
                self.csv_path = candidates[0]
        else:
            self.csv_path = candidates[0]

        try:
            self.df = pd.read_csv(self.csv_path)
            if self.df.empty:
                QMessageBox.critical(self, "Error", "CSV file is empty.")
                return
                
            self.df.columns = self.df.columns.str.strip()
            
            # Find time column and convert to seconds
            self.time_col = next(
                (col for col in self.df.columns if "time" in col.lower()),
                self.df.columns[0]
            )
            
            # Normalize time data
            self.df = normalize_time_data(self.df, self.time_col)
            
            # Store the actual time range
            self.chart_manager.actual_time_max = float(self.df[self.time_col].max())
            
            # Update feature widget with dataframe
            self.feature_widget.df = self.df
            
            QMessageBox.information(self, "Done", f"Loaded: {os.path.basename(self.csv_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading CSV file:\n{e}")
            return

    def plot_selected(self):
        if not hasattr(self, "df") or self.df.empty:
            QMessageBox.warning(self, "Warning", "Please load a data file first.")
            return

        try:
            self.control_widget.progress_bar.setVisible(True)
            self.control_widget.progress_bar.setValue(0)
            
            # Get current line width from the feature widget
            current_line_width = self.feature_widget.line_width_slider.value() / 2.0
            
            # Clear all existing charts
            for chart_view in self.chart_manager.chart_views:
                if chart_view.chart():
                    # Remove all series from the chart
                    for series in chart_view.chart().series():
                        chart_view.chart().removeSeries(series)
                        series.deleteLater()
                    # Create a new empty chart
                    new_chart = QChart()
                    new_chart.setTitle(chart_view.chart().title())
                    new_chart.setAnimationOptions(QChart.NoAnimation)
                    new_chart.setTheme(QChart.ChartThemeLight)
                    new_chart.setMargins(QMargins(10, 10, 10, 10))
                    new_chart.legend().setVisible(False)
                    chart_view.setChart(new_chart)
            
            # Get selected features
            selected_features = self.feature_widget.get_selected_features()
            if not selected_features:
                QMessageBox.warning(self, "Warning", "Please select at least one data column.")
                return

            # Calculate time range
            time_min = 0.0
            time_max = float(self.chart_manager.actual_time_max)
            margin = time_max * 0.02
            self.chart_manager.full_time_range = (time_min, time_max + margin)
            
            # Create a dictionary to store series by category
            series_by_category = {}
            
            # Process each axis
            axis_names = ['Roll', 'Pitch', 'Yaw', 'Throttle']
            for axis in range(4):
                # Filter features for this axis
                if axis < 3:  # For Roll, Pitch, Yaw
                    axis_features = [f for f in selected_features if f'[{axis}]' in f and not f.lower().startswith('motor[')]
                else:  # For Throttle/Motors
                    axis_features = [f for f in selected_features if any(name in f.lower() for name in ['throttle', 'rc[3]', 'rc3', 'rc_command[3]', 'rccommand[3]'])]
                    axis_features += [f for f in selected_features if f.lower().startswith('motor[')]
                
                if not axis_features:
                    continue

                # Process data for this axis
                series_data = []
                for feature in axis_features:
                    if feature in self.df.columns:
                        time_data, value_data = decimate_data(
                            self.df[self.time_col].values,
                            self.df[feature].values
                        )
                        clean_name = get_clean_name(feature)
                        series_data.append({
                            'name': clean_name,
                            'time': time_data,
                            'values': value_data
                        })

                # Update chart
                if axis < 3:  # Roll, Pitch, Yaw
                    self.chart_manager.update_chart(
                        self.chart_manager.chart_views[axis],
                        series_data,
                        time_min,
                        time_max,
                        line_width=current_line_width  # Pass the current line width
                    )
                else:  # Throttle/Motors
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
                        line_width=current_line_width  # Pass the current line width
                    )

                # Store series for legend
                for data in series_data:
                    if data['name'] not in series_by_category:
                        series_by_category[data['name']] = self.chart_manager.chart_views[axis].chart().series()[-1]

            # Update legend
            self.feature_widget.update_legend(series_by_category)

            # Reset zoom to initial state
            self.control_widget.zoom_slider.setValue(0)
            self.control_widget.zoom_ratio_label.setText("1.0x")
            
            self.control_widget.progress_bar.setValue(100)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during plotting:\n{e}")
        finally:
            self.control_widget.progress_bar.setVisible(False)

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

    def scroll_slider_changed(self, value):
        # Trigger a zoom update to apply the new scroll position
        self.zoom_slider_changed(self.control_widget.zoom_slider.value())

    def reset_zoom(self):
        self.chart_manager.reset_zoom()
        self.control_widget.zoom_slider.setValue(0)
        self.control_widget.zoom_ratio_label.setText("1.0x")
        self.control_widget.scroll_slider.setValue(500) 