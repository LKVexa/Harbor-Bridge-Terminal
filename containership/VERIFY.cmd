@echo off
REM Unikernel_Containership\VERIFY.cmd -- the ship battery; exit non-zero on any FAIL
REM The ship runs its Python in UTF-8 mode: the hull's verifier and the engines' toolchains write UTF-8, and a
REM cp1252 console or pipe must not be able to crash them (PYTHONUTF8 also reaches every tool the ship starts).
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"
if "%PYTHON%"=="" set PYTHON=python
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
"%PYTHON%" -X utf8 -B uc.py verify %*
set "UC_EXIT=%ERRORLEVEL%"
endlocal & exit /b %UC_EXIT%
