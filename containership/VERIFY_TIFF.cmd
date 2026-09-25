@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || exit /b 3
if not defined PYTHON set "PYTHON=python"
set PYTHONUTF8=1
"%PYTHON%" -X utf8 -B tools\verify-tiff.py %*
set "UC_EXIT=%ERRORLEVEL%"
popd
endlocal & exit /b %UC_EXIT%
