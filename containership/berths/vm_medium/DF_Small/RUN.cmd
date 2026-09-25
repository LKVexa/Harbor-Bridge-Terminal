@echo off
REM vm_medium\DF_Small\RUN.cmd -- delegates to the ship (uc.py slot-run vm_medium DF_Small).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" slot-run vm_medium DF_Small %*
endlocal
