@echo off
setlocal DisableDelayedExpansion
pushd "%~dp0vws" || exit /b 2
if not defined NODE set "NODE=node"
"%NODE%" tools\test.js %*
set "RC=%ERRORLEVEL%"
popd
if not "%RC%"=="0" echo VWS check failed with exit %RC%.
if not defined UC_NO_PAUSE pause
exit /b %RC%
