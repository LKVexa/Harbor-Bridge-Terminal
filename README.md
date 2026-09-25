# Harbor Bridge Terminal

A combined workspace that puts **Unikernel Containership UC-2.8.0** (edge atoms) beside a **live virtual console** — the HERMIT / SPIRAL terminal with its RAM-resident virtual WebSocket bridge — plus a **50× QVM Qnode fleet** (full independent copies), the **DF fabric** containers, **VB-JA21 Portable Optical Desktop 9.8.7** as the Harbor browser (omni-bin window), and a **mobile platform** whose application nodes are **Bottle Rocket VMs** (iOS735_LCTL + LinearAndroid_LCTL), with **RODEO** as the Linear Android Gradle-substitute **sidecar**, plus **mobile cubbies** (Bottle Rocket sessions projected on local 127; cubby materializer; no VM download).

Think of the containership as the harbor yard and the virtual console as the bridge: one place to inspect the ship, run edge checks, talk to sessions over a bounded, ledgered websocket, and focus into individual Qnodes or DF containers. The local gateway URL opens inside JA21, **not** the system default browser.


## Technical note

**Full platform monograph (architecture, figures, verification / historical replay results):**
[docs/Harbor-Bridge-Terminal-Technical-Note.md](docs/Harbor-Bridge-Terminal-Technical-Note.md)

Supporting artifacts: [docs/figures/](docs/figures/) (charts from the Qnode load audit JSON), [docs/verification/](docs/verification/) (session probe outputs), and [docs/verification/spiral-landing/](docs/verification/spiral-landing/) (live SPIRAL/landing HTTP + WS admission probes). Metrics in that note are taken only from repo files and commands that were actually run — no fabricated trading backtests.

## Layout

```
Harbor-Bridge-Terminal/
├── containership/      Unikernel Containership UC-2.8.0 (edge atoms applied)
├── bridge-terminal/    HERMIT virtual terminal + RAMWS virtual WebSocket gateway
├── optical-desktop/    VB-JA21 9.8.7 portable (junction + PRODUCT_LINK)
│   ├── PRODUCT_LINK.txt
│   ├── VERSION
│   ├── README.md
│   └── portable/       junction → Downloads JA21-Portable-Desktop-9.8.7 (gitignored)
├── mobile-platform/   Bottle Rocket VM + iOS/Android app nodes + compiler
│   ├── bottle-rocket/  VM substrate (junction)
│   ├── nodes/          ios-lctl, android-lctl (+ sidecar-rodeo)
│   └── compiler/       reproducible mobile VM node compiler + auth hook
├── qvm/
│   ├── PRODUCT_LINK.txt  absolute path to the QVM 8.1.0-alpha seed
│   └── product/          optional junction → QVM seed (rematerialize only)
├── qnodes/
│   ├── FLEET.json        roster of QN-01 … QN-50 (mode: full-copies)
│   └── QN-01/ … QN-50/   FULL independent QVM trees + IDENTITY.json + QNODE.cmd
├── fleet/
│   ├── HARBOR_FLEET.json DF containers + Qnodes + focus codes
│   ├── MOBILE_PLATFORM.json  Bottle Rocket VM + app nodes + compiler
│   └── QNODE_LOAD_AUDIT.md  latest load-carry audit (all 50)
├── scripts/
│   ├── link-qvm.cmd
│   ├── link-optical-desktop.cmd
│   ├── link-mobile-platform.cmd
│   ├── compile-mobile-vm-node.cmd / on-mobile-auth.cmd / deliver-mobile-vm-node.cmd
│   ├── materialize-qnode-copies.cmd
│   ├── audit-qnode-load.cmd / .js
│   └── generate-qnodes.js
├── START_HARBOR.cmd
├── START_HARBOR_BROWSER.cmd   launch JA21 alone against a running gateway
├── ACCESS_TOKEN.txt      LOCAL ONLY (gitignored) — paste into the sign-in box
└── README.md
```

## Quick start

### Harbor (recommended)

```bat
START_HARBOR.cmd
```

