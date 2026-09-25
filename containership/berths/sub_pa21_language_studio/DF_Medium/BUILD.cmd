@echo off
REM sub_pa21_language_studio\DF_Medium\BUILD.cmd -- delegates to the ship (uc.py build).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" build %*
endlocal
