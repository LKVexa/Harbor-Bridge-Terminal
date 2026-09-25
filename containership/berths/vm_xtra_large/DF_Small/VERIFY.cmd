@echo off
REM vm_xtra_large\DF_Small\VERIFY.cmd -- delegates to the ship (uc.py verify vm_xtra_large).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" verify vm_xtra_large %*
endlocal
