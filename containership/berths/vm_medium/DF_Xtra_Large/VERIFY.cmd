@echo off
REM vm_medium\DF_Xtra_Large\VERIFY.cmd -- delegates to the ship (uc.py verify vm_medium).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" verify vm_medium %*
endlocal
