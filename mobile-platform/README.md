# Mobile platform integration (Bottle Rocket VMs)

Harbor links a **mobile platform** whose rules are:

1. **Each mobile platform application node is a Bottle Rocket VM.**
2. **RODEO is a sidecar to Linear Android** because RODEO is a **Gradle substitute**
   (build toolchain companion) — **not** a peer application node.

`BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K` is the shared **VM substrate**.
Application nodes: **iOS735_LCTL** (iOS) and **LinearAndroid_LCTL** (Android).
**RODEO** lives under the Android node as `sidecar-rodeo/`.

This is a **linked operator surface** (junctions + identity metadata). It does
**not** invent a runtime that launches iOS/Android binaries inside HERMIT.

## Layout

```
mobile-platform/
├── README.md
├── bottle-rocket/                          VM substrate (shared)
│   ├── PRODUCT_LINK.txt / VERSION / README.md
│   └── product/                            junction → BR 110K (gitignored)
└── nodes/
    ├── ios-lctl/                           iOS app node = Bottle Rocket VM
    │   ├── PRODUCT_LINK.txt / VERSION / IDENTITY.json / README.md
    │   └── product/                        junction (gitignored)
    └── android-lctl/                       Android app node = Bottle Rocket VM
        ├── PRODUCT_LINK.txt / VERSION / IDENTITY.json / README.md
        ├── product/                        junction (gitignored)
        └── sidecar-rodeo/                  RODEO = Gradle substitute sidecar
            ├── PRODUCT_LINK.txt / VERSION / IDENTITY.json / README.md
            └── product/                    junction → RODEO (gitignored)
```

Fleet twin: [`fleet/MOBILE_PLATFORM.json`](../fleet/MOBILE_PLATFORM.json).

## Link / refresh

```bat
scripts\link-mobile-platform.cmd
```

`START_HARBOR.cmd` calls this after the optical-desktop link. Missing Desktop
`New folder` sources **warn**; Harbor start is not blocked.

| Role | Default absolute path |
|---|---|
| VM substrate | `…\New folder\BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K\BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K` |
| iOS app node | `…\New folder\iOS735_LCTL_v0.1.0\iOS735_LCTL_v0.1.0` |
| Android app node | `…\New folder\LinearAndroid_LCTL_v0.1.0\LinearAndroid_LCTL_v0.1.0` |
| Android sidecar (RODEO) | `…\New folder\RODEO` |

## Component summaries (from real product files)

| Piece | Role | Summary |
|---|---|---|
| **Bottle Rocket 3.0.0 110K** | VM substrate | Offline C11 SIM-core VM (`MODEL_OPERATIONAL`); `brctl`; MSSL→BRIM; Photon unbound. |
| **iOS735_LCTL 0.1.0** | iOS app node (BR VM) | iOS735 Swift skeleton → LCTL-C / canonical LCTL + verify evidence. |
| **LinearAndroid_LCTL 0.1.0** | Android app node (BR VM) | LinearAndroid Kotlin/Gradle skeleton → LCTL translation + round-trip tools. |
| **RODEO 0.1.0** | Sidecar to Linear Android | Gradle substitute (~196/1005 checklist); boots on Bottle Rocket; not a peer app node. |

## Licensing

Root Harbor `LICENSE` remains the **Product Preview Tester License**. Mobile
component trees may carry their own notices (e.g. RODEO `THIRD-PARTY-NOTICES.md`,
Bottle Rocket `PHOTON/` / `pk/` notices). No separate LICENSE was found at the
iOS/Android LCTL package roots at integrate time — treat upstream packaging
terms as authoritative when redistributing those trees.

## Reproducible mobile VM node compiler

When a **mobile platform authenticates / enters Harbor**, compile a Bottle Rocket-based
VM application node and stage/deliver it toward that device:

```bat
scripts\on-mobile-auth.cmd --platform android --session <id> --device <id>
scripts\compile-mobile-vm-node.cmd --platform ios --dry-run
```

Full contract, reproducibility notes, and delivery limits:
[compiler/README.md](compiler/README.md).

## Closures (2026-09-25 PT)

- Build host control: `scripts\build-brctl.cmd` → `compiler/bin/brctl.exe`
- Device delivery: `scripts\deliver-mobile-vm-node.cmd` (`--wait-device`); evidence in `docs/verification/mobile-delivery/`
- SPIRAL auto-wire: gateway `mobile-auth-hook.js` on ticket mint; disable with `HARBOR_MOBILE_AUTH_HOOK=0`
- Measured notes: `docs/verification/MOBILE_PLATFORM_CLOSURE.md`
