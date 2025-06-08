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
- **Spectral Analyzer**
  - Power spectral density (PSD) for Roll, Pitch, and Yaw
  - Dual plots: full range and 0–100 Hz zoom
  - Interactive tooltips and adjustable smoothing
- **Step Response Analysis**
  - Visualize step response for all axes
  - Interactive tooltips and annotation box
- **Frequency Analyzer**
  - Advanced noise analysis with heatmap visualization
  - Six-panel layout for Roll, Pitch, Yaw (filtered/raw/D-Term)
  - Logarithmic frequency scaling and data normalization
- **Export Plots**
  - One-click export of all plots as 1200 DPI JPEG images
  - Stacked layout, detailed headers, and timestamped filenames
  - Antialiased, publication-quality output
- **Interactive Controls**
  - Zoom, pan, and select data types
  - Customizable smoothing, resolution, and axis ticks
- **Responsive and Lightweight**
  - Built with PySide6 for fast, efficient rendering
  - Minimal dependencies
- **Multi-Log Support**
  - Load and select multiple logs for analysis
  - Plot multiple logs simultaneously in Spectral Analysis and Step Response tabs

---

## 📦 Requirements

- Python 3.8+  
- [PySide6](https://doc.qt.io/qtforpython/) – Qt bindings for Python  
- [pandas](https://pandas.pydata.org/) – Data manipulation  
- [numpy](https://numpy.org/) – Numerical computing  
- [matplotlib](https://matplotlib.org/) – Plotting backend  
- [scipy](https://scipy.org/) – Signal processing  
- `blackbox_decode` – CLI tool for decoding `.bbl` to `.csv` (included in `tools/`)

---

## 🚀 Installation

```bash
git clone https://github.com/Jakub-Espandr/B4F-FL1GHT.git
cd b4f-fl1ght
```

Create a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
```

Install required Python libraries:

```bash
pip install -r requirements.txt
```

Ensure the decoder tool is executable:

```bash
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
b4f-fl1ght/
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
© 2025 Jakub Ešpandr - Born4FLight, FlyCamCzech

See the [LICENSE](https://github.com/Jakub-Espandr/B4F-FL1GHT/raw/main/LICENSE) file for full terms.

---

## 🙏 Acknowledgments

- Built with ❤️ using PySide6 and open-source libraries
