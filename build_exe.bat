@echo off
echo Building Employee Scheduler v1.0.5 executable...
echo.

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Build the executable using the spec file
pyinstaller Employee_Scheduler_v1.0.5.spec

echo.
echo Build complete! 
echo Executable is located in: dist\Employee_Scheduler_v1.0.5.exe
echo.
pause