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
    QFileDialog, QTabWidget, QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QLabel
)
from PySide6.QtGui import QFont, QPainter
from PySide6.QtCore import Qt, QMargins
from PySide6.QtCharts import QChart
from ui.widgets import FeatureSelectionWidget, ControlWidget, SpectralAnalyzerWidget, StepResponseWidget, FrequencyAnalyzerWidget, PlotExportWidget, ParametersWidget, SpectrogramWidget, ErrorPerformanceWidget
from .chart_manager import ChartManager
from utils.data_processor import normalize_time_data, get_clean_name, decimate_data
from utils.config import FONT_CONFIG

class FL1GHTViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("B4F: FL1GHT")
        self.setMinimumSize(400, 400)
        self.previous_tab_index = 0  # Track previous tab index
        self.expanded_chart = None
        
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
            chart_view.clicked.connect(lambda cv=chart_view: self.on_chart_clicked(cv))
        
        # Spectral analyzer tab
        self.spectral_widget = SpectralAnalyzerWidget(self.feature_widget)
        
        # Step response tab
        self.step_response_widget = StepResponseWidget(self.feature_widget)
        
        # Noise analysis tab
        self.frequency_analyzer_widget = FrequencyAnalyzerWidget(self.feature_widget)
        
        # Frequency Evolution tab
        self.spectrogram_widget = SpectrogramWidget(self.feature_widget)
        
        # Drone Config tab
        self.parameters_widget = ParametersWidget(self.feature_widget)
        
        # Error & Performance Analysis tab
        self.error_performance_widget = ErrorPerformanceWidget(self.feature_widget)
        
        # Export tab
        self.export_widget = PlotExportWidget()
        
        # Add tabs
        self.tab_widget.addTab(time_domain_widget, "Time Domain")
        self.tab_widget.addTab(self.spectral_widget, "Frequency Domain")
        self.tab_widget.addTab(self.step_response_widget, "Step Response")
        self.tab_widget.addTab(self.frequency_analyzer_widget, "Noise Analysis")
        self.tab_widget.addTab(self.spectrogram_widget, "Frequency Evolution")
        self.tab_widget.addTab(self.error_performance_widget, "Error && Performance")
        self.tab_widget.addTab(self.parameters_widget, "Drone Config")
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

    def on_chart_clicked(self, clicked_chart_view):
        """Handle chart click to expand or restore."""
        # If the clicked chart is already expanded, restore all
        if self.expanded_chart is clicked_chart_view:
            for chart_view in self.chart_manager.chart_views:
                chart_view.show()
            self.expanded_chart = None
        else:
            # If another chart is expanded, or no chart is expanded
            for chart_view in self.chart_manager.chart_views:
                if chart_view is not clicked_chart_view:
                    chart_view.hide()
                else:
                    chart_view.show() # Ensure the clicked one is visible.
            self.expanded_chart = clicked_chart_view

    def create_font(self, font_type):
        font = QFont(FONT_CONFIG[font_type]['family'])
        font.setPointSize(FONT_CONFIG[font_type]['size'])
        if FONT_CONFIG[font_type]['weight'] == 'bold':
            font.setBold(True)
        return font

    def extract_flights_from_error(self, error_text):
        """Extract flight information from the error output of blackbox_decode."""
        flights = []
        lines = error_text.split('\n')
        in_table = False
        
        if getattr(self.feature_widget, 'debug_verbose', False):
            print(f"[DEBUG] Extracting flights from error output")
        
        for line in lines:
            line = line.strip()
            if "Index" in line and "Start offset" in line and "Size" in line:
                in_table = True
                if getattr(self.feature_widget, 'debug_verbose', False):
                    print(f"[DEBUG] Found table header: {line}")
                continue
            
            if in_table and line and line[0].isdigit():
                if getattr(self.feature_widget, 'debug_verbose', False):
                    print(f"[DEBUG] Parsing flight line: {line}")
                parts = line.split()
                if len(parts) >= 3:  # At least index, offset, and size
                    try:
                        index = int(parts[0])
                        start_offset = int(parts[1])
                        size = int(parts[2])
                        flights.append({
                            'index': index,
                            'start_offset': start_offset,
                            'size': size
                        })
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Added flight: index={index}, size={size}")
                    except (ValueError, IndexError) as e:
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Failed to parse flight line: {e}")
                        continue
        
        if getattr(self.feature_widget, 'debug_verbose', False):
            print(f"[DEBUG] Found {len(flights)} flights")
        return flights if flights else None

    def estimate_flight_duration(self, flight_size):
        """Estimate flight duration in minutes based on flight data size.
        
        This is an approximation - blackbox logs around 2MB per minute depending on 
        logging rate and enabled features.
        """
        # Typical logging rates: ~2MB per minute at 2K logging rate
        # Adjust this value based on your logging configuration
        bytes_per_minute = 2 * 1024 * 1024  # 2MB per minute
        
        # Convert bytes to minutes
        minutes = flight_size / bytes_per_minute
        
        # If less than a minute, show seconds
        if minutes < 1:
            seconds = int(minutes * 60)
            return f"{seconds} sec"
        
        # If it's a longer flight, show minutes and seconds
        minutes_int = int(minutes)
        seconds = int((minutes - minutes_int) * 60)
        
        if seconds > 0:
            return f"{minutes_int}:{seconds:02d} min"
        else:
            return f"{minutes_int} min"

    def show_flight_selection_dialog(self, filename, flights):
        """Show a dialog to select which flight to load and return the selected index."""
        if not flights:
            return None
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Flight Log")
        dialog.setMinimumWidth(600)
        dialog.setMinimumHeight(400)
        
        # Set fccTYPO font for the dialog
        font = QFont("fccTYPO")
        font.setPointSize(14)
        dialog.setFont(font)
        
        layout = QVBoxLayout(dialog)
        
        # Add label with larger font
        header_font = QFont("fccTYPO")
        header_font.setPointSize(18)
        
        # Check which tab we're in
        current_tab = self.tab_widget.currentIndex()
        is_spectral = current_tab == 1
        is_step_response = current_tab == 2
        
        # Set max selection based on tab
        if is_spectral:
            max_selection = 2
            selection_text = "flights"
            tab_note = "frequency domain"
        elif is_step_response:
            max_selection = 5
            selection_text = "flights"
            tab_note = "step response"
        else:
            max_selection = len(flights)
            selection_text = "flight(s)" if max_selection > 1 else "flight"
            tab_note = None
        
        label = QLabel(f"File '{filename}' contains {len(flights)} flight logs.\nPlease select which {selection_text} to load:")
        if tab_note:
            label.setText(label.text() + f"\n(Note: Maximum {max_selection} flights can be selected for {tab_note}.")
        label.setFont(header_font)
        layout.addWidget(label)
        
        # Create list widget with multiple selection
        list_widget = QListWidget()
        list_widget.setFont(font)
        list_widget.setSelectionMode(QListWidget.MultiSelection)  # Allow multiple selection
        for flight in flights:
            # Calculate approximate duration
            duration = self.estimate_flight_duration(flight['size'])
            size_mb = flight['size'] / (1024 * 1024)  # Convert to MB
            
            # Create item with duration and size information
            item = QListWidgetItem(f"Flight {flight['index']} - Duration: {duration} (Size: {size_mb:.1f} MB)")
            item.setData(Qt.UserRole, flight['index'])
            list_widget.addItem(item)
        
        # Select the first item by default
        if list_widget.count() > 0:
            list_widget.setCurrentRow(0)
        
        # Add selection change handler for frequency domain or step response
        if is_spectral or is_step_response:
            def on_selection_changed():
                selected = list_widget.selectedItems()
                if len(selected) > max_selection:
                    # Uncheck the last selected item
                    selected[-1].setSelected(False)
                    QMessageBox.warning(dialog, "Warning", f"You can only select up to {max_selection} flights for {tab_note}.")
            list_widget.itemSelectionChanged.connect(on_selection_changed)
        
        layout.addWidget(list_widget)
        
        # Add buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        button_box.setFont(font)
        
        # Create custom LOAD button
        load_button = button_box.addButton("LOAD", QDialogButtonBox.AcceptRole)
        load_button.setStyleSheet("""
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
        
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        # Show dialog and get selected indices
        result = dialog.exec()
        if getattr(self.feature_widget, 'debug_verbose', False):
            print(f"[DEBUG] Dialog result: {result}")
        
        if result == QDialog.Accepted and list_widget.selectedItems():
            selected_indices = [item.data(Qt.UserRole) for item in list_widget.selectedItems()]
            if (is_spectral or is_step_response) and len(selected_indices) > max_selection:
                selected_indices = selected_indices[:max_selection]  # Take only first N selections
            if getattr(self.feature_widget, 'debug_verbose', False):
                print(f"[DEBUG] Selected flight indices: {selected_indices}")
            return selected_indices
        
        return None

    def load_bbl(self):
        """Load BBL file(s) and convert to CSV."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select BBL file(s)",
            "",
            "BBL Files (*.bbl);;All Files (*.*)"
        )
        
        if not file_paths:
            return
        
        files_loaded = 0
        
        for file_path in file_paths:
            try:
                # Get the filename for display
                filename = os.path.basename(file_path)
                base_filename = os.path.splitext(filename)[0]
                
                if getattr(self.feature_widget, 'debug_verbose', False):
                    print(f"[DEBUG] Processing file: {filename}")
                
                # Check if this log is already loaded
                if filename in self.feature_widget.loaded_logs:
                    QMessageBox.information(self, "Info", f"Log '{filename}' is already loaded.")
                    continue
                
                # Parse PID values from the BBL header
                pid_vals = {'roll': None, 'pitch': None, 'yaw': None}
                ff_weights = {'roll': None, 'pitch': None, 'yaw': None}
                d_min_vals = {'roll': None, 'pitch': None, 'yaw': None}
                try:
                    with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Reading BBL header from {filename}")
                        for i, line in enumerate(f):
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Line {i}: {line.strip()}")  # Debug print
                            if 'rollPID:' in line:
                                pid_vals['roll'] = line.split('rollPID:')[1].strip().split()[0]
                            if 'pitchPID:' in line:
                                pid_vals['pitch'] = line.split('pitchPID:')[1].strip().split()[0]
                            if 'yawPID:' in line:
                                pid_vals['yaw'] = line.split('yawPID:')[1].strip().split()[0]
                            if 'ff_weight:' in line:
                                weights = line.split('ff_weight:')[1].strip().split(',')
                                ff_weights['roll'] = weights[0]
                                ff_weights['pitch'] = weights[1]
                                ff_weights['yaw'] = weights[2]
                            if 'd_min:' in line:
                                dmins = line.split('d_min:')[1].strip().split(',')
                                d_min_vals['roll'] = dmins[0]
                                d_min_vals['pitch'] = dmins[1]
                                d_min_vals['yaw'] = dmins[2]
                            if i > 100:  # Only read first 100 lines of header
                                break
                except Exception as e:
                    if getattr(self.feature_widget, 'debug_verbose', False):
                        print(f"[DEBUG] Could not parse PID from .bbl: {e}")
                
                # Get the path to the blackbox decoder tool
                decoder_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "blackbox_decode")
                
                # First try to run the decoder without an index to see if it contains multiple flights
                initial_cmd = [decoder_path, '--stdout', '--unit-rotation', 'deg/s', file_path]
                if getattr(self.feature_widget, 'debug_verbose', False):
                    print(f"[DEBUG] Running initial decoder command: {' '.join(initial_cmd)}")
                
                initial_result = subprocess.run(
                    initial_cmd,
                    capture_output=True,
                    text=True
                )
                
                selected_indices = None
                display_filename = filename
                
                # Check if this is a multi-flight file
                if initial_result.returncode != 0 and "This file contains multiple flight logs" in initial_result.stderr:
                    if getattr(self.feature_widget, 'debug_verbose', False):
                        print(f"[DEBUG] Multiple flights detected in error output")
                    
                    # Extract flight information from the error output
                    flights = self.extract_flights_from_error(initial_result.stderr)
                    
                    if not flights:
                        QMessageBox.warning(self, "Warning", 
                            "Multiple flights detected but couldn't parse flight information. Please try again.")
                        continue
                    
                    # Show dialog to select which flight(s) to load
                    selected_indices = self.show_flight_selection_dialog(filename, flights)
                    
                    if not selected_indices:
                        # User canceled, skip this file
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] User canceled flight selection")
                        continue
                    
                    # Process each selected flight
                    for selected_index in selected_indices:
                        # Update filename to include the selected index
                        display_filename = f"{base_filename}[{selected_index}]"
                        
                        # Check if this log is already loaded
                        if display_filename in self.feature_widget.loaded_logs:
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Flight {display_filename} already loaded, skipping")
                            continue
                        
                        # Now run the decoder with the selected index
                        decoder_cmd = [decoder_path, '--stdout', '--unit-rotation', 'deg/s', '--index', str(selected_index), file_path]
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Running decoder with index {selected_index}: {' '.join(decoder_cmd)}")
                        
                        result = subprocess.run(
                            decoder_cmd,
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode != 0:
                            error_msg = result.stderr.strip()
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Decoder error with index: {error_msg}")
                            QMessageBox.critical(self, "Error", f"Failed to decode BBL file with index {selected_index}: {error_msg}")
                            continue
                        
                        if not result.stdout.strip():
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] No output from decoder with index")
                            QMessageBox.warning(self, "Warning", f"No data was decoded from flight {selected_index}")
                            continue
                        
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Successfully decoded flight {selected_index}")
                        stdout_data = result.stdout
                        
                        # Create a temporary file to store the CSV data
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                            temp_file.write(stdout_data)
                            temp_file_path = temp_file.name
                        
                        try:
                            # Load the CSV data
                            df = pd.read_csv(temp_file_path)
                            
                            # Inject PID values as columns if found
                            if pid_vals['roll']:
                                df['rollPID'] = pid_vals['roll']
                            if pid_vals['pitch']:
                                df['pitchPID'] = pid_vals['pitch']
                            if pid_vals['yaw']:
                                df['yawPID'] = pid_vals['yaw']
                            # Inject feed forward weights
                            if ff_weights['roll']:
                                df['rollFF'] = int(ff_weights['roll'])
                            if ff_weights['pitch']:
                                df['pitchFF'] = int(ff_weights['pitch'])
                            if ff_weights['yaw']:
                                df['yawFF'] = int(ff_weights['yaw'])
                            # Inject d_min values
                            if d_min_vals['roll']:
                                df['rollDMin'] = int(d_min_vals['roll'])
                            if d_min_vals['pitch']:
                                df['pitchDMin'] = int(d_min_vals['pitch'])
                            if d_min_vals['yaw']:
                                df['yawDMin'] = int(d_min_vals['yaw'])
                            
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Added feed forward weights to DataFrame: roll={ff_weights['roll']}, pitch={ff_weights['pitch']}, yaw={ff_weights['yaw']}")
                                print(f"[DEBUG] Added d_min to DataFrame: roll={d_min_vals['roll']}, pitch={d_min_vals['pitch']}, yaw={d_min_vals['yaw']}")
                            
                            # Strip leading/trailing spaces from all column names
                            df.columns = df.columns.str.strip()
                            
                            if df.empty:
                                if getattr(self.feature_widget, 'debug_verbose', False):
                                    print(f"[DEBUG] DataFrame is empty")
                                QMessageBox.warning(self, "Warning", f"No valid data found in flight {selected_index}")
                                continue
                            
                            # Find time column
                            time_col = next((col for col in df.columns if 'time' in col.lower()), None)
                            if time_col is None:
                                if getattr(self.feature_widget, 'debug_verbose', False):
                                    print(f"[DEBUG] No time column found")
                                QMessageBox.critical(self, "Error", f"No time column found in flight {selected_index}")
                                continue
                            
                            # Rename time column to 'time' for consistency
                            df = df.rename(columns={time_col: 'time'})
                            
                            # Normalize time data
                            df['time'] = (df['time'] - df['time'].iloc[0]) / 1_000_000.0
                            
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Adding flight to loaded_logs as {display_filename}")
                            
                            # Store the dataframe in the loaded_logs dictionary
                            self.feature_widget.loaded_logs[display_filename] = df
                            # Store the .bbl file path for this log
                            self.feature_widget.loaded_log_paths[display_filename] = file_path
                            
                            # Add the filename to the logs list and combo box
                            self.feature_widget.logs_list.addItem(display_filename)
                            self.feature_widget.logs_combo.addItem(display_filename)
                            
                            # If this is the first log, select it automatically
                            if len(self.feature_widget.loaded_logs) == 1:
                                self.feature_widget.logs_list.setCurrentRow(0)
                                self.feature_widget.logs_combo.setCurrentIndex(0)
                                self.feature_widget.current_log = df
                                self.df = df
                                self.feature_widget.df = df
                                
                                # Update actual time range
                                self.actual_time_range = (df['time'].min(), df['time'].max())
                                self.chart_manager.actual_time_max = float(df['time'].max())
                                
                                # Clear existing noise analysis plots but don't update with new data
                                self.frequency_analyzer_widget.clear_all_plots()
                            
                            files_loaded += 1
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Successfully loaded flight {display_filename}")
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_file_path)
                            except Exception as e:
                                if getattr(self.feature_widget, 'debug_verbose', False):
                                    print(f"[DEBUG] Failed to clean up temp file: {e}")
                else:
                    # This is a single flight file or the decoder succeeded
                    if initial_result.returncode != 0:
                        # Decoder failed for a reason other than multiple flights
                        error_msg = initial_result.stderr.strip()
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Decoder error: {error_msg}")
                        QMessageBox.critical(self, "Error", f"Failed to decode BBL file {filename}: {error_msg}")
                        continue
                    
                    # Use the output from the initial run
                    stdout_data = initial_result.stdout
                    
                    if not stdout_data.strip():
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] No output from decoder")
                        QMessageBox.warning(self, "Warning", f"No data was decoded from file {filename}")
                        continue
                    
                    if getattr(self.feature_widget, 'debug_verbose', False):
                        print(f"[DEBUG] Successfully decoded single flight")
                    
                    # Create a temporary file to store the CSV data
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
                        temp_file.write(stdout_data)
                        temp_file_path = temp_file.name
                    
                    try:
                        # Load the CSV data
                        df = pd.read_csv(temp_file_path)
                        
                        # Inject PID values as columns if found
                        if pid_vals['roll']:
                            df['rollPID'] = pid_vals['roll']
                        if pid_vals['pitch']:
                            df['pitchPID'] = pid_vals['pitch']
                        if pid_vals['yaw']:
                            df['yawPID'] = pid_vals['yaw']
                        # Inject feed forward weights
                        if ff_weights['roll']:
                            df['rollFF'] = int(ff_weights['roll'])
                        if ff_weights['pitch']:
                            df['pitchFF'] = int(ff_weights['pitch'])
                        if ff_weights['yaw']:
                            df['yawFF'] = int(ff_weights['yaw'])
                        # Inject d_min values
                        if d_min_vals['roll']:
                            df['rollDMin'] = int(d_min_vals['roll'])
                        if d_min_vals['pitch']:
                            df['pitchDMin'] = int(d_min_vals['pitch'])
                        if d_min_vals['yaw']:
                            df['yawDMin'] = int(d_min_vals['yaw'])
                        
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Added feed forward weights to DataFrame: roll={ff_weights['roll']}, pitch={ff_weights['pitch']}, yaw={ff_weights['yaw']}")
                            print(f"[DEBUG] Added d_min to DataFrame: roll={d_min_vals['roll']}, pitch={d_min_vals['pitch']}, yaw={d_min_vals['yaw']}")
                        
                        # Strip leading/trailing spaces from all column names
                        df.columns = df.columns.str.strip()
                        
                        if df.empty:
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] DataFrame is empty")
                            QMessageBox.warning(self, "Warning", f"No valid data found in file {filename}")
                            continue
                        
                        # Find time column
                        time_col = next((col for col in df.columns if 'time' in col.lower()), None)
                        if time_col is None:
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] No time column found")
                            QMessageBox.critical(self, "Error", f"No time column found in file {filename}")
                            continue
                        
                        # Rename time column to 'time' for consistency
                        df = df.rename(columns={time_col: 'time'})
                        
                        # Normalize time data
                        df['time'] = (df['time'] - df['time'].iloc[0]) / 1_000_000.0
                        
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Adding flight to loaded_logs as {filename}")
                        
                        # Store the dataframe in the loaded_logs dictionary
                        self.feature_widget.loaded_logs[filename] = df
                        # Store the .bbl file path for this log
                        self.feature_widget.loaded_log_paths[filename] = file_path
                        
                        # Add the filename to the logs list and combo box
                        self.feature_widget.logs_list.addItem(filename)
                        self.feature_widget.logs_combo.addItem(filename)
                        
                        # If this is the first log, select it automatically
                        if len(self.feature_widget.loaded_logs) == 1:
                            self.feature_widget.logs_list.setCurrentRow(0)
                            self.feature_widget.logs_combo.setCurrentIndex(0)
                            self.feature_widget.current_log = df
                            self.df = df
                            self.feature_widget.df = df
                            
                            # Update actual time range
                            self.actual_time_range = (df['time'].min(), df['time'].max())
                            self.chart_manager.actual_time_max = float(df['time'].max())
                            
                            # Clear existing noise analysis plots but don't update with new data
                            self.frequency_analyzer_widget.clear_all_plots()
                        
                        files_loaded += 1
                        if getattr(self.feature_widget, 'debug_verbose', False):
                            print(f"[DEBUG] Successfully loaded flight {filename}")
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_file_path)
                        except Exception as e:
                            if getattr(self.feature_widget, 'debug_verbose', False):
                                print(f"[DEBUG] Failed to clean up temp file: {e}")
                
            except Exception as e:
                if getattr(self.feature_widget, 'debug_verbose', False):
                    print(f"[DEBUG] Error loading file: {e}")
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
                continue
        
        if files_loaded > 0:
            QMessageBox.information(self, "Success", f"Successfully loaded {files_loaded} file(s)")

    def plot_selected(self):
        """Unified method for plotting one or multiple logs"""
        # Check if we have logs selected in the list widget
        if hasattr(self.feature_widget, 'selected_logs') and self.feature_widget.selected_logs:
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 1:  # Frequency Domain
                # Always clear the spectrum plot before plotting
                for (chart_view_full, chart_view_zoom) in self.spectral_widget.chart_views:
                    chart_view_full.chart().removeAllSeries()
                    chart_view_zoom.chart().removeAllSeries()
                # If multiple logs are selected, plot all
                if len(self.feature_widget.selected_logs) > 1:
                    self.plot_multiple_logs_spectral()
                    return
                # If only one log is selected, plot just that one
                elif len(self.feature_widget.selected_logs) == 1:
                    log_name = self.feature_widget.selected_logs[0]
                    self.feature_widget.current_log = self.feature_widget.loaded_logs[log_name]
                    self.spectral_widget.update_spectrum(self.feature_widget.current_log, log_label=log_name)
                    return
            if current_tab == 2:
                # Step Response tab: multi-log plotting
                if len(self.feature_widget.selected_logs) > 1:
                    self.plot_multiple_logs_step_response()
                    return
            # For Time Domain tab, only allow single log
            if current_tab == 0:
                if len(self.feature_widget.selected_logs) > 1:
                    QMessageBox.information(self, "Info", "Only one log can be plotted at a time in the Time Domain tab.")
                    return
            # If only one log is selected
            if len(self.feature_widget.selected_logs) == 1:
                log_name = self.feature_widget.selected_logs[0]
                self.feature_widget.current_log = self.feature_widget.loaded_logs[log_name]
                # Update drone config tab if it's active
                if current_tab == 5:  # Drone Config tab (changed from 4 to 5)
                    self.parameters_widget.update_parameters([log_name])
        # Check if we have a current log
        if not hasattr(self.feature_widget, 'current_log') or self.feature_widget.current_log is None:
            QMessageBox.warning(self, "Warning", "Please select a log first.")
            return
        # Only plot for the active tab
        current_tab = self.tab_widget.currentIndex()
        # 0 = Time Domain, 1 = Frequency Domain, 2 = Step Response, 3 = Noise Analysis, 4 = Frequency Evolution, 5 = Drone Config, 6 = Export
        if current_tab == 0:
            try:
                self.control_widget.progress_bar.setVisible(True)
                # Check for missing features and show warnings
                self.feature_widget.check_missing_features()
                # Get selected features from the feature widget
                selected_features = self.feature_widget.get_selected_features()
                if not selected_features:
                    QMessageBox.warning(self, "Warning", "Please select at least one feature to plot.")
                    self.control_widget.progress_bar.setVisible(False)
                    return
                # Get the current line width from feature widget
                line_width = getattr(self.feature_widget, 'current_line_width', 1.0)
                # Plot selected features with the current line width
                series_by_category = self.chart_manager.plot_features(self.feature_widget.current_log, selected_features, self.control_widget.progress_bar, line_width=line_width)
                # Update the legend with the new series
                if series_by_category:
                    self.feature_widget.update_legend(series_by_category)
                self.control_widget.progress_bar.setValue(100)
                self.control_widget.progress_bar.setVisible(False)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to plot data: {str(e)}")
                self.control_widget.progress_bar.setVisible(False)
        elif current_tab == 1:
            # Check for missing features and show warnings
            self.feature_widget.check_missing_features()
            # Set spectral defaults to select gyro (raw) and gyro (filtered)
            self.set_spectral_defaults()
            # Enable checkboxes for frequency domain except motors and throttle
            # Enforce 2-log limit for frequency domain
            self.feature_widget._set_checkboxes_enabled(True)
            self.feature_widget.motor_checkbox.setEnabled(False)
            self.feature_widget.throttle_checkbox.setEnabled(False)
            if hasattr(self.feature_widget, 'selected_logs') and len(self.feature_widget.selected_logs) > 2:
                # Keep only the first 2 selected logs
                self.feature_widget.selected_logs = self.feature_widget.selected_logs[:2]
                # Update the list widget selection
                self.feature_widget.logs_list.clearSelection()
                for i in range(self.feature_widget.logs_list.count()):
                    item = self.feature_widget.logs_list.item(i)
                    if item.text() in self.feature_widget.selected_logs:
                        item.setSelected(True)
        elif current_tab == 2:
            # Check for missing features and show warnings
            self.feature_widget.check_missing_features()
            # Step response tab
            # Update step response analysis
            line_width = getattr(self.feature_widget, 'current_line_width', 1.0)
            # Pass the correct log name (filename) if available
            log_name = None
            if hasattr(self.feature_widget, 'selected_logs') and self.feature_widget.selected_logs:
                log_name = self.feature_widget.selected_logs[0]
            self.step_response_widget.update_step_response(self.feature_widget.current_log, line_width=line_width, log_name=log_name, log_index=0)
        elif current_tab == 3:  # Noise Analysis
            try:
                # Calculate the Nyquist frequency (half of the sampling rate)
                time_data = self.feature_widget.current_log['time'].values.astype(float)
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
                self.frequency_analyzer_widget.update_frequency_plots(self.feature_widget.current_log, max_freq=max_freq)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update frequency plots: {str(e)}")
        elif current_tab == 4:  # Frequency Evolution
            # Check for missing features and show warnings
            self.feature_widget.check_missing_features()
            try:
                # Clear existing plots first
                self.spectrogram_widget.clear_all_plots()
                # Update spectrogram with current log data
                self.spectrogram_widget.update_spectrogram(self.feature_widget.current_log)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update spectrogram: {str(e)}")
        elif current_tab == 5:  # Drone Config (changed from 4 to 5)
            # Update drone config display
            if hasattr(self.feature_widget, 'selected_logs') and self.feature_widget.selected_logs:
                self.parameters_widget.update_parameters(self.feature_widget.selected_logs[:2])
            self.feature_widget.legend_group.setVisible(False)
            try:
                self.error_performance_widget.update_error_performance(self.feature_widget.current_log)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update error/performance plots: {str(e)}")
        elif current_tab == 6:  # Export (changed from 5 to 6)
            # Export functionality is handled in on_tab_changed
            pass

    def update_spectral_analysis(self):
        """Update the frequency domain when inputs change"""
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
        # Select gyro filtered, setpoint, and throttle, deselect others
        self.feature_widget.throttle_checkbox.setChecked(True)      # Throttle
        self.feature_widget.gyro_scaled_checkbox.setChecked(True)   # Gyro (filtered)
        self.feature_widget.gyro_unfilt_checkbox.setChecked(False)  # Gyro (raw)
        self.feature_widget.pid_p_checkbox.setChecked(False)        # P-Term
        self.feature_widget.pid_i_checkbox.setChecked(False)        # I-Term
        self.feature_widget.pid_d_checkbox.setChecked(False)        # D-Term
        self.feature_widget.pid_f_checkbox.setChecked(False)        # FeedForward
        self.feature_widget.setpoint_checkbox.setChecked(True)      # Setpoint
        self.feature_widget.rc_checkbox.setChecked(False)           # RC Command
        self.feature_widget.motor_checkbox.setChecked(False)        # Motor Outputs

    def set_spectral_defaults(self):
        # Select gyro filtered and gyro raw, deselect others
        self.feature_widget.throttle_checkbox.setChecked(False)
        self.feature_widget.gyro_scaled_checkbox.setChecked(True)  # Gyro (filtered)
        self.feature_widget.gyro_unfilt_checkbox.setChecked(True)  # Gyro (raw)
        self.feature_widget.pid_p_checkbox.setChecked(False)
        self.feature_widget.pid_i_checkbox.setChecked(False)
        self.feature_widget.pid_d_checkbox.setChecked(False)
        self.feature_widget.pid_f_checkbox.setChecked(False)
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

    def set_spectrogram_checkbox_states(self):
        # Enable only gyro checkboxes for frequency evolution, disable others
        if hasattr(self.feature_widget, 'gyro_unfilt_checkbox'):
            self.feature_widget.gyro_unfilt_checkbox.setEnabled(True)
        if hasattr(self.feature_widget, 'gyro_scaled_checkbox'):
            self.feature_widget.gyro_scaled_checkbox.setEnabled(True)
        if hasattr(self.feature_widget, 'pid_p_checkbox'):
            self.feature_widget.pid_p_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'pid_i_checkbox'):
            self.feature_widget.pid_i_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'pid_d_checkbox'):
            self.feature_widget.pid_d_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'pid_f_checkbox'):
            self.feature_widget.pid_f_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'setpoint_checkbox'):
            self.feature_widget.setpoint_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'rc_checkbox'):
            self.feature_widget.rc_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'throttle_checkbox'):
            self.feature_widget.throttle_checkbox.setEnabled(False)
        if hasattr(self.feature_widget, 'motor_checkbox'):
            self.feature_widget.motor_checkbox.setEnabled(False)

    def select_first_log_if_multiple(self):
        """Automatically select the first log if multiple logs are selected for single-log tabs"""
        if hasattr(self.feature_widget, 'selected_logs') and len(self.feature_widget.selected_logs) > 1:
            # Keep only the first selected log
            first_log = self.feature_widget.selected_logs[0]
            self.feature_widget.selected_logs = [first_log]
            # Update the list widget selection
            self.feature_widget.logs_list.clearSelection()
            for i in range(self.feature_widget.logs_list.count()):
                item = self.feature_widget.logs_list.item(i)
                if item.text() == first_log:
                    item.setSelected(True)
                    break
            # Update current log
            if first_log in self.feature_widget.loaded_logs:
                self.feature_widget.current_log = self.feature_widget.loaded_logs[first_log]
                self.feature_widget.df = self.feature_widget.current_log

    def on_tab_changed(self, index):
        # Store the previous tab index before any logic
        prev_tab = self.previous_tab_index
        self.previous_tab_index = index
        # 0 = Time Domain, 1 = Frequency Domain, 2 = Step Response, 3 = Noise Analysis, 4 = Frequency Evolution, 5 = Error & Performance, 6 = Drone Config, 7 = Export
        if index == 7:  # Export tab (was 6, now 7)
            # Only export if we're coming from a valid tab (0-5)
            if 0 <= prev_tab <= 5:
                self.export_widget.set_previous_tab(prev_tab)
                self.export_widget.export_plots()
            else:
                self.export_widget.status_label.setText("Please select a valid tab to export from.")
        if index == 0:  # Time Domain
            self.set_time_domain_defaults()
            self.feature_widget.set_time_domain_mode(True)
            self.feature_widget.legend_group.setVisible(True)
            # Enable checkboxes for time domain
            self.feature_widget._set_checkboxes_enabled(True)
            # Select first log if multiple are selected
            self.select_first_log_if_multiple()
            # Update plot for time domain if we have data
            if hasattr(self, 'df') and self.df is not None:
                self.plot_selected()
        elif index == 1:  # Frequency Domain
            # Check for missing features and show warnings
            self.feature_widget.check_missing_features()
            # Set spectral defaults to select gyro (raw) and gyro (filtered)
            self.set_spectral_defaults()
            # Enable checkboxes for frequency domain except motors and throttle
            # Enforce 2-log limit for frequency domain
            self.feature_widget._set_checkboxes_enabled(True)
            self.feature_widget.motor_checkbox.setEnabled(False)
            self.feature_widget.throttle_checkbox.setEnabled(False)
            if hasattr(self.feature_widget, 'selected_logs') and len(self.feature_widget.selected_logs) > 2:
                # Keep only the first 2 selected logs
                self.feature_widget.selected_logs = self.feature_widget.selected_logs[:2]
                # Update the list widget selection
                self.feature_widget.logs_list.clearSelection()
                for i in range(self.feature_widget.logs_list.count()):
                    item = self.feature_widget.logs_list.item(i)
                    if item.text() in self.feature_widget.selected_logs:
                        item.setSelected(True)
        elif index == 2:  # Step Response
            self.set_step_response_defaults()
            self.feature_widget.set_step_response_mode(True)
            self.feature_widget.legend_group.setVisible(False)
            # Disable checkboxes for step response
            self.feature_widget._set_checkboxes_enabled(False)
            # Clear any existing legends in step response charts
            if hasattr(self, 'step_response_widget'):
                self.step_response_widget.clear_all_legends()
        elif index == 3:  # Noise Analysis
            # Check for missing features and show warnings
            self.set_frequency_analyzer_defaults()
            self.feature_widget.set_time_domain_mode(False)
            self.feature_widget.legend_group.setVisible(False)
            # Disable checkboxes for noise analysis
            self.feature_widget._set_checkboxes_enabled(False)
            # Set single selection mode for noise analysis
            # No longer auto-update noise analysis plots
            self.feature_widget.logs_list.setSelectionMode(QListWidget.SingleSelection)
            # Select first log if multiple are selected
            self.select_first_log_if_multiple()
        elif index == 4:  # Frequency Evolution
            self.set_spectrogram_checkbox_states()
            # Only auto-select Gyro (raw) and deselect others ONCE, when entering the tab
            if not hasattr(self, '_spectrogram_tab_initialized') or not self._spectrogram_tab_initialized:
                if hasattr(self.feature_widget, 'gyro_unfilt_checkbox'):
                    self.feature_widget.gyro_unfilt_checkbox.setChecked(True)
                if hasattr(self.feature_widget, 'gyro_scaled_checkbox'):
                    self.feature_widget.gyro_scaled_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'pid_p_checkbox'):
                    self.feature_widget.pid_p_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'pid_i_checkbox'):
                    self.feature_widget.pid_i_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'pid_d_checkbox'):
                    self.feature_widget.pid_d_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'pid_f_checkbox'):
                    self.feature_widget.pid_f_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'setpoint_checkbox'):
                    self.feature_widget.setpoint_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'rc_checkbox'):
                    self.feature_widget.rc_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'throttle_checkbox'):
                    self.feature_widget.throttle_checkbox.setChecked(False)
                if hasattr(self.feature_widget, 'motor_checkbox'):
                    self.feature_widget.motor_checkbox.setChecked(False)
                self._spectrogram_tab_initialized = True
            self.feature_widget.legend_group.setVisible(False)
            self.feature_widget.logs_list.setSelectionMode(QListWidget.SingleSelection)
            # Select first log if multiple are selected
            self.select_first_log_if_multiple()
            # Removed auto-plotting - plots will only be generated when user clicks "Show Plot" button
        elif index == 5:  # Error & Performance
            # Disable checkboxes for error & performance (handled in widget)
            self.feature_widget._set_checkboxes_enabled(False)
            self.feature_widget.legend_group.setVisible(False)
        elif index == 6:  # Drone Config
            self.feature_widget._set_checkboxes_enabled(False)
            # Allow up to 2 logs to be selected in Drone Config tab
            self.feature_widget.logs_list.setSelectionMode(QListWidget.ExtendedSelection)
            self.feature_widget.legend_group.setVisible(False)

    def plot_multiple_logs(self):
        """Plot multiple selected logs together"""
        # Only implement multi-plotting for Time Domain tab for now
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:  # Time Domain
            try:
                self.control_widget.progress_bar.setVisible(True)
                
                # Get selected features from the feature widget
                selected_features = self.feature_widget.get_selected_features()
                if not selected_features:
                    QMessageBox.warning(self, "Warning", "Please select at least one feature to plot.")
                    self.control_widget.progress_bar.setVisible(False)
                    return
                
                # Get the current line width from feature widget
                line_width = getattr(self.feature_widget, 'current_line_width', 1.0)
                
                # First clear all charts
                self.chart_manager.clear_all_charts()
                
                # Plot each selected log with a different line style/pattern
                num_logs = len(self.feature_widget.selected_logs)
                for i, log_name in enumerate(self.feature_widget.selected_logs):
                    if log_name in self.feature_widget.loaded_logs:
                        log_df = self.feature_widget.loaded_logs[log_name]
                        
                        # Update progress bar
                        progress = int(((i + 1) / num_logs) * 100)
                        self.control_widget.progress_bar.setValue(progress)
                        
                        # Rename columns to include log name to avoid conflicts in legend
                        renamed_df = log_df.copy()
                        for feature in selected_features:
                            if feature in renamed_df.columns:
                                # Add a suffix to help identify in the legend
                                renamed_df.rename(columns={feature: f"{feature} [{log_name}]"}, inplace=True)
                        
                        # Get renamed column names
                        renamed_features = []
                        for feature in selected_features:
                            renamed_feature = f"{feature} [{log_name}]"
                            if renamed_feature in renamed_df.columns:
                                renamed_features.append(renamed_feature)
                            elif feature in renamed_df.columns:  # Fallback if rename failed
                                renamed_features.append(feature)
                        
                        # Plot the renamed features
                        self.chart_manager.plot_features(
                            renamed_df, 
                            renamed_features, 
                            self.control_widget.progress_bar,
                            line_width=line_width,
                            clear_charts=False,  # Don't clear between logs
                            log_name=log_name
                        )
                
                self.control_widget.progress_bar.setValue(100)
                self.control_widget.progress_bar.setVisible(False)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to plot multiple logs: {str(e)}")
                self.control_widget.progress_bar.setVisible(False)
        else:
            QMessageBox.information(self, "Info", "Multi-log plotting is currently not available for this tab.") 

    def plot_multiple_logs_spectral(self):
        """Plot spectra for multiple selected logs in the Frequency Domain tab."""
        try:
            # Get selected features from the feature widget
            selected_features = self.feature_widget.get_selected_features()
            if not selected_features:
                QMessageBox.warning(self, "Warning", "Please select at least one feature to plot.")
                return
            # For each selected log, plot its spectrum
            for idx, log_name in enumerate(self.feature_widget.selected_logs):
                if log_name in self.feature_widget.loaded_logs:
                    df = self.feature_widget.loaded_logs[log_name]
                    # Use the existing update_spectrum but pass a label/log_name for legend
                    self.spectral_widget.update_spectrum(df, log_label=log_name, clear_charts=(idx==0))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to plot multiple spectra: {str(e)}")

    def plot_multiple_logs_step_response(self):
        """Plot step response for multiple selected logs in the Step Response tab."""
        line_width = getattr(self.feature_widget, 'current_line_width', 1.0)
        for idx, log_name in enumerate(self.feature_widget.selected_logs):
            if log_name in self.feature_widget.loaded_logs:
                df = self.feature_widget.loaded_logs[log_name]
                clear_charts = (idx == 0)
                self.step_response_widget.update_step_response(df, line_width=line_width, log_name=log_name, clear_charts=clear_charts, log_index=idx) 