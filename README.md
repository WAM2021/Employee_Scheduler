# Employee Scheduler

A comprehensive employee scheduling application with auto-update capabilities.

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

The application includes an intelligent auto-update system:
- Checks for updates on startup
- Downloads and installs updates automatically
- Preserves all user data during updates

See [Auto-Update User Guide](AUTO_UPDATE_USER_GUIDE.md) for details.

## Documentation

- [Auto-Update User Guide](AUTO_UPDATE_USER_GUIDE.md) - How to use the update system
- [Update Setup Guide](UPDATE_SETUP_GUIDE.md) - How to set up GitHub releases

## System Requirements

- Windows 10 or later
- 50MB free disk space
- Internet connection (for updates)

## Privacy & Security

- All employee data stays local on your computer
- No data is transmitted except for update checks
- Updates are downloaded securely from GitHub

## Version History

- **v1.2.x**: Auto-update system, UI improvements
- **v1.1.x**: Advanced calendar features, drag-and-drop
- **v1.0.x**: Initial release with basic scheduling

## Support

For issues or questions:
1. Check the documentation files
2. Review [GitHub Issues](../../issues)
3. Create a new issue if needed

---

**Built with ❤️ by WILLSTER**