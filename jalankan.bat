@echo off
title Monitoring BBM ^& Alat
cd /d "%~dp0"
echo ==========================================================
echo   MONITORING BBM ^& ALAT  (BBM / SOLAR)
echo   PC : http://127.0.0.1:8791
echo   Hentikan : tekan CTRL+C di jendela ini
echo ==========================================================
echo.
python app.py
pause
