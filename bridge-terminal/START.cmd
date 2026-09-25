@echo off
setlocal
pushd "%~dp0"
where node >nul 2>&1 || (echo Node.js 20 or newer is required. Nothing was installed. & pause & exit /b 2)
node tools\start-local.js %*
popd
pause
