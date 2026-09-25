@echo off
rem  The scriptable command line. `studio.cmd status --json`, `studio.cmd run myapp`, …
setlocal
set HERE=%~dp0
where py >nul 2>&1 && (py -3 "%HERE%studio.py" %* & goto :eof)
where python >nul 2>&1 && (python "%HERE%studio.py" %* & goto :eof)
echo Python 3.8 or newer is required and was not found on PATH.
exit /b 2
