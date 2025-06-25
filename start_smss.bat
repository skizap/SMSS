@echo off
echo 🔍 SMSS Auto-Start (Lazy Mode)
echo ================================
echo 🤖 Automatically fixing and starting SMSS...
echo.

REM Change to script directory
cd /d "%~dp0"

REM Run the auto-start script
python auto_start.py

REM Keep window open if there are errors
if errorlevel 1 (
    echo.
    echo ❌ Startup completed with issues
    echo Press any key to close...
    pause >nul
) else (
    echo.
    echo ✅ SMSS is running!
)
