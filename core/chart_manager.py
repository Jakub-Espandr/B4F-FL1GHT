"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

from PySide6.QtWidgets import QSizePolicy, QLabel, QToolTip
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QLegend, QValueAxis
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import Qt, QMargins, QPointF
from utils.config import CHART_CONFIG, COLOR_PALETTE, MOTOR_COLORS
from utils.data_processor import get_clean_name, decimate_data

class ChartManager:
    def __init__(self):
        self.chart_views = []
        self.full_time_range = None
        self.actual_time_max = None
        self.parent = None  # Add parent property

    def create_chart_views(self, parent, min_chart_height):
        """Create and initialize chart views"""
        self.parent = parent  # Store parent reference
        self.chart_views = []
        for i in range(4):
            chart_view = QChartView()
            chart_view.setRenderHint(QPainter.Antialiasing)
            chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            chart_view.setMinimumHeight(min_chart_height)
            
            chart = QChart()
            chart.setTitle(f"{['Roll', 'Pitch', 'Yaw', 'Throttle'][i]}")
            title_font = QFont()
            title_font.setPointSize(10)
            chart.setTitleFont(title_font)
            chart.legend().setVisible(False)
            chart.setMargins(QMargins(10, 10, 10, 10))
            chart_view.setChart(chart)
            
            # Add tooltip support only to the throttle chart (index 3)
            if i == 3:  # Throttle chart
                chart_view.setMouseTracking(True)
                chart_view.mouseMoveEvent = lambda event, cv=chart_view: self.show_tooltip(event, cv)
                chart_view.setCursor(Qt.CrossCursor)  # Add crosshair cursor
            
            self.chart_views.append(chart_view)
            
        return self.chart_views

    def update_chart(self, chart_view, series_data, time_min, time_max, y_min=None, y_max=None, line_width=1.0):
        """Update a chart with new data. Returns list of QLineSeries added."""
        if not chart_view.chart():
            return []

        # Clear existing series
        for series in chart_view.chart().series():
            chart_view.chart().removeSeries(series)
            series.deleteLater()

        added_series = []
        
        # Add zero line for Roll, Pitch, Yaw plots (not for Throttle)
        chart_title = chart_view.chart().title()
        if chart_title in ["Roll", "Pitch", "Yaw"] and y_min is not None and y_max is not None:
            # Create a zero reference line
            zero_line = QLineSeries()
            zero_line.setName("Zero")
            # Set color to black with 1px width (always fixed)
            pen = zero_line.pen()
            pen.setColor(QColor(0, 0, 0))  # Black
            pen.setWidthF(1.0)  # Always 1px width for reference line
            zero_line.setPen(pen)
            
            # Add two points to create a horizontal line across the chart
            zero_line.append(time_min, 0)
            zero_line.append(time_max * 1.2, 0)  # Extend slightly beyond max to ensure visibility
            
            chart_view.chart().addSeries(zero_line)
        
        for data in series_data:
            series = QLineSeries()
            # Set name to clean name for legend and chart
            clean_name = get_clean_name(data['name'])
            series.setName(clean_name)

            # Set color based on the type of data using get_clean_name
            color_key = clean_name
            if color_key.startswith('Motor'):
                try:
                    motor_num = int(color_key.split(' ')[1])
                    color = QColor(*MOTOR_COLORS[motor_num % len(MOTOR_COLORS)])
                except Exception:
                    color = QColor(*COLOR_PALETTE.get(color_key, (128, 128, 128)))
            else:
                color = QColor(*COLOR_PALETTE.get(color_key, (128, 128, 128)))

            pen = series.pen()
            pen.setColor(color)
            pen.setWidthF(line_width)  # Only user data series get the custom line width
            series.setPen(pen)

            for t, v in zip(data['time'], data['values']):
                series.append(t, v)

            chart_view.chart().addSeries(series)
            added_series.append(series)

        # Configure axes
        chart_view.chart().createDefaultAxes()
        axis_x = chart_view.chart().axes(Qt.Horizontal)[0]
        axis_y = chart_view.chart().axes(Qt.Vertical)[0]
        
        # Configure X axis
        axis_x.setTitleText("Time (s)")
        axis_x.setTitleVisible(True)
        axis_x.setLabelsVisible(True)
        axis_x.setGridLineVisible(True)
        axis_x.setRange(time_min, time_max)
        rounded_max = ((int(time_max) + 4) // 5) * 5
        axis_x.setRange(time_min, rounded_max)
        axis_x.setTickCount(int((rounded_max - time_min) / 5) + 1)
        
        # Special handling for throttle chart (index 3)
        if chart_title == "Throttle":
            # Determine if throttle and/or motor series are present
            has_throttle = any(s.name().lower() == 'throttle' or 'rccommand[3]' in s.name().lower() for s in chart_view.chart().series())
            has_motor = any(s.name().lower().startswith('motor') for s in chart_view.chart().series())
            # Remove all Y axes before adding new ones
            for axis in chart_view.chart().axes(Qt.Vertical):
                chart_view.chart().removeAxis(axis)
            # Single axis for both throttle and motors
            axis_y = QValueAxis()
            axis_y.setRange(0, 2000)
            axis_y.setTitleText("Throttle & Motors")
            axis_y.setTitleVisible(True)
            axis_y.setLabelsVisible(True)
            axis_y.setGridLineVisible(True)
            chart_view.chart().addAxis(axis_y, Qt.AlignLeft)
            # Attach all series to the single axis
            for series in chart_view.chart().series():
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)
        else:
            # Configure Y axis for Roll, Pitch, Yaw
            axis_y.setTitleText("Value")
            axis_y.setTitleVisible(True)
            axis_y.setLabelsVisible(True)
            axis_y.setGridLineVisible(True)
            # Apply custom Y axis range if provided
            if y_min is not None and y_max is not None:
                axis_y.setRange(y_min, y_max)
                # Set appropriate tick count based on range
                if abs(y_max - y_min) > 2000:
                    axis_y.setTickCount(11)  # Every 400 units
                elif abs(y_max - y_min) > 1000:
                    axis_y.setTickCount(6)   # Every 400 units
                elif abs(y_max - y_min) > 500:
                    axis_y.setTickCount(6)   # Every 200 units
                else:
                    axis_y.setTickCount(6)   # Every 100 units or less
        # Make sure zero line is attached to the axes
        if chart_title in ["Roll", "Pitch", "Yaw"]:
            for series in chart_view.chart().series():
                if series.name() == "Zero":
                    series.attachAxis(axis_x)
                    series.attachAxis(axis_y)
                    break
        
        return added_series

    def update_zoom(self, zoom_factor, scroll_position):
        """Update zoom level for all charts"""
        if not self.full_time_range:
            return
            
        time_min, time_max = self.full_time_range
        time_range = time_max - time_min
        visible_range = time_range / zoom_factor
        
        # Calculate new range based on scroll position
        available_range = time_range - visible_range
        new_min = time_min + (available_range * scroll_position)
        new_max = new_min + visible_range
        
        # Clamp to data boundaries
        if new_min < time_min:
            new_min = time_min
            new_max = min(time_max, new_min + visible_range)
        if new_max > time_max:
            new_max = time_max
            new_min = max(time_min, new_max - visible_range)
        
        # Apply to all charts
        for chart_view in self.chart_views:
            if chart_view.chart() and chart_view.chart().axes(Qt.Horizontal):
                axes = chart_view.chart().axes(Qt.Horizontal)
                if axes:
                    axis = axes[0]
                    axis.setRange(new_min, new_max)
                    chart_view.chart().update()
                    chart_view.viewport().update()

    def reset_zoom(self):
        """Reset zoom level for all charts"""
        if self.full_time_range:
            time_min, time_max = self.full_time_range
            rounded_max = ((int(time_max) + 4) // 5) * 5
            for chart_view in self.chart_views:
                if chart_view.chart() and chart_view.chart().axes(Qt.Horizontal):
                    axes = chart_view.chart().axes(Qt.Horizontal)
                    if axes:
                        axis = axes[0]
                        axis.setRange(time_min, rounded_max)
                        axis.setTickCount(int((rounded_max - time_min) / 5) + 1)
                        chart_view.chart().update()

    def plot_features(self, df, selected_features, progress_bar=None, line_width=1.0):
        """Plot selected features and directly update legend (like SpectralAnalyzerWidget)."""
        if not selected_features:
            return
            
        # Get time data
        time_data = df['time'].values
        if time_data.max() > 1e6:
            time_data = time_data / 1_000_000.0
        elif time_data.max() > 1e3:
            time_data = time_data / 1_000.0
        time_data = time_data - time_data.min()
        
        # Determine the number of points - use full dataset only when needed
        # Import the decimate_data function for data reduction
        from utils.data_processor import decimate_data
        
        # Track what types are actually plotted (for legend)
        plotted_types = set()
        plotted_labels = {}  # Use dict to deduplicate by clean_name

        axis_labels = ['Roll', 'Pitch', 'Yaw', 'Throttle']
        self.full_time_range = (time_data.min(), time_data.max())
        self.actual_time_max = time_data.max()
        
        if progress_bar:
            progress_bar.setMaximum(len(self.chart_views))
            progress_bar.setValue(0)
        
        # First pass: collect data for all axes to find overall min/max
        all_axis_data = [[] for _ in range(4)]
        
        for i, chart_view in enumerate(self.chart_views):
            for feature in selected_features:
                if feature not in df.columns:
                    continue
                
                # Only allow motor outputs in the bottom chart
                if i < 3:  # Roll, Pitch, Yaw
                    if feature.lower().startswith('motor['):
                        continue
                    if f'[{i}]' in feature or \
                       (i == 0 and 'roll' in feature.lower()) or \
                       (i == 1 and 'pitch' in feature.lower()) or \
                       (i == 2 and 'yaw' in feature.lower()):
                        # Add to the data collection for this axis
                        all_axis_data[i].append(df[feature].values)
                else:  # Throttle
                    if feature.lower().startswith('motor[') or \
                       'throttle' in feature.lower() or 'rccommand[3]' in feature.lower():
                        # Add to the data collection for this axis
                        all_axis_data[i].append(df[feature].values)
        
        # Calculate common min/max for Roll, Pitch, Yaw
        rpy_min = float('inf')
        rpy_max = float('-inf')
        
        # Find min/max across Roll, Pitch, Yaw
        for i in range(3):  # Only Roll, Pitch, Yaw
            if all_axis_data[i]:
                for data in all_axis_data[i]:
                    axis_min = float(min(data))
                    axis_max = float(max(data))
                    rpy_min = min(rpy_min, axis_min)
                    rpy_max = max(rpy_max, axis_max)
        
        # Make the min/max symmetric around 0
        if rpy_min != float('inf') and rpy_max != float('-inf'):
            sym_limit = max(abs(rpy_min), abs(rpy_max))
            rpy_min = -sym_limit
            rpy_max = sym_limit
        else:
            # Default if no data
            rpy_min = -1000
            rpy_max = 1000
        
        # Second pass: actually plot the data
        for i, chart_view in enumerate(self.chart_views):
            axis_series = []
            for feature in selected_features:
                if feature not in df.columns:
                    continue
                
                # Only allow motor outputs in the bottom chart
                if i < 3:
                    if feature.lower().startswith('motor['):
                        continue
                    if f'[{i}]' in feature or \
                       (i == 0 and 'roll' in feature.lower()) or \
                       (i == 1 and 'pitch' in feature.lower()) or \
                       (i == 2 and 'yaw' in feature.lower()):
                        # Apply data reduction here for better performance
                        reduced_time, reduced_values = decimate_data(time_data, df[feature].values)
                        axis_series.append({
                            'name': feature,
                            'time': reduced_time,
                            'values': reduced_values
                        })
                else:
                    if feature.lower().startswith('motor[') or \
                       'throttle' in feature.lower() or 'rccommand[3]' in feature.lower():
                        # Apply data reduction here for better performance
                        reduced_time, reduced_values = decimate_data(time_data, df[feature].values)
                        axis_series.append({
                            'name': feature,
                            'time': reduced_time,
                            'values': reduced_values
                        })
            
            # Use custom Y-axis limits based on chart type
            if i < 3:  # Roll, Pitch, Yaw - use symmetric values
                added_series = self.update_chart(chart_view, axis_series, time_data.min(), time_data.max(), 
                                           y_min=rpy_min, y_max=rpy_max, line_width=line_width)
            else:  # Throttle - use 0 to 2000
                added_series = self.update_chart(chart_view, axis_series, time_data.min(), time_data.max(),
                                           y_min=0, y_max=2000, line_width=line_width)
            
            # Track what was plotted for the legend
            for data, series in zip(axis_series, added_series):
                clean_name = get_clean_name(data['name'])
                
                # Get color from COLOR_PALETTE or MOTOR_COLORS
                if clean_name.startswith('Motor'):
                    try:
                        motor_num = int(clean_name.split(' ')[1])
                        color = QColor(*MOTOR_COLORS[motor_num % len(MOTOR_COLORS)])
                    except:
                        color = QColor(*COLOR_PALETTE.get(clean_name, (128, 128, 128)))
                else:
                    color = QColor(*COLOR_PALETTE.get(clean_name, (128, 128, 128)))
                
                # Store for legend - use clean_name as key to deduplicate
                # Only add this label if we haven't seen it yet
                if clean_name not in plotted_labels:
                    plotted_labels[clean_name] = color.name()
                    plotted_types.add(clean_name)
            
            if progress_bar:
                progress_bar.setValue(i + 1)

        # Create a dictionary for the update_legend method
        series_by_category = {}
        for label, color_name in plotted_labels.items():
            series_by_category[label] = color_name
            
        # Update the legend using the feature_widget's update_legend method
        if self.parent and hasattr(self.parent, 'feature_widget'):
            self.parent.feature_widget.update_legend(series_by_category) 

    def show_tooltip(self, event, chart_view):
        """Show tooltip with time and value information"""
        chart = chart_view.chart()
        if not chart:
            return
        # Only show tooltip for throttle chart
        if chart.title() != "Throttle":
            return
        # Get axes
        if not chart.axes(Qt.Horizontal) or not chart.axes(Qt.Vertical):
            return
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
        time_val = x_min + (x_max - x_min) * (event.position().x() - left) / (right - left)
        # Draw or update vertical line
        scene = chart_view.scene()
        if not hasattr(chart_view, '_track_line'):
            from PySide6.QtWidgets import QGraphicsLineItem
            chart_view._track_line = QGraphicsLineItem()
            chart_view._track_line.setZValue(1000)
            pen = chart_view._track_line.pen()
            pen.setColor(QColor(255, 0, 0, 128))
            pen.setWidth(1)
            chart_view._track_line.setPen(pen)
            scene.addItem(chart_view._track_line)
        # Calculate X position in scene coordinates
        x_scene = chart_view.mapToScene(event.pos()).x()
        # Restrict the line to the plot area
        if left <= event.position().x() <= right:
            chart_view._track_line.setLine(x_scene, top, x_scene, bottom)
            chart_view._track_line.setVisible(True)
            # Get all series data at the current time point
            tooltip_lines = [f"Time: {time_val:.2f}s"]
            all_series = chart.series()
            for series in all_series:
                if series.name() == "Zero":
                    continue
                # Find closest point to current time
                closest_point = None
                closest_dist = float('inf')
                for i in range(series.count()):
                    point = series.at(i)
                    dist = abs(point.x() - time_val)
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_point = point
                if closest_point and closest_dist < (x_max - x_min) / 100:  # Only show if reasonably close
                    name = series.name()
                    value = closest_point.y()
                    if name.lower().startswith('motor'):
                        percentage = (value / 2050) * 100
                        tooltip_lines.append(f"{name}: {value:.0f} ({percentage:.1f}%)")
                    elif name.lower() == 'throttle' or 'rccommand[3]' in name.lower():
                        tooltip_lines.append(f"{name}: {value:.0f} µs")
                    else:
                        tooltip_lines.append(f"{name}: {value:.1f}")
            tooltip = "\n".join(tooltip_lines)
            QToolTip.showText(event.globalPos(), tooltip, chart_view)
        else:
            chart_view._track_line.setVisible(False)
            QToolTip.hideText() 