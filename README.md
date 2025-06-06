# B4F: FL1GHT – Blackbox Log Viewer

A modern, feature-rich blackbox log viewer for FPV drone flight data analysis. Developed by **Born4Flight**, this application provides an intuitive interface for visualizing and analyzing flight data from Betaflight `.bbl` logs.

---

## ✨ Features

- **Multi-Chart Display**: View Roll, Pitch, Yaw, and Throttle data simultaneously  
- **Spectral Analyzer**: Analyze power spectral density (PSD) for Roll, Pitch, and Yaw axes  
  - Dual plots for each axis: full frequency range and zoomed-in 0–100 Hz view  
  - Interactive tooltips show frequency and PSD values on hover  
  - Adjustable smoothing (window size) for spectral analysis
- **Interactive Controls**:  
  - Zoom and pan with the mouse  
  - Selectable data types (gyro, PID, RC, etc.)  
  - Adjustable smoothing and resolution  
  - Customizable axis ticks and improved tab highlighting
- **Data Categories**:  
  - Gyro (raw, unfiltered, scaled)  
  - PID controller terms (P, I, D)  
  - RC commands  
  - Motor outputs
- **Responsive and Lightweight**:  
  - Built with PySide6  
  - Fast rendering with efficient memory usage  
  - Minimal dependencies

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

---
