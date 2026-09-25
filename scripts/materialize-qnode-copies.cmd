@echo off
setlocal EnableExtensions
pushd "%~dp0.."
where node >nul 2>&1 || (
  echo Node.js required to materialize Qnode full copies.
  popd
  exit /b 2
)
echo [Harbor] Materializing 50 full QVM copies into qnodes\QN-01..QN-50 ...
node "%~dp0materialize-qnode-copies.js" %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
