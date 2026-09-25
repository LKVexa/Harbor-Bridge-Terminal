@echo off
setlocal EnableExtensions
pushd "%~dp0"
set HARBOR_ROOT=%CD%

REM --- Bind DF fabric (New folder beside Desktop Harbor) ---
if not defined DF_ROOT (
  if exist "%USERPROFILE%\OneDrive\Desktop\New folder\DF_Fabric\adapter\dfabric\cli.py" (
    set "DF_ROOT=%USERPROFILE%\OneDrive\Desktop\New folder"
  )
)
if not defined DF_ROOT (
  if exist "%HARBOR_ROOT%\..\New folder\DF_Fabric\adapter\dfabric\cli.py" (
    for %%I in ("%HARBOR_ROOT%\..\New folder") do set "DF_ROOT=%%~fI"
  )
)

REM --- Qnode fleet ---
set "QNODE_ROOT=%HARBOR_ROOT%\qnodes"
set "HARBOR_ROOT=%HARBOR_ROOT%"

REM --- Optional seed junction for rematerializing copies ---
call "%~dp0scripts\link-qvm.cmd"
if errorlevel 1 (
  echo [START_HARBOR] warning: QVM seed link missing; rematerialize will need PRODUCT_LINK.txt.
)

REM --- Ensure full QVM copies exist (QN-01 has local qvm\cli.py) ---
if not exist "%QNODE_ROOT%\QN-01\qvm\cli.py" (
  echo [START_HARBOR] Qnode full copies missing — materializing from seed...
  call "%~dp0scripts\materialize-qnode-copies.cmd"
  if errorlevel 1 (
    echo [START_HARBOR] warning: materialize failed; Qnodes will show incomplete until fixed.
  )
)

echo.
echo   Harbor Bridge Terminal
echo   HARBOR_ROOT=%HARBOR_ROOT%
echo   QNODE_ROOT=%QNODE_ROOT%
echo   DF_ROOT=%DF_ROOT%
echo   Focus codes: qn01..qn50  ns nm nl nx nf
echo.

cd /d "%HARBOR_ROOT%\bridge-terminal"
where node >nul 2>&1 || (echo Node.js 20+ required. & popd & pause & exit /b 2)
node tools\start-local.js %*
set RC=%ERRORLEVEL%
popd
exit /b %RC%
