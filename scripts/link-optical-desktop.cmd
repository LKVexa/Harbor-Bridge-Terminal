@echo off
setlocal
set HARBOR_ROOT=%~dp0..
if "%HARBOR_ROOT:~-1%"=="\" set HARBOR_ROOT=%HARBOR_ROOT:~0,-1%
set LINK_FILE=%HARBOR_ROOT%\optical-desktop\PRODUCT_LINK.txt
set JUNCTION=%HARBOR_ROOT%\optical-desktop\portable
set DEFAULT_SRC=%USERPROFILE%\Downloads\VB-JA21-VEC1-Portable-Optical-Desktop-9.8.7-WindowsSafe\JA21-Portable-Desktop-9.8.7

set JA21_SRC=
if exist "%LINK_FILE%" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%LINK_FILE%") do (
    if /I "%%A"=="JA21_PORTABLE_ROOT" set JA21_SRC=%%B
  )
)
if "%JA21_SRC%"=="" set JA21_SRC=%DEFAULT_SRC%

if not exist "%JA21_SRC%\Start JA21 Portable Desktop.cmd" (
  echo [link-optical-desktop] JA21 Portable Desktop not found at:
  echo   %JA21_SRC%
  echo Update optical-desktop\PRODUCT_LINK.txt then re-run.
  exit /b 1
)

if exist "%JUNCTION%\Start JA21 Portable Desktop.cmd" (
  echo [link-optical-desktop] already linked: %JUNCTION%
  exit /b 0
)

if exist "%JUNCTION%" (
  echo [link-optical-desktop] removing stale junction/folder: %JUNCTION%
  rmdir "%JUNCTION%" 2>nul
)

mklink /J "%JUNCTION%" "%JA21_SRC%"
if errorlevel 1 (
  echo [link-optical-desktop] junction failed; trying directory symlink...
  mklink /D "%JUNCTION%" "%JA21_SRC%"
)
if exist "%JUNCTION%\Start JA21 Portable Desktop.cmd" (
  echo [link-optical-desktop] OK -^> %JA21_SRC%
  exit /b 0
)
echo [link-optical-desktop] FAILED to create link.
exit /b 1
