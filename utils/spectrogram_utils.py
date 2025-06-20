"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import numpy as np
from scipy.signal import spectrogram

def calculate_spectrogram(df, axis_idx, gyro_type='filtered', max_freq=1000, gain=1.0, clip_seconds=1.0, nperseg=None, noverlap=None):
    """
    Calculate the spectrogram for a given axis and gyro type from a DataFrame.
    Returns a dict: {'t': t, 'f': f, 'Sxx': Sxx} or None if not enough data.
    nperseg and noverlap can be set for time/frequency resolution control.
    """
    if gyro_type == 'raw':
        col_pattern = f'gyroUnfilt[{axis_idx}]'
    else:
        col_pattern = f'gyroADC[{axis_idx}] (deg/s)'
    if col_pattern not in df.columns:
        return None
    data = df[col_pattern].values.astype(float)
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    # Clip first and last 1s
    mask = (time > clip_seconds) & (time < (time.max() - clip_seconds))
    if not np.any(mask):
        return None
    data = data[mask]
    time = time[mask]
    if len(data) < 2:
        return None
    dt = np.mean(np.diff(time))
    fs = 1.0 / dt if dt > 0 else 0.0
    if fs <= 0:
        return None
    # Use provided nperseg/noverlap or defaults
    if nperseg is None:
        nperseg = min(1024, len(data))
    if noverlap is None:
        noverlap = int(nperseg * 0.5)
    f, t, Sxx = spectrogram(data, fs=fs, nperseg=nperseg, noverlap=noverlap, scaling='density')
    # Limit frequency axis to max_freq
    freq_mask = f <= max_freq
    f = f[freq_mask]
    Sxx = Sxx[freq_mask, :]
    Sxx = Sxx * gain
    return {'t': t, 'f': f, 'Sxx': Sxx} 