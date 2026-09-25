@echo off
REM vm_xtra_large\DF_Fabric\RUN.cmd -- delegates to the ship (uc.py run vm_xtra_large).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" run vm_xtra_large %*
endlocal
