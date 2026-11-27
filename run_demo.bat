@echo off
setlocal enabledelayedexpansion
chcp 65001 > nul
title [NHOM 5] HE THONG DEMO COLUMN-STORE VS ROW-STORE (SIGMOD 2008)
color 0A

echo ===============================================================================
echo            KÍCH HOẠT HỆ THỐNG DEMO THỰC THI (SIGMOD 2008 - NHÓM 5)
echo ===============================================================================
echo.

:: 1. Kiem tra Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [LỖI] Máy tính chưa tìm thấy lệnh Python!
    echo Vui lòng kiểm tra lại Python đã được cài đặt và tick 'Add Python to PATH'.
    echo.
    pause
    exit /b 1
)

cd /d "%~dp0"

echo [1/3] Đang kiểm tra và giải phóng cổng 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [*] Giải phóng cổng 8000 (PID: %%a)...
    taskkill /f /pid %%a >nul 2>nul
)

echo [2/3] Tự động mở trình duyệt web tại http://localhost:8000 ...
start "" cmd /c "ping -n 3 127.0.0.1 >nul & start http://localhost:8000"

echo [3/3] Khởi động Web Server Python...
echo.
echo ===============================================================================
echo   >> MÁY CHỦ DEMO ĐANG CHẠY TRỰC TIẾP TẠI: http://localhost:8000
echo   >> Bạn có thể trình chiếu và tương tác mượt mà trên trình duyệt.
echo   >> ĐỂ DỪNG DEMO: Đóng cửa sổ dòng lệnh (CMD) này hoặc nhấn Ctrl + C.
echo ===============================================================================
echo.

python web_server.py

if %errorlevel% neq 0 (
    echo.
    echo [CẢNH BÁO] Máy chủ đã dừng (Mã lỗi: %errorlevel%).
    pause
)
