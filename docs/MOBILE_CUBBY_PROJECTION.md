# Mobile cubby projection (local 127)

**Primary enter-Harbor path:** cubby spawn + browser projection on `127.0.0.1`.  
**Not** a VM download to phone storage. Optional `adb` sideload is advanced-only.

## Vocabulary

| Term | Meaning |
|------|---------|
| **Cubby** | Harbor execution slot. QVM Qnodes (`QN-01`…`QN-50`), containership/DF slots (`CS-NS`…), and mobile Bottle Rocket sessions (`MC-001`…) are all cubbies. |
| **Mobile cubby** | Bottle Rocket VM session allocated on mobile browser SPIRAL login. VM runs in the cubby on the Harbor gateway; the device browser gets a **projected** view on local 127. |
| **Cubby materializer** | Reproducible compiler (`brctl assemble` + pins). Prepares the VM **image for the cubby** — does not mean download to phone storage. |
| **Projection** | `http://127.0.0.1:{port}/cubby/{id}/projection` (HTML session page; for `MC-*`, proxies live `brctl serve` hex-APDU REPL). |
| **Sideload** | Optional `adb`/`idevice` push — **demoted**; not the enter-Harbor path. |

Registry: [`fleet/CUBBIES.json`](../fleet/CUBBIES.json) (grows past 50 when mobile logins create `MC-*` nodes).

## Entry paths

### Desktop (local 127)

Service requests from desktop open **QVM** and **containership** cubbies directly via Harbor local 127 projection. **No** Bottle Rocket mobile cubby is required.

```
GET http://127.0.0.1:{port}/cubby/QN-01/projection
GET http://127.0.0.1:{port}/cubby/CS-NF/projection
```

### Mobile (browser setting)

1. Mobile device logs into Harbor (SPIRAL / `POST /api/ws-ticket` with `X-Harbor-Mobile-Platform: android|ios`).
2. Gateway allocates a new **mobile BR cubby** (`MC-001`, …), binds a Bottle Rocket session in that cubby, returns `cubby_id` + `projection_url` on the ticket body.
3. Browser opens/embeds the projection URL on local 127 — **VM stays in the cubby; nothing is downloaded to device storage**.
4. **Access gate:** only after the BR mobile cubby is **live** may the mobile session attach to / request **QVM** or **containership** cubbies (proxied via the BR cubby). Creating those from mobile also requires the gate.

```
# Prerequisite (automatic on mobile ws-ticket)
→ MC-001 live + /cubby/MC-001/projection

# Then allowed
GET /api/cubbies/QN-07/attach   (X-Harbor-Mobile-Platform still set)
GET /cubby/QN-07/projection

# Without live MC-* → 403 mobile_br_cubby_required
```

Gate module: `bridge-terminal/gateway/cubby-access-gate.js`  
Routes: `/api/cubbies/:id/attach`, `/api/cubbies/access-check?target=`, `/cubby/:id/projection`.

## SPIRAL / gateway sequence (mobile login)

1. `POST /api/ws-ticket` succeeds (principal + ticket mint).
2. `mobile-auth-hook.js` allocates `MC-NNN` in `fleet/CUBBIES.json`, writes session under `mobile-platform/compiler/cubbies/sessions/`.
3. Ticket JSON may include `cubby_id`, `projection_url`, `device_download: false`, `primary: "cubby-projection"`.
4. Auth-queue job recorded (materializer may run `brctl assemble` for cubby image prep).
5. Optional `HARBOR_MOBILE_AUTH_DELIVER=1` only enables demoted sideload.

## Compiler role

Rebranded as **cubby materializer**. `brctl assemble` prepares the BRIM for the cubby. Keep `scripts\build-brctl.cmd` / `brctl assemble`. `brctl serve` is launched per mobile cubby and proxied into the projection page (APDU REPL; not a framebuffer).

## Operability on landing / fleet board

Mobile cubbies appear in `fleet/CUBBIES.json` → `mobile_cubbies[]` with `status: "live"` and `operable: true` when the projection session file exists. API: `GET /api/cubbies`.

## `brctl serve` proxy (real REPL, not a stub)

`brctl serve --state <prefix>` is a **stdio hex-APDU REPL** (banner: `READY hex-APDU per line; EOF stops`). It is **not** an HTTP server and does **not** expose a framebuffer.

Harbor therefore:

1. Launches **one `brctl serve` per mobile cubby** (`MC-*`) via `bridge-terminal/gateway/brctl-serve-manager.js`
   - Args: `serve --state mobile-platform/compiler/cubbies/serve-states/<MC-id>/br`
   - Bound to process stdio (localhost-only by construction; no listen port from brctl itself)
2. Tracks `pid` + state prefix in the cubby session registry; **reaps** on session end / gateway shutdown (`stopAll`)
3. Proxies APDUs into the browser projection page:
   - `GET  /cubby/:id/serve/status` — process readiness / pid / state
   - `POST /cubby/:id/serve/apdu` — body `{ "hex": "..." }` → one APDU request/response
   - `WS   /cubby/:id/serve/ws` — optional streaming of READY/responses
4. Projection HTML for `MC-*` embeds an interactive APDU console (HELLO / STATUS / CAPS presets)

QN/CS projection remains Harbor fabric HTML; live serve proxy is attached to **mobile BR cubbies**. Mobile BR gate for QN/CS is unchanged. `device_download: false` remains.

## Honest gaps

- ~~Projection page is a contract stub~~ **Superseded:** projection now proxies `brctl serve` APDU REPL for MC-* proving cubby id + session + “projected, not downloaded.” Full Bottle Rocket host UI embedded in the browser is not claimed complete in this pass.
- `brctl serve` is a stdio hex-APDU REPL (not a framebuffer); Harbor now launches + proxies it per MC cubby.
- Physical `adb` push remains optional and was already staged-only when `adb`/device absent.

## Verification

See `docs/verification/mobile-cubby/` and `docs/verification/brctl-serve-proxy/`.
