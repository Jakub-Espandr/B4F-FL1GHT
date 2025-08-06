# Changelog

All notable changes to this project will be documented in this file.

## [0.7.1] - 2025-08-06

### Added
- **Enhanced Noise Analysis (4-Plot System)**: Advanced visualization with four plot types per axis:
  - **Gyro (Filtered)**: Processed gyroscope data visualization
  - **Gyro (Raw)**: Unfiltered gyroscope data using `gyroUnfilt` columns
  - **D-Term (Filtered)**: Processed derivative term analysis
  - **D-Term (Unfiltered)**: Raw derivative term calculated as `derivative(raw gyro) × D-gain`
  - **3×4 Grid Layout**: Roll, Pitch, Yaw for each signal type with consistent scaling
  - **D-Gain Extraction**: Automatic parsing of PID parameters from BBL headers for accurate unfiltered D-term calculation
  - **Interactive Features**: Logarithmic scaling, gain adjustment (1x-10x), interactive tooltips

### Improved
- **Flight Duration Calculation**: Replaced file size estimation with actual time-based duration calculation:
  - **Accurate Duration**: Uses `blackbox_decode` to extract actual flight time from time-series data
  - **Real-time Processing**: Calculates duration during flight selection dialog with progress feedback
  - **Enhanced UI**: Loading messages with success/warning indicators and automatic cleanup
  - **Robust Error Handling**: Graceful fallback to estimated duration if actual calculation fails
- **Raw Gyro Data Detection**: Improved column detection prioritizing `gyroUnfilt` over `debug` columns:
  - **Better Data Source**: Uses `gyroUnfilt[X]` as primary source for raw gyroscope data
  - **Fallback Support**: Maintains compatibility with `debug` columns when `gyroUnfilt` unavailable
  - **Enhanced Reliability**: More accurate raw data visualization for noise analysis
- **Comprehensive Help System**: Complete user guide with detailed explanations:
  - **Detailed Tab Explanations**: In-depth coverage of all analysis tabs and their features
  - **Navigation & Controls**: Complete guide to chart interactions and UI controls
  - **Advanced Features**: Statistical analysis, PID tuning support, vibration analysis
  - **Tips & Best Practices**: Workflow recommendations for different analysis types
  - **Troubleshooting Section**: Common issues and debug features
  - **Technical Details**: Analysis methods, data processing, and visualization features

### Fixed
- **Flight Selection Dialog**: Fixed `file_path` parameter passing and `blackbox_decode_path` initialization
- **Command-line Arguments**: Corrected `blackbox_decode` arguments from `-f` to `--index` with proper flags
- **Debug Output**: Fixed debug level checking logic for consistent verbose logging
- **UI Feedback**: Improved loading message visibility and styling for duration calculation

### Technical Details
- **New Functions**:
  - `compute_unfiltered_dterm()`: Calculates raw D-term using derivative and D-gain
  - `get_d_gain()`: Extracts D-gain values from PID parameters with fallback logic
  - `get_actual_flight_duration()`: Real-time duration calculation from time data
- **Enhanced Data Processing**: Improved column detection patterns and error handling
- **UI Improvements**: Better progress feedback and status message management
- **Code Architecture**: More robust error handling and graceful degradation

---

## [0.7.0] - 2025-07-03

### Added
- **Error & Performance Analysis Tab**: Comprehensive new analysis tab for drone performance evaluation:
  - **Six Analysis Types**: Tracking Error, I-Term, PID Output, Step Response, Error Histogram, and Cumulative Error
  - **Multi-Axis Support**: Individual analysis for Roll, Pitch, and Yaw axes with dedicated charts
  - **Interactive Plot Selection**: Radio button controls for switching between different analysis types
  - **Professional Visualization**: 
    - Histogram plots with KDE (Kernel Density Estimation) overlay for error distribution analysis
    - Step response plots showing both setpoint and actual traces with legends
    - Time-series plots for tracking error, I-term, PID output, and cumulative error
  - **Advanced Features**:
    - Global error range normalization for consistent histogram comparison across axes
    - Vertical zero-reference lines on histograms for error distribution visualization
    - Missing data detection with graceful fallback and user warnings
    - Click-to-expand functionality for detailed chart analysis
    - Full export support with high-quality image generation

### Technical Details
- **Calculation Functions**: 
  - `calculate_tracking_error()`: Setpoint minus actual gyro values
  - `calculate_i_term()`: Integral term extraction from PID controller
  - `calculate_pid_output()`: Combined P+I+D terms with actuator limits
  - `calculate_step_response_data()`: Setpoint and actual traces for step analysis
  - `calculate_error_histogram_data()`: Error distribution with statistical analysis
  - `calculate_cumulative_error()`: Running sum of tracking errors over time
- **Data Processing**: Robust column detection with multiple naming patterns and graceful degradation
- **Export Integration**: Full compatibility with existing export system including tab-specific headers

---

## [0.6.2] - 2025-06-22

