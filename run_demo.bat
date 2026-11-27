@echo off
pushd "%~sdp0"
title [NHOM 5] HE THONG DIEU KHIEN DEMO (SIGMOD 2008)
color 0B

:MENU
cls
echo ===============================================================================
echo            HE THONG DIEU KHIEN DEMO COLUMN-STORE (SIGMOD 2008 - NHOM 5)
echo ===============================================================================
echo.
echo   [1] Khoi chay Web Server Local va Mo trinh duyet (http://localhost:8000)
echo   [2] Mo Web Truc Tuyen Cloudflare Pages (Khong can Python, click la chay)
echo   [3] Mo Web Truc Tuyen GitHub Pages (Ban du phong online)
echo   [4] Mo Kich Ban Thuyet Trinh Word (KichBan_ThuyetTrinh_Demo_Web_Chuan.docx)
echo   [5] Mo Slide Thuyet Trinh PowerPoint (Group5_ColumnStore_vs_RowStore_Chuan.pptx)
echo   [6] Kiem tra va Giai phong Cong 8000 (Don dep cong khi bi ket)
echo   [0] Thoat chuong trinh
echo.
echo ===============================================================================
choice /C 1234560 /N /M ">> Nhap phim lua chon [1, 2, 3, 4, 5, 6, 0]: "

if errorlevel 7 goto EXIT_PROG
if errorlevel 6 goto RESET_PORT
if errorlevel 5 goto OPEN_PPTX
if errorlevel 4 goto OPEN_DOCX
if errorlevel 3 goto OPEN_GITHUB
if errorlevel 2 goto OPEN_CLOUDFLARE
if errorlevel 1 goto START_LOCAL
goto MENU

:START_LOCAL
cls
echo ===============================================================================
echo          [1] KHOI CHAY WEB SERVER LOCAL (PORT 8000)
echo ===============================================================================
echo.
cd /d "%~sdp0"

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
    echo [LOI] Khong tim thay Python tren may tinh!
    echo Goi y: Hay bam phim [2] tai Menu de dung ban Web Cloudflare Pages!
    echo.
    pause
    goto MENU
)

echo [*] Dang khoi chay web_server.py bang: %PY_CMD%
echo [*] Trinh duyet se tu dong bat len tai http://localhost:8000 ...
echo.
"%PY_CMD%" web_server.py
echo.
echo [THONG BAO] May chu da dung.
pause
goto MENU

:OPEN_CLOUDFLARE
cls
echo ===============================================================================
echo          [2] MO LIVE DEMO CLOUDFLARE PAGES
echo ===============================================================================
echo.
echo [*] Dang mo trinh duyet toi: https://cs-lab-a3k.pages.dev ...
start https://cs-lab-a3k.pages.dev
ping -n 3 127.0.0.1 > nul
goto MENU

:OPEN_GITHUB
cls
echo ===============================================================================
echo          [3] MO LIVE DEMO GITHUB PAGES
echo ===============================================================================
echo.
echo [*] Dang mo trinh duyet toi: https://nngocit.github.io/columnstore-lab/ ...
start https://nngocit.github.io/columnstore-lab/
ping -n 3 127.0.0.1 > nul
goto MENU

:OPEN_DOCX
cls
echo ===============================================================================
echo          [4] MO KICH BAN THUYET TRINH (WORD DOCX)
echo ===============================================================================
echo.
cd /d "%~sdp0"
if exist "KichBan_ThuyetTrinh_Demo_Web_Chuan.docx" (
    echo [*] Dang mo file Word: KichBan_ThuyetTrinh_Demo_Web_Chuan.docx ...
    start "" "KichBan_ThuyetTrinh_Demo_Web_Chuan.docx"
) else if exist "..\KichBan_ThuyetTrinh_Demo_Web_Chuan.docx" (
    echo [*] Dang mo file Word: KichBan_ThuyetTrinh_Demo_Web_Chuan.docx ...
    start "" "..\KichBan_ThuyetTrinh_Demo_Web_Chuan.docx"
) else (
    echo [LOI] Khong tim thay file Word!
)
ping -n 3 127.0.0.1 > nul
goto MENU

:OPEN_PPTX
cls
echo ===============================================================================
echo          [5] MO SLIDE THUYET TRINH (POWERPOINT PPTX)
echo ===============================================================================
echo.
cd /d "%~sdp0"
if exist "Group5_ColumnStore_vs_RowStore_Chuan.pptx" (
    echo [*] Dang mo Slide PowerPoint: Group5_ColumnStore_vs_RowStore_Chuan.pptx ...
    start "" "Group5_ColumnStore_vs_RowStore_Chuan.pptx"
) else if exist "..\Group5_ColumnStore_vs_RowStore_Chuan.pptx" (
    echo [*] Dang mo Slide PowerPoint: Group5_ColumnStore_vs_RowStore_Chuan.pptx ...
    start "" "..\Group5_ColumnStore_vs_RowStore_Chuan.pptx"
) else (
    echo [LOI] Khong tim thay file PowerPoint!
)
ping -n 3 127.0.0.1 > nul
goto MENU

:RESET_PORT
cls
echo ===============================================================================
echo          [6] KIEM TRA VA GIAI PHONG CONG 8000
echo ===============================================================================
echo.
echo [*] Dang quet cac tien trinh dang chiem cong 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo [*] Dang giai phong PID: %%a ...
    taskkill /f /pid %%a >nul 2>nul
)
echo.
echo [XONG] Da giai phong sach cong 8000!
ping -n 3 127.0.0.1 > nul
goto MENU

:EXIT_PROG
popd
exit
