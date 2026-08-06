@echo off
title TCRM Server
echo ==========================================
echo   TCRM - Connect . Grow . Win
echo   Starting server on http://localhost:8069
echo ==========================================
echo.
cd /d "d:\tcrm"
set PYTHONPATH=d:\tcrm\tcrm-src
"d:\tcrm\venv\Scripts\python.exe" -m tcrm -c "d:\tcrm\tcrm.conf"
pause
