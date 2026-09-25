@echo off
setlocal
set "HARBOR_ROOT=%~dp0.."
node "%HARBOR_ROOT%\mobile-platform\compiler\compile-mobile-vm-node.js" %*
exit /b %ERRORLEVEL%
