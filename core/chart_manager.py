"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QLegend
from PySide6.QtGui import QPainter, QFont, QColor
from PySide6.QtCore import Qt, QMargins, QPointF
from utils.config import CHART_CONFIG, COLOR_PALETTE, MOTOR_COLORS

class ChartManager:
    def __init__(self):
        self.chart_views = []
        self.full_time_range = None
        self.actual_time_max = None

    def create_chart_views(self, parent, min_chart_height):
        """Create and initialize chart views"""
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
            self.chart_views.append(chart_view)
            
        return self.chart_views

    def update_chart(self, chart_view, series_data, time_min, time_max, y_min=None, y_max=None, line_width=1.0):
        """Update a chart with new data"""
        if not chart_view.chart():
            return

        # Clear existing series
        for series in chart_view.chart().series():
            chart_view.chart().removeSeries(series)
            series.deleteLater()

        # Add new series
        for data in series_data:
            series = QLineSeries()
            series.setName(data['name'])
            
            # Set color based on the type of data
            if data['name'].startswith('Motor'):
                # For motors, use the motor number to get a color
                motor_num = int(data['name'].split(' ')[1])
                color = QColor(*MOTOR_COLORS[motor_num % len(MOTOR_COLORS)])
            else:
                # For other data types, use the predefined colors
                color = QColor(*COLOR_PALETTE.get(data['name'], (128, 128, 128)))  # Default to gray if not found
            
            # Set the color and line width
            pen = series.pen()
            pen.setColor(color)
            pen.setWidthF(line_width)  # Use setWidthF for floating point width
            series.setPen(pen)
            
            # Add points
            for t, v in zip(data['time'], data['values']):
                series.append(t, v)
            
            chart_view.chart().addSeries(series)

        # Configure axes
        chart_view.chart().createDefaultAxes()
        
        # Get axes
        axis_x = chart_view.chart().axes(Qt.Horizontal)[0]
        axis_y = chart_view.chart().axes(Qt.Vertical)[0]
        
        # Format the x-axis
        axis_x.setTitleText("Time (s)")
        axis_x.setTitleVisible(True)
        axis_x.setLabelsVisible(True)
        axis_x.setGridLineVisible(True)
        axis_x.setRange(time_min, time_max)
        rounded_max = ((int(time_max) + 4) // 5) * 5
        axis_x.setRange(time_min, rounded_max)
        axis_x.setTickCount(int((rounded_max - time_min) / 5) + 1)
        
        # Format the y-axis
        axis_y.setTitleText("Value")
        axis_y.setTitleVisible(True)
        axis_y.setLabelsVisible(True)
        axis_y.setGridLineVisible(True)
        
        # Set y-axis range if provided
        if y_min is not None and y_max is not None:
            axis_y.setRange(y_min, y_max)

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