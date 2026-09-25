@echo off
REM sub_pa21_language_studio\DF_Fabric\RUN.cmd -- delegates to the ship (uc.py run sub_pa21_language_studio).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" run sub_pa21_language_studio %*
endlocal
