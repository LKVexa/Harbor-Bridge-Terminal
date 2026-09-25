@echo off
REM sub_mssl_to_lctlc\DF_Fabric\RUN.cmd -- delegates to the ship (uc.py run sub_mssl_to_lctlc).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" run sub_mssl_to_lctlc %*
endlocal
