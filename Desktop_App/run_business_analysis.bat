@echo off
cd /d "%~dp0"
py -3 business_analysis_v2.py
if errorlevel 1 pause
