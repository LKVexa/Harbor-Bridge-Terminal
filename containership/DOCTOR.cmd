@echo off
setlocal
cd /d "%~dp0"
if "%PYTHON%"=="" set "PYTHON=python"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
"%PYTHON%" -X utf8 -B uc.py doctor %*
set "UC_EXIT=%ERRORLEVEL%"
if not "%UC_EXIT%"=="0" echo DOCTOR failed or was blocked. Exit code %UC_EXIT%.
endlocal & exit /b %UC_EXIT%
