@echo off
setlocal EnableExtensions
pushd "%~dp0"
set HARBOR_ROOT=%CD%

REM Ensure optical desktop junction exists
call "%~dp0scripts\link-optical-desktop.cmd"
if errorlevel 1 (
  echo [START_HARBOR_BROWSER] optical desktop not available.
  popd
  exit /b 1
)

set "JA21_ROOT=%HARBOR_ROOT%\optical-desktop\portable"
if not exist "%JA21_ROOT%\Start JA21 Portable Desktop.cmd" (
  echo [START_HARBOR_BROWSER] missing: %JA21_ROOT%\Start JA21 Portable Desktop.cmd
  popd
  exit /b 1
)

REM URL from arg1, else JA21_START_URL, else probe Harbor loopback ports
set "URL=%~1"
if not defined URL set "URL=%JA21_START_URL%"
if not defined URL (
  for /L %%P in (10000,1,10019) do (
    if not defined URL (
      powershell -NoLogo -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.ReceiveTimeout=200; $c.SendTimeout=200; $iar=$c.BeginConnect('127.0.0.1',%%P,$null,$null); if ($iar.AsyncWaitHandle.WaitOne(200) -and $c.Connected) { $c.Close(); exit 0 } else { try{$c.Close()}catch{}; exit 1 } } catch { exit 1 }" >nul 2>&1
      if not errorlevel 1 set "URL=http://127.0.0.1:%%P/"
    )
  )
)
if not defined URL set "URL=http://127.0.0.1:10000/"

set "JA21_START_URL=%URL%"
echo [START_HARBOR_BROWSER] JA21_START_URL=%JA21_START_URL%
echo [START_HARBOR_BROWSER] launching optical desktop (omni-bin), NOT the system default browser.
cd /d "%JA21_ROOT%"
call "%JA21_ROOT%\host\portable-env.cmd" || (
  popd
  exit /b %ERRORLEVEL%
)
where powershell.exe >nul 2>nul || (
  echo ERROR: Windows PowerShell required.
  popd
  exit /b 2
)
REM Pass -StartUrl explicitly so omni/start navigation is guaranteed
start "JA21 Harbor" powershell.exe -NoLogo -NoProfile -STA -ExecutionPolicy Bypass -File "%JA21_ROOT%\host\Start-JA21Browser.ps1" -Root "%JA21_ROOT%" -StartUrl "%JA21_START_URL%"
echo [START_HARBOR_BROWSER] started JA21 Portable Desktop 9.8.7 with start URL.
popd
exit /b 0
