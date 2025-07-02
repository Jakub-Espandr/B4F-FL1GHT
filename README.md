<p align="center">
  <a href="https://i.imghippo.com/files/Dk2733PtA.png">
    <img src="https://i.imghippo.com/files/Dk2733PtA.png" alt="B4F: FL1GHT Logo" width="250"/>
  </a>
</p>

<h1 align="center">B4F: FL1GHT</h1>
<p align="center"><em>(Born4Flight | FlyCamCzech)</em></p>

## Overview
A modern, feature-rich blackbox log viewer for FPV drone flight data analysis. Developed by **Born4Flight**, this application provides an intuitive interface for visualizing and analyzing flight data from Betaflight `.bbl` logs.

---

## ✨ Features

- **Time Domain Analyzer**
  - View Roll, Pitch, Yaw, Throttle and more simultaneously in time
- **Frequency Domain Analyzer**
  - Power spectral density (PSD) for Roll, Pitch, and Yaw
  - Dual plots: full range and 0–100 Hz zoom
  - Interactive tooltips and adjustable smoothing
- **Step Response Analysis**
  - Visualize step response for all axes
  - Interactive tooltips and annotation box
- **Noise Analysis**
  - Advanced noise analysis with heatmap visualization
  - Six-panel layout for Roll, Pitch, Yaw (filtered/raw/D-Term)
  - Logarithmic frequency scaling and data normalization
- **Frequency Evolution**
  - Spectrogram visualization showing frequency content over time
  - Heatmap display with configurable window size control
- **Error & Performance Analysis**
  - Comprehensive drone performance evaluation with six analysis types:
    - **Tracking Error**: Setpoint vs actual gyro response analysis
    - **I-Term**: Integral term behavior and saturation detection
    - **PID Output**: Combined P+I+D controller output analysis
    - **Step Response**: Setpoint and actual traces with dual-line visualization
    - **Error Histogram**: Statistical error distribution with KDE overlay
    - **Cumulative Error**: Running sum of tracking errors over time
  - Multi-axis support for Roll, Pitch, and Yaw with dedicated charts
  - Professional visualization with consistent scaling and zero-reference lines
  - Interactive radio button controls for switching between analysis types

- **Export Plots**
  - One-click export of all plots as 1200 DPI JPEG images
  - Stacked layout, detailed headers, and timestamped filenames
  - Antialiased, publication-quality output
- **Drone Config Tab**
  - View all parsed Betaflight `.bbl` header parameters in a clean, scrollable table
  - **Multi-log comparison:** Select up to two logs to compare parameters side-by-side, with options to highlight or show only differences.

- **Interactive Controls**
  - Zoom, pan, and select data types
  - Customizable smoothing, resolution, and axis ticks
- **Click-to-Expand Charts**
  - Click any chart to expand it to full screen for detailed analysis
  - Available in Time Domain, Frequency Domain, and Step Response tabs
  - Second click restores original layout with equal heights
  - Maintains all interactive features (tooltips, zoom, annotations) during expansion
- **Responsive and Lightweight**
  - Built with PySide6 for fast, efficient rendering
  - Minimal dependencies
- **Multi-Log Support**
  - Load and select multiple logs for analysis
  - Plot multiple logs simultaneously in Frequency Domain and Step Response tabs
- **Multi-Flight BBL Support**
  - Load and analyze individual flights from multi-flight BBL files
  - Flight selection dialog with duration and size information
  - Support for different flight limits per analysis mode:
    - Time Domain: Single flight
    - Frequency Domain: Up to 2 flights
    - Step Response: Up to 5 flights
    - Noise Analysis: Single flight
    - Frequency Evolution: Single flight
    - Error & Performance: Single flight
    - Drone Config: Up to 2 flights

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

1. Select a `.bbl` blackbox file when prompted  
2. Choose signals to visualize (e.g., `gyro (raw)`, `gyro (filtered)`, `D-Term`)  
3. View interactive charts  
4. Zoom, pan, and analyze your flight data

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
