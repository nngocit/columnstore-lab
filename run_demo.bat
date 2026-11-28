@echo off
setlocal
cd /d "%~dp0"
title Column-Store vs Row-Store Demo (SIGMOD 2008)
color 0B

:MENU
cls
echo ===============================================================================
echo   COLUMN-STORES VS. ROW-STORES: HOW DIFFERENT ARE THEY REALLY? [SIGMOD 2008]
echo   Interactive Replication Lab and Benchmark Dashboard
echo ===============================================================================
echo.
echo   [1] Start Local Web Demo [Recommended: http://localhost:8000]
echo       - Auto-checks Python, installs requirements.txt if missing, opens browser
echo.
echo   [2] Open Standalone Offline Web Demo [No Python Required]
echo       - Opens index.html directly in your web browser
echo.
echo   [3] Open Live Cloud Demo [Cloudflare Pages]
echo       - URL: https://cs-lab-a3k.pages.dev
echo.
echo   [4] Free Port 8000 [Clean up stuck background server if needed]
echo.
echo   [0] Exit
echo ===============================================================================
choice /C 12340 /N /M ">> Enter your choice [1, 2, 3, 4, 0]: "

if errorlevel 5 goto EXIT_PROG
if errorlevel 4 goto RESET_PORT
if errorlevel 3 goto OPEN_CLOUDFLARE
if errorlevel 2 goto OPEN_OFFLINE
if errorlevel 1 goto START_LOCAL
goto MENU

:START_LOCAL
cls
echo ===============================================================================
echo   [1] STARTING LOCAL WEB DEMO [PORT 8000]
echo ===============================================================================
echo.
cd /d "%~dp0"

set "PY_CMD="
where python >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"
if "%PY_CMD%"=="" (
    where py >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py"
)
if "%PY_CMD%"=="" if exist "C:\Program Files\Python313\python.exe" set "PY_CMD=C:\Program Files\Python313\python.exe"
if "%PY_CMD%"=="" if exist "C:\Program Files\Python312\python.exe" set "PY_CMD=C:\Program Files\Python312\python.exe"
if "%PY_CMD%"=="" if exist "C:\Program Files\Python311\python.exe" set "PY_CMD=C:\Program Files\Python311\python.exe"
if "%PY_CMD%"=="" if exist "C:\Program Files\Python310\python.exe" set "PY_CMD=C:\Program Files\Python310\python.exe"

if "%PY_CMD%"=="" goto NO_PYTHON

echo [+] Found Python:
"%PY_CMD%" --version
echo.
echo [*] Checking NumPy dependency...
"%PY_CMD%" -c "import numpy" >nul 2>&1
if errorlevel 1 goto INSTALL_DEPS
goto LAUNCH_SERVER

:INSTALL_DEPS
echo [*] NumPy not found. Installing from requirements.txt...
"%PY_CMD%" -m pip install -r requirements.txt
if errorlevel 1 goto INSTALL_FAILED
goto LAUNCH_SERVER

:INSTALL_FAILED
echo.
echo [WARNING] Could not install NumPy automatically via pip.
echo You can still run the demo offline by selecting [2] in the Main Menu.
echo.
pause
goto MENU

:LAUNCH_SERVER
echo [+] Dependencies ready.
echo [*] Starting local server at http://127.0.0.1:8000 ...
echo [*] Your browser will open automatically. Press Ctrl+C to stop the server.
echo.
"%PY_CMD%" web_server.py
echo.
echo [INFO] Web server stopped.
pause
goto MENU

:NO_PYTHON
echo.
echo [NOTICE] Python was not found in PATH on this computer.
echo You can still run the full interactive demo without Python:
echo.
echo   [1] Open Standalone Offline Web Demo [index.html]
echo   [2] Open Live Cloud Demo [https://cs-lab-a3k.pages.dev]
echo   [0] Return to Main Menu
echo.
choice /C 120 /N /M ">> Select [1, 2, 0]: "
if errorlevel 3 goto MENU
if errorlevel 2 goto OPEN_CLOUDFLARE
if errorlevel 1 goto OPEN_OFFLINE
goto MENU

:OPEN_OFFLINE
cls
echo [*] Opening index.html in default web browser...
start "" "%~dp0index.html"
goto MENU

:OPEN_CLOUDFLARE
cls
echo [*] Opening Live Cloud Demo: https://cs-lab-a3k.pages.dev ...
start "" "https://cs-lab-a3k.pages.dev"
goto MENU

:RESET_PORT
cls
echo ===============================================================================
echo   [4] CHECKING AND FREEING PORT 8000
echo ===============================================================================
echo.
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [*] Terminating process PID %%a on port 8000...
    taskkill /f /pid %%a >nul 2>&1
)
echo [OK] Port 8000 is now free.
pause
goto MENU

:EXIT_PROG
exit /b 0
