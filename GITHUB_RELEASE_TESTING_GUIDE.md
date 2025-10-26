# 🚀 GitHub Release Creation Guide - Testing Auto-Update

## Step-by-Step Instructions for Creating a Release

### 1. 📂 Navigate to GitHub
1. Go to: https://github.com/WAM2021/Employee_Scheduler
2. Click on **"Releases"** (on the right side of the main page)
3. Click **"Create a new release"**

### 2. 🏷️ Set Release Information
**Tag version:** `v1.1.0`
- ✅ Use format: `v` + version number
- ✅ Must match or be higher than APP_VERSION in code (1.1.0)

**Release title:** `Employee Scheduler v1.1.0`

**Description:** Copy this text:
```
## 🎉 What's New in v1.1.0

### ✨ Features
- **Version Display**: Application title now shows version number
- **Auto-Update System**: Automatic update checking and installation
- **Enhanced UI**: Improved user experience across all tabs

### 🛠️ Technical Improvements  
- Added comprehensive auto-update infrastructure
- Improved repository structure and documentation
- Enhanced security with proper file exclusions

### 📋 For Users
- Download the `.exe` file below to get the latest version
- The app will automatically check for future updates
- All your employee data and settings are preserved during updates

### 🔄 Auto-Update Testing
This release is specifically for testing the auto-update system. Users with v1.0.0 should see an update notification when they start the application.

---

**Installation:** Download `Employee_Scheduler.exe` and run it. No installation required!
```

### 3. 📎 Upload the Executable
1. **Drag and drop** the file: `dist\Employee_Scheduler.exe`
2. **Wait** for upload to complete (the file will show up in the "Assets" section)

### 4. ✅ Publish Release
1. **Check "Set as the latest release"** (should be checked by default)
2. Click **"Publish release"**

## 🧪 Testing the Auto-Update

### Testing Steps:

1. **Go back to version 1.0.0** by changing the code:
   ```python
   APP_VERSION = "1.0.0"  # Change back to 1.0.0
   ```

2. **Build the old version**:
   ```cmd
   .\build_exe.bat
   ```

3. **Run the 1.0.0 executable** - it should:
   - Show "Work Scheduler" in the title (no version)
   - Check for updates on startup
   - Show update dialog for v1.1.0
   - Allow you to download and install the update

4. **After update**:
   - App should restart automatically
   - Title should show "Work Scheduler v1.1.0"
   - Update was successful!

## 🔍 What to Watch For:

### ✅ Success Indicators:
- Update dialog appears with v1.1.0 information
- Download progress bar works
- Installation completes without errors
- App restarts with new version
- Title shows "v1.1.0"

### ❌ Potential Issues:
- **No update dialog**: Check internet connection, GitHub repo URL
- **Download fails**: Check file permissions, antivirus settings
- **Update fails**: Check write permissions to application folder

## 🛠️ Troubleshooting:

**If update doesn't work:**
1. Check that `GITHUB_REPO = "WAM2021/Employee_Scheduler"` is correct
2. Verify the release is marked as "latest"
3. Ensure the .exe file is attached to the release
4. Check Windows firewall/antivirus isn't blocking

**Manual Testing:**
You can test the version check by running:
```python
python test_versions.py
```

## 🎯 Next Steps After Testing:

1. **Create more releases** to test multiple updates
2. **Version progression**: 1.0.0 → 1.1.0 → 1.2.0 → etc.
3. **Real deployment**: Change version back to production number
4. **Distribution**: Share the .exe files via GitHub releases

This system will keep all your users automatically updated! 🚀