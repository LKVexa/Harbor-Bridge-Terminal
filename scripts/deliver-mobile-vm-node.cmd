@echo off
setlocal
set "HARBOR_ROOT=%~dp0.."
node "%HARBOR_ROOT%\mobile-platform\compiler\deliver-mobile-vm-node.js" %*
exit /b %ERRORLEVEL%
