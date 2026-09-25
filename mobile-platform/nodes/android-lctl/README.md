# LinearAndroid_LCTL — Bottle Rocket VM application node (Android)

**Kind:** `bottle-rocket-vm-app-node`  
**Node ID:** `BR-VM-LINEARANDROID-LCTL`  
**VM substrate:** `mobile-platform/bottle-rocket` (BOTTLE_ROCKET 3.0.0 MODEL OPERATIONAL 110K)  
**Sidecar:** `sidecar-rodeo/` — **RODEO** (Gradle substitute), not a peer app node

In Harbor this package is the **Android application node that is a Bottle Rocket
VM**. Build/toolchain work for this node uses the RODEO sidecar.

## What the product is (from its TRANSLATION_REPORT)

**LinearAndroid v0.1.0 → LCTL**: Kotlin/Gradle Android skeleton translated to
LCTL-C 1.0 (LCTL 1.6.1-RC1) and sealed canonical LCTL/1.3. **22 units**,
~29,970 rows; semantic overlay (topology, memory, distributed sync) plus a
source-line MODEL layer. Reported verify 22/22 and round-trip 152/152 files
SHA-identical. Tools: `kt2lctlc.py`, `lctl2src.py`, mutation campaign.

## On-disk layout

```
mobile-platform/nodes/android-lctl/
  PRODUCT_LINK.txt / VERSION / IDENTITY.json / README.md
  product/              junction → LinearAndroid_LCTL nested root (gitignored)
  sidecar-rodeo/        RODEO Gradle-substitute sidecar (junction + metadata)
```

```bat
scripts\link-mobile-platform.cmd
```

## Honest scope

This is an **LCTL translation / verification corpus** for LinearAndroid plus a
linked **build sidecar** (RODEO). Harbor does **not** claim an Android APK or
emulator session is running inside the bridge terminal.
