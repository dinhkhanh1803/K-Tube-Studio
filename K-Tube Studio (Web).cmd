@echo off
chcp 65001 >nul
title K-Tube Studio - Web Local
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

:: Kiểm tra nếu chưa cài đặt môi trường ảo .venv
if not exist ".venv\Scripts\python.exe" (
    echo ====================================================
    echo    CHƯA TÌM THẤY MÔI TRƯỜNG PYTHON (.VENV)
    echo    Đang tự động khởi chạy trình cài đặt setup.cmd...
    echo ====================================================
    echo.
    call "%~dp0setup.cmd"
    if not exist ".venv\Scripts\python.exe" (
        echo.
        echo [LỖI] Chưa hoàn tất thiết lập môi trường .venv.
        echo Vui lòng chạy lại file setup.cmd để kiểm tra lỗi.
        pause
        exit /b 1
    )
)

echo ====================================================
echo            K-TUBE STUDIO (WEB LOCAL)
echo       Khởi động hệ thống AI tạo video tự động
echo ====================================================
echo.
echo Đang mở trình duyệt tại: http://localhost:8765
echo (Nhấn Ctrl+C trên cửa sổ này để tắt máy chủ)
echo.
".venv\Scripts\python.exe" -m icontent ui --port 8765
if errorlevel 1 pause
