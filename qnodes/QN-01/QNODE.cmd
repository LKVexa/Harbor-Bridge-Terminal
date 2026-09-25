@echo off
setlocal
set QNODE_ID=QN-01
set QNODE_CODE=qn01
set QNODE_HOME=%~dp0
if "%QNODE_HOME:~-1%"=="\" set QNODE_HOME=%QNODE_HOME:~0,-1%
set PRODUCT=%QNODE_HOME%
if not exist "%PRODUCT%\qvm\cli.py" (
  echo [QNODE] full QVM copy missing — run scripts\materialize-qnode-copies.cmd
  exit /b 1
)
set PYTHONPATH=%PRODUCT%
cd /d "%PRODUCT%"
if "%~1"=="" (
  where py >nul 2>nul && (py -3 -m qvm.cli info & exit /b %errorlevel%)
  where python >nul 2>nul && (python -m qvm.cli info & exit /b %errorlevel%)
  echo Python 3 not found & exit /b 2
)
where py >nul 2>nul && (py -3 -m qvm.cli %* & exit /b %errorlevel%)
where python >nul 2>nul && (python -m qvm.cli %* & exit /b %errorlevel%)
echo Python 3 not found & exit /b 2
