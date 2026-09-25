@echo off
REM vm_small\DF_Small\BUILD.cmd -- delegates to the ship (uc.py build).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" build %*
endlocal
