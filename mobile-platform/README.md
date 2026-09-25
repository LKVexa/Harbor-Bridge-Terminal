# Mobile platform + cubbies (Bottle Rocket projection)

Harbor links a **mobile platform** whose rules are:

1. **Each mobile platform application node is a Bottle Rocket VM.**
2. **RODEO is a sidecar to Linear Android** (Gradle substitute) — not a peer application node.
3. **Enter Harbor via cubby + browser projection on local 127** — the device does **not** download the VM.
4. **Mobile access gate:** a live Bottle Rocket mobile cubby (`MC-*`) is required before the mobile session may attach to QVM or containership cubbies.

`BOTTLE_ROCKET_3.0.0_MODEL_OPERATIONAL_110K` is the shared **VM substrate**.
Application nodes: **iOS735_LCTL** (iOS) and **LinearAndroid_LCTL** (Android).
**RODEO** lives under the Android node as `sidecar-rodeo/`.

Desktop projects QVM/containership cubbies on local 127 directly (same cubby family).

Model: [`docs/MOBILE_CUBBY_PROJECTION.md`](../docs/MOBILE_CUBBY_PROJECTION.md)  
Registry: [`fleet/CUBBIES.json`](../fleet/CUBBIES.json) · [`fleet/MOBILE_PLATFORM.json`](../fleet/MOBILE_PLATFORM.json)

## Link / refresh

```bat
scripts\link-mobile-platform.cmd
```

`START_HARBOR.cmd` calls this after the optical-desktop link. Missing Desktop sources **warn**; Harbor start is not blocked.
