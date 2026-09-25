@echo off
setlocal EnableExtensions
set "HARBOR_ROOT=%~dp0.."
set "PRODUCT=%HARBOR_ROOT%\mobile-platform\bottle-rocket\product"
set "BIN=%HARBOR_ROOT%\mobile-platform\compiler\bin"
set "COMPAT=%BIN%\wincompat.h"
set "LOGDIR=%HARBOR_ROOT%\mobile-platform\compiler\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
set "LOG=%LOGDIR%\build-brctl.log"

echo [build-brctl] Harbor Bottle Rocket brctl builder > "%LOG%"
echo [build-brctl] %DATE% %TIME% >> "%LOG%"

if not exist "%PRODUCT%\Makefile" (
  echo [build-brctl] ERROR: product Makefile missing. Run scripts\link-mobile-platform.cmd
  echo ERROR: product Makefile missing >> "%LOG%"
  exit /b 2
)
if not exist "%BIN%" mkdir "%BIN%"

REM Prefer MSYS2 UCRT64 gcc+make (installed on MoneyMoneyMoney)
set "MSYS_GCC="
if exist "C:\msys64\ucrt64\bin\gcc.exe" set "MSYS_GCC=C:\msys64\ucrt64\bin"
if not defined MSYS_GCC if exist "C:\msys64\mingw64\bin\gcc.exe" set "MSYS_GCC=C:\msys64\mingw64\bin"
if not defined MSYS_GCC (
  echo [build-brctl] ERROR: MSYS2 gcc not found. Install MSYS2 UCRT64 toolchain + openssl.
  echo   pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-make mingw-w64-ucrt-x86_64-openssl
  echo   Or use WSL: wsl -e bash -lc "sudo apt-get install -y build-essential libssl-dev && make -C product all"
  echo ERROR: no gcc >> "%LOG%"
  exit /b 3
)

set "PATH=%MSYS_GCC%;C:\msys64\usr\bin;%PATH%"
echo [build-brctl] using gcc from %MSYS_GCC%
echo using %MSYS_GCC% >> "%LOG%"

if not exist "%COMPAT%" (
  echo [build-brctl] ERROR: missing %COMPAT%
  exit /b 4
)

pushd "%PRODUCT%"
if not exist ".build" mkdir ".build"
copy /Y "%COMPAT%" ".build\wincompat.h" >nul
set "CPPFLAGS=-Isrc -D_GNU_SOURCE -D_POSIX_C_SOURCE=200809L -include .build/wincompat.h"
set "CFLAGS=-std=c11 -O2 -Wall -Wextra -fno-common -fstack-protector-strong"
make CC=gcc "CPPFLAGS=%CPPFLAGS%" "CFLAGS=%CFLAGS%" all >> "%LOG%" 2>&1
set RC=%ERRORLEVEL%
popd

if not "%RC%"=="0" (
  echo [build-brctl] make FAILED exit=%RC% ? see %LOG%
  exit /b %RC%
)

if exist "%PRODUCT%\.build\brctl.exe" (
  copy /Y "%PRODUCT%\.build\brctl.exe" "%BIN%\brctl.exe" >nul
) else if exist "%PRODUCT%\.build\brctl" (
  copy /Y "%PRODUCT%\.build\brctl" "%BIN%\brctl.exe" >nul
) else (
  echo [build-brctl] ERROR: brctl binary not produced
  exit /b 5
)

echo [build-brctl] installed %BIN%\brctl.exe
"%BIN%\brctl.exe" >> "%LOG%" 2>&1
echo [build-brctl] smoke assemble...
"%BIN%\brctl.exe" assemble "%PRODUCT%\examples\boot.mssl" "%PRODUCT%\.build\harbor-boot.brimg" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo [build-brctl] WARNING: assemble smoke failed ? binary installed but compile may skip assemble
  echo assemble smoke FAILED >> "%LOG%"
  exit /b 6
)
echo [build-brctl] OK assemble smoke PASS
echo OK >> "%LOG%"
exit /b 0
