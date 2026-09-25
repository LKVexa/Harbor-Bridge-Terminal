# edge/ — supplied edge-component atoms (UC-2.8.0)

- `source/` — the supplied archives, byte-for-byte (duplicates stored once)
- `atoms/<key>/` — one canonical extracted build per element
- `variants/<archive>/` — distinct alternative builds of the same element
- `EDGE_MANIFEST.json` — hashes, roles, choices and paths (the authority)
- `evidence/EDGE_TEST_RESULTS.json` — the recorded per-atom suite run with every failure classified

Do not edit files under `atoms/` or `variants/`: `uc edge check --deep` treats any difference from the archive as tampering. See `docs/edge/EDGE_INTEGRATION.md`.

```
EDGE.cmd status
EDGE.cmd check --deep
EDGE.cmd show INV-24
EDGE.cmd test PLN-07
EDGE.cmd test all --jobs 4
```
