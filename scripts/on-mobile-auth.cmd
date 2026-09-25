@echo off
setlocal
set "HARBOR_ROOT=%~dp0.."
node "%HARBOR_ROOT%\mobile-platform\compiler\hooks\on-mobile-auth.js" %*
exit /b %ERRORLEVEL%
