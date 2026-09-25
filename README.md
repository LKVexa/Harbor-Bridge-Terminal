# Harbor Bridge Terminal

A combined workspace that puts **Unikernel Containership UC-2.8.0** (edge atoms) beside a **live virtual console** — the HERMIT / SPIRAL terminal with its RAM-resident virtual WebSocket bridge — plus a **50× QVM Qnode fleet** (full independent copies) and the **DF fabric** containers.

Think of the containership as the harbor yard and the virtual console as the bridge: one place to inspect the ship, run edge checks, talk to sessions over a bounded, ledgered websocket, and focus into individual Qnodes or DF containers.

## Layout

```
Harbor-Bridge-Terminal/
├─ containership/      Unikernel Containership UC-2.8.0 (edge atoms applied)
├─ bridge-terminal/    HERMIT virtual terminal + RAMWS virtual WebSocket gateway
├─ qvm/
│  ├─ PRODUCT_LINK.txt absolute path to the QVM 8.1.0-alpha seed (source of truth)
│  └─ product/         optional directory junction → QVM seed (for rematerialize only)
├─ qnodes/
│  ├─ FLEET.json       roster of QN-01 … QN-50 (mode: full-copies)
│  └─ QN-01/ … QN-50/  FULL independent QVM trees + IDENTITY.json + QNODE.cmd
├─ fleet/
│  └─ HARBOR_FLEET.json  DF containers + Qnodes + focus codes
├─ scripts/
│  ├─ link-qvm.cmd                  create/refresh the optional qvm\product seed junction
│  ├─ materialize-qnode-copies.cmd  robocopy 50 full copies from the seed
│  └─ generate-qnodes.js            delegates to materialize (thin instances obsolete)
├─ START_HARBOR.cmd      bind DF_ROOT + QNODE_ROOT, materialize if needed, start gateway
└─ README.md
```

## Quick start

### Harbor (recommended)

```bat
START_HARBOR.cmd
```

Opens `http://127.0.0.1:10000/`. On session open the landing banner shows the **Harbor fleet board**: DF containers (`ns` `nm` `nl` `nx` `nf`) and all 50 Qnodes (`qn01`…`qn50`) with operability and focus codes.

First run (or after a fresh clone) will **materialize** 50 full QVM copies into `qnodes\QN-XX` if `QN-01\qvm\cli.py` is missing (~840 MB total). Bulk product trees are gitignored; only Harbor metadata + scripts are committed.

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

## Qnode fleet (50 × full QVM 8.1.0-alpha copies)

- **Full copies:** each `qnodes\QN-XX\` is a complete independent QVM product tree (`qvm/`, `examples/`, `PHOTON/`, `RUN_QVM.cmd`, `VERSION`, …) plus Harbor `IDENTITY.json` and `QNODE.cmd`.
- **Seed (optional at runtime):** `qvm\PRODUCT_LINK.txt` + `scripts\link-qvm.cmd` create `qvm\product` for **rematerializing** copies only. Runtime does **not** depend on the junction.
- **Materialize:** `scripts\materialize-qnode-copies.cmd` (or `node scripts\materialize-qnode-copies.js`) robocopies the seed into QN-01…QN-50 (parallel 4 by default; set `QNODE_COPY_PARALLEL`).
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

Type a code alone to enter focus. In Qnode focus: `info`, `capabilities`, `resources`, `run <circuit.json>`, `bell`, `selftest`, `status`, `where`, `exit`. In DF focus: `status`, `build`, `verify`, `run`, `where`, `doctor`, `exit`.

Also: `qn status`, `qn list`, `qn where`, `df nodes`, `fabric status`.

### DF containers

`START_HARBOR.cmd` / `tools\start-local.js` bind `DF_ROOT` to Desktop `New folder` when `DF_Fabric` is present. HERMIT already understands these via `DFLocator` and `df` / `fabric` / `node`.

## Honesty

Landing and `qn status` report **incomplete** / **absent** / **not built** when copies or containers are missing. Green/operable only when each QN-XX is a real full tree with IDENTITY.

## What was combined

| Piece | Source |
|---|---|
| Containership UC-2.8.0 edge atoms | Desktop `Unikernel_Containership_v2.8.0_EdgeAtoms` applied onto UC-2.7.0 |
| Bridge / virtual WebSocket | Attached HERMIT RAMWS candidate (`hermit-spiral-terminal` 2.0.0-ramws.1) |
| QVM Qnode fleet | QVM 8.1.0-alpha **full-copied** into 50 Harbor Qnodes (seed via PRODUCT_LINK) |

Neither the original QVM tree nor the DF_* containers under `New folder` are modified in place.

## License

See `containership\LICENSE` and `bridge-terminal\LICENSE` for the respective components.