1. Ensures QVM + **optical-desktop** + **mobile-platform** junctions exist (warns if mobile sources missing).
2. Starts the HERMIT gateway on `http://127.0.0.1:10000/` (or the next free port if busy — the console prints the URL).
3. When the gateway is listening, launches **VB-JA21 Portable Desktop** with that URL as `JA21_START_URL` / `-StartUrl` so the **omni-bin** navigates to Harbor.
4. Does **not** call `start http://...` or open Edge/Chrome.

On session open the landing banner shows the **Harbor fleet board**: DF containers (`ns` `nm` `nl` `nx` `nf`) and all 50 Qnodes (`qn01`…`qn50`) with operability and focus codes.

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

Probes `10000`–`10019` when no URL is given. Same `JA21_START_URL` / `-StartUrl` contract.

### Access token (sign-in)

The sign-in box **inside JA21** needs the **operator access token**.

| Where | What |
|--------|------|
| **`ACCESS_TOKEN.txt`** (repo root on your machine) | Plaintext token for local loopback sign-in. **Gitignored — never committed.** |
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
- **Start URL:** env `JA21_START_URL` and/or `host\Start-JA21Browser.ps1 -StartUrl …` — presenter navigates the active tab on load.
- **Private / loopback hosts:** Harbor sets `JA21_ALLOW_PRIVATE_HOSTS=1` so `127.0.0.1` is allowed (JA21 denies private addresses by default).
- **Bulk tree (~800 MB)** is gitignored; clone + `link-optical-desktop.cmd` restores operability when the portable exists under Downloads (or update `PRODUCT_LINK.txt`).
- **Electron `vendor/browser`:** optional secondary slot for an in-process BrowserView adapter. Primary UX is the standalone WPF omni-bin window above.


## Mobile platform + cubbies (projection on local 127)

**Primary story:** when a mobile browser logs into Harbor, a **Bottle Rocket VM session** spins up as a **mobile cubby** (`MC-NNN`) on the Harbor gateway and is **projected** to the device browser on **local 127**. The device does **not** download the VM.

**Same family:** QVM Qnodes (`QN-01`…`QN-50`) and Containership/DF slots (`CS-*`) are also **cubbies**. Desktop opens them on local 127 **directly**. Mobile must hold a **live BR mobile cubby** before attaching to QVM/containership cubbies (access gate `mobile_br_cubby_required`).

**Rules:** (1) each mobile **application node** is a **Bottle Rocket VM**; (2) **RODEO is a sidecar to Linear Android** (Gradle substitute), not a peer app node; (3) compiler = **cubby materializer** (`brctl assemble` image prep for the cubby — not phone storage).

| Piece | Harbor path | Role |
|-------|-------------|------|
| Bottle Rocket 3.0.0 MODEL OPERATIONAL 110K | `mobile-platform/bottle-rocket/` | Shared **VM substrate** / cubby image source |
| iOS735_LCTL v0.1.0 | `mobile-platform/nodes/ios-lctl/` | **iOS** app node = Bottle Rocket VM |
| LinearAndroid_LCTL v0.1.0 | `mobile-platform/nodes/android-lctl/` | **Android** app node = Bottle Rocket VM |
| RODEO 0.1.0 | `mobile-platform/nodes/android-lctl/sidecar-rodeo/` | **Sidecar** to Linear Android (Gradle substitute) |
| Cubby registry | `fleet/CUBBIES.json` | QN + CS + growing `MC-*` mobile cubbies |

**Link:** `scripts\link-mobile-platform.cmd` (also from `START_HARBOR.cmd`; missing sources warn).

**Mobile login → cubby + projection:**

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

**Optional sideload (demoted — not enter-Harbor):**

```bat
scripts\deliver-mobile-vm-node.cmd --manifest <COMPILE_MANIFEST.json> --platform android [--wait-device]
```

