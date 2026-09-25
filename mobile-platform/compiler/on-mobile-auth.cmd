@echo off
setlocal
set "HERE=%~dp0"
node "%HERE%hooks\on-mobile-auth.js" %*
exit /b %ERRORLEVEL%
