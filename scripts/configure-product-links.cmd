@echo off
setlocal EnableExtensions EnableDelayedExpansion
REM Write workstation PRODUCT_LINK.txt defaults for Russell's known product trees.
REM Override any path by setting the matching env var before calling this script.
REM Does NOT commit secrets. Never touches ACCESS_TOKEN.txt.

set "HARBOR_ROOT=%~dp0.."
for %%I in ("%HARBOR_ROOT%") do set "HARBOR_ROOT=%%~fI"

if not defined QVM_PRODUCT_ROOT set "QVM_PRODUCT_ROOT=C:\Users\russe\OneDrive\Desktop\New folder\QVM_Quantum_VM_v8.1.0-alpha\QVM_Quantum_VM_v8.1.0-alpha"
if not defined JA21_PORTABLE_ROOT set "JA21_PORTABLE_ROOT=C:\Users\russe\Downloads\VB-JA21-VEC1-Portable-Optical-Desktop-9.8.7-WindowsSafe\JA21-Portable-Desktop-9.8.7"
if not defined BOTTLE_ROCKET_PRODUCT_ROOT set "BOTTLE_ROCKET_PRODUCT_ROOT=C:\Users\russe\OneDrive\Desktop\New folder\BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K\BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K"
if not defined IOS735_PRODUCT_ROOT set "IOS735_PRODUCT_ROOT=C:\Users\russe\OneDrive\Desktop\New folder\iOS735_LCTL_v0.1.0\iOS735_LCTL_v0.1.0"
if not defined LINEAR_ANDROID_PRODUCT_ROOT set "LINEAR_ANDROID_PRODUCT_ROOT=C:\Users\russe\OneDrive\Desktop\New folder\LinearAndroid_LCTL_v0.1.0\LinearAndroid_LCTL_v0.1.0"
if not defined RODEO_PRODUCT_ROOT set "RODEO_PRODUCT_ROOT=C:\Users\russe\OneDrive\Desktop\New folder\RODEO"

echo [configure-product-links] HARBOR_ROOT=%HARBOR_ROOT%

> "%HARBOR_ROOT%\qvm\PRODUCT_LINK.txt" (
  echo QVM_PRODUCT_ROOT=%QVM_PRODUCT_ROOT%
  echo QVM_VERSION=8.1.0-alpha
  echo LINK_TARGET=qvm\product
  echo NOTE=Written by scripts\configure-product-links.cmd. Junction only; do not commit the external product tree.
)

> "%HARBOR_ROOT%\optical-desktop\PRODUCT_LINK.txt" (
  echo JA21_PORTABLE_ROOT=%JA21_PORTABLE_ROOT%
  echo JA21_VERSION=9.8.7
  echo LINK_TARGET=optical-desktop\portable
  echo NOTE=Written by scripts\configure-product-links.cmd. Junction only; do not commit the external product tree.
)

> "%HARBOR_ROOT%\mobile-platform\bottle-rocket\PRODUCT_LINK.txt" (
  echo BOTTLE_ROCKET_PRODUCT_ROOT=%BOTTLE_ROCKET_PRODUCT_ROOT%
  echo BOTTLE_ROCKET_VERSION=3.0.0-MODEL_OPERATIONAL_110K
  echo ROLE=vm-substrate
  echo LINK_TARGET=mobile-platform\bottle-rocket\product
  echo NOTE=Written by scripts\configure-product-links.cmd. Junction only; do not commit the external product tree.
)

> "%HARBOR_ROOT%\mobile-platform\nodes\ios-lctl\PRODUCT_LINK.txt" (
  echo PRODUCT_ROOT=%IOS735_PRODUCT_ROOT%
  echo PRODUCT_VERSION=0.1.0
  echo NODE_ID=BR-VM-IOS735-LCTL
  echo KIND=bottle-rocket-vm-app-node
  echo VM_SUBSTRATE=mobile-platform\bottle-rocket
  echo LINK_TARGET=mobile-platform\nodes\ios-lctl\product
  echo NOTE=Written by scripts\configure-product-links.cmd. Junction only; do not commit the external product tree.
)

> "%HARBOR_ROOT%\mobile-platform\nodes\android-lctl\PRODUCT_LINK.txt" (
  echo PRODUCT_ROOT=%LINEAR_ANDROID_PRODUCT_ROOT%
  echo PRODUCT_VERSION=0.1.0
  echo NODE_ID=BR-VM-LINEARANDROID-LCTL
  echo KIND=bottle-rocket-vm-app-node
  echo VM_SUBSTRATE=mobile-platform\bottle-rocket
  echo LINK_TARGET=mobile-platform\nodes\android-lctl\product
  echo NOTE=Written by scripts\configure-product-links.cmd. Junction only; do not commit the external product tree.
)

> "%HARBOR_ROOT%\mobile-platform\nodes\android-lctl\sidecar-rodeo\PRODUCT_LINK.txt" (
  echo PRODUCT_ROOT=%RODEO_PRODUCT_ROOT%
  echo PRODUCT_VERSION=0.1.0
  echo SIDECAR_ID=RODEO-GRADLE-SUBSTITUTE
  echo KIND=linear-android-sidecar
  echo PAIRS_WITH=mobile-platform\nodes\android-lctl
  echo ROLE=gradle-substitute-build-toolchain
  echo VM_SUBSTRATE=mobile-platform\bottle-rocket
  echo LINK_TARGET=mobile-platform\nodes\android-lctl\sidecar-rodeo\product
  echo NOTE=Written by scripts\configure-product-links.cmd. Junction only; do not commit the external product tree.
)

echo [configure-product-links] wrote PRODUCT_LINK.txt for qvm, optical-desktop, bottle-rocket, ios-lctl, android-lctl, rodeo-sidecar.
echo Next: scripts\link-qvm.cmd ^& scripts\link-optical-desktop.cmd ^& scripts\link-mobile-platform.cmd
exit /b 0