@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 verify.py
  exit /b %ERRORLEVEL%
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python verify.py
  exit /b %ERRORLEVEL%
)
echo VERIFY=FAIL reason=python_not_found
exit /b 1
