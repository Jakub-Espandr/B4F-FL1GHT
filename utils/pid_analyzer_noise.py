"""
This file is part of a project licensed under the Non-Commercial Public License (NCPL).
See LICENSE file or contact the authors for full terms.
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
import matplotlib.colors as colors
from matplotlib.gridspec import GridSpec
import pandas as pd
import logging
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.gridspec as gridspec
import os, sys, json

def spectrum(time, traces):
    """Calculate spectrum (frequency domain) from time domain data"""
    pad = 1024 - (len(traces[0]) % 1024)
    traces = np.pad(traces, [[0, 0], [0, pad]], mode='constant')
    trspec = np.fft.rfft(traces, axis=-1, norm='ortho')
    trfreq = np.fft.rfftfreq(len(traces[0]), time[1] - time[0])
    return trfreq, trspec

def process_gyro_data(time, gyro, throttle, name="", gain=1.0):
    """Process gyro data for a single axis (roll/pitch/yaw)"""
    # Windowing parameters (same as PID-Analyzer)
    noise_framelen = 0.3
    noise_superpos = 16
    
    tlen = len(time)
    dt = time[1] - time[0]
    winlen = int(noise_framelen / dt)
    shift = int(winlen / noise_superpos)
    wins = int(tlen / shift) - noise_superpos
    
    logging.info(f"Processing {name}: time len={tlen}, dt={dt:.6f}, winlen={winlen}, wins={wins}, gain={gain}")
    # Print detailed stats only at VERBOSE (INFO level if VERBOSE, else DEBUG)
    try:
        app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        config_dir = os.path.join(app_dir, "config")
        settings_path = os.path.join(config_dir, "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                debug_level = settings.get('debug_level', 'INFO')
    except Exception:
        pass
    if debug_level == "VERBOSE":
        logging.info(f"Data stats: gyro min/max={np.min(gyro)}/{np.max(gyro)}, throttle min/max={np.min(throttle)}/{np.max(throttle)}")
    else:
        logging.debug(f"Data stats: gyro min/max={np.min(gyro)}/{np.max(gyro)}, throttle min/max={np.min(throttle)}/{np.max(throttle)}")
    
    # Stack windows
    if wins <= 0:
        logging.warning(f"Not enough data for windowing: wins={wins}")
        return None
    
    data_windows = []
    throttle_windows = []
    for i in range(wins):
        start_idx = i * shift
        end_idx = start_idx + winlen
        if end_idx > len(gyro):
            break
        data_windows.append(gyro[start_idx:end_idx])
        throttle_windows.append(throttle[start_idx:end_idx])
    
    if not data_windows:
        logging.warning(f"No valid windows created")
        return None
    
    data_windows = np.array(data_windows)
    throttle_windows = np.array(throttle_windows)
    
    # Apply window function
    window = np.hanning(winlen)
    data_windows = data_windows * window
    
    # Calculate spectrum
    freq, spec = spectrum(time[:winlen], data_windows)
    
    # Calculate mean throttle for each window
    mean_throttle = np.mean(throttle_windows, axis=1)
    
    # Create 2D histogram of spectral power vs throttle
    weights = np.abs(spec.real)
    hist_bins = [101, int(len(freq) / 4)]
    
    # Create throttle-frequency histogram
    hist2d = create_2d_histogram(mean_throttle, freq, weights, hist_bins)
    
    # Smooth the histogram
    hist2d_sm = gaussian_filter1d(hist2d['hist2d_norm'], 3, axis=1, mode='constant')
    
    # Apply gain to the smoothed histogram
    hist2d_sm = hist2d_sm * gain
    
    # Find maximum value
    maxval = np.max(hist2d_sm) if hist2d_sm.size > 0 else 1.0
    
    return {
        'throt_hist': hist2d['throt_hist'],
        'throt_axis': hist2d['throt_scale'],
        'freq_axis': freq[::4],
        'hist2d_norm': hist2d['hist2d_norm'],
        'hist2d_sm': hist2d_sm,
        'hist2d': hist2d['hist2d'],
        'max': maxval
    }

def create_2d_histogram(x, y, weights, bins):
    """Create a 2D histogram of weights mapped to x,y coordinates"""
    # Prepare histogram
    freqs = np.repeat(np.array([y], dtype=np.float64), len(x), axis=0)
    throts = np.repeat(np.array([x], dtype=np.float64), len(y), axis=0).transpose()
    
    # Get throttle histogram for normalization
    throt_hist, throt_scale = np.histogram(x, 101, [0, 100])
    
    # Create 2D histogram
    hist2d = np.histogram2d(
        throts.flatten(), freqs.flatten(),
        range=[[0, 100], [y[0], y[-1]]],
        bins=bins, weights=weights.flatten(), density=False
    )[0].transpose()
    
    # Process histogram
    hist2d = np.array(abs(hist2d), dtype=np.float64)
    hist2d_norm = np.copy(hist2d)
    
    # Normalize by throttle count
    nonzero_mask = throt_hist > 0
    for i in range(hist2d_norm.shape[1]):
        if i < len(nonzero_mask) and nonzero_mask[i]:
            hist2d_norm[:, i] /= throt_hist[i]
    
    return {
        'hist2d_norm': hist2d_norm,
        'hist2d': hist2d,
        'throt_hist': throt_hist,
        'throt_scale': throt_scale
    }

def plot_noise_from_df(df, max_freq=1000, gain=1.0):
    """Create PID-Analyzer style noise plot from DataFrame"""
    logging.info(f"Starting plot_noise_from_df with DataFrame shape: {df.shape}, gain={gain}")
    
    # Prepare time data
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    
    # Find throttle column
    throttle_col = None
    for col in df.columns:
        if 'rccommand[3]' in col.lower() or 'throttle' in col.lower():
            throttle_col = col
            break
    
    if throttle_col is None:
        logging.error("No throttle column found")
        return plt.figure()
    
    # Process throttle data
    throttle = df[throttle_col].values.astype(float)
    if throttle.max() > 500:
        throttle = ((throttle - 1000) / 10).clip(0, 100)
    else:
        throttle = throttle.clip(0, 100)
    
    # Find gyro and debug columns
    gyro_data = []
    debug_data = []
    
    for axis_idx, axis_name in enumerate(['roll', 'pitch', 'yaw']):
        # Try to find gyro column
        gyro_col = None
        for pattern in [f'gyroADC[{axis_idx}] (deg/s)', f'gyroADC[{axis_idx}]', f'gyro[{axis_idx}]']:
            if pattern in df.columns:
                gyro_col = pattern
                break
        
        # Try to find debug column
        debug_col = None
        for pattern in [f'debug[{axis_idx}]', f'debug{axis_idx}']:
            if pattern in df.columns:
                debug_col = pattern
                break
        
        if gyro_col:
            gyro = df[gyro_col].values.astype(float)
        else:
            logging.warning(f"No gyro column found for {axis_name}")
            gyro = np.zeros_like(time)
        
        if debug_col:
            debug = df[debug_col].values.astype(float)
        else:
            logging.warning(f"No debug column found for {axis_name}")
            debug = np.zeros_like(time)
        
        # Process data with gain
        gyro_result = process_gyro_data(time, gyro, throttle, name=f"gyro {axis_name}", gain=gain)
        debug_result = process_gyro_data(time, debug, throttle, name=f"debug {axis_name}", gain=gain)
        
        if gyro_result is not None:
            gyro_data.append((axis_name, gyro_result))
        if debug_result is not None:
            debug_data.append((axis_name, debug_result))
    
    # Create figure with GridSpec
    fig = plt.figure(figsize=(40, 32))
    fig.patch.set_facecolor('white')
    gs = gridspec.GridSpec(3, 3, wspace=0.01, hspace=0.01)
    
    # Create colorbars
    cax_gyro = fig.add_subplot(gs[0, 0:7])
    cax_debug = fig.add_subplot(gs[0, 8:15])
    
    # Calculate color normalization
    if gyro_data:
        vmin_gyro = 1
        vmax_gyro = max(data[1]['max'] for data in gyro_data) + 1
    else:
        vmin_gyro, vmax_gyro = 1, 10
    
    if debug_data:
        vmin_debug = 1
        vmax_debug = max(data[1]['max'] for data in debug_data) + 1
    else:
        vmin_debug, vmax_debug = 1, 10
    
    # Plot each axis
    for i, ((axis_name, gyro_result), (_, debug_result)) in enumerate(zip(gyro_data, debug_data)):
        # Gyro plot
        ax_gyro = fig.add_subplot(gs[1+i*8:1+i*8+8, 0:7])
        ax_gyro.set_facecolor('black')
        
        # Plot gyro data
        pc_gyro = ax_gyro.pcolormesh(
            gyro_result['throt_axis'], 
            gyro_result['freq_axis'], 
            gyro_result['hist2d_sm'] + 1e-6,
            norm=colors.LogNorm(vmin=vmin_gyro, vmax=vmax_gyro),
            cmap='inferno'
        )
        
        # Style the gyro plot
        ax_gyro.set_ylabel('frequency in Hz', color='white')
        ax_gyro.set_ylim(0, max_freq)
        ax_gyro.grid(True, color='white', alpha=0.3, linestyle='-')
        
        # Set tick colors
        ax_gyro.tick_params(axis='x', colors='white')
        ax_gyro.tick_params(axis='y', colors='white')
        for spine in ax_gyro.spines.values():
            spine.set_color('white')
        
        # Only show x label on bottom plot
        if i == len(gyro_data)-1:
            ax_gyro.set_xlabel('throttle in %', color='white')
        else:
            ax_gyro.set_xticklabels([])
        
        # Debug plot
        ax_debug = fig.add_subplot(gs[1+i*8:1+i*8+8, 8:15])
        ax_debug.set_facecolor('black')
        
        # Plot debug data
        pc_debug = ax_debug.pcolormesh(
            debug_result['throt_axis'], 
            debug_result['freq_axis'], 
            debug_result['hist2d_sm'] + 1e-6,
            norm=colors.LogNorm(vmin=vmin_debug, vmax=vmax_debug),
            cmap='inferno'
        )
        
        # Style the debug plot
        ax_debug.set_ylabel('frequency in Hz', color='white')
        ax_debug.set_ylim(0, max_freq)
        ax_debug.grid(True, color='white', alpha=0.3, linestyle='-')
        
        # Set tick colors
        ax_debug.tick_params(axis='x', colors='white')
        ax_debug.tick_params(axis='y', colors='white')
        for spine in ax_debug.spines.values():
            spine.set_color('white')
        
        # Only show x label on bottom plot
        if i == len(debug_data)-1:
            ax_debug.set_xlabel('throttle in %', color='white')
        else:
            ax_debug.set_xticklabels([])
    
    # Add colorbars
    if gyro_data:
        cb_gyro = fig.colorbar(pc_gyro, cax=cax_gyro, orientation='horizontal')
        cb_gyro.ax.xaxis.set_ticks_position('top')
        cb_gyro.ax.tick_params(colors='black', labelcolor='black')
        
        # Remove ticks and labels
        cb_gyro.ax.set_xticks([])
        cb_gyro.ax.set_xticklabels([])
        cb_gyro.ax.tick_params(axis='x', bottom=False, top=False)
        
        # Remove all spines (borders) around the colorbar
        for spine in cb_gyro.ax.spines.values():
            spine.set_visible(False)
    
    if debug_data:
        cb_debug = fig.colorbar(pc_debug, cax=cax_debug, orientation='horizontal')
        cb_debug.ax.xaxis.set_ticks_position('top')
        cb_debug.ax.tick_params(colors='black', labelcolor='black')
        
        # Remove ticks and labels
        cb_debug.ax.set_xticks([])
        cb_debug.ax.set_xticklabels([])
        cb_debug.ax.tick_params(axis='x', bottom=False, top=False)
        
        # Remove all spines (borders) around the colorbar
        for spine in cb_debug.ax.spines.values():
            spine.set_visible(False)
    
    # Add info text including gain value
    ax_info = fig.add_subplot(gs[23:25, 0:15])
    ax_info.text(0.5, 0.5, f'PID-Analyzer style noise plot (Gain: {gain}x)', 
                ha='center', va='center', color='white', alpha=0.7)
    ax_info.axis('off')
    
    # Big shared axis labels
    fig.text(0.5, 0.025, "Throttle (%)", ha='center', va='center', fontsize=26, color='black', weight='bold')
    fig.text(0.015, 0.5, "Frequency (Hz)", ha='center', va='center', fontsize=26, color='black', weight='bold', rotation=90)
    # Column headers, aligned to plot centers
    col_xs = [0.17, 0.5, 0.83]
    col_titles = ["Gyro (filtered)", "Gyro (raw)", "D-Term"]
    for i, title in enumerate(col_titles):
        fig.text(col_xs[i], 0.965, title, ha='center', va='bottom', fontsize=16, color='black', weight='bold', family='sans-serif')
    # Row headers
    row_titles = ["Roll", "Pitch", "Yaw"]
    row_y_positions = [0.80, 0.65, 0.70]  # Moved Yaw higher from 0.60 to 0.70 to be more centered
    for i, title in enumerate(row_titles):
        fig.text(0.06, row_y_positions[i], title, ha='right', va='center', fontsize=12, color='black', weight='bold', rotation=90, family='sans-serif')
    
    return fig

# For backwards compatibility
def plot_all_noise_from_df(df, headdict=None, max_freq=1000, gain=1.0):
    """Compatibility function that calls the new implementation"""
    return plot_noise_from_df(df, max_freq, gain)

def generate_individual_noise_figures(df, max_freq=1000, gain=1.0):
    """Generate six individual matplotlib Figures for gyro/debug (roll, pitch, yaw)"""
    time = df['time'].values.astype(float)
    if time.max() > 1e6:
        time = time / 1_000_000.0
    elif time.max() > 1e3:
        time = time / 1_000.0
    time = time - time.min()
    throttle_col = None
    for col in df.columns:
        if 'rccommand[3]' in col.lower() or 'throttle' in col.lower():
            throttle_col = col
            break
    if throttle_col is None:
        return []
    throttle = df[throttle_col].values.astype(float)
    if throttle.max() > 500:
        throttle = ((throttle - 1000) / 10).clip(0, 100)
    else:
        throttle = throttle.clip(0, 100)
    figures = []
    axis_labels = ['Roll', 'Pitch', 'Yaw']
    for axis_idx, axis_name in enumerate(axis_labels):
        # Gyro
        gyro_col = None
        for pattern in [f'gyroADC[{axis_idx}] (deg/s)', f'gyroADC[{axis_idx}]', f'gyro[{axis_idx}]']:
            if pattern in df.columns:
                gyro_col = pattern
                break
        if gyro_col:
            gyro = df[gyro_col].values.astype(float)
        else:
            gyro = np.zeros_like(time)
        gyro_result = process_gyro_data(time, gyro, throttle, name=f"gyro {axis_name}", gain=gain)
        fig_gyro = plt.figure(figsize=(7, 5))
        fig_gyro.patch.set_facecolor('white')
        ax_gyro = fig_gyro.add_subplot(111)
        if gyro_result is not None:
            pc_gyro = ax_gyro.pcolormesh(
                gyro_result['throt_axis'],
                gyro_result['freq_axis'],
                gyro_result['hist2d_sm'] + 1e-6,
                norm=colors.LogNorm(vmin=1, vmax=gyro_result['max']+1),
                cmap='inferno'
            )
            ax_gyro.set_title(f'Gyro (filtered) {axis_name}', color='black', loc='left', pad=5)
            ax_gyro.set_ylabel('Frequency (Hz)', color='black')
            ax_gyro.set_xlabel('Throttle (%)', color='black')
            ax_gyro.set_ylim(0, max_freq)
            ax_gyro.set_xlim(0, 100)
            ax_gyro.set_facecolor('black')
            ax_gyro.grid(True, color='white', alpha=0.3, linestyle='-')
            ax_gyro.tick_params(axis='x', colors='black')
            ax_gyro.tick_params(axis='y', colors='black')
            for spine in ax_gyro.spines.values():
                spine.set_color('black')
            # Maximize plot area and eliminate black bar at top
            fig_gyro.tight_layout(pad=0.5)
        figures.append(fig_gyro)
        # Debug
        debug_col = None
        for pattern in [f'debug[{axis_idx}]', f'debug{axis_idx}']:
            if pattern in df.columns:
                debug_col = pattern
                break
        if debug_col:
            debug = df[debug_col].values.astype(float)
        else:
            debug = np.zeros_like(time)
        debug_result = process_gyro_data(time, debug, throttle, name=f"debug {axis_name}", gain=gain)
        fig_debug = plt.figure(figsize=(7, 5))
        fig_debug.patch.set_facecolor('white')
        ax_debug = fig_debug.add_subplot(111)
        if debug_result is not None:
            pc_debug = ax_debug.pcolormesh(
                debug_result['throt_axis'],
                debug_result['freq_axis'],
                debug_result['hist2d_sm'] + 1e-6,
                norm=colors.LogNorm(vmin=1, vmax=debug_result['max']+1),
                cmap='inferno'
            )
            ax_debug.set_title(f'Gyro (raw) {axis_name}', color='black', loc='left', pad=5)
            ax_debug.set_ylabel('Frequency (Hz)', color='black')
            ax_debug.set_xlabel('Throttle (%)', color='black')
            ax_debug.set_ylim(0, max_freq)
            ax_debug.set_xlim(0, 100)
            ax_debug.set_facecolor('black')
            ax_debug.grid(True, color='white', alpha=0.3, linestyle='-')
            ax_debug.tick_params(axis='x', colors='black')
            ax_debug.tick_params(axis='y', colors='black')
            for spine in ax_debug.spines.values():
                spine.set_color('black')
            # Maximize plot area and eliminate black bar at top
            fig_debug.tight_layout(pad=0.5)
        figures.append(fig_debug)
        # D-term
        dterm_col = f'axisD[{axis_idx}]'
        if dterm_col in df.columns:
            dterm = df[dterm_col].values.astype(float)
        else:
            dterm = np.zeros_like(time)
        dterm_result = process_gyro_data(time, dterm, throttle, name=f"dterm {axis_name}", gain=gain)
        fig_dterm = plt.figure(figsize=(7, 5))
        fig_dterm.patch.set_facecolor('white')
        ax_dterm = fig_dterm.add_subplot(111)
        if dterm_result is not None:
            pc_dterm = ax_dterm.pcolormesh(
                dterm_result['throt_axis'],
                dterm_result['freq_axis'],
                dterm_result['hist2d_sm'] + 1e-6,
                norm=colors.LogNorm(vmin=1, vmax=dterm_result['max']+1),
                cmap='inferno'
            )
            ax_dterm.set_title(f'D-Term {axis_name}', color='black', loc='left', pad=5)
            ax_dterm.set_ylabel('Frequency (Hz)', color='black')
            ax_dterm.set_xlabel('Throttle (%)', color='black')
            ax_dterm.set_ylim(0, max_freq)
            ax_dterm.set_xlim(0, 100)
            ax_dterm.set_facecolor('black')
            ax_dterm.grid(True, color='white', alpha=0.3, linestyle='-')
            ax_dterm.tick_params(axis='x', colors='black')
            ax_dterm.tick_params(axis='y', colors='black')
            for spine in ax_dterm.spines.values():
                spine.set_color('black')
            # Maximize plot area and eliminate black bar at top
            fig_dterm.tight_layout(pad=0.5)
        figures.append(fig_dterm)

    # Build results for all axes and types
    gyro_results = []
    debug_results = []
    dterm_results = []
    for idx in range(3):
        # Gyro
        gyro_col = None
        for pattern in [f'gyroADC[{idx}] (deg/s)', f'gyroADC[{idx}]', f'gyro[{idx}]']:
            if pattern in df.columns:
                gyro_col = pattern
                break
        if gyro_col:
            gyro = df[gyro_col].values.astype(float)
        else:
            gyro = np.zeros_like(time)
        gyro_results.append(process_gyro_data(time, gyro, throttle, name=f"gyro {axis_labels[idx]}", gain=gain))
        # Debug
        debug_col = None
        for pattern in [f'debug[{idx}]', f'debug{idx}']:
            if pattern in df.columns:
                debug_col = pattern
                break
        if debug_col:
            debug = df[debug_col].values.astype(float)
        else:
            debug = np.zeros_like(time)
        debug_results.append(process_gyro_data(time, debug, throttle, name=f"debug {axis_labels[idx]}", gain=gain))
        # D-term
        dterm_col = f'axisD[{idx}]'
        if dterm_col in df.columns:
            dterm = df[dterm_col].values.astype(float)
        else:
            dterm = np.zeros_like(time)
        dterm_results.append(process_gyro_data(time, dterm, throttle, name=f"dterm {axis_labels[idx]}", gain=gain))

    # Create a single figure with 9 axes (3x3)
    fig = plt.figure(figsize=(22, 20))
    fig.patch.set_facecolor('white')
    # Further adjust spacing to completely eliminate the black bar at top
    gs = gridspec.GridSpec(3, 3, wspace=0.2, hspace=0.3, top=0.94, bottom=0.13, left=0.08, right=0.95)
    axes = []
    all_pcs = []
    vmax_list = []
    for i, axis_name in enumerate(axis_labels):
        for j, (result, title) in enumerate(zip([gyro_results[i], debug_results[i], dterm_results[i]], [f'Gyro {axis_name}', f'Debug {axis_name}', f'D-Term {axis_name}'])):
            ax = fig.add_subplot(gs[i, j])
            ax.set_facecolor('black')
            if result is not None:
                pc = ax.pcolormesh(
                    result['throt_axis'],
                    result['freq_axis'],
                    result['hist2d_sm'] + 1e-6,
                    norm=colors.LogNorm(vmin=1, vmax=result['max']+1),
                    cmap='inferno'
                )
                all_pcs.append(pc)
                vmax_list.append(result['max']+1)
            if j == 0:
                ax.set_ylabel('Frequency (Hz)', color='black')
            else:
                ax.set_ylabel("")
            if i == 2:
                ax.set_xlabel('Throttle (%)', color='black')
            else:
                ax.set_xlabel("")
            ax.set_ylim(0, max_freq)
            ax.set_xlim(0, 100)
            ax.grid(True, color='white', alpha=0.3, linestyle='-')
            ax.tick_params(axis='x', colors='black')
            ax.tick_params(axis='y', colors='black')
            for spine in ax.spines.values():
                spine.set_color('black')
            # Set title inside the plot to avoid black space
            if j == 0:
                plot_title = f'Gyro (filtered) {axis_name}'
            elif j == 1:
                plot_title = f'Gyro (raw) {axis_name}'
            else:
                plot_title = f'D-Term {axis_name}'
            ax.set_title(plot_title, color='black', fontsize=10, pad=5, loc='left')
            axes.append(ax)

    # Add a single shared colorbar at the bottom
    if all_pcs:
        vmax_global = max(vmax_list)
        # Add a dedicated axis for the colorbar below the grid
        cbar_ax = fig.add_axes([0.15, 0.06, 0.7, 0.025])  # [left, bottom, width, height] in figure coordinates
        cbar = fig.colorbar(
            all_pcs[0], cax=cbar_ax, orientation='horizontal',
            norm=colors.LogNorm(vmin=1, vmax=vmax_global), cmap='inferno'
        )
        # Remove ticks and labels
        cbar.ax.set_xticks([])
        cbar.ax.set_xticklabels([])
        cbar.ax.tick_params(axis='x', bottom=False, top=False)
        
        # Remove all spines (borders) around the colorbar
        for spine in cbar.ax.spines.values():
            spine.set_visible(False)
    
    return [fig] 