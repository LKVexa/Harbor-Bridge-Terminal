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

REM --- VB-JA21 portable optical desktop (omni-bin browser for Harbor URL) ---
call "%~dp0scripts\link-optical-desktop.cmd"
if errorlevel 1 (
  echo [START_HARBOR] warning: optical desktop not linked; Harbor URL will not open in JA21.
  echo               Update optical-desktop\PRODUCT_LINK.txt then re-run scripts\link-optical-desktop.cmd
)

REM --- Mobile platform: Bottle Rocket VM + iOS/Android app nodes; RODEO=Linear Android sidecar ---
call "%~dp0scripts\link-mobile-platform.cmd"
if errorlevel 1 (
  echo [START_HARBOR] warning: mobile-platform link incomplete; Harbor continues.
  echo               Update mobile-platform\*\PRODUCT_LINK.txt then re-run scripts\link-mobile-platform.cmd
)

REM --- Ensure full QVM copies exist (QN-01 has local qvm\cli.py) ---
if not exist "%QNODE_ROOT%\QN-01\qvm\cli.py" (
  echo [START_HARBOR] Qnode full copies missing - materializing from seed...
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
echo   Browser: VB-JA21 Portable Optical Desktop (not system default)
echo   Mobile: Bottle Rocket VM + iOS/Android nodes (RODEO=Android sidecar)
echo.

cd /d "%HARBOR_ROOT%\bridge-terminal"
where node >nul 2>&1 || (
  echo Node.js 20+ required. Nothing was started.
  popd
  echo.
  pause
  exit /b 2
)
node tools\start-local.js %*
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo.
  echo [START_HARBOR] bridge exited with code %RC%.
  echo.
  pause
)
popd
exit /b %RC%
