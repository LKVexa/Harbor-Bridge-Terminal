# Bottle Rocket VM substrate (3.0.0 MODEL OPERATIONAL 110K)

This folder is Harbor's **shared Bottle Rocket VM layer** for the mobile platform.

**Mobile application nodes** (iOS735_LCTL, LinearAndroid_LCTL) are **Bottle Rocket
VMs** that bind to this substrate. **RODEO** is **not** an application node — it
is the **Gradle-substitute sidecar** under Linear Android.

Harbor does **not** claim those apps are already launched inside the HERMIT
gateway — this is a first-class linked platform binding with operator docs.

## On-disk layout

```
mobile-platform/bottle-rocket/
  PRODUCT_LINK.txt   absolute path to Desktop New folder BR 110K (committed)
  VERSION            3.0.0-MODEL_OPERATIONAL_110K (committed)
  README.md          this file
  product/           directory junction → BOTTLE_ROCKET_…_110K nested root (gitignored)
```

```bat
scripts\link-mobile-platform.cmd
```

`START_HARBOR.cmd` calls that automatically. Missing sources warn; Harbor start continues.

## What the product is (from its README)

Offline **C11 SIM-core VM**, profile `MODEL_OPERATIONAL` (110K variant). Host
controller `brctl` assembles/runs MSSL→BRIM images; Photon control plane is
vendored unbound under `PHOTON/`. No production card/AID authority is included.

## Relation to mobile platform pieces

| Harbor path | Role |
|---|---|
| `mobile-platform/bottle-rocket/` | Shared VM / model operational stack |
| `mobile-platform/nodes/ios-lctl/` | **iOS** app node = Bottle Rocket VM |
| `mobile-platform/nodes/android-lctl/` | **Android** app node = Bottle Rocket VM |
| `…/android-lctl/sidecar-rodeo/` | **Sidecar** to Linear Android (Gradle substitute) |

See `../README.md` and `fleet/MOBILE_PLATFORM.json`.
