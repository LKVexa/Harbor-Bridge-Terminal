@echo off
REM vm_medium\DF_Fabric\RUN.cmd -- delegates to the ship (uc.py run vm_medium).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" run vm_medium %*
endlocal
