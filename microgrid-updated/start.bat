@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (echo Install Python 3.10 or later first. & pause & exit /b 1)
echo Open http://localhost:8000 in your browser. Press Ctrl+C to stop.
python backend/server.py
pause
