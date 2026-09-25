@echo off
REM vm_small\DF_Medium\RUN.cmd -- delegates to the ship (uc.py slot-run vm_small DF_Medium).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" slot-run vm_small DF_Medium %*
endlocal
