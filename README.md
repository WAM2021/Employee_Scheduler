# 📅 Employee Scheduler

A comprehensive employee scheduling application built with Python and Tkinter, featuring intelligent scheduling validation, modern UI design, and powerful management tools.

![Employee Scheduler](https://img.shields.io/badge/Version-1.0.5-blue.svg)
![Python](https://img.shields.io/badge/Python-3.7+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### Core Scheduling
- **Intelligent Shift Management** - Create, edit, and delete employee shifts with comprehensive validation
- **Drag & Drop Scheduling** - Intuitive calendar interface with visual feedback
- **Copy/Paste Shifts** - Easily duplicate schedules across different days
- **Store Hours Integration** - Schedule options automatically adjust to store operating hours

### Advanced Validation
- **Employee Availability Checking** - Prevents scheduling outside available hours
- **Time-Off Request Validation** - Respects full-day and partial time-off requests
- **Shift Overlap Detection** - Prevents double-booking employees
- **Conflict Resolution** - Smart conflict detection with user override options

### Employee Management
- **Employee Profiles** - Manage employee information and availability
- **Flexible Availability** - Set different hours for each day of the week
- **Time-Off Requests** - Track full-day and partial time-off requests
- **Alphabetical Sorting** - All employee dropdowns sorted for easy navigation

### Modern User Interface
- **Dark Mode Support** - Professional dark theme throughout the application
- **Responsive Design** - Clean, modern interface that adapts to content
- **Interactive Tooltips** - Helpful guidance for all menu buttons
- **Enhanced Feedback** - Comprehensive user feedback for all operations
- **2-Column Layout** - Optimized shift display with automatic font sizing

### Administrative Tools
- **Store Hours Management** - Configure operating hours for each day
- **Data Export/Import** - Backup and restore scheduling data
- **Auto-Update System** - Built-in update checking and installation
- **Professional Calendar View** - Month-by-month schedule overview

## Quick Start

### Prerequisites
- Python 3.7 or higher
- Tkinter (usually included with Python)

### Installation

1. **Download the latest release:**
   ```bash
   git clone https://github.com/WAM2021/Employee_Scheduler.git
   cd Employee_Scheduler
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python WorkScheduler.py
   ```

### Using the Executable
Alternatively, download the pre-built executable from the [Releases](https://github.com/WAM2021/Employee_Scheduler/releases) page and run `Employee_Scheduler.exe` directly.

## Usage Guide

### Setting Up Your Schedule

1. **Configure Store Hours**
   - Navigate to Admin → Store Hours
   - Set operating hours for each day of the week
   - Leave days blank for closed days

2. **Add Employees**
   - Go to the Employees tab
   - Click "Add New Employee"
   - Set their availability for each day
   - Add any time-off requests

3. **Create Shifts**
   - Click on any day in the calendar
   - Use the "Add Shift" dialog
   - Select employee, start time, and end time
   - The system will validate for conflicts

### Advanced Features

#### Intelligent Validation
The system automatically checks for:
- Employee availability conflicts
- Requested time-off conflicts  
- Shift overlap detection
- Store hours compliance

#### Copy/Paste Workflows
- **Copy Shifts**: Click the copy button on any day
- **Paste Shifts**: Click paste on the target day
- **Drag & Drop**: Hold Ctrl and drag between days

#### Tooltips and Guidance
- Hover over any menu button for helpful tooltips
- Get detailed feedback for all copy/paste/delete operations
- Clear conflict messages with resolution options

## UI Improvements (v1.0.3)

### Enhanced User Experience
- **Professional Tooltips** - 500ms delay with dark theme styling
- **Enhanced Feedback Dialogs** - Detailed information with emoji styling
- **2-Column Shift Display** - Optimized layout with time-based sorting
- **Dynamic Font Sizing** - Automatic adjustment based on shift density
- **Improved Menu Buttons** - Professional styling with hover effects

### Visual Enhancements
- Modern dark theme throughout
- Consistent spacing and typography
- Professional button styling with shadows
- Enhanced calendar cell design
- Improved dialog layouts

## Validation System

The application includes comprehensive scheduling validation:

```python
# Example validation checks:
✅ Time format validation
✅ Employee availability checking
✅ Day-of-week restrictions
✅ Requested time-off conflicts
✅ Existing shift overlaps
✅ Store hours compliance
```

### Conflict Resolution
When conflicts are detected, users receive detailed information:
- Clear description of each conflict
- Option to proceed despite conflicts
- Suggested resolutions where applicable

## File Structure

```
Employee_Scheduler/
├── WorkScheduler.py           # Main application file
├── employees.json             # Employee and schedule data
├── requirements.txt           # Python dependencies
├── build_exe.bat             # Executable build script
├── Employee_Scheduler_v1.0.3.spec # PyInstaller specification
├── README.md                 # This file
├── docs/                     # Documentation files
│   ├── UI_MODERNIZATION_SUMMARY.md
│   └── DARK_MODE_SUMMARY.md
└── test/                     # Test scripts
    ├── test_validation.py
    └── test_sorting.py
```

## Development

### Building from Source

1. **Clone the repository:**
   ```bash
   git clone https://github.com/WAM2021/Employee_Scheduler.git
   cd Employee_Scheduler
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run in development mode:**
   ```bash
   python WorkScheduler.py
   ```

### Building Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build executable
pyinstaller Employee_Scheduler_v1.0.3.spec
```

## Data Format

The application stores data in JSON format:

```json
{
  "employees": [
    {
      "id": 1,
      "name": "John Doe",
      "availability": {
        "monday": ["09:00", "17:00"],
        "tuesday": ["09:00", "17:00"],
        "wednesday": ["off"]
      },
      "requested_days_off": [
        {
          "type": "full",
          "date": "2025-10-28",
          "reason": "Personal day"
        }
      ]
    }
  ],
  "schedule": {
    "2025-10": {
      "2025-10-27": [
        {
          "employee": "John Doe",
          "start": "10:00",
          "end": "15:00"
        }
      ]
    }
  },
  "store_hours": {
    "monday": ["08:00", "18:00"],
    "tuesday": ["08:00", "18:00"]
  }
}
```

## What's New in v1.0.3

### Major Features
- **Comprehensive Scheduling Validation** - Intelligent conflict detection and resolution
- **Enhanced Copy/Paste System** - Validation during copy operations with detailed feedback
- **Professional Tooltip System** - Helpful guidance for all menu buttons
- **2-Column Layout** - Optimized shift display with time-based sorting

### UI Improvements  
- Dynamic font sizing based on shift density
- Enhanced user feedback for all operations
- Professional dark theme styling
- Improved dialog layouts and spacing
- Modern button designs with hover effects

### Technical Improvements
- Centralized validation system
- Alphabetical sorting in all employee dropdowns
- Enhanced error handling and user messaging
- Improved code organization and maintainability


### Development Guidelines
- Follow existing code style and conventions
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting


## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/WAM2021/Employee_Scheduler/issues) page
2. Create a new issue with detailed information
3. Include steps to reproduce any bugs
4. Attach relevant screenshots if applicable

## Acknowledgments

- Built with Python and Tkinter
- Coded with assistance from Copilot AI
- Inspired by modern scheduling applications
- Community feedback and feature requests
- Open source contributors

---


*Last updated: October 27, 2025*
