# Employee Scheduler Program Documentation

## Overview
The Employee Scheduler is a comprehensive Python application built with Tkinter for managing employee schedules, availability, and store hours. The program features a modern dark-mode UI with copy/paste functionality, conflict detection, store modification undo system, enhanced mouse wheel scrolling, transparent modified hours display, heatmap analytics, automatic data cleanup, and automatic update capabilities.

**Version:** 1.0.6  
**Main File:** WorkScheduler.py  
**Total Lines:** ~7400+ lines  
**Framework:** Tkinter/TTK with custom styling  

---

## Program Structure

### Constants and Configuration (Lines 15-30)
- `APP_VERSION = "1.0.6"` - Current application version
- `GITHUB_REPO = "WAM2021/Employee_Scheduler"` - Repository for updates
- `UPDATE_CHECK_URL` - GitHub API endpoint for version checking
- `DATA_FILE = "employees.json"` - Primary data storage file
- `DATE_FMT = "%Y-%m-%d"` - Standard date format
- `TIME_FMT = "%I:%M %p"` - Standard time format (12-hour)

---

## Utility Functions

### Data Management Functions
- **`ensure_data_file()`** (Lines 32-47) - Creates default JSON structure if file doesn't exist
- **`load_data()`** (Lines 45-68) - Loads employee data with backwards compatibility and automatic cleanup
- **`save_data(data)`** (Lines 70-72) - Saves data to JSON file with automatic cleanup
- **`get_date_months_ago(reference_date, months)`** (Lines 76-86) - Calculates cutoff date for data retention
- **`clean_old_data(data, months=6)`** (Lines 87-138) - Removes schedule and day-off entries older than specified months
- **`generate_times(start_str, end_str, interval_minutes=30)`** (Lines 140-148) - Creates time intervals
- **`get_store_hours_for_date(date_str, store_hours_data)`** (Lines 150-163) - Gets store hours for specific date

### Version Management Functions
- **`version_compare(version1, version2)`** - Compares version strings
- **`check_for_updates(callback=None)`** - Background update checking
- **`apply_update(update_file_path=None)`** - Launches update assistant
- **`create_update_assistant()`** - Creates update executable

### Utility Helper Functions
- **`friendly_weekday_name(dt)`** - Returns weekday name
- **`format_time_simple(time_str)`** - Converts time format for display

---

## Main Application Class: WorkSchedulerApp

### Initialization and Setup (Lines 246-438)

#### `__init__(self, root)` (Lines 246-438)
Main constructor that initializes the entire application:
- Sets up dark mode color palette (Lines 253-270)
- Configures TTK styles for modern appearance (Lines 282-340)
- Initializes font sizing and UI scaling parameters (Lines 342-367)
- Creates tabbed interface and menu system (Lines 397-420)
- Handles splash screen and startup checks (Lines 424-437)

#### Color System (Lines 253-270)
Comprehensive dark mode color palette including:
- Primary colors, backgrounds, surfaces
- Text colors (primary, secondary, muted)
- Status colors (success, warning, danger)
- Border and accent colors

### UI Creation and Styling Methods

#### Modern UI Components
- **`create_modern_button(parent, text, command, style, width)`** - Creates styled buttons with hover effects
- **`create_modern_frame(parent, padding)`** - Creates frames with modern styling
- **`center_dialog(dialog, width, height)`** - Centers dialogs and applies styling

#### Menu and Dialog Systems
- **`create_menu_bar()`** - Creates application menu bar
- **`show_about_dialog()`** - Displays about dialog

#### Validation Helper Functions
- **`_show_name_required_error()`** - Standardized error for empty name fields
- **`_show_employee_selection_warning()`** - Standardized warning for no employee selection

#### Splash Screen and Startup
- **`show_splash_screen()`** (Lines 592-684) - Shows startup splash screen
- **`close_splash_and_show_main(splash)`** (Lines 698-707) - Manages splash screen transition

### Settings and Configuration

#### Settings Management (Lines 1199-1446)
- **`init_settings()`** (Lines 1199-1236) - Initializes default settings
- **`get_setting(key, default)`** (Lines 1238-1240) - Retrieves setting values
- **`set_setting(key, value)`** (Lines 1242-1246) - Updates and saves settings
- **`show_settings_dialog()`** (Lines 1248-1433) - Comprehensive settings interface
- **`reset_settings_to_defaults()`** (Lines 1445-1461) - Resets all settings
- **`apply_settings_changes()`** (Lines 1463-1476) - Applies UI changes from settings

