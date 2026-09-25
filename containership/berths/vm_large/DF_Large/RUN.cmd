@echo off
REM vm_large\DF_Large\RUN.cmd -- delegates to the ship (uc.py slot-run vm_large DF_Large).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" slot-run vm_large DF_Large %*
endlocal
