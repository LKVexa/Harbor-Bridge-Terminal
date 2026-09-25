# Cubby materializer (reproducible Bottle Rocket image prep)

Prepares a **Bottle Rocket VM image for a Harbor cubby**. This is **not** “download VM to phone storage.”

**Primary enter-Harbor path:** mobile browser login → allocate `MC-*` cubby → **project** to local 127.  
Optional `--deliver` / `adb` is **sideload only** (demoted).

See [`docs/MOBILE_CUBBY_PROJECTION.md`](../../docs/MOBILE_CUBBY_PROJECTION.md).

## Architecture

| Piece | Role |
|---|---|
| Bottle Rocket 3.0.0 110K | VM substrate / cubby image source |
| iOS735_LCTL | iOS application node = Bottle Rocket VM |
| LinearAndroid_LCTL | Android application node = Bottle Rocket VM |
| RODEO | Sidecar to Linear Android (Gradle substitute) |
| `fleet/CUBBIES.json` | QN + CS + mobile cubby registry |

## Contract

**Input:** `--platform android|ios`, optional `--session`, `--cubby MC-NNN`, `--device`, `--principal` (never a token/secret).

**Process:**
1. Resolve junctions (or absolute PRODUCT_LINK roots).
2. Hash pinned inputs → `content_hash`.
3. Emit content-addressed package under `compiler/out/nodes/{platform}-{hash12}/`.
4. Android: run `rodeo doctor` when RODEO is linked (non-fatal if it fails).
5. Run `brctl assemble` when brctl exists (cubby image prep).
6. Write `COMPILE_MANIFEST.json`.
7. Optional `--deliver`: **sideload only** — `adb push` if present; else stage. iOS stages.

## SPIRAL login → cubby + projection

Successful `POST /api/ws-ticket` → `mobile-auth-hook.js` → allocate `MC-*` + projection URL on ticket body. Auth-queue may run this materializer. Desktop projects QN/CS on 127 directly; mobile needs live `MC-*` before QN/CS (access gate).

| Env | Effect |
|---|---|
| `HARBOR_MOBILE_AUTH_HOOK=0` | Disable hook + queue watcher |
| `HARBOR_MOBILE_AUTH_HOOK_MODE=queue` | Default: enqueue only |
| `HARBOR_MOBILE_AUTH_HOOK_MODE=compile` | Also spawn materializer |
| `HARBOR_MOBILE_AUTH_DEFAULT_PLATFORM` | `android` (default) or `ios` |
| `HARBOR_MOBILE_AUTH_DELIVER=1` | Optional sideload only |

## Honest limits

- Does **not** flash phones or claim store installs.
- Without `brctl`, assemble is skipped (package still valid as Harbor artifact).
- Without `adb`/device, sideload stays **staged**.
- Full BR UI in the browser projection page is optional/gap; stub proves cubby contract.