### Font and UI Scaling System

#### Responsive Design (Lines 1541-1642)
- **`calculate_font_size(base_size)`** (Lines 1541-1576) - Dynamic font size calculation
- **`on_window_resize(event)`** (Lines 1578-1608) - Handles window resize events
- **`update_ui_sizes_optimized()`** (Lines 2813-2840) - Optimized UI size updates
- **`update_calendar_fonts(...)`** (Lines 2842-2867) - Updates calendar font sizes
- **`update_employee_tab_fonts(...)`** (Lines 2973-3031) - Updates employee tab fonts
- **`update_store_hours_tab_fonts(...)`** (Lines 3033-3075) - Updates store hours tab fonts

---

## Tab-Specific Implementations

### Employee Management Tab

#### Core Employee Tab Setup
- **`setup_employee_tab()`** (Lines 1650-2001) - Creates employee management interface with three-column layout:
  - Left: Employee list and management buttons
  - Center: Availability schedule editor  
  - Right: Requested time-off management

#### Employee CRUD Operations
- **`refresh_employee_list()`** (Lines 2004-2010) - Updates employee listbox
- **`add_employee()`** (Lines 2167-2224) - Creates new employee with validation
- **`remove_employee()`** (Lines 2226-2296) - Removes employee with confirmation
- **`edit_employee_name()`** (Lines 2359-2433) - Edits employee display name
- **`on_employee_select(event)`** (Lines 2298-2357) - Handles employee selection

#### Employee Data Management
- **`find_employee_by_display(display_name)`** (Lines 2046-2051) - Finds employee by name
- **`save_employee_changes(silent)`** (Lines 2649-2731) - Saves employee modifications
- **`clear_employee_editor()`** (Lines 2435-2442) - Clears availability editor
- **`mark_employee_dirty()`** (Lines 2012-2029) - Marks unsaved changes
- **`clear_employee_dirty()`** (Lines 2031-2044) - Clears dirty state

#### Time-Off Management
- **`add_requested_day()`** (Lines 2444-2639) - Adds requested time-off with validation
- **`remove_requested_day()`** (Lines 2641-2647) - Removes time-off request

#### Store Modification Management (v1.0.5)
- **`add_store_modification()`** (Lines 3250-3426) - Adds store hour modifications with conflict checking
- **`undo_store_modification(date_str)`** (Lines 3430-3485) - New undo functionality for store modifications with confirmation dialogs

#### Shift Validation System
- **`validate_shift_scheduling(...)`** (Lines 2054-2165) - Comprehensive validation for:
  - Employee availability conflicts
  - Existing shift overlaps
  - Time-off request conflicts
  - Store hours compliance

### Schedule Management Tab

#### Calendar Interface
- **`setup_schedule_tab()`** (Lines 2736-2795) - Creates calendar view with navigation
- **`draw_calendar()`** (Lines 4924-6233) - Enhanced calendar rendering with:
  - Dynamic cell sizing and responsive design
  - Shift display with 2-column layout
  - Interactive cell menu system with undo functionality (v1.0.5)
  - Background overlay for modified hours display (v1.0.5)
  - Weekend and closed day styling
  - Universal mouse wheel scrolling support (v1.0.5)

#### Calendar Navigation
- **`prev_month()`** (Lines 2797-2803) - Navigates to previous month
- **`next_month()`** (Lines 2805-2811) - Navigates to next month

#### Copy/Paste System (Lines 6238-6509)
Modern shift copying functionality with conflict detection:

- **`copy_day_shifts(day_str, shifts)`** (Lines 6238-6252) - Copies shifts to clipboard
- **`paste_day_shifts(target_day_str)`** (Lines 6255-6378) - Pastes with conflict resolution
- **`show_paste_conflict_dialog(...)`** (Lines 6381-6509) - Professional conflict resolution interface

#### Cell Menu System (Lines 4924-6233)
**CellMenuManager Class** - Enhanced interactive menu system embedded within `draw_calendar()`:
- Context-aware menu buttons with dynamic undo functionality (v1.0.5)
- Tooltip system with modification type information
- Background overlay system for transparent modified hours display (v1.0.5)
- Universal mouse wheel scrolling throughout shift lists (v1.0.5)
- Button creation and event handling with proper timing
- Vignette effects for visual feedback
- Safety checks for widget lifecycle management

