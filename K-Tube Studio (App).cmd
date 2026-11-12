@echo off
chcp 65001 >nul
title K-Tube Studio
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: Kiểm tra nếu chưa cài đặt môi trường ảo .venv
if not exist ".venv\Scripts\pythonw.exe" (
    echo ====================================================
    echo    CHƯA TÌM THẤY MÔI TRƯỜNG PYTHON (.VENV)
    echo    Đang tự động khởi chạy trình cài đặt setup.cmd...
    echo ====================================================
    echo.
    call "%~dp0setup.cmd"
    if not exist ".venv\Scripts\pythonw.exe" (
        echo.
        echo [LỖI] Chưa hoàn tất thiết lập môi trường .venv.
        echo Vui lòng chạy lại file setup.cmd để kiểm tra lỗi.
        pause
        exit /b 1
    )
)

start "" ".venv\Scripts\pythonw.exe" -m icontent ui --app %*
