<p align="center">
  <a href="https://i.imghippo.com/files/Dk2733PtA.png">
    <img src="https://i.imghippo.com/files/Dk2733PtA.png" alt="B4F: FL1GHT Logo" width="250"/>
  </a>
</p>

<h1 align="center">B4F: FL1GHT</h1>
<p align="center"><em>(Born4Flight | FlyCamCzech)</em></p>

## Overview
A modern, feature-rich blackbox log viewer for FPV drone flight data analysis. Developed by **Born4Flight**, this application provides an intuitive interface for visualizing and analyzing flight data from Betaflight `.bbl` logs.

**Latest Version: 0.7.1** - Enhanced noise analysis with 4-plot system, accurate flight duration calculation, and comprehensive help system.

### 🆕 **What's New in v0.7.1**
- **Enhanced Noise Analysis**: Advanced 3×4 grid visualization with filtered/unfiltered comparisons
- **Accurate Duration Calculation**: Real-time flight duration using actual time data instead of file size estimation
- **Improved Raw Data Detection**: Better `gyroUnfilt` column detection for more accurate analysis
- **Comprehensive Help System**: Complete user guide with detailed explanations and troubleshooting
- **Enhanced UI Feedback**: Loading messages with progress indicators and automatic cleanup

---

## ✨ Features

### 🎯 **Core Analysis Tabs**

- **⏱️ Time Domain Analysis**
  - Real-time visualization of Roll, Pitch, Yaw, Throttle, and system data
  - Interactive zoom controls, scroll navigation, and line width adjustment
  - Comprehensive data selection: Gyro (raw/filtered), PID terms, RC commands, Motor outputs

- **📈 Frequency Domain Analysis**
  - Power spectral density (PSD) for vibration and noise detection
  - Dual plots: full range (0-1000Hz) and zoomed view (0-100Hz)
  - Interactive tooltips, adjustable smoothing (1-10 levels)
  - Multi-flight comparison (up to 2 flights simultaneously)

- **⚡ Step Response Analysis**
  - Control loop response validation for PID tuning
  - Automatic step detection with response metrics (rise time, overshoot, settling time)
  - PID values display with annotation boxes
  - Multi-flight comparison (up to 5 flights for tuning evolution)

- **🔊 Noise Analysis (4-Plot System)**
  - Advanced 3×4 grid visualization with four plot types per axis:
    - **Gyro (Filtered)**: Processed gyroscope data
    - **Gyro (Raw)**: Unfiltered gyroscope data using `gyroUnfilt` columns
    - **D-Term (Filtered)**: Processed derivative term
    - **D-Term (Unfiltered)**: Raw derivative term calculated as `derivative(raw gyro) × D-gain`
  - Logarithmic scaling, gain adjustment (1x-10x), interactive tooltips
  - D-gain extraction from BBL headers for accurate unfiltered D-term calculation

- **🌊 Frequency Evolution (Spectrogram)**
  - Time-frequency analysis showing frequency content changes during flight
  - Configurable window size (2^8 to 2^14 samples) for detail vs overview
  - Gain control and interactive tooltips for time, frequency, and power values

- **⚠️ Error & Performance Analysis**
  - Comprehensive flight performance evaluation with six analysis types:
    - **Tracking Error**: Setpoint vs actual gyro response analysis
    - **I-Term**: Integral term behavior and saturation detection
    - **PID Output**: Combined P+I+D controller output analysis
    - **Step Response**: Setpoint and actual traces with dual-line visualization
    - **Error Histogram**: Statistical error distribution with KDE overlay
    - **Cumulative Error**: Running sum of tracking errors over time
  - Professional visualization with consistent scaling and zero-reference lines
  - Interactive radio button controls for switching between analysis types

- **⚙️ Drone Configuration Analysis**
  - Complete parameter table from BBL headers with organized sections
  - Multi-log comparison with side-by-side parameter analysis
  - Difference highlighting and filtering options
  - Color-coded comparison (green for log 1, blue for log 2)

### 🎮 **Interactive Features**

- **Click-to-Expand Charts**
  - Click any chart to expand it to full screen for detailed analysis
  - Available across all analysis tabs
  - Second click restores original layout with equal heights
  - Maintains all interactive features (tooltips, zoom, annotations) during expansion

- **Multi-Flight Support**
  - Load and analyze individual flights from multi-flight BBL files
  - **Accurate Duration Calculation**: Real-time duration calculation using actual time data
  - Flight selection dialog with progress feedback and success/warning indicators
  - Support for different flight limits per analysis mode:
    - Time Domain: Single flight
    - Frequency Domain: Up to 2 flights
    - Step Response: Up to 5 flights
    - Noise Analysis: Single flight
    - Frequency Evolution: Single flight
    - Error & Performance: Single flight
    - Drone Config: Up to 2 flights

