@echo off
setlocal
set "HERE=%~dp0"
node "%HERE%compile-mobile-vm-node.js" %*
exit /b %ERRORLEVEL%
