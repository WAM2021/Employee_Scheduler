# Employee Scheduler

A comprehensive employee scheduling application with automatic update capabilities.

## Features

- 📅 **Visual Calendar Interface** - Easy-to-use monthly calendar view
- 👥 **Employee Management** - Add, edit, and manage employee information  
- ⏰ **Shift Scheduling** - Create and manage work shifts with conflict detection
- 🔄 **Auto-Update System** - Automatic updates from GitHub releases
- 📱 **Responsive Design** - Scales with window size and font preferences
- 🎨 **Modern UI** - Clean, professional interface with drag-and-drop support
- 📊 **PDF Export** - Generate monthly schedule reports
- ⚙️ **Store Hours Management** - Configure operating hours for each day

## Quick Start

### For Users
1. Download the latest `.exe` file from [Releases](../../releases)
2. Run `Employee_Scheduler.exe`
3. Start scheduling!

### For Developers
1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python WorkScheduler.py`

## Building Executable

Use the provided batch file to build an executable:
```cmd
build_exe.bat
```

Or manually with PyInstaller:
```cmd
pyinstaller --onefile --windowed WorkScheduler.py
```

## Auto-Update System

The application includes an intelligent auto-update system that:
- Automatically checks for updates on startup and every 30 minutes
- Downloads and installs updates seamlessly in the background
- Preserves all user data and settings during updates
- Provides user control over when updates are applied

## File Structure

- `WorkScheduler.py` - Main application file
- `employees.json` - Employee data storage (created automatically)
- `build_exe.bat` - Executable build script
- `requirements.txt` - Python dependencies

## License

This project is open source. Feel free to use, modify, and distribute.

## System Requirements

- Windows 10 or later
- 50MB free disk space  
- Internet connection (for updates)

## Privacy & Security

- All employee data stays local on your computer
- No data is transmitted except for update checks
- Updates are downloaded securely from GitHub

For issues or questions:
1. Check the documentation files
2. Review [GitHub Issues](../../issues)
3. Create a new issue if needed

---

**Built with ❤️ by WILLSTER**