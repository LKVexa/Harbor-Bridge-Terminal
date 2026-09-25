@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYEXE="
where py >nul 2>nul && set "PYEXE=py -3"
if not defined PYEXE where python >nul 2>nul && set "PYEXE=python"
if not defined PYEXE (
  echo ERROR: Python 3 was not found on PATH.
  exit /b 2
)

%PYEXE% verify.py
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo GAP-09 verification FAILED with exit code %RC%.
  exit /b %RC%
)

echo GAP-09 standalone verification PASS.
exit /b 0
