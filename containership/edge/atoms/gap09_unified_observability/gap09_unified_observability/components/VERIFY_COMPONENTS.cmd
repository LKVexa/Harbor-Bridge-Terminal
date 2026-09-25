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
%PYEXE% -B run_all.py
exit /b %ERRORLEVEL%
