# Employee Scheduler Auto-Update Setup Guide

## Overview
The Employee Scheduler now includes an automatic update system that checks for new versions on GitHub and can download and install updates automatically.

## Setup Instructions

### 1. Update the GitHub Repository Information
In `WorkScheduler.py`, update the following line (around line 15):
```python
GITHUB_REPO = "your-username/employee-scheduler"  # Replace with your actual GitHub repo
```

Replace `"your-username/employee-scheduler"` with your actual GitHub repository path (e.g., `"johnsmith/employee-scheduler"`).

### 2. Create a GitHub Repository
1. Create a new repository on GitHub (e.g., `employee-scheduler`)
2. Upload your `WorkScheduler.py` and other project files
3. Make sure the repository is public (for easier access to releases)

### 3. Creating Releases with Executable Files

When you want to release a new version:

1. **Build the executable** (if you haven't already):
   ```bash
   pip install pyinstaller
   pyinstaller --onefile --windowed WorkScheduler.py
   ```
   This creates `WorkScheduler.exe` in the `dist/` folder.

2. **Update the version** in `WorkScheduler.py`:
   ```python
   APP_VERSION = "1.3.0"  # Increment version number
   ```

3. **Create a GitHub Release**:
   - Go to your GitHub repository
   - Click "Releases" → "Create a new release"
   - Tag version: `v1.3.0` (match your APP_VERSION)
   - Release title: `Version 1.3.0`
   - Add release notes describing what's new
   - **Important**: Attach the `WorkScheduler.exe` file to the release
   - Click "Publish release"

### 4. How the Auto-Update System Works

**Automatic Check on Startup**:
- When the app starts, it checks GitHub for the latest release
- If a newer version is found, it shows an update dialog
- Users can choose to download and install or skip the update

**Manual Check**:
- Users can check for updates via Help → Check for Updates
- Shows current version and any available updates

**Update Process**:
1. Downloads the new .exe file to a temporary location
2. Shows progress during download
3. When complete, asks user to confirm installation
4. Replaces the current executable and restarts the application

### 5. Version Format
- Use semantic versioning: `MAJOR.MINOR.PATCH` (e.g., `1.2.0`, `1.2.1`, `2.0.0`)
- The system compares versions numerically
- Always increment the version when releasing updates

### 6. Testing the Update System

To test locally:
1. Set your version to something lower (e.g., `1.0.0`)
2. Create a release on GitHub with version `1.1.0`
3. Run the application - it should detect the update

### 7. Important Notes

- **Internet Connection**: Auto-update requires internet access
- **Executable Only**: Auto-update only works with compiled .exe files
- **Permissions**: Users need write access to the application directory
- **GitHub Rate Limits**: GitHub API has rate limits for anonymous requests
- **Security**: The system downloads and replaces executable files - ensure your GitHub account is secure

### 8. Troubleshooting

**Common Issues**:
- Update check fails: Check internet connection and GitHub repository URL
- Download fails: Ensure the .exe file is properly attached to the GitHub release
- Update fails to apply: Check if user has write permissions to the application folder

**Error Messages**:
- "Failed to check for updates": Network issue or incorrect repository URL
- "Download failed": Issue accessing the release file
- "Failed to apply update": Permission or file access issue

## Example Release Process

1. Make your code changes
2. Update `APP_VERSION = "1.3.0"` in the code
3. Test the application
4. Build: `pyinstaller --onefile --windowed WorkScheduler.py`
5. Create GitHub release with tag `v1.3.0`
6. Upload the `WorkScheduler.exe` file to the release
7. Publish the release

Users with older versions will now be notified of the update when they start the application!