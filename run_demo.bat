@echo off
setlocal
chcp 65001 > nul
title Column-Store vs Row-Store - Web Dashboard
echo Starting Web Dashboard at http://localhost:8000 ...
start "" /b cmd /c "ping -n 2 127.0.0.1 > nul & start http://localhost:8000"
python "%~dp0web_server.py"
if errorlevel 1 pause
