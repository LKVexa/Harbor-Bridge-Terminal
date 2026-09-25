# Qnode load audit

- **Date (America/Los_Angeles):** 09/25/2026, 13:23:42 PDT
- **Harbor root:** `C:\Users\russe\OneDrive\Desktop\Harbor-Bridge-Terminal`
- **Scope:** QN-01 … QN-50 (full QVM 8.1.0-alpha copies)
- **Parallelism:** 5
- **Python:** `py -3`

## Method

1. **Fleet inventory** — confirm each `qnodes/QN-XX` exists with key entrypoints (`qvm/cli.py`, `VERSION`, `IDENTITY.json`, `QNODE.cmd`, `examples/bell.json`, `RUN_QVM.cmd`); count files/bytes; detect directory reparse/junction.
2. **Independence** — write a unique marker under `QN-01/runtime/` and verify it does **not** appear under `QN-02/runtime/`.
3. **Load probe** (per node, cwd = that copy, `PYTHONPATH` = that copy):
   - `py -3 -m qvm.cli info`
   - `py -3 -m qvm.cli selftest` (built-in CLI selftest / unit suite)
   - `py -3 -m qvm.cli run examples/bell.json` (statevector Bell circuit, 1024 shots)
4. **Harbor integration** — align `fleet/HARBOR_FLEET.json` focus codes `qn01`…`qn50` with on-disk nodes (`qnode_mode=full-copies`).

## Summary

| Check | Result |
|-------|--------|
| Nodes inventoried | 50 / 50 |
| Inventory pass | 50 / 50 |
| Load probe pass | 50 / 50 |
| Overall carry-load pass | **50 / 50** |
| Independence | PASS — Marker written under QN-01/runtime did not appear under QN-02/runtime (independent trees). |
| Fleet alignment | PASS — HARBOR_FLEET.json lists all 50 qnodes (qn01…qn50), qnode_mode=full-copies. |
| Failures | none |

**Verdict:** all 50 Qnodes can carry a load (inventory + info + selftest + bell run).

## Per-node results

