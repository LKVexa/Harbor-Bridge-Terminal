# Mobile VM node compiler (reproducible)

Compiles a **Bottle Rocket VM application node** package for a mobile platform
that is **authenticating / entering Harbor**, then stages (and optionally
delivers) the artifact toward that device.

## Architecture

| Piece | Role |
|---|---|
| Bottle Rocket 3.0.0 110K | VM substrate |
| iOS735_LCTL | iOS **application node** = Bottle Rocket VM |
| LinearAndroid_LCTL | Android **application node** = Bottle Rocket VM |
| RODEO | **Sidecar** to Linear Android (Gradle substitute) — not a peer app node |

## Contract

**Input:** `--platform android|ios`, optional `--session`, `--device`, `--principal` (never a token/secret), pinned `PRODUCT_LINK` / `VERSION` / `IDENTITY` (+ LCTL unit hashes, RODEO bootstrap pin on Android).

**Process:**
1. Resolve junctions (or absolute PRODUCT_LINK roots).
2. Hash pinned inputs → `content_hash`.
3. Emit content-addressed package under `compiler/out/nodes/{platform}-{hash12}/`.
4. Android: run `rodeo doctor` when RODEO is linked (non-fatal if it fails).
5. Attempt `brctl` assemble only if `.build/brctl` exists; otherwise skip honestly.
6. Write `COMPILE_MANIFEST.json` (see `schema/compile-manifest.schema.json`).
7. Optional `--deliver`: `adb push` on Android if `adb` exists; else stage + print next command. iOS always stages.

**Output:** `NODE_IDENTITY.json`, substrate/app pins, `node-bundle.harbundle` (deterministic `HARBOR_BUNDLE_V1`), manifest.

## Commands

```bat
REM from Harbor root (after scripts\link-mobile-platform.cmd)
scripts\compile-mobile-vm-node.cmd --platform android --dry-run
scripts\compile-mobile-vm-node.cmd --platform ios --dry-run

REM auth / enter-Harbor hook
scripts\on-mobile-auth.cmd --platform android --session sess-1 --device emulator-5554
scripts\on-mobile-auth.cmd --platform ios --session sess-2

REM deliver (adb if present)
scripts\deliver-mobile-vm-node.cmd --manifest mobile-platform\compiler\out\nodes\android-XXXXXXXXXXXX\COMPILE_MANIFEST.json --platform android
```

## Auth / enter-Harbor integration point

Ordinary operator `ACCESS_TOKEN` sign-in does **not** auto-compile mobile nodes
(that would confuse bridge login with device entry).

When a **mobile platform authenticates into Harbor**, call:

```bat
scripts\on-mobile-auth.cmd --platform android|ios --session <id> --device <id>
```

Optional queue watcher (drop JSON into `compiler/auth-queue/`):

```bat
node mobile-platform\compiler\hooks\watch-auth-queue.js
```

Example queue file:

```json
{ "platform": "android", "session_id": "enter-1", "device_id": "emulator-5554", "deliver": false }
```

Set `HARBOR_MOBILE_AUTH_DELIVER=1` to push after compile when adb is available.

## Reproducibility

Same linked product pins → same `content_hash` → same output directory name and
`bundle_sha256`. Prove with two dry-runs:

```bat
scripts\compile-mobile-vm-node.cmd --platform android --dry-run
scripts\compile-mobile-vm-node.cmd --platform android --dry-run
```

Compare `bundle_sha256` in the two `LATEST_android.json` / manifest files.

## Honest limits

- Does **not** flash phones or claim App Store / Play installs.
- Without a built `brctl`, native BRIM assemble is skipped (package still valid as Harbor node artifact).
- Without `adb` / iOS tooling, delivery stays **staged** with `next_command`.

## Proven locally (2026-09-25 PT)

Two android `--dry-run` compiles produced identical:

- `content_hash` = `ac68a899fc80f88b177b7a7e2964829b97e4c4754cb4e51edda2585ac91c4cee`
- `bundle_sha256` = `cc49c8d2be9d66212dedf8c57f6e38cde4490f79d3f2299e108a246542672e19`

`deliver` without `adb` exited staged with an explicit `adb push` next_command (no fake install).

Session/device fields live in `AUTH_CONTEXT.json` / `COMPILE_MANIFEST.json` only (not inside the harbundle), so auth-triggered compiles with the same product pins keep the same `bundle_sha256`.
