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
5. Run `brctl assemble` when `compiler/bin/brctl.exe` or `product/.build/brctl` exists (build via `scripts\build-brctl.cmd`); otherwise skip honestly.
6. Write `COMPILE_MANIFEST.json` (see `schema/compile-manifest.schema.json`).
7. Optional `--deliver`: `adb push` on Android if `adb` + device present; `--wait-device` polls; else stage + print next command. iOS always stages.

**Output:** `NODE_IDENTITY.json`, substrate/app pins, optional `payload/boot.brimg`, `node-bundle.harbundle` (deterministic `HARBOR_BUNDLE_V1`), manifest.

## Commands

```bat
REM from Harbor root (after scripts\link-mobile-platform.cmd)
scripts\build-brctl.cmd
scripts\compile-mobile-vm-node.cmd --platform android --dry-run
scripts\compile-mobile-vm-node.cmd --platform ios --dry-run

REM auth / enter-Harbor hook (manual)
scripts\on-mobile-auth.cmd --platform android --session sess-1 --device emulator-5554
scripts\on-mobile-auth.cmd --platform ios --session sess-2

REM deliver (adb if present; optional wait)
scripts\deliver-mobile-vm-node.cmd --manifest mobile-platform\compiler\out\nodes\android-XXXXXXXXXXXX\COMPILE_MANIFEST.json --platform android
scripts\deliver-mobile-vm-node.cmd --manifest ... --platform android --wait-device --wait-timeout 120
```

## SPIRAL login → mobile-auth (auto-wire)

Successful gateway ticket mint (`POST /api/ws-ticket` after Bearer/principal auth) invokes
`bridge-terminal/gateway/mobile-auth-hook.js`, which writes a job into
`compiler/auth-queue/` (no secrets). `tools/start-local.js` / `START_HARBOR.cmd`
enable the hook by default and start `hooks/watch-auth-queue.js`.

| Env | Effect |
|---|---|
| `HARBOR_MOBILE_AUTH_HOOK=0` | Disable hook + queue watcher |
| `HARBOR_MOBILE_AUTH_HOOK_MODE=queue` | Default: enqueue only |
| `HARBOR_MOBILE_AUTH_HOOK_MODE=compile` | Also spawn `on-mobile-auth.js` |
| `HARBOR_MOBILE_AUTH_DEFAULT_PLATFORM` | `android` (default) or `ios` when UA/header absent |
| `HARBOR_MOBILE_AUTH_DELIVER=1` | Pass `--deliver` when compile mode runs |

Platform hints: header `X-Harbor-Mobile-Platform`, query `mobile_platform`/`platform`, else User-Agent, else default.

Evidence: `docs/verification/mobile-auth-hook/LATEST.json` and `HOOK_FIRE.log`.

Manual queue (same as before):

```bat
node mobile-platform\compiler\hooks\watch-auth-queue.js
```

```json
{ "platform": "android", "session_id": "enter-1", "device_id": "emulator-5554", "deliver": false }
```

## Reproducibility

Same linked product pins → same `content_hash` → same output directory name.
`bundle_sha256` changes when `brctl assemble` adds `payload/boot.brimg` (expected).

## Honest limits

- Does **not** flash phones or claim App Store / Play installs.
- Without a built `brctl`, native BRIM assemble is skipped (package still valid as Harbor node artifact).
- Without `adb` / online device / iOS tooling, delivery stays **staged** with `next_command` (never fake success).
- MinGW `brctl selftest` may FAIL some host cases; `assemble` is the compile contract and was verified PASS on this machine.

## Proven locally (2026-09-25 PT)

See `docs/verification/mobile-delivery/` and `docs/verification/mobile-auth-hook/` for measured
probes from this closure (device presence, brctl assemble, SPIRAL ticket hook).
