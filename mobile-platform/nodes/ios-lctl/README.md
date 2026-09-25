# iOS735_LCTL — Bottle Rocket VM application node (iOS)

**Kind:** `bottle-rocket-vm-app-node`  
**Node ID:** `BR-VM-IOS735-LCTL`  
**Platform:** iOS  
**VM substrate:** `mobile-platform/bottle-rocket` (BOTTLE_ROCKET 3.0.0 MODEL OPERATIONAL 110K)

In Harbor this package is the **iOS application node that is a Bottle Rocket VM**
— peer to Linear Android LCTL. (RODEO is **not** an iOS peer; it is the Gradle
substitute **sidecar** under the Android node.)

## What the product is (from its README)

**iOS735 → LCTL v0.1.0**: the iOS735 skeleton (Swift L3 of the iOS735_VEC1 stack)
translated into LCTL using LCTL 1.6.1-RC1 (column compile) and verified with
LCTL 1.6.0. Ships 43 phase modules + app unit, sealed canonical LCTL
(~17k rows / 822 frames), translation map, and verify tools. Round-trip
reported 735/735 components matching the Swift skeleton. Needs Java 21 +
Python 3.10+ and the LCTL toolchains to re-verify.

## On-disk layout

```
mobile-platform/nodes/ios-lctl/
  PRODUCT_LINK.txt   → Desktop New folder\iOS735_LCTL_v0.1.0\… nested root
  VERSION            0.1.0
  IDENTITY.json      node identity + VM binding
  README.md          this file
  product/           junction (gitignored)
```

```bat
scripts\link-mobile-platform.cmd
```

## Honest scope

This is an **LCTL translation / verification corpus** for the iOS735 design
skeleton. Harbor does **not** claim an iOS app binary is running inside the
bridge terminal.