- **Export System**
  - One-click export of all plots as 1200 DPI JPEG images
  - Publication-quality output with antialiasing
  - Stacked layout with detailed headers and timestamped filenames
  - Configurable author name, drone name, and export directory

- **Comprehensive Help System**
  - Complete user guide with detailed explanations of all features
  - Tips & best practices for different analysis workflows
  - Troubleshooting section with common issues and solutions
  - Technical details about analysis methods and data processing

### 🔧 **Advanced Features**

- **Statistical Analysis**
  - Error distribution analysis with KDE (Kernel Density Estimation)
  - Peak detection for resonant frequencies
  - Outlier filtering for cleaner analysis
  - Global scaling for consistent histogram comparison

- **PID Tuning Support**
  - Step response metrics (rise time, overshoot, settling time)
  - I-term saturation detection
  - D-term effectiveness evaluation
  - Multi-flight comparison for tuning evolution

- **Vibration Analysis**
  - Frequency domain analysis for motor and propeller resonances
  - Throttle-dependent vibration analysis with 2D histograms
  - Filter performance comparison (filtered vs unfiltered)
  - Time-frequency analysis for transient vibration events

### 🚀 **Performance & Usability**

- **Responsive and Lightweight**
  - Built with PySide6 for fast, efficient rendering
  - Minimal dependencies and optimized memory usage
  - Automatic data decimation for large files

- **Robust Error Handling**
  - Graceful fallback mechanisms for missing data
  - Comprehensive debug logging with verbose mode
  - User-friendly error messages and warnings

- **Cross-Platform Support**
  - Windows, macOS, and Linux compatibility
  - Custom fonts and modern UI design
  - Consistent experience across platforms

---

## 📦 Requirements

- Python 3.8+
- [PySide6](https://doc.qt.io/qtforpython/) >= 6.0.0 – Qt bindings for Python (UI framework)
- [pandas](https://pandas.pydata.org/) >= 1.3.0 – Data manipulation and CSV parsing
- [numpy](https://numpy.org/) >= 1.21.0 – Numerical computing and array operations
- [matplotlib](https://matplotlib.org/) >= 3.4.0 – Plotting backend (for some visualizations)
- [scipy](https://scipy.org/) >= 1.7.0 – Signal processing (FFT, frequency domain analysis)
- `blackbox_decode` – CLI tool for decoding `.bbl` to `.csv` (included in `tools/`)

---

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/Jakub-Espandr/B4F-FL1GHT.git
cd B4F-FL1GHT

# (Optional) Create and activate virtual environment
python -m venv venv
source venv/bin/activate    # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Ensure blackbox decoder is executable
chmod +x tools/blackbox_decode
```

---

## 🛠️ Usage

```bash
python main.py
```

### 📋 **Quick Start Guide**

1. **Load Flight Data**
   - Click "Select BBL" to choose your Betaflight blackbox file
   - For multi-flight files, select the desired flight from the dialog
   - Flight duration is calculated in real-time for accurate timing

2. **Select Analysis Features**
   - Choose data types to analyze (Gyro, PID terms, Motors, etc.)
   - Different tabs support different data requirements
   - Missing data warnings help identify available features

3. **Analyze Your Data**
   - Use the tab system to access different analysis types
   - Click charts to expand them for detailed analysis
   - Hover over plots for interactive tooltips with precise values

4. **Export Results**
   - Use the Export tab for high-quality image generation
   - Configure author name, drone name, and export directory
   - Publication-ready 1200 DPI output with detailed headers

### 📚 **Help & Documentation**
- **Built-in Help**: Access comprehensive user guide from the Help tab
- **Tips & Best Practices**: Workflow recommendations for different analysis types
- **Troubleshooting**: Common issues and solutions
- **Technical Details**: Analysis methods and data processing information

---

## 📁 Project Structure

```
B4F-FL1GHT/
├── main.py                  # Entry point
├── core/
│   ├── fl1ght_viewer.py     # Main viewer window
│   └── chart_manager.py     # Plot logic
├── ui/
│   └── widgets.py           # UI components
├── utils/
│   ├── data_processor.py    # CSV parsing and prep
│   └── config.py            # Constants and settings
├── tools/
│   └── blackbox_decode      # Decoder executable
└── assets/
    ├── icons/               # Application icons
    └── fonts/               # Custom fonts
```

---

## 🔐 License

This project is licensed under the **Non-Commercial Public License (NCPL v1.0)**  
© 2025 Jakub Ešpandr - Born4Flight, FlyCamCzech

See the [LICENSE](https://github.com/Jakub-Espandr/B4F-FL1GHT/raw/main/LICENSE) file for full terms.

---

## 🙏 Acknowledgments

- Built with ❤️ using PySide6 and open-source libraries
