"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import numpy as np
import pandas as pd

def find_gyro_col(df, axis):
    """Find the appropriate gyro column for the given axis"""
    axis_map = {'roll': 0, 'pitch': 1, 'yaw': 2}
    axis_idx = axis_map.get(axis)
    if axis_idx is None:
        return None
    
    # Try different column naming patterns
    patterns = [
        f'gyroADC[{axis_idx}] (deg/s)',
        f'gyroADC[{axis_idx}]',
        f'gyro[{axis_idx}]'
    ]
    
    for pattern in patterns:
        if pattern in df.columns:
            return pattern
    return None

def calculate_tracking_error(df, axis):
    """Calculate tracking error (setpoint - actual) for the given axis"""
    axis_map = {'roll': 0, 'pitch': 1, 'yaw': 2}
    axis_idx = axis_map.get(axis)
    if axis_idx is None:
        return None, None
    
    # Find setpoint column
    setpoint_col = None
    for col in df.columns:
        if f'rccommand[{axis_idx}]' in col.lower() or f'setpoint[{axis_idx}]' in col.lower():
            setpoint_col = col
            break
    
    if setpoint_col is None:
        return None, None
    
    # Find gyro column
    gyro_col = find_gyro_col(df, axis)
    if gyro_col is None:
        return None, None
    
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    
    setpoint = df[setpoint_col].values.astype(float)
    actual = df[gyro_col].values.astype(float)
    error = setpoint - actual
    
    return time, error

def calculate_i_term(df, axis):
    """Calculate I-term for the given axis"""
    axis_map = {'roll': 0, 'pitch': 1, 'yaw': 2}
    axis_idx = axis_map.get(axis)
    if axis_idx is None:
        return None, None
    
    # Find I-term column
    iterm_col = None
    for col in df.columns:
        if f'axisi[{axis_idx}]' in col.lower() or f'iterm[{axis_idx}]' in col.lower() or f'axispid[{axis_idx}].i' in col.lower():
            iterm_col = col
            break
    
    if iterm_col is None:
        return None, None
    
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    
    iterm = df[iterm_col].values.astype(float)
    
    return time, iterm

def calculate_pid_output(df, axis):
    """Calculate PID output for the given axis"""
    axis_map = {'roll': 0, 'pitch': 1, 'yaw': 2}
    axis_idx = axis_map.get(axis)
    if axis_idx is None:
        return None, None
    
    # Try to find P, I, D terms and calculate PID output
    p_col = None
    i_col = None
    d_col = None
    
    for col in df.columns:
        if f'axisp[{axis_idx}]' in col.lower():
            p_col = col
        elif f'axisi[{axis_idx}]' in col.lower():
            i_col = col
        elif f'axisd[{axis_idx}]' in col.lower():
            d_col = col
    
    # If we have P, I, D terms, calculate PID output
    if p_col and i_col:
        time = df['time'].values.astype(float)
        if time.max() > 1e6:
            time = time / 1_000_000.0
        elif time.max() > 1e3:
            time = time / 1_000.0
        time = time - time.min()
        
        p_term = df[p_col].values.astype(float)
        i_term = df[i_col].values.astype(float)
        d_term = df[d_col].values.astype(float) if d_col else np.zeros_like(p_term)
        
        pid_output = p_term + i_term + d_term
        return time, pid_output
    
    # Fallback to motor columns or direct PID output
    pid_col = None
    for col in df.columns:
        if f'motor[{axis_idx}]' in col.lower() or f'pidoutput[{axis_idx}]' in col.lower():
            pid_col = col
            break
    
    if pid_col is None:
        return None, None
    
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    
    pid_output = df[pid_col].values.astype(float)
    
    return time, pid_output

def calculate_step_response_data(df, axis):
    """Calculate step response data (setpoint and actual) for the given axis"""
    axis_map = {'roll': 0, 'pitch': 1, 'yaw': 2}
    axis_idx = axis_map.get(axis)
    if axis_idx is None:
        return None, None, None
    
    # Find setpoint column
    setpoint_col = None
    for col in df.columns:
        if f'rccommand[{axis_idx}]' in col.lower() or f'setpoint[{axis_idx}]' in col.lower():
            setpoint_col = col
            break
    
    if setpoint_col is None:
        return None, None, None
    
    # Find gyro column
    gyro_col = find_gyro_col(df, axis)
    if gyro_col is None:
        return None, None, None
    
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    
    setpoint = df[setpoint_col].values.astype(float)
    actual = df[gyro_col].values.astype(float)
    
    return time, setpoint, actual

def calculate_error_histogram_data(df, axis):
    """Calculate error data for histogram analysis"""
    time, error = calculate_tracking_error(df, axis)
    if time is None or error is None:
        return None
    
    # Remove outliers (beyond 3 standard deviations)
    std_error = np.std(error)
    mean_error = np.mean(error)
    mask = np.abs(error - mean_error) <= 3 * std_error
    
    return error[mask]

def calculate_cumulative_error(df, axis):
    """Calculate cumulative error over time"""
    time, error = calculate_tracking_error(df, axis)
    if time is None or error is None:
        return None, None
    
    # The original code used cumsum of error (not absolute error)
    cumulative_error = np.cumsum(error)
    
    return time, cumulative_error

def calculate_global_error_range(df):
    """Calculate global min/max error across all axes for consistent histogram scaling"""
    all_errors = []
    
    for axis in ['roll', 'pitch', 'yaw']:
        error_data = calculate_error_histogram_data(df, axis)
        if error_data is not None:
            all_errors.extend(error_data)
    
    if not all_errors:
        return -50, 50  # Default range
    
    all_errors = np.array(all_errors)
    error_min = np.min(all_errors)
    error_max = np.max(all_errors)
    
    # Make range symmetric around zero
    max_abs = max(abs(error_min), abs(error_max))
    
    return -max_abs, max_abs

def get_plot_data(df, plot_type, axis):
    """Get data for a specific plot type and axis"""
    if plot_type == "Tracking Error":
        return calculate_tracking_error(df, axis)
    elif plot_type == "I-Term":
        return calculate_i_term(df, axis)
    elif plot_type == "PID Output":
        return calculate_pid_output(df, axis)
    elif plot_type == "Step Response":
        return calculate_step_response_data(df, axis)
    elif plot_type == "Error Histogram":
        return calculate_error_histogram_data(df, axis)
    elif plot_type == "Cumulative Error":
        return calculate_cumulative_error(df, axis)
    else:
        return None

def get_plot_labels(plot_type):
    """Get appropriate axis labels for each plot type"""
    labels = {
        "Tracking Error": ("Time (s)", "Error (deg/s)"),
        "I-Term": ("Time (s)", "I-Term"),
        "PID Output": ("Time (s)", "PID Output"),
        "Step Response": ("Time (s)", "Rate (deg/s)"),
        "Error Histogram": ("Error (deg/s)", "Count"),
        "Cumulative Error": ("Time (s)", "Cumulative |Error|")
    }
    return labels.get(plot_type, ("X", "Y"))

def is_histogram_plot(plot_type):
    """Check if the plot type should be rendered as a histogram"""
    return plot_type == "Error Histogram" 