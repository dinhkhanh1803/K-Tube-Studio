@echo off
chcp 65001 >nul
title K-Tube Studio - Cài đặt môi trường
cd /d "%~dp0"

echo ====================================================
echo        K-TUBE STUDIO - THIẾT LẬP MÔI TRƯỜNG
echo ====================================================
echo.

:: 1. Kiểm tra Python
set PYTHON_CMD=
where python >nul 2>&1 && set PYTHON_CMD=python
if not defined PYTHON_CMD (
    where py >nul 2>&1 && set PYTHON_CMD=py
)

if not defined PYTHON_CMD (
    echo [LỖI] Không tìm thấy Python trên máy tính của bạn!
    echo.
    echo Vui lòng tải và cài đặt Python (phiên bản khuyên dùng: 3.10 - 3.12):
    echo 👉 https://www.python.org/downloads/
    echo.
    echo ⚠️ QUAN TRỌNG: Khi cài đặt, hãy tích chọn vào ô:
    echo    "Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

echo [*] Đang dùng Python:
%PYTHON_CMD% --version
echo.

:: 2. Khởi tạo môi trường ảo .venv
if not exist ".venv\Scripts\python.exe" (
    echo [*] Đang khởi tạo môi trường ảo .venv (vui lòng chờ trong giây lát)...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [LỖI] Không thể tạo thư mục .venv. Vui lòng kiểm tra lại quyền ghi hoặc phiên bản Python.
        pause
        exit /b 1
    )
    echo [OK] Đã tạo môi trường ảo thành công.
) else (
    echo [OK] Đã có sẵn môi trường ảo .venv.
)
echo.

:: 3. Cài đặt các thư viện cần thiết
echo [*] Đang kiểm tra và cài đặt các thư viện từ requirements.txt...
echo (Quá trình này có thể mất 1 - 3 phút tùy tốc độ mạng của bạn)...
echo.
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [CẢNH BÁO] Có thư viện chưa thể cài đặt tự động. Đang thử lại với chế độ dự phòng...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt --no-warn-script-location
)
echo.

:: 4. Kiểm tra công cụ FFmpeg
echo [*] Kiểm tra công cụ FFmpeg...
set FF_OK=0
where ffmpeg >nul 2>&1 && set FF_OK=1
if exist "tools\ffmpeg\ffmpeg.exe" set FF_OK=1

if "%FF_OK%"=="0" (
    echo [LƯU Ý] Chưa tìm thấy FFmpeg trên máy tính của bạn.
    echo FFmpeg là công cụ bắt buộc để xuất video và phụ đề.
    echo.
    echo Bạn có thể cài đặt tự động bằng cách mở PowerShell / CMD (Run as Administrator) và chạy:
    echo 👉 winget install Gyan.FFmpeg
    echo Hoặc tải file ffmpeg.exe chép vào thư mục tools\ffmpeg\
) else (
    echo [OK] Đã tìm thấy FFmpeg trên hệ thống.
)
echo.

:: 5. Khởi tạo file cấu hình mẫu nếu chưa có
if not exist "keys.json" (
    if exist "keys.example.json" (
        copy "keys.example.json" "keys.json" >nul
        echo [OK] Đã khởi tạo file keys.json từ keys.example.json.
    )
)

if not exist "config.yaml" (
    if exist "config.example.yaml" (
        copy "config.example.yaml" "config.yaml" >nul
        echo [OK] Đã khởi tạo file config.yaml từ config.example.yaml.
    )
)

echo.
echo ====================================================
echo        CÀI ĐẶT HOÀN TẤT! SẴN SÀNG SỬ DỤNG
echo ====================================================
echo.
echo Giờ đây bạn có thể khởi động K-Tube Studio bằng cách bấm:
echo 👉 "K-Tube Studio (Web).cmd"
echo.
pause
