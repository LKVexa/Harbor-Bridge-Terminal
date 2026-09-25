@echo off
REM sub_mssl_to_lctlc\DF_Xtra_Large\VERIFY.cmd -- delegates to the ship (uc.py verify sub_mssl_to_lctlc).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" verify sub_mssl_to_lctlc %*
endlocal