- Model + gate: [`docs/MOBILE_CUBBY_PROJECTION.md`](docs/MOBILE_CUBBY_PROJECTION.md)
- Fleet: [`fleet/CUBBIES.json`](fleet/CUBBIES.json), [`fleet/MOBILE_PLATFORM.json`](fleet/MOBILE_PLATFORM.json)
- Compiler contract: [`mobile-platform/compiler/README.md`](mobile-platform/compiler/README.md)
- **brctl:** `assemble` = cubby image prep; `serve` = advanced host-state hint. Harbor projection page is the browser path.
- **SPIRAL hook:** `bridge-terminal/gateway/mobile-auth-hook.js` (default ON). Disable: `set HARBOR_MOBILE_AUTH_HOOK=0`.
- **Access gate:** `bridge-terminal/gateway/cubby-access-gate.js` — mobile → QN/CS without live `MC-*` → **403** `mobile_br_cubby_required`.
- Honest scope: projection stub proves cubby + session; full BR UI-in-browser is optional/gap. Sideload never fakes success without real `adb`/`idevice`.

## Qnode fleet (50× full QVM 8.1.0-alpha copies)

- **Full copies:** each `qnodes\QN-XX\` is a complete independent QVM product tree (`qvm/`, `examples/`, `PHOTON/`, `RUN_QVM.cmd`, `VERSION`, …) plus Harbor `IDENTITY.json` and `QNODE.cmd`.
- **Seed (optional at runtime):** `qvm\PRODUCT_LINK.txt` + `scripts\link-qvm.cmd` create `qvm\product` for **rematerializing** copies only. Runtime does **not** depend on the junction.
- **Materialize:** `scripts\materialize-qnode-copies.cmd` (or `node scripts\materialize-qnode-copies.js`) robocopies the seed into QN-01…QN-50.
- **Operable** means IDENTITY present **and** that copy has local `qvm\cli.py` + `VERSION`.
- **Launcher:** `QNODE.cmd info` sets `PYTHONPATH` to **that copy's root** and runs `py -3 -m qvm.cli` with cwd = the copy root.

### Focus codes (interactive terminal)

| Code | Target |
|------|--------|
| `qn01` … `qn50` | Qnode full copy → QVM focus REPL |
| `ns` | DF_Small / N_SMALL |
| `nm` | DF_Medium / N_MEDIUM |
| `nl` | DF_Large / N_LARGE |
| `nx` | DF_Xtra_Large / N_XLARGE |
| `nf` | DF_Fabric |

Type a code alone to enter a focused interactive terminal for that target. Use `exit` to leave focus. Also: `qn status`, `qn where`, `qn attach qn07`.

### Load audit (all 50 can carry a load)

**Audited 2026-09-25 (America/Los_Angeles / PDT):** every Qnode `QN-01` … `QN-50` passed inventory, independence, fleet alignment, and a concrete load probe.

| Layer | What was checked | Result |
|-------|------------------|--------|
| Inventory | Key entrypoints (`qvm\cli.py`, `VERSION`, `IDENTITY.json`, `QNODE.cmd`, `examples\bell.json`); ~520 files / ~16.8 MB per copy; not junctions | **50 / 50** |
| Independence | Marker under `QN-01\runtime` does not appear under `QN-02\runtime` | **PASS** |
| Load probe | Per node: `qvm.cli info`, `qvm.cli selftest`, `qvm.cli run examples\bell.json` (statevector Bell, 1024 shots) | **50 / 50** |
| Fleet | `fleet\HARBOR_FLEET.json` focus codes `qn01`…`qn50`, `qnode_mode=full-copies` | **PASS** |

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
| Optical desktop | VB-JA21 Portable Desktop 9.8.7 (junction from Downloads; start URL → Harbor) |
| Mobile / cubbies | BR 110K mobile cubbies projected on local 127; QN+CS same cubby family; mobile BR gate before QVM/CS; adb sideload demoted |

Neither upstream QVM, DF archive, nor the Downloads JA21 portable was modified in place; this repo is the integrated working tree.

## License

**Harbor Bridge Terminal** is distributed under the **Product Preview Tester License**
(see root `LICENSE`): evaluation and tester use only — not a production grant,
not an OSI open-source license.

Component notices still apply to their own trees:

- `containership\LICENSE`
- `bridge-terminal\LICENSE`
- `optical-desktop\portable\LICENSE` / `LICENSING.md` (when linked)