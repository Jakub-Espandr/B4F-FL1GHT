"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import numpy as np
import pandas as pd
from utils.config import DATA_CONFIG

def decimate_data(time_data, value_data, max_points=DATA_CONFIG['max_points']):
    """Decimate data to reduce number of points while preserving shape"""
    if len(time_data) <= max_points:
        return time_data, value_data
        
    # Calculate decimation factor
    factor = len(time_data) // max_points
    
    # Use numpy's stride tricks for efficient decimation
    time_decimated = time_data[::factor]
    value_decimated = value_data[::factor]
    
    # Always include the last point
    if time_decimated[-1] != time_data[-1]:
        time_decimated = np.append(time_decimated, time_data[-1])
        value_decimated = np.append(value_decimated, value_data[-1])
    
    return time_decimated, value_decimated

def process_axis_data(axis, df_dict, time_col, features):
    """Process data for a single axis in parallel"""
    # Convert dictionary back to DataFrame
    df = pd.DataFrame(df_dict)
    
    # Create series data
    series_data = []
    
    # Process each selected feature
    for feature in features:
        if feature in df.columns:
            time_data, value_data = decimate_data(df[time_col].values, df[feature].values)
            series_data.append({
                'name': feature,
                'time': time_data,
                'values': value_data
            })

    return series_data

def get_clean_name(feature_name):
    """Convert raw feature name to a clean, categorized name"""
    # Convert to lowercase for easier matching
    name = feature_name.lower()
    
    # Handle different types of features
    if 'gyrounfilt' in name:
        return "Gyro (raw)"
    elif '(deg/s)' in name:
        return "Gyro (filtered)"
    elif 'axisp' in name:
        return "P-Term"
    elif 'axisi' in name:
        return "I-Term"
    elif 'axisd' in name:
        return "D-Term"
    elif 'axisf' in name:
        return "FeedForward"
    elif 'setpoint' in name:
        return "Setpoint"
    elif 'rccommand' in name:
        if '[3]' in name:
            return "Throttle"
        else:
            return "RC Command"
    elif 'motor' in name:
        motor_num = name.split('[')[1].split(']')[0]
        return f"Motor {motor_num}"
    return feature_name

def normalize_time_data(df, time_col):
    """Normalize time data to start from zero and convert to seconds"""
    df = df.copy()
    df[time_col] = df[time_col].astype(float) / DATA_CONFIG['time_scale']
    df[time_col] = df[time_col] - df[time_col].min()
    return df 