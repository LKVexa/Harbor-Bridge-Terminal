@echo off
setlocal
set QNODE_ID=QN-26
set QNODE_CODE=qn26
set QNODE_HOME=%~dp0
if "%QNODE_HOME:~-1%"=="\" set QNODE_HOME=%QNODE_HOME:~0,-1%
set HARBOR_ROOT=%QNODE_HOME%\..\..
call "%HARBOR_ROOT%\scripts\link-qvm.cmd" >nul 2>&1
set PRODUCT=%HARBOR_ROOT%\qvm\product
if not exist "%PRODUCT%\qvm\cli.py" (
  echo [QNODE] product missing — run scripts\link-qvm.cmd
  exit /b 1
)
set PYTHONPATH=%PRODUCT%
cd /d "%QNODE_HOME%\runtime"
if "%~1"=="" (
  where py >nul 2>nul && (py -3 -m qvm.cli info & exit /b %errorlevel%)
  where python >nul 2>nul && (python -m qvm.cli info & exit /b %errorlevel%)
  echo Python 3 not found & exit /b 2
)
where py >nul 2>nul && (py -3 -m qvm.cli %* & exit /b %errorlevel%)
where python >nul 2>nul && (python -m qvm.cli %* & exit /b %errorlevel%)
echo Python 3 not found & exit /b 2
