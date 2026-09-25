@echo off
REM sub_pa21_language_studio\DF_Small\VERIFY.cmd -- delegates to the ship (uc.py verify sub_pa21_language_studio).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" verify sub_pa21_language_studio %*
endlocal
