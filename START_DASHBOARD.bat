@echo off
cd /d "%~dp0"
echo ========================================================
echo   ARIADNE HEALTH AGENT - ADMIN DASHBOARD
echo   System V2 (The Crystal)
echo ========================================================
echo.
echo Launching...
echo.

python -m streamlit run 03_Apps/admin_dashboard.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to start. Please check if Python is installed or env is active.
    pause
)
