@echo off
REM vm_large\DF_Fabric\BUILD.cmd -- delegates to the ship (uc.py build).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" build %*
endlocal