**Key Methods:**
- `create_menu_buttons()` - Creates action buttons (edit, copy, paste, delete, undo)
- `handle_undo_modification()` - New undo handler for store modifications (v1.0.5)
- `show_menu()` / `hide_menu()` - Menu visibility management
- `handle_copy_action()` / `handle_paste_action()` - Action handlers
- `handle_delete_action()` - Delete with confirmation dialog
- `bind_mouse_wheel_events()` - Cross-platform mouse wheel support (v1.0.5)

#### Shift Management
- **`delete_day_shifts(day_str)`** (Lines 6512-6534) - Deletes all shifts for a day
- **`open_day_editor(day_str)`** (Lines 6537-6853) - Opens day-specific shift editor with enhanced validation

### Store Hours Management Tab

#### Store Hours Interface
- **`setup_store_hours_tab()`** (Lines 3152-3423) - Creates store hours management interface with:
  - Day-by-day hour configuration
  - Closed day settings
  - Auto-save functionality
  - Responsive layout design

#### Store Hours Management
- **`mark_store_hours_dirty()`** (Lines 3477-3492) - Marks unsaved changes
- **`auto_save_store_hours()`** (Lines 3494-3550) - Auto-saves changes with timer
- **`refresh_employee_availability_times()`** (Lines 3552-3579) - Updates availability dropdowns

---

## Dialog Systems

### Shift Editing Dialogs
- **`open_day_editor_dialog(day_str, shifts)`** (Lines 836-1089) - Comprehensive day editor with:
  - Current shifts display with scrollable list
  - Add new shift interface
  - Store hours integration
  - Employee validation

- **`edit_shift_dialog(...)`** (Lines 1091-1197) - Individual shift editing dialog

### Update System Dialogs
- **`show_changelog_dialog(old_version, new_version)`** (Lines 709-799) - Post-update changelog
- **`show_update_available_dialog(...)`** (Lines 7145-7205) - Update notification dialog
- **`check_for_updates_on_startup()`** (Lines 7135-7142) - Background update checking
- **`manual_check_for_updates()`** (Lines 7208-7257) - Manual update checking

### Utility Dialog Methods
- **`format_github_markdown(markdown_text)`** (Lines 801-834) - Converts markdown for display

---

## File Operations and Export

### PDF Generation
- **`generate_month_pdf()`** (Lines 6856-7131) - Generates monthly schedule PDF with:
  - Professional formatting
  - Employee shift details
  - Store hours information
  - Company branding support

### Update System File Operations
- **`cleanup_old_executable()`** (Lines 1478-1497) - Cleans up after updates
- **`check_for_update_completion()`** (Lines 1499-1526) - Detects successful updates
- **`show_update_success_message()`** (Lines 1528-1540) - Shows update completion

---

## Data Structures

### Employee Data Structure
```json
{
  "name": "string",           // Employee identifier
  "display_name": "string",   // Display name (optional)
  "availability": {
    "monday": ["8:00 AM", "5:00 PM"],
    // ... other days
  },
  "requested_days_off": ["2024-12-25", "2024-12-31"]
}
```

### Schedule Data Structure
```json
{
  "schedule": {
    "2024-12": {
      "2024-12-15": [
        {
          "employee": "John Doe",
          "start": "9:00 AM",
          "end": "5:00 PM"
        }
      ]
    }
  }
}
```

### Store Hours Structure
```json
{
  "store_hours": {
    "monday": ["8:30 AM", "7:00 PM"],
    "sunday": null  // null indicates closed
  },
  "store_modifications": {
    "2024-12-25": {
      "type": "closed",
      "reason": "Christmas Day"
    },
    "2024-12-31": {
      "type": "modified",
      "hours": ["10:00 AM", "2:00 PM"],
      "reason": "New Year's Eve - Early Close"
    }
  }
}
```

---

## Key Features and Systems

