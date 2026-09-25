@echo off
REM vm_small\DF_Small\VERIFY.cmd -- delegates to the ship (uc.py verify vm_small).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" verify vm_small %*
endlocal
