@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "HARBOR_ROOT=%~dp0.."
for %%I in ("%HARBOR_ROOT%") do set "HARBOR_ROOT=%%~fI"

set FAIL=0

REM VM substrate
call :link_one "bottle-rocket" "BOTTLE_ROCKET_PRODUCT_ROOT" "%HARBOR_ROOT%\mobile-platform\bottle-rocket\PRODUCT_LINK.txt" "%HARBOR_ROOT%\mobile-platform\bottle-rocket\product" "%USERPROFILE%\OneDrive\Desktop\New folder\BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K\BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K" "MANIFEST.json"
if errorlevel 1 set /a FAIL+=1

REM iOS app node (Bottle Rocket VM)
call :link_one "ios-lctl" "PRODUCT_ROOT" "%HARBOR_ROOT%\mobile-platform\nodes\ios-lctl\PRODUCT_LINK.txt" "%HARBOR_ROOT%\mobile-platform\nodes\ios-lctl\product" "%USERPROFILE%\OneDrive\Desktop\New folder\iOS735_LCTL_v0.1.0\iOS735_LCTL_v0.1.0" "README.md"
if errorlevel 1 set /a FAIL+=1

REM Android app node (Bottle Rocket VM)
call :link_one "android-lctl" "PRODUCT_ROOT" "%HARBOR_ROOT%\mobile-platform\nodes\android-lctl\PRODUCT_LINK.txt" "%HARBOR_ROOT%\mobile-platform\nodes\android-lctl\product" "%USERPROFILE%\OneDrive\Desktop\New folder\LinearAndroid_LCTL_v0.1.0\LinearAndroid_LCTL_v0.1.0" "TRANSLATION_REPORT.md"
if errorlevel 1 set /a FAIL+=1

REM RODEO = sidecar to Linear Android (Gradle substitute), not a peer app node
call :link_one "rodeo-sidecar" "PRODUCT_ROOT" "%HARBOR_ROOT%\mobile-platform\nodes\android-lctl\sidecar-rodeo\PRODUCT_LINK.txt" "%HARBOR_ROOT%\mobile-platform\nodes\android-lctl\sidecar-rodeo\product" "%USERPROFILE%\OneDrive\Desktop\New folder\RODEO" "rodeo.cmd"
if errorlevel 1 set /a FAIL+=1

if !FAIL!==0 (
  echo [link-mobile-platform] OK - VM substrate + iOS/Android app nodes + RODEO sidecar
  exit /b 0
)
echo [link-mobile-platform] completed with !FAIL! missing/failed link^(s^). Harbor can still start.
exit /b 1

:link_one
set "LABEL=%~1"
set "KEY=%~2"
set "LINK_FILE=%~3"
set "JUNCTION=%~4"
set "DEFAULT_SRC=%~5"
set "MARKER=%~6"
set "SRC="

if exist "%LINK_FILE%" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%LINK_FILE%") do (
    if /I "%%A"=="!KEY!" set "SRC=%%B"
  )
)
if not defined SRC set "SRC=!DEFAULT_SRC!"
if "!SRC!"=="" set "SRC=!DEFAULT_SRC!"

if not exist "!SRC!\!MARKER!" (
  echo [link-mobile-platform] !LABEL!: source not found:
  echo   "!SRC!"
  echo   ^(expected marker !MARKER!^) - update PRODUCT_LINK.txt then re-run.
  exit /b 1
)

if exist "!JUNCTION!\!MARKER!" (
  echo [link-mobile-platform] !LABEL!: already linked: "!JUNCTION!"
  exit /b 0
)

if exist "!JUNCTION!" (
  echo [link-mobile-platform] !LABEL!: removing stale junction/folder: "!JUNCTION!"
  rmdir "!JUNCTION!" 2>nul
)

mklink /J "!JUNCTION!" "!SRC!" >nul 2>&1
if errorlevel 1 (
  echo [link-mobile-platform] !LABEL!: junction failed; trying directory symlink...
  mklink /D "!JUNCTION!" "!SRC!" >nul 2>&1
)

if exist "!JUNCTION!\!MARKER!" (
  echo [link-mobile-platform] !LABEL!: OK -^> "!SRC!"
  exit /b 0
)
echo [link-mobile-platform] !LABEL!: FAILED to create link.
exit /b 1
