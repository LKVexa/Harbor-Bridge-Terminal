@echo off
setlocal
set HARBOR_ROOT=%~dp0..
if "%HARBOR_ROOT:~-1%"=="\" set HARBOR_ROOT=%HARBOR_ROOT:~0,-1%
set LINK_FILE=%HARBOR_ROOT%\qvm\PRODUCT_LINK.txt
set JUNCTION=%HARBOR_ROOT%\qvm\product
set DEFAULT_SRC=C:\Users\russe\OneDrive\Desktop\New folder\QVM_Quantum_VM_v8.1.0-alpha\QVM_Quantum_VM_v8.1.0-alpha

set QVM_SRC=
if exist "%LINK_FILE%" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%LINK_FILE%") do (
    if /I "%%A"=="QVM_PRODUCT_ROOT" set QVM_SRC=%%B
  )
)
if "%QVM_SRC%"=="" set QVM_SRC=%DEFAULT_SRC%

if not exist "%QVM_SRC%\qvm\cli.py" (
  echo [link-qvm] QVM product not found at:
  echo   %QVM_SRC%
  echo Update qvm\PRODUCT_LINK.txt then re-run.
  exit /b 1
)

if exist "%JUNCTION%" (
  echo [link-qvm] already linked: %JUNCTION%
  exit /b 0
)

mklink /J "%JUNCTION%" "%QVM_SRC%"
if errorlevel 1 (
  echo [link-qvm] junction failed; trying directory symlink...
  mklink /D "%JUNCTION%" "%QVM_SRC%"
)
if exist "%JUNCTION%\qvm\cli.py" (
  echo [link-qvm] OK -^> %QVM_SRC%
  exit /b 0
)
echo [link-qvm] FAILED to create link. Create junction manually or copy product once.
exit /b 1
