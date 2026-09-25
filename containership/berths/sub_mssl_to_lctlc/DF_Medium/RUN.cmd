@echo off
REM sub_mssl_to_lctlc\DF_Medium\RUN.cmd -- delegates to the ship (uc.py slot-run sub_mssl_to_lctlc DF_Medium).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" slot-run sub_mssl_to_lctlc DF_Medium %*
endlocal