### v1.0.5 Major Enhancements
- **Store Modification Undo System** - Right-click undo functionality (⟲ button) for store hour modifications with detailed confirmation dialogs
- **Enhanced Mouse Wheel Scrolling** - Universal scroll support throughout shift lists with cross-platform compatibility (Windows MouseWheel + Linux Button-4/5)
- **Transparent Modified Hours Display** - Background overlay system that shows modification information without disrupting shift layout
- **Dynamic Menu System** - Context-aware right-click menus that adapt based on day state and available actions
- **Improved User Experience** - Enhanced tooltips, better visual feedback, and professional polish throughout

### Modern UI System
- **Dark Mode Theme** - Professional color palette with eye-friendly design
- **Responsive Design** - Dynamic font sizing and layout adaptation
- **Modern Controls** - Custom styled buttons, frames, and dialogs
- **Interactive Elements** - Hover effects, tooltips, and visual feedback

### Advanced Copy/Paste System
- **Conflict Detection** - Comprehensive validation against:
  - Employee availability
  - Existing shifts
  - Time-off requests
  - Store hours and modifications (enhanced in v1.0.5)
- **Professional Resolution** - User-friendly conflict resolution dialogs
- **Safety Checks** - Widget lifecycle management and error prevention
- **Cross-Platform Scrolling** - Universal mouse wheel support for better navigation (v1.0.5)

### Validation Framework
- **Multi-layer Validation** - Employee, schedule, and store hour validation
- **Real-time Feedback** - Immediate validation during data entry
- **Conflict Prevention** - Proactive scheduling conflict detection with store modification awareness (v1.0.5)
- **Data Integrity** - Comprehensive data consistency checks
- **Undo System** - Safe modification reversal with user confirmation (v1.0.5)

### Auto-Update System
- **GitHub Integration** - Automatic version checking against repository
- **Update Assistant** - Guided update process with manual installation
- **Version Management** - Intelligent version comparison and tracking
- **Changelog Display** - Formatted release notes presentation

### Data Persistence
- **JSON Storage** - Human-readable data format
- **Auto-save** - Configurable automatic saving
- **Backup System** - Optional data backup functionality
- **Migration Support** - Backwards compatibility handling

---

## Debug and Development Features

### Debug Output System (Commented in v1.0.4)
- **Emoji-coded Categories** - Different emojis for different debug types:
  - 📱 Menu system debugging
  - 📊 Data and shift information  
  - 📋 Copy/paste operation tracking
  - 🖱️ User interaction debugging
  - 🔍 Analysis and validation debugging
  - ⚠️ Conflict and warning debugging
  - ✅ Success confirmation debugging
  - ❌ Error and failure debugging

### Development Tools
- **Comprehensive Logging** - Detailed operation tracking (when enabled)
- **Error Handling** - Graceful error recovery throughout application
- **Performance Optimization** - Efficient UI updates and data processing
- **Memory Management** - Proper widget cleanup and resource management

---

### Application Entry Point

### Main Execution (Lines 7250-7257)
```python
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Work Scheduler")
    root.withdraw()  # Hidden initially for splash screen
    
    # Theme configuration
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    
    # Create and run application
    app = WorkSchedulerApp(root)
    root.mainloop()
```

---

## Dependencies and Requirements
- **Python 3.x** - Core runtime
- **tkinter/ttk** - GUI framework (standard library)
- **tkcalendar** - Enhanced calendar widgets
- **reportlab** - PDF generation
- **datetime** - Date/time handling
- **json** - Data serialization
- **threading** - Background operations
- **subprocess** - Update system
- **tempfile** - Temporary file management
- **os, sys** - System operations

---

## Summary
The Employee Scheduler is a sophisticated desktop application that demonstrates advanced Tkinter programming techniques, modern UI design principles, and comprehensive business logic for employee scheduling. Version 1.0.5 introduces significant UX improvements including store modification undo functionality, enhanced mouse wheel scrolling, and transparent modified hours display. 

The codebase is well-structured with clear separation of concerns, robust error handling, and professional-grade features including auto-updates, conflict detection, responsive design, and advanced user interaction systems. The application successfully balances user-friendly operation with powerful functionality, making it suitable for real-world employee scheduling needs while maintaining code quality and maintainability.

**Latest Enhancements (v1.0.5):**
- Store hour modification undo system with confirmation dialogs
- Universal mouse wheel scrolling with cross-platform support  
- Background overlay display for modified hours information
- Enhanced right-click context menus with dynamic button generation
- Improved calendar interaction and visual feedback systems