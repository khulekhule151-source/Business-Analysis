@echo off
cd /d "%~dp0"
if not exist config.json copy /Y config.example.json config.json >nul
py -m pip install -r requirements.txt
py business_analysis.py
pause
