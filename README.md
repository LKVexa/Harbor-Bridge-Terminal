# Harbor Bridge Terminal

>Harbor Bridge Terminal: UC containership + HERMIT/SPIRAL bridge on local 127. 50+ cubbies (QVM Qnodes, DF/containership slots, mobile Bottle Rocket MC-*). Browser projects cubbies on 127.0.0.1 — no VM download. Mobile requires a live BR cubby before QVM/CS access. Product Preview Tester License (evaluation).

A combined workspace that puts **Unikernel Containership UC-2.8.0** (edge atoms) beside a **live virtual console** â€” the HERMIT / SPIRAL terminal with its RAM-resident virtual WebSocket bridge â€” plus a **50Ã— QVM Qnode fleet** (full independent copies), the **DF fabric** containers, **VB-JA21 Portable Optical Desktop 9.8.7** as the Harbor browser (omni-bin window), and a **mobile platform** whose application nodes are **Bottle Rocket VMs** (iOS735_LCTL + LinearAndroid_LCTL), with **RODEO** as the Linear Android Gradle-substitute **sidecar**, plus **mobile cubbies** (Bottle Rocket sessions projected on local 127; per-cubby `brctl serve` APDU REPL proxied into the projection page; cubby materializer; per-cubby brctl serve APDU proxy into projection; no VM download).

Think of the containership as the harbor yard and the virtual console as the bridge: one place to inspect the ship, run edge checks, talk to sessions over a bounded, ledgered websocket, and focus into individual Qnodes or DF containers. The local gateway URL opens inside JA21, **not** the system default browser.


## Technical note

**Full platform monograph v2.0** (architecture incl. mobile cubbies / Bottle Rocket projection / `brctl serve` APDU proxy, figures, verification / historical replay results):
[docs/Harbor-Bridge-Terminal-Technical-Note.md](docs/Harbor-Bridge-Terminal-Technical-Note.md)

Supporting artifacts:
- [docs/figures/](docs/figures/) — charts from the Qnode load audit JSON
- [docs/verification/](docs/verification/) — session probe outputs
- [docs/verification/spiral-landing/](docs/verification/spiral-landing/) — SPIRAL/landing HTTP + WS admission
- [docs/MOBILE_CUBBY_PROJECTION.md](docs/MOBILE_CUBBY_PROJECTION.md), [docs/verification/mobile-cubby/](docs/verification/mobile-cubby/), [docs/verification/brctl-serve-proxy/](docs/verification/brctl-serve-proxy/) — mobile cubby gate + serve proxy (**12/12** and **8/8** PASS cited in the note)
- [fleet/CUBBIES.json](fleet/CUBBIES.json), [fleet/MOBILE_PLATFORM.json](fleet/MOBILE_PLATFORM.json)
- [docs/reviews/](docs/reviews/) — attached independent expository reviews (PDFs):
  - [cubby-mobile-expository.pdf](docs/reviews/cubby-mobile-expository.pdf) — *Harbor Bridge Terminal Platform Technical Expository Note* (Cubby Mobile Edition, 2026-09-25)
  - [HBT-EXP-002.pdf](docs/reviews/HBT-EXP-002.pdf) — *Harbor Bridge Terminal / HBT-EXP-002* (platform-at-a-glance expository note)


Metrics in that note are taken only from repo files and commands that were actually run — no fabricated trading backtests.

## Windows checkout (MAX_PATH)

GitHub **ZIP downloads** and some deep clones can fail on Windows when relative paths approach the legacy **260**-character `MAX_PATH` limit (especially under `containership/edge/...`).

**Prefer:**

```bat
git clone https://github.com/LKVexa/Harbor-Bridge-Terminal.git
cd Harbor-Bridge-Terminal
git config core.longpaths true
```

Enabling long paths is a **secondary** mitigation. This repo also **shortens** the worst tracked paths (flattened duplicate atom/variant folders, shortened checklist names, dropped `build/` / `*.egg-info` artifacts from tracking). Measured after path hygiene: max relative path **144** characters (0 paths >=160). See docs/verification/path-length-after.txt.

Do **not** commit bulky junctions (`mobile-platform/**/product/`, `optical-desktop/portable/`, compiler `out/` / sessions).

## Layout

