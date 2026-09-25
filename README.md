# Harbor Bridge Terminal

A combined workspace that puts **Unikernel Containership UC-2.8.0** (edge atoms) beside a **live virtual console** — the HERMIT / SPIRAL terminal with its RAM-resident virtual WebSocket bridge — plus a **50× QVM Qnode fleet** and the **DF fabric** containers.

Think of the containership as the harbor yard and the virtual console as the bridge: one place to inspect the ship, run edge checks, talk to sessions over a bounded, ledgered websocket, and focus into individual Qnodes or DF containers.

## Layout

```
Harbor-Bridge-Terminal/
├─ containership/      Unikernel Containership UC-2.8.0 (edge atoms applied)
├─ bridge-terminal/    HERMIT virtual terminal + RAMWS virtual WebSocket gateway
├─ qvm/
│  ├─ PRODUCT_LINK.txt absolute path to the QVM 8.1.0-alpha product (source of truth)
│  └─ product/         directory junction → QVM product (created by link-qvm / START_HARBOR)
├─ qnodes/
│  ├─ FLEET.json       roster of QN-01 … QN-50
│  └─ QN-01/ … QN-50/  thin instances (IDENTITY + runtime + QNODE.cmd)
├─ fleet/
│  └─ HARBOR_FLEET.json  DF containers + Qnodes + focus codes
├─ scripts/
│  ├─ link-qvm.cmd       create/refresh the qvm\product junction
│  └─ generate-qnodes.js regenerate the 50 thin instances
├─ START_HARBOR.cmd      bind DF_ROOT + QNODE_ROOT, link QVM, start gateway
└─ README.md
```

## Quick start

### Harbor (recommended)

```bat
START_HARBOR.cmd
```

Opens `http://127.0.0.1:10000/`. On session open the landing banner shows the **Harbor fleet board**: DF containers (`ns` `nm` `nl` `nx` `nf`) and all 50 Qnodes (`qn01`…`qn50`) with operability and focus codes.

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

## Qnode fleet (50 × QVM 8.1.0-alpha)

- **Product binding:** `qvm\PRODUCT_LINK.txt` records the absolute QVM source under Desktop `New folder\…`. `scripts\link-qvm.cmd` creates a **junction** at `qvm\product` — the original QVM tree is never duplicated or modified.
- **Thin instances:** each `qnodes\QN-XX\` has `IDENTITY.json`, `runtime\`, `QNODE.cmd`, and a short README. Operable means IDENTITY present **and** the product junction resolves to `qvm\cli.py`.
- **Launcher:** `QNODE.cmd info` / `QNODE.cmd run …` sets `PYTHONPATH` to the shared product and runs `py -3 -m qvm.cli` with cwd under that instance’s `runtime\`.

### Focus codes (interactive terminal)

| Code | Target |
|------|--------|
| `qn01` … `qn50` | Qnode instance → QVM focus REPL |
| `ns` | DF_Small / N_SMALL |
| `nm` | DF_Medium / N_MEDIUM |
| `nl` | DF_Large / N_LARGE |
| `nx` | DF_Xtra_Large / N_XLARGE |
| `nf` | DF_Fabric |

Type a code alone to enter focus (prompt becomes `qn07›` / `ns›`). In Qnode focus: `info`, `capabilities`, `resources`, `run <circuit.json>`, `bell`, `selftest`, `status`, `where`, `exit`. In DF focus: `status`, `build`, `verify`, `run`, `where`, `doctor`, `exit`.

Also: `qn status`, `qn list`, `qn where`, `df nodes`, `fabric status`.

### DF containers

`START_HARBOR.cmd` / `tools\start-local.js` bind `DF_ROOT` to Desktop `New folder` when `DF_Fabric` is present. HERMIT already understands these via `DFLocator` and `df` / `fabric` / `node`.

## Honesty

Landing and `qn status` report **unbound** / **absent** / **not built** when product or containers are missing. Green/operable only when the product link and IDENTITY are real.

## What was combined

| Piece | Source |
|---|---|
| Containership UC-2.8.0 edge atoms | Desktop `Unikernel_Containership_v2.8.0_EdgeAtoms` applied onto UC-2.7.0 |
| Bridge / virtual WebSocket | Attached HERMIT RAMWS candidate (`hermit-spiral-terminal` 2.0.0-ramws.1) |
| QVM Qnode fleet | QVM 8.1.0-alpha linked by reference; 50 thin Harbor instances |

Neither the original QVM tree nor the DF_* containers under `New folder` are modified in place.

## License

See `containership\LICENSE` and `bridge-terminal\LICENSE` for the respective components.
