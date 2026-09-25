@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  py -3 -B verify.py
  exit /b %ERRORLEVEL%
)
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
  python -B verify.py
  exit /b %ERRORLEVEL%
)
echo ERROR: Python 3 was not found on PATH. 1>&2
exit /b 9009