```
Harbor-Bridge-Terminal/
â”œâ”€â”€ containership/      Unikernel Containership UC-2.8.0 (edge atoms applied)
â”œâ”€â”€ bridge-terminal/    HERMIT virtual terminal + RAMWS virtual WebSocket gateway
â”œâ”€â”€ optical-desktop/    VB-JA21 9.8.7 portable (junction + PRODUCT_LINK)
â”‚   â”œâ”€â”€ PRODUCT_LINK.txt
â”‚   â”œâ”€â”€ VERSION
â”‚   â”œâ”€â”€ README.md
â”‚   â””â”€â”€ portable/       junction â†’ Downloads JA21-Portable-Desktop-9.8.7 (gitignored)
â”œâ”€â”€ mobile-platform/   Bottle Rocket VM + iOS/Android app nodes + compiler
â”‚   â”œâ”€â”€ bottle-rocket/  VM substrate (junction)
â”‚   â”œâ”€â”€ nodes/          ios-lctl, android-lctl (+ sidecar-rodeo)
â”‚   â””â”€â”€ compiler/       reproducible mobile VM node compiler + auth hook
â”œâ”€â”€ qvm/
â”‚   â”œâ”€â”€ PRODUCT_LINK.txt  absolute path to the QVM 8.1.0-alpha seed
â”‚   â””â”€â”€ product/          optional junction â†’ QVM seed (rematerialize only)
â”œâ”€â”€ qnodes/
â”‚   â”œâ”€â”€ FLEET.json        roster of QN-01 â€¦ QN-50 (mode: full-copies)
â”‚   â””â”€â”€ QN-01/ â€¦ QN-50/   FULL independent QVM trees + IDENTITY.json + QNODE.cmd
â”œâ”€â”€ fleet/
â”‚   â”œâ”€â”€ HARBOR_FLEET.json DF containers + Qnodes + focus codes
â”‚   â”œâ”€â”€ MOBILE_PLATFORM.json  Bottle Rocket VM + app nodes + compiler
â”‚   â””â”€â”€ QNODE_LOAD_AUDIT.md  latest load-carry audit (all 50)
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ link-qvm.cmd
â”‚   â”œâ”€â”€ link-optical-desktop.cmd
â”‚   â”œâ”€â”€ link-mobile-platform.cmd
â”‚   â”œâ”€â”€ compile-mobile-vm-node.cmd / on-mobile-auth.cmd / deliver-mobile-vm-node.cmd
â”‚   â”œâ”€â”€ materialize-qnode-copies.cmd
â”‚   â”œâ”€â”€ audit-qnode-load.cmd / .js
â”‚   â””â”€â”€ generate-qnodes.js
â”œâ”€â”€ START_HARBOR.cmd
â”œâ”€â”€ START_HARBOR_BROWSER.cmd   launch JA21 alone against a running gateway
â”œâ”€â”€ ACCESS_TOKEN.txt      LOCAL ONLY (gitignored) â€” paste into the sign-in box
â””â”€â”€ README.md
```

## Quick start

### Harbor (recommended)

```bat
START_HARBOR.cmd
```

1. Ensures QVM + **optical-desktop** + **mobile-platform** junctions exist (warns if mobile sources missing).
2. Starts the HERMIT gateway on `http://127.0.0.1:10000/` (or the next free port if busy â€” the console prints the URL).
3. When the gateway is listening, launches **VB-JA21 Portable Desktop** with that URL as `JA21_START_URL` / `-StartUrl` so the **omni-bin** navigates to Harbor.
4. Does **not** call `start http://...` or open Edge/Chrome.

On session open the landing banner shows the **Harbor fleet board**: DF containers (`ns` `nm` `nl` `nx` `nf`) and all 50 Qnodes (`qn01`â€¦`qn50`) with operability and focus codes.

First run (or after a fresh clone) will **materialize** 50 full QVM copies into `qnodes\QN-XX` if `QN-01\qvm\cli.py` is missing (~840 MB total). Bulk product trees are gitignored; only Harbor metadata + scripts are committed.

Flags (passed through to `start-local.js`):

| Flag | Effect |
|------|--------|
| `--no-browser` | Start gateway only; skip JA21 launch |
| `--no-fabric` | Do not bind DF_ROOT |
| `--port N` | Prefer loopback port N |
| `--reuse` | If N is already listening, skip starting a second gateway and only launch JA21 |

### Optical desktop only (gateway already up)

```bat
START_HARBOR_BROWSER.cmd
START_HARBOR_BROWSER.cmd http://127.0.0.1:10001/
```

