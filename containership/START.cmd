@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0" || (echo Cannot open the containership directory. & exit /b 2)
if defined NODE goto run
set "NODE=node"
:run
"%NODE%" vws\tools\start-ship.js %*
set "UC_EXIT=%ERRORLEVEL%"
if not "%UC_EXIT%"=="0" echo Terminal stopped or was refused. Exit code %UC_EXIT%.
popd
if not "%UC_NO_PAUSE%"=="1" pause
endlocal & exit /b %UC_EXIT%
