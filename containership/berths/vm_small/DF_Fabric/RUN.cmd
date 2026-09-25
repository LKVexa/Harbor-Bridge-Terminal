@echo off
REM vm_small\DF_Fabric\RUN.cmd -- delegates to the ship (uc.py run vm_small).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" run vm_small %*
endlocal
