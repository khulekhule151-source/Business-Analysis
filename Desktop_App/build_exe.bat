@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install -r requirements.txt
if errorlevel 1 goto :error
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name BUSINESS_ANALYSIS --collect-all customtkinter business_analysis_v2.py
if errorlevel 1 goto :error
if exist "dist\BUSINESS_ANALYSIS.exe" echo.
echo BUILD SUCCESSFUL: dist\BUSINESS_ANALYSIS.exe
pause
exit /b 0
:error
echo BUILD FAILED. Review the error above.
pause
exit /b 1
