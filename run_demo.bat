@echo off
chcp 65001 > nul
title [NHÓM 5] DEMO COLUMN-STORE VS ROW-STORE (SIGMOD 2008)
color 0A

echo ===============================================================================
echo            KÍCH HOẠT HỆ THỐNG DEMO THỰC THI (SIGMOD 2008 - NHÓM 5)
echo ===============================================================================
echo.

cd /d "%~dp0"

if not exist "web_server.py" (
    echo [LỖI] Không tìm thấy file web_server.py!
    echo.
    pause
    exit /b 1
)

:: Tim dung Python (uu tien Python 3.13 co san thu vien NumPy)
set "PY_CMD="
if exist "C:\Program Files\Python313\python.exe" (
    set "PY_CMD=C:\Program Files\Python313\python.exe"
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=python"
    ) else (
        where py >nul 2>nul
        if not errorlevel 1 (
            set "PY_CMD=py"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [LỖI] Không tìm thấy Python trên máy tính của bạn!
    echo.
    pause
    exit /b 1
)

echo [*] Đang khởi động hệ thống demo qua Python...
"%PY_CMD%" web_server.py

if errorlevel 1 (
    echo.
    echo [THÔNG BÁO] Hệ thống demo đã dừng.
    pause
)
