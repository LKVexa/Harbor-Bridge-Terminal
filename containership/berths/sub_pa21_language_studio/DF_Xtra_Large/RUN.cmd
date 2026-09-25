@echo off
REM sub_pa21_language_studio\DF_Xtra_Large\RUN.cmd -- delegates to the ship (uc.py slot-run sub_pa21_language_studio DF_Xtra_Large).
setlocal
set HERE=%~dp0
if "%PYTHON%"=="" set PYTHON=python
"%PYTHON%" -B "%HERE%..\..\..\uc.py" slot-run sub_pa21_language_studio DF_Xtra_Large %*
endlocal
