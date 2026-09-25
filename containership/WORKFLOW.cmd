@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON (
  "%PYTHON%" -X utf8 -B "%~dp0uc.py" workflow %*
) else (
  python -X utf8 -B "%~dp0uc.py" workflow %*
)
set "RC=%ERRORLEVEL%"
exit /b %RC%