### Added
- **Click-to-Expand Chart Functionality**: Interactive chart expansion across all analysis tabs:
  - **Time Domain Tab**: Click any chart (Roll, Pitch, Yaw, Throttle) to expand it to full screen
  - **Frequency Domain Tab**: Click any chart (full spectrum or 0-100Hz zoomed) to expand it to full width
  - **Step Response Tab**: Click any chart (Roll, Pitch, Yaw) to expand it to full screen
  - **Second click** on expanded chart restores original layout with equal heights

### Improved
- **Chart Interaction**: Enhanced user experience with full-screen chart viewing
- **Layout Management**: Smart height and width management for expanded charts
- **UI Responsiveness**: Smooth transitions between expanded and normal chart layouts
- **Code Architecture**: Added reusable `ClickableChartView` class for consistent click handling

### Technical Details
- Added `ClickableChartView` class with `clicked` signal emission
- Implemented `expand_chart()` and `restore_all_charts()` methods in all chart widgets
- Added state tracking with `expanded_chart` and `original_heights` attributes
- Maintained existing functionality (tooltips, resize events, annotations) during expansion

---

## [0.6.1] - 2025-06-21

### Added
- **Step Response Sample Statistics**: Enhanced step response plots with detailed sample processing information:
  - Shows number of useful windows used for analysis (filtered by signal quality)
  - Displays total samples processed for each axis
  - Automatic detection of insufficient data (< 100 useful windows) with warning message
  - Per-axis statistics showing different useful window counts (e.g., 270 roll, 260 pitch, insufficient yaw)
  - Window filtering based on signal amplitude (100++ for optimal analysis)

---

## [0.6.0] - 2025-06-21

### Added
-**Frequency Evolution Tab**: New spectrogram visualization for time-frequency analysis:
  - Heatmap display showing frequency content over time
  - Configurable window size control
  - Gain control for adjusting color intensity
  - Smoothing and interpolation options for enhanced visualization
  - Interactive tooltips showing time, frequency, and power values
- **Missing Data Warnings**: Warning dialogs when selected features are not available in the current log:
  - Shows clear warning message listing which selected features are missing
  - Prevents confusion when plots appear empty due to missing data
  - Covers all feature types: Gyro (raw/filtered), PID terms, Setpoint, RC Commands, Throttle, and Motor Outputs
  - Integrated into Time Series, Frequency Domain, Step Response, and Frequency Evolution tabs
- **Tab Renaming**: Improved clarity with new tab names:
  - "Time Domain" → "Time Series"
  - "Spectral Analysis" → "Frequency Domain"
  - "Frequency Analyzer" → "Noise Analysis"
  - "Parameters" → "Drone Config"
- **Smart Log Selection**: Automatic log selection management when switching tabs:
  - Single-log tabs (Time Series, Noise Analysis, Frequency Evolution) automatically select the first log when multiple are selected
  - Multi-log tabs (Frequency Domain: up to 2, Step Response: up to 5, Drone Config: up to 2) maintain appropriate selection limits
  - Improved user experience with predictable log selection behavior

### Improved
- **UI/UX**: Better checkbox state management and UI responsiveness
- Enhanced error handling and user feedback
- **Code Cleanup:** Removed unused dependencies (`customtkinter`, `rasterio`, `Pillow`), unused class (`StepResponseCalculator`), and unused imports. Verified that all remaining classes and methods are actively used in the codebase

### Fixed
- Fixed tab switching to maintain clean state between different analysis modes
- Fixed signal disconnection warnings

### Changed
- Code organization and documentation updates throughout the codebase
- Plot styling improvements with white background and black text for better readability
- General UI/UX improvements for Drone Config tab, legend visibility, and button styling
- Logging configuration is now set dynamically at app startup based on settings.json, ensuring consistent debug output control

---

## [0.5.1] - 2025-06-20

### Added
- Parameters tab: Side-by-side comparison of up to two logs, with three-column layout (parameter name, log1, log2).
- Highlight Differences: Toggle button to highlight differing parameter values in the Parameters tab.
- Show Only Differences: Toggle button to filter and show only rows with differences in the Parameters tab.
- Settings dialog: Debug verbosity control (INFO, DEBUG, VERBOSE) with dropdown selector and persistent storage in settings.json.

### Improved
- All debug/info print statements in Frequency Analyzer and Spectral Analyzer are now wrapped with debug level checks and labeled ([INFO], [DEBUG], etc.).
- Suppressed noisy RuntimeWarnings from failed signal disconnects in the UI.
- General UI/UX improvements for Parameters tab, legend visibility, and button styling.
- Logging configuration is now set dynamically at app startup based on settings.json, ensuring consistent debug output control.

---

## [0.5.0] - 2025-06-09

### Added
- Added a new Parameters tab for viewing and editing parameters.

### Improved
- Increased the resolution of exported images for better quality and detail.
- Enhanced multiple file selection using Ctrl control for better user interaction.

---

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