| Node | Code | Files | Size | Inv | Info | Selftest | Bell | Overall | Notes |
|------|------|------:|-----:|:---:|:----:|:--------:|:----:|:-------:|-------|
| QN-01 | qn01 | 538 | 16.8 MB | PASS | PASS (456ms) | PASS (373ms) | PASS (309ms) | PASS | — |
| QN-02 | qn02 | 520 | 16.8 MB | PASS | PASS (306ms) | PASS (458ms) | PASS (426ms) | PASS | — |
| QN-03 | qn03 | 520 | 16.8 MB | PASS | PASS (320ms) | PASS (418ms) | PASS (317ms) | PASS | — |
| QN-04 | qn04 | 520 | 16.8 MB | PASS | PASS (293ms) | PASS (419ms) | PASS (394ms) | PASS | — |
| QN-05 | qn05 | 520 | 16.8 MB | PASS | PASS (311ms) | PASS (417ms) | PASS (386ms) | PASS | — |
| QN-06 | qn06 | 520 | 16.8 MB | PASS | PASS (427ms) | PASS (416ms) | PASS (353ms) | PASS | — |
| QN-07 | qn07 | 520 | 16.8 MB | PASS | PASS (313ms) | PASS (423ms) | PASS (327ms) | PASS | — |
| QN-08 | qn08 | 520 | 16.8 MB | PASS | PASS (340ms) | PASS (425ms) | PASS (361ms) | PASS | — |
| QN-09 | qn09 | 520 | 16.8 MB | PASS | PASS (326ms) | PASS (431ms) | PASS (370ms) | PASS | — |
| QN-10 | qn10 | 520 | 16.8 MB | PASS | PASS (321ms) | PASS (435ms) | PASS (370ms) | PASS | — |
| QN-11 | qn11 | 520 | 16.8 MB | PASS | PASS (357ms) | PASS (418ms) | PASS (337ms) | PASS | — |
| QN-12 | qn12 | 520 | 16.8 MB | PASS | PASS (332ms) | PASS (427ms) | PASS (355ms) | PASS | — |
| QN-13 | qn13 | 520 | 16.8 MB | PASS | PASS (329ms) | PASS (424ms) | PASS (366ms) | PASS | — |
| QN-14 | qn14 | 520 | 16.8 MB | PASS | PASS (316ms) | PASS (423ms) | PASS (375ms) | PASS | — |
| QN-15 | qn15 | 520 | 16.8 MB | PASS | PASS (313ms) | PASS (439ms) | PASS (351ms) | PASS | — |
| QN-16 | qn16 | 520 | 16.8 MB | PASS | PASS (351ms) | PASS (418ms) | PASS (288ms) | PASS | — |
| QN-17 | qn17 | 520 | 16.8 MB | PASS | PASS (322ms) | PASS (415ms) | PASS (314ms) | PASS | — |
| QN-18 | qn18 | 520 | 16.8 MB | PASS | PASS (307ms) | PASS (413ms) | PASS (330ms) | PASS | — |
| QN-19 | qn19 | 520 | 16.8 MB | PASS | PASS (310ms) | PASS (408ms) | PASS (390ms) | PASS | — |
| QN-20 | qn20 | 520 | 16.8 MB | PASS | PASS (312ms) | PASS (390ms) | PASS (295ms) | PASS | — |
| QN-21 | qn21 | 520 | 16.8 MB | PASS | PASS (342ms) | PASS (432ms) | PASS (334ms) | PASS | — |
| QN-22 | qn22 | 520 | 16.8 MB | PASS | PASS (316ms) | PASS (449ms) | PASS (372ms) | PASS | — |
| QN-23 | qn23 | 520 | 16.8 MB | PASS | PASS (352ms) | PASS (445ms) | PASS (338ms) | PASS | — |
| QN-24 | qn24 | 520 | 16.8 MB | PASS | PASS (332ms) | PASS (448ms) | PASS (356ms) | PASS | — |
| QN-25 | qn25 | 520 | 16.8 MB | PASS | PASS (332ms) | PASS (435ms) | PASS (375ms) | PASS | — |
| QN-26 | qn26 | 520 | 16.8 MB | PASS | PASS (347ms) | PASS (424ms) | PASS (322ms) | PASS | — |
| QN-27 | qn27 | 520 | 16.8 MB | PASS | PASS (316ms) | PASS (441ms) | PASS (336ms) | PASS | — |
| QN-28 | qn28 | 520 | 16.8 MB | PASS | PASS (324ms) | PASS (429ms) | PASS (339ms) | PASS | — |
| QN-29 | qn29 | 520 | 16.8 MB | PASS | PASS (319ms) | PASS (436ms) | PASS (337ms) | PASS | — |
| QN-30 | qn30 | 520 | 16.8 MB | PASS | PASS (308ms) | PASS (438ms) | PASS (350ms) | PASS | — |
| QN-31 | qn31 | 520 | 16.8 MB | PASS | PASS (348ms) | PASS (441ms) | PASS (924ms) | PASS | — |
| QN-32 | qn32 | 520 | 16.8 MB | PASS | PASS (325ms) | PASS (444ms) | PASS (553ms) | PASS | — |
| QN-33 | qn33 | 520 | 16.8 MB | PASS | PASS (317ms) | PASS (437ms) | PASS (860ms) | PASS | — |
| QN-34 | qn34 | 520 | 16.8 MB | PASS | PASS (321ms) | PASS (488ms) | PASS (540ms) | PASS | — |
| QN-35 | qn35 | 520 | 16.8 MB | PASS | PASS (313ms) | PASS (1229ms) | PASS (303ms) | PASS | — |
| QN-36 | qn36 | 520 | 16.8 MB | PASS | PASS (350ms) | PASS (425ms) | PASS (295ms) | PASS | — |
| QN-37 | qn37 | 520 | 16.8 MB | PASS | PASS (308ms) | PASS (416ms) | PASS (335ms) | PASS | — |
| QN-38 | qn38 | 520 | 16.8 MB | PASS | PASS (296ms) | PASS (426ms) | PASS (314ms) | PASS | — |
| QN-39 | qn39 | 520 | 16.8 MB | PASS | PASS (310ms) | PASS (429ms) | PASS (302ms) | PASS | — |
| QN-40 | qn40 | 520 | 16.8 MB | PASS | PASS (334ms) | PASS (418ms) | PASS (301ms) | PASS | — |
| QN-41 | qn41 | 520 | 16.8 MB | PASS | PASS (306ms) | PASS (421ms) | PASS (304ms) | PASS | — |
| QN-42 | qn42 | 520 | 16.8 MB | PASS | PASS (306ms) | PASS (418ms) | PASS (311ms) | PASS | — |
| QN-43 | qn43 | 520 | 16.8 MB | PASS | PASS (312ms) | PASS (414ms) | PASS (304ms) | PASS | — |
| QN-44 | qn44 | 520 | 16.8 MB | PASS | PASS (304ms) | PASS (422ms) | PASS (314ms) | PASS | — |
| QN-45 | qn45 | 520 | 16.8 MB | PASS | PASS (331ms) | PASS (451ms) | PASS (298ms) | PASS | — |
| QN-46 | qn46 | 520 | 16.8 MB | PASS | PASS (303ms) | PASS (422ms) | PASS (299ms) | PASS | — |
| QN-47 | qn47 | 520 | 16.8 MB | PASS | PASS (327ms) | PASS (415ms) | PASS (300ms) | PASS | — |
| QN-48 | qn48 | 520 | 16.8 MB | PASS | PASS (310ms) | PASS (417ms) | PASS (299ms) | PASS | — |
| QN-49 | qn49 | 520 | 16.8 MB | PASS | PASS (308ms) | PASS (428ms) | PASS (264ms) | PASS | — |
| QN-50 | qn50 | 520 | 16.8 MB | PASS | PASS (329ms) | PASS (384ms) | PASS (258ms) | PASS | — |

## Failure details

None.
## Re-run

```bat
scripts\audit-qnode-load.cmd
```

Or: `node scripts\audit-qnode-load.js` (optional `set QNODE_AUDIT_PARALLEL=5`).

If inventory fails (missing `qvm\cli.py`), rematerialize first:

```bat
scripts\materialize-qnode-copies.cmd
```

Machine-local artifact also written: `fleet/QNODE_LOAD_AUDIT.json`.
