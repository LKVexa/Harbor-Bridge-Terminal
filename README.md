# Harbor Bridge Terminal

A combined workspace that puts **Unikernel Containership UC-2.8.0** (edge atoms) beside a **live virtual console** — the HERMIT / SPIRAL terminal with its RAM-resident virtual WebSocket bridge.

Think of the containership as the harbor yard and the virtual console as the bridge: one place to inspect the ship, run edge checks, and talk to sessions over a bounded, ledgered websocket without treating DRAM as a CPU.

## Layout

```
Harbor-Bridge-Terminal/
├─ containership/      Unikernel Containership UC-2.8.0 (edge atoms applied)
├─ bridge-terminal/    HERMIT virtual terminal + RAMWS virtual WebSocket gateway
└─ README.md
```

## Quick start

### Containership (Windows)

From `containership\` (keep the path short on Windows):

```bat
EDGE.cmd status
uc.py verify --quick --no-hull
EDGE.cmd check --deep
```

See `containership\README_START_HERE.md` for the full ship workflow.

### Bridge terminal (Node 18+)

```bash
cd bridge-terminal
npm install
npm start          # desktop HERMIT
npm run gateway    # virtual WebSocket gateway
npm test           # protocol / worker / RAM ledger tests
```

## What was combined

| Piece | Source |
|---|---|
| Containership UC-2.8.0 edge atoms | Desktop `Unikernel_Containership_v2.8.0_EdgeAtoms` applied onto UC-2.7.0 |
| Bridge / virtual WebSocket | Attached HERMIT RAMWS candidate (`hermit-spiral-terminal` 2.0.0-ramws.1) |

Neither upstream archive was modified; this repo is the integrated working tree.

## License

See `containership\LICENSE` and `bridge-terminal\LICENSE` for the respective components.
