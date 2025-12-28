@echo off
echo ==========================================
echo      Starting Health Data Import
echo ==========================================
echo.
echo Running Ingestor...
py 03_Apps/ingest.py
echo.
echo ==========================================
echo           Import Complete
echo ==========================================
pause
