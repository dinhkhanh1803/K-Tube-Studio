@echo off
title K-Tube Studio - Web Local
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ====================================================
echo            K-TUBE STUDIO (WEB LOCAL)
echo       Khoi dong he thong AI tao video tu dong
echo ====================================================
echo.
echo Dang mo trinh duyet tai: http://localhost:8765
echo (Nhan Ctrl+C tren cua so nay de tat may chu)
echo.
".venv\Scripts\python.exe" -m icontent ui --port 8765
if errorlevel 1 pause
