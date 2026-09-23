@echo off
title Monitoring BBM ^& Alat - PC + HP
cd /d "%~dp0"
echo ==========================================================
echo   MONITORING BBM ^& ALAT - bisa dibuka dari PC DAN HP
echo   (HP harus tersambung WiFi yang sama)
echo ==========================================================
echo.

netsh advfirewall firewall show rule name="BBM App 8791" >nul 2>&1
if errorlevel 1 (
  echo   Menyiapkan izin firewall sekali saja...
  netsh advfirewall firewall add rule name="BBM App 8791" dir=in action=allow protocol=TCP localport=8791 profile=private >nul 2>&1
)

echo   Alamat untuk HP:
python -c "import socket;s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));ip=s.getsockname()[0];print('     >>  http://'+ip+':8791/m');print();print('  Dari PC :  http://127.0.0.1:8791')"
echo.
echo   Di HP: buka alamat di atas, menu browser ^> "Tambahkan ke layar utama".
echo   Hentikan: tekan CTRL+C di jendela ini
echo ==========================================================
echo.

set BBM_HOST=0.0.0.0
set BBM_PORT=8791
python app.py
pause
