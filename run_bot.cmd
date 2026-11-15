@echo off
chcp 65001 >nul
title K-Tube Studio - 24/7 AI Telegram Bot & Watchdog
cd /d "%~dp0"

echo ============================================================
echo   K-TUBE STUDIO - TRỢ LÍ AI TỰ ĐỘNG HÓA 24/7 (TELEGRAM & WATCHDOG)
echo ============================================================
echo.

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" run_bot.py

pause

