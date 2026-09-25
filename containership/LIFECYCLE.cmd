@echo off
setlocal
cd /d "%~dp0"
if defined PYTHON (
  "%PYTHON%" -X utf8 -B "%~dp0uc.py" lifecycle %*
) else (
  python -X utf8 -B "%~dp0uc.py" lifecycle %*
)
set "RC=%ERRORLEVEL%"
exit /b %RC%
