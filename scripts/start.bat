@echo off
chcp 65001 >nul
title Daneshjo360 - Samane Modiriat Amoozeshi
cd /d "%~dp0..\backend"

where python >nul 2>nul
if errorlevel 1 (
  echo Khata: Python nasb nist. Az python.org nasb konid.
  pause
  exit /b 1
)

echo Nasb vabastegi-ha...
python -m pip install -q -r requirements.txt

echo Ejraye samane rooye http://127.0.0.1:8000  (baraye tavaqof: Ctrl+C)
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
