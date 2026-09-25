@echo off
setlocal
cd /d "%~dp0.."
where node >nul 2>nul || (
  echo Node.js not found on PATH.
  exit /b 2
)
node "%~dp0audit-qnode-load.js" %*
exit /b %errorlevel%
