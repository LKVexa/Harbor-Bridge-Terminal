@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 2
if not defined PYTHON set "PYTHON=python"
"%PYTHON%" -X utf8 -B uc.py vws-workflow %*
set "UC_EXIT=%ERRORLEVEL%"
popd
endlocal & exit /b %UC_EXIT%
