@echo off
echo Building Employee Scheduler executable...
echo.

REM Install PyInstaller if not already installed
pip install pyinstaller

REM Build the executable
pyinstaller --onefile --windowed --name "Employee_Scheduler" WorkScheduler.py

echo.
echo Build complete! 
echo Executable is located in: dist\Employee_Scheduler.exe
echo.
pause