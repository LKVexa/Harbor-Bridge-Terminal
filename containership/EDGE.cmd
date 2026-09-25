@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
where py >nul 2>nul && (py -3 -B "%ROOT%uc.py" edge %* & exit /b %errorlevel%)
where python >nul 2>nul && (python -B "%ROOT%uc.py" edge %* & exit /b %errorlevel%)
echo Python 3 was not found. 1>&2
exit /b 3
