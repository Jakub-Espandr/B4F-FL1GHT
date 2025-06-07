# Changelog

All notable changes to this project will be documented in this file.

## [0.4.1] - 2025-06-08

### Added
- Plot Export feature:
  - New "Export Plots" tab for automatic export of current plots
  - One-click export with no additional configuration needed
  - Stacks all plots from the current tab into a single ultra-high-resolution JPEG image
  - Detailed two-line header with log name, date and tab-specific settings:
    - Time Domain: Line width and zoom level
    - Spectral Analysis: Smoothing window size
    - Frequency Analysis: Gain setting
  - Publication-quality 1200 DPI resolution for maximum detail
  - 3x higher resolution than screen display for exceptional clarity
  - Maximum-quality JPEG format (99% quality) for optimal image fidelity
  - Antialiased rendering with enhanced quality settings
  - Maintains original layout with plots arranged vertically
  - Timestamped filenames for easy organization
  - "Return to Previous Tab" functionality

  ---

## [0.4.0] - 2025-06-07

### Added
- Frequency Analyzer tab with noise plots (heatmaps) for gyro data:
  - Six-panel layout showing noise analysis for Roll, Pitch, and Yaw axes
  - Logarithmic frequency scaling for better noise analysis
  - Proper colorbar placement and styling
  - Data normalization and smoothing

### Improved
- Major refactor and enhancement of `core/chart_manager.py`:
  - Improved axis handling
  - Added zero reference lines for Roll, Pitch, and Yaw charts
  - Enhanced legend update logic
  - Added interactive tooltips and crosshair cursor
  - Improved data decimation for performance on large datasets
  - Refactored code for maintainability and integration with feature widgets

---

## [0.3.0] - 2025-06-06

### Added
- Step response plots for Roll, Pitch, and Yaw
- Interactive tooltips for step response charts (showing time and value on hover)
- Annotation box showing max response and response time for each axis

---

## [0.2.0] - 2025-06-06

### Added
- Spectral Analyzer tab with power spectral density (PSD) plots for Roll, Pitch, and Yaw axes
- Dual-plot layout for each axis: full frequency range and zoomed-in 0–100 Hz view
- Interactive tooltips showing frequency and PSD values on hover
- Smoothing (window size) control for spectral analysis

### Improved
- Active tab highlighting
- Frequency axis ticks and label formatting for better readability
- UI layout adjustments for clarity
- Legend improvements

### Fixed
- Time axis normalization and display in seconds
- Symmetric y-axis scaling for time domain plots
- Various import and plotting bugs

---

## [0.1.0] - 2025-06-05

### Added
- Initial project setup
- Basic blackbox log viewer functionality
- Simple data visualization
- File loading and parsing
- Initial UI implementation
- Multi-chart display for Roll, Pitch, Yaw, and Throttle data
- Interactive zoom and scroll controls
- Data decimation for performance optimization
- Support for multiple data categories:
  - Gyro data (raw and filtered)
  - PID controller data
  - RC commands
  - Motor outputs
  - Throttle data
- Modern UI with custom fonts and icons
- Cross-platform support (Windows, macOS, Linux)
- Chart manager for handling multiple data views
- Custom widgets for feature selection and controls
- Data processing utilities
- Configuration system
- Modular code structure:
  - Separated core functionality into dedicated modules
  - Created reusable UI components
  - Centralized configuration management
  - Improved data processing utilities
- Memory optimization for large log files
- Smooth rendering of large datasets
- Proper handling of different time formats
- Accurate data scaling and normalization