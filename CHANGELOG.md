# Changelog

All notable changes to this project will be documented in this file.

## [0.4.4] - 2025-06-09

### Added
- Multi-log color support: Each log uses a distinct color palette 
- Legends now show each feature for each log, with log names and correct colors.
- Step Response PID legend displays Feed Forward (FF) and D_min values parsed from the BBL header

### Fixed
- Legend formatting

### Changed
- PID, Feed Forward, and D_min values are now always shown in the Step Response legend for each axis, with improved formatting
- Improved debug output and ensured color assignments are consistent for plots and legends

---

## [0.4.3] - 2025-06-09

### Added
- Added multi-flight loading mechanism:
  - Support for loading and selecting individual flights from multi-flight BBL files
  - Flight selection dialog with duration and size information
  - Support for selecting up to 5 flights in Step Response tab for comparison
  - Support for selecting up to 2 flights in Spectral Analysis tab
- Added automatic deselection of logs when switching between tabs
- Added improved handling of spectral analysis checkbox selection
- Added proper separation of spectral and step response log selection handlers

### Improved
- Enhanced signal handling for checkbox and log selection events
- Improved error handling for signal disconnections
- Better state management when switching between analysis modes

### Fixed
- Fixed spectral analysis checkbox selection to properly handle all checkboxes
- Fixed step response mode to correctly handle 5-file limit
- Fixed tab switching to maintain clean state between different analysis modes
- Fixed signal disconnection warnings

---

## [0.4.2] - 2025-06-08

### Added
- Multi-log loading and selection:
  - Load and display multiple logs in a list
  - Select one or more logs for plotting
  - Multi-selection and single-selection UI modes
- Multi-log plotting:
  - Plot multiple logs at once in Spectral Analysis and Step Response tabs

### Improved
- UI/UX:
  - More compact log selector (combo box for single selection)
  - Space-efficient and modern layout
- Plot clearing:
  - All plots and annotation labels are cleared before plotting new data to prevent caching/overlays
- Annotation management:
  - Robust handling to prevent crashes and segmentation faults

### Fixed
- Prevented double-attaching axes ("Axis already attached to series" warning)
- Safely deleted annotation proxies and handled signal disconnects
- Removed debug print statements
- Various segmentation faults and warnings addressed

---

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