@echo off
setlocal
set "HERE=%~dp0"
node "%HERE%deliver-mobile-vm-node.js" %*
exit /b %ERRORLEVEL%
