@echo off
REM vm_xtra_large\DF_Medium\RUN.cmd -- delegates to the ship (uc.py slot-run vm_xtra_large DF_Medium).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" slot-run vm_xtra_large DF_Medium %*
endlocal
