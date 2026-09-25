# RODEO — sidecar to Linear Android (Gradle substitute)

**Kind:** `linear-android-sidecar`  
**Sidecar ID:** `RODEO-GRADLE-SUBSTITUTE`  
**Pairs with:** `BR-VM-LINEARANDROID-LCTL` (`mobile-platform/nodes/android-lctl`)  
**VM substrate (shared):** `mobile-platform/bottle-rocket`

RODEO is **not** a peer mobile application node alongside iOS / Android LCTL.
It is the **Gradle-substitute build toolchain sidecar** for the Linear Android
application node (which is itself a Bottle Rocket VM).

## What the product is (from its README)

RODEO 0.1.0 is a **Gradle substitute** (Python 3.10+, stdlib only) from the
Gradle Substitute 1,005-component checklist (~196/1005 implemented). It can
bootstrap against a Bottle Rocket VM (`rodeo.bootstrap.json`), run `brctl`
preflight when built, and support `brvm` tasks. In Harbor that VM context is
the shared 110K substrate; the app it accompanies is Linear Android LCTL.

## On-disk layout

```
mobile-platform/nodes/android-lctl/sidecar-rodeo/
  PRODUCT_LINK.txt   → Desktop New folder\RODEO
  VERSION            0.1.0
  IDENTITY.json      sidecar identity + pairs_with Linear Android
  README.md          this file
  product/           junction (gitignored)
```

```bat
scripts\link-mobile-platform.cmd
```

## Operator note

RODEO's shipped `rodeo.bootstrap.json` points at a relative **61K** Bottle Rocket
path. Harbor's linked substrate is the **110K** tree under
`mobile-platform/bottle-rocket/product`. Point `vm_root` at that junction if you
want `require_vm` / `brvm` against Harbor's binding while building for Linear Android.
