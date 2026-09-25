@echo off
REM vm_large\DF_Large\VERIFY.cmd -- delegates to the ship (uc.py verify vm_large).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" verify vm_large %*
endlocal
