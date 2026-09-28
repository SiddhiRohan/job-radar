@echo off
rem Double-click to start job radar. Keep the window open while you use it.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 start.py
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Python 3.11 or newer is needed. Install it from https://www.python.org/downloads/
    echo and tick "Add python.exe to PATH" in the installer, then double-click this file again.
    pause
    exit /b 1
  )
  python start.py
)
if errorlevel 1 pause
