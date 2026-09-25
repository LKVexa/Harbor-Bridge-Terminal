# Harbor Bridge Terminal

A combined workspace that puts **Unikernel Containership UC-2.8.0** (edge atoms) beside a **live virtual console** — the HERMIT / SPIRAL terminal with its RAM-resident virtual WebSocket bridge — plus a **50× QVM Qnode fleet** (full independent copies), the **DF fabric** containers, and **VB-JA21 Portable Optical Desktop 9.8.7** as the Harbor browser (omni-bin window).

Think of the containership as the harbor yard and the virtual console as the bridge: one place to inspect the ship, run edge checks, talk to sessions over a bounded, ledgered websocket, and focus into individual Qnodes or DF containers. The local gateway URL opens inside JA21, **not** the system default browser.

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
├── qvm/
│   ├── PRODUCT_LINK.txt  absolute path to the QVM 8.1.0-alpha seed
│   └── product/          optional junction → QVM seed (rematerialize only)
├── qnodes/
│   ├── FLEET.json        roster of QN-01 … QN-50 (mode: full-copies)
│   └── QN-01/ … QN-50/   FULL independent QVM trees + IDENTITY.json + QNODE.cmd
├── fleet/
│   └── HARBOR_FLEET.json DF containers + Qnodes + focus codes
├── scripts/
│   ├── link-qvm.cmd
│   ├── link-optical-desktop.cmd
│   ├── materialize-qnode-copies.cmd
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

1. Ensures QVM + **optical-desktop** junctions exist.
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
- **Bulk tree (~800 MB)** is gitignored; clone + `link-optical-desktop.cmd` restores operability when the portable exists under Downloads (or update `PRODUCT_LINK.txt`).
- **Electron `vendor/browser`:** optional secondary slot for an in-process BrowserView adapter. Primary UX is the standalone WPF omni-bin window above.

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

## What was combined

| Piece | Source |
|---|---|
| Containership UC-2.8.0 edge atoms | Desktop `Unikernel_Containership_v2.8.0_EdgeAtoms` applied onto UC-2.7.0 |
| Bridge / virtual WebSocket | Attached HERMIT RAMWS candidate (`hermit-spiral-terminal` 2.0.0-ramws.1) |
| Qnode fleet | 50 full copies of `QVM_Quantum_VM_v8.1.0-alpha` under `qnodes/` |
| DF fabric | Bound from Desktop `New folder` (`DF_Fabric` + node containers) |
| Optical desktop | VB-JA21 Portable Desktop 9.8.7 (junction from Downloads; start URL → Harbor) |

Neither upstream QVM, DF archive, nor the Downloads JA21 portable was modified in place; this repo is the integrated working tree.

## License

See `containership\LICENSE` and `bridge-terminal\LICENSE` for the respective components. JA21 licensing lives under `optical-desktop\portable\` (when linked).