Probes `10000`â€“`10019` when no URL is given. Same `JA21_START_URL` / `-StartUrl` contract.

### Access token (sign-in)

The sign-in box **inside JA21** needs the **operator access token**.

| Where | What |
|--------|------|
| **`ACCESS_TOKEN.txt`** (repo root on your machine) | Plaintext token for local loopback sign-in. **Gitignored â€” never committed.** |
| First-start console | Printed once when `bridge-terminal/.vws-local/principals.json` is created. |
| On disk after that | Only a SHA-256 of the token is kept in `principals.json` (not reversible). |

**How to use:** after `START_HARBOR.cmd` opens JA21 on the Harbor URL, paste the contents of `ACCESS_TOKEN.txt` into the sign-in box, then open the terminal.

**Lost the token?** Delete both of these, then run `START_HARBOR.cmd` again (a new token is printed and written to `ACCESS_TOKEN.txt`):

```bat
del bridge-terminal\.vws-local\principals.json
del ACCESS_TOKEN.txt
START_HARBOR.cmd
```

> This repository is **public**. The live token is **not** stored in this README or anywhere else on GitHub. Putting a loopback credential in a public file would let anyone who clones the repo impersonate the local operator session.

### Containership (Windows)

From `containership\` (keep the path short on Windows):

```bat
EDGE.cmd status
uc.py verify --quick --no-hull
EDGE.cmd check --deep
```

See `containership\README_START_HERE.md` for the full ship workflow.

### Bridge terminal only (Node 18+)

```bash
cd bridge-terminal
npm install
npm start          # desktop HERMIT
npm run gateway    # virtual WebSocket gateway (also via START_HARBOR.cmd)
npm test
```

## Optical desktop binding (VB-JA21 9.8.7)

- **Source (read-only):** Downloads `VB-JA21-VEC1-Portable-Optical-Desktop-9.8.7-WindowsSafe\JA21-Portable-Desktop-9.8.7`
- **Harbor path:** `optical-desktop\portable\` (junction). See `optical-desktop\PRODUCT_LINK.txt` and `scripts\link-optical-desktop.cmd`.
- **Start URL:** env `JA21_START_URL` and/or `host\Start-JA21Browser.ps1 -StartUrl â€¦` â€” presenter navigates the active tab on load.
- **Private / loopback hosts:** Harbor sets `JA21_ALLOW_PRIVATE_HOSTS=1` so `127.0.0.1` is allowed (JA21 denies private addresses by default).
- **Bulk tree (~800 MB)** is gitignored; clone + `link-optical-desktop.cmd` restores operability when the portable exists under Downloads (or update `PRODUCT_LINK.txt`).
- **Electron `vendor/browser`:** optional secondary slot for an in-process BrowserView adapter. Primary UX is the standalone WPF omni-bin window above.


## Mobile platform + cubbies (projection on local 127)

**Primary story:** when a mobile browser logs into Harbor, a **Bottle Rocket VM session** spins up as a **mobile cubby** (`MC-NNN`) on the Harbor gateway and is **projected** to the device browser on **local 127**. The device does **not** download the VM.

**Same family:** QVM Qnodes (`QN-01`â€¦`QN-50`) and Containership/DF slots (`CS-*`) are also **cubbies**. Desktop opens them on local 127 **directly**. Mobile must hold a **live BR mobile cubby** before attaching to QVM/containership cubbies (access gate `mobile_br_cubby_required`).

**Rules:** (1) each mobile **application node** is a **Bottle Rocket VM**; (2) **RODEO is a sidecar to Linear Android** (Gradle substitute), not a peer app node; (3) compiler = **cubby materializer** (`brctl assemble` image prep for the cubby â€” not phone storage).

| Piece | Harbor path | Role |
|-------|-------------|------|
| Bottle Rocket 3.0.0 MODEL OPERATIONAL 110K | `mobile-platform/bottle-rocket/` | Shared **VM substrate** / cubby image source |
| iOS735_LCTL v0.1.0 | `mobile-platform/nodes/ios-lctl/` | **iOS** app node = Bottle Rocket VM |
| LinearAndroid_LCTL v0.1.0 | `mobile-platform/nodes/android-lctl/` | **Android** app node = Bottle Rocket VM |
| RODEO 0.1.0 | `mobile-platform/nodes/android-lctl/sidecar-rodeo/` | **Sidecar** to Linear Android (Gradle substitute) |
| Cubby registry | `fleet/CUBBIES.json` | QN + CS + growing `MC-*` mobile cubbies |

**Link:** `scripts\link-mobile-platform.cmd` (also from `START_HARBOR.cmd`; missing sources warn).

**Mobile login â†’ cubby + projection:**

```bat
REM SPIRAL: POST /api/ws-ticket with header X-Harbor-Mobile-Platform: android|ios
REM Ticket body includes cubby_id + projection_url (device_download=false)
REM Open http://127.0.0.1:{port}/cubby/MC-001/projection
```

**Cubby materializer (optional image prep):**

```bat
scripts\build-brctl.cmd
scripts\on-mobile-auth.cmd --platform android --session <id> --cubby MC-001
scripts\compile-mobile-vm-node.cmd --platform ios --dry-run
```

**Optional sideload (demoted â€” not enter-Harbor):**

```bat
scripts\deliver-mobile-vm-node.cmd --manifest <COMPILE_MANIFEST.json> --platform android [--wait-device]
```

- Model + gate: [`docs/MOBILE_CUBBY_PROJECTION.md`](docs/MOBILE_CUBBY_PROJECTION.md)
- Fleet: [`fleet/CUBBIES.json`](fleet/CUBBIES.json), [`fleet/MOBILE_PLATFORM.json`](fleet/MOBILE_PLATFORM.json)
- Compiler contract: [`mobile-platform/compiler/README.md`](mobile-platform/compiler/README.md)
- **brctl:** `assemble` = cubby image prep; `serve` = advanced host-state hint. Harbor projection page is the browser path.
- **SPIRAL hook:** `bridge-terminal/gateway/mobile-auth-hook.js` (default ON). Disable: `set HARBOR_MOBILE_AUTH_HOOK=0`.
- **Access gate:** `bridge-terminal/gateway/cubby-access-gate.js` â€” mobile â†’ QN/CS without live `MC-*` â†’ **403** `mobile_br_cubby_required`.
- Honest scope: `MC-*` projection proxies `brctl serve` hex-APDU REPL (not a framebuffer); full BR host UI-in-browser remains a gap. Sideload never fakes success without real `adb`/`idevice`.

## Qnode fleet (50Ã— full QVM 8.1.0-alpha copies)

- **Full copies:** each `qnodes\QN-XX\` is a complete independent QVM product tree (`qvm/`, `examples/`, `PHOTON/`, `RUN_QVM.cmd`, `VERSION`, â€¦) plus Harbor `IDENTITY.json` and `QNODE.cmd`.
- **Seed (optional at runtime):** `qvm\PRODUCT_LINK.txt` + `scripts\link-qvm.cmd` create `qvm\product` for **rematerializing** copies only. Runtime does **not** depend on the junction.
- **Materialize:** `scripts\materialize-qnode-copies.cmd` (or `node scripts\materialize-qnode-copies.js`) robocopies the seed into QN-01â€¦QN-50.
- **Operable** means IDENTITY present **and** that copy has local `qvm\cli.py` + `VERSION`.
- **Launcher:** `QNODE.cmd info` sets `PYTHONPATH` to **that copy's root** and runs `py -3 -m qvm.cli` with cwd = the copy root.

### Focus codes (interactive terminal)

| Code | Target |
|------|--------|
| `qn01` â€¦ `qn50` | Qnode full copy â†’ QVM focus REPL |
| `ns` | DF_Small / N_SMALL |
| `nm` | DF_Medium / N_MEDIUM |
| `nl` | DF_Large / N_LARGE |
| `nx` | DF_Xtra_Large / N_XLARGE |
| `nf` | DF_Fabric |

Type a code alone to enter a focused interactive terminal for that target. Use `exit` to leave focus. Also: `qn status`, `qn where`, `qn attach qn07`.

### Load audit (all 50 can carry a load)

**Audited 2026-09-25 (America/Los_Angeles / PDT):** every Qnode `QN-01` â€¦ `QN-50` passed inventory, independence, fleet alignment, and a concrete load probe.

| Layer | What was checked | Result |
|-------|------------------|--------|
| Inventory | Key entrypoints (`qvm\cli.py`, `VERSION`, `IDENTITY.json`, `QNODE.cmd`, `examples\bell.json`); ~520 files / ~16.8 MB per copy; not junctions | **50 / 50** |
| Independence | Marker under `QN-01\runtime` does not appear under `QN-02\runtime` | **PASS** |
| Load probe | Per node: `qvm.cli info`, `qvm.cli selftest`, `qvm.cli run examples\bell.json` (statevector Bell, 1024 shots) | **50 / 50** |
| Fleet | `fleet\HARBOR_FLEET.json` focus codes `qn01`â€¦`qn50`, `qnode_mode=full-copies` | **PASS** |

Full per-node table (exit timings, sizes, notes): [`fleet/QNODE_LOAD_AUDIT.md`](fleet/QNODE_LOAD_AUDIT.md). Machine-readable twin: `fleet/QNODE_LOAD_AUDIT.json`.

Re-run after rematerializing or changing copies:

```bat
scripts\audit-qnode-load.cmd
```

Optional: `set QNODE_AUDIT_PARALLEL=5` (default) before running. If inventory fails, rematerialize with `scripts\materialize-qnode-copies.cmd` then audit again.


## What was combined

| Piece | Source |
|---|---|
| Containership UC-2.8.0 edge atoms | Desktop `Unikernel_Containership_v2.8.0_EdgeAtoms` applied onto UC-2.7.0 |
| Bridge / virtual WebSocket | Attached HERMIT RAMWS candidate (`hermit-spiral-terminal` 2.0.0-ramws.1) |
| Qnode fleet | 50 full copies of `QVM_Quantum_VM_v8.1.0-alpha` under `qnodes/` |
| DF fabric | Bound from Desktop `New folder` (`DF_Fabric` + node containers) |
| Optical desktop | VB-JA21 Portable Desktop 9.8.7 (junction from Downloads; start URL â†’ Harbor) |
| Mobile / cubbies | BR MC-* cubbies projected on local 127 with per-cubby brctl serve APDU proxy; QN+CS same cubby family; mobile BR gate before QVM/CS; adb sideload demoted |

Neither upstream QVM, DF archive, nor the Downloads JA21 portable was modified in place; this repo is the integrated working tree.

## External product links (QVM / JA21 / mobile)

Harbor does **not** bundle QVM, VB-JA21, Bottle Rocket, iOS735, LinearAndroid, or RODEO. Point at local trees with:

| Env var | PRODUCT_LINK key | Rematerialize |
|---------|------------------|---------------|
| `QVM_PRODUCT_ROOT` | `qvm/PRODUCT_LINK.txt` → `QVM_PRODUCT_ROOT` | `scripts\link-qvm.cmd` |
| `JA21_PORTABLE_ROOT` | `optical-desktop/PRODUCT_LINK.txt` → `JA21_PORTABLE_ROOT` | `scripts\link-optical-desktop.cmd` |
| `BOTTLE_ROCKET_PRODUCT_ROOT` | `mobile-platform/bottle-rocket/PRODUCT_LINK.txt` | `scripts\link-mobile-platform.cmd` |
| `IOS735_PRODUCT_ROOT` | `mobile-platform/nodes/ios-lctl/PRODUCT_LINK.txt` → `PRODUCT_ROOT` | same |
| `LINEAR_ANDROID_PRODUCT_ROOT` | `mobile-platform/nodes/android-lctl/PRODUCT_LINK.txt` → `PRODUCT_ROOT` | same |
| `RODEO_PRODUCT_ROOT` | `mobile-platform/nodes/android-lctl/sidecar-rodeo/PRODUCT_LINK.txt` → `PRODUCT_ROOT` | same |

Quick path for this workstation:

```bat
scripts\configure-product-links.cmd
scripts\link-qvm.cmd
scripts\link-optical-desktop.cmd
scripts\link-mobile-platform.cmd
```

See `*/PRODUCT_LINK.example` for commented absolute-path examples. Never commit `ACCESS_TOKEN.txt` or junction payloads under `qvm/product/`, `optical-desktop/portable/`, or `mobile-platform/**/product/`.

## License
**Harbor Bridge Terminal** is distributed under the **Product Preview Tester License**
(see root `LICENSE`): evaluation and tester use only â€” not a production grant,
not an OSI open-source license.

Component notices still apply to their own trees:

- `containership\LICENSE`
- `bridge-terminal\LICENSE`
- `optical-desktop\portable\LICENSE` / `LICENSING.md` (when linked)