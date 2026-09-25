@echo off
rem  Opens the Language Studio install window in the default browser.
rem  Nothing is installed until the button in that window is pressed.
setlocal
set HERE=%~dp0
where py >nul 2>&1 && (py -3 "%HERE%studio.py" ui %* & goto :eof)
where python >nul 2>&1 && (python "%HERE%studio.py" ui %* & goto :eof)
echo Python 3.8 or newer is required and was not found on PATH.
echo Install it from python.org, then run this file again.
pause
