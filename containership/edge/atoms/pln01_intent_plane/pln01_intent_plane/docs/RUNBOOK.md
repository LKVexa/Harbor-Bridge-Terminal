# PLN-01 operations runbook (MC-019, MC-026, MC-044)

Self-contained: nothing here needs `pk_core`.

## Bootstrap (day 0)
```bash
python -m pip install ./pln01_intent_plane-4.3.0.tar.gz        # or add the source dir to PYTHONPATH
python pln01_intent_plane/tools/run_checks.py                  # unit + production suites, -O too
python pln01_intent_plane/tools/perf_gate.py                   # perf gate on this host
```
```python
from pln01_intent_plane.config import build_config, load_layer
from pln01_intent_plane.store import DurableStore, FileLease
from pln01_intent_plane.trust import KeyProvider, HmacTokenAuthenticator
from pln01_intent_plane.service import IntentPlaneService
cfg   = build_config([load_layer("prod.json"), load_layer("site-eu1.json")], author="deploy@ci")
keys  = KeyProvider(material_from_kms)            # never a literal key
lease = FileLease("/var/lib/pln01/LEASE", owner=hostname); lease.acquire()
svc   = IntentPlaneService(config=cfg, authenticator=HmacTokenAuthenticator(keys),
                           store=DurableStore("/var/lib/pln01", keys), lease=lease)
```
Readiness = `svc.health.readiness()["status"] == "pass"`; liveness = `svc.health.liveness()`.

## Deploy (day 1)
1. `tools/exit_gate.py --archive dist/<archive>` must print `GO` or `CONDITIONAL_GO` with owner-approved waivers.
2. Canary: one region / one tenant cohort for 24 h (see Rollout). 3. Promote. 4. Record the gate JSON with the release.

## Rollout, canary and emergency disable {#rollout}
Stages: 1 % tenants → 10 % → 50 % → 100 %, each ≥ 24 h, abort if any page-level alert fires or error rate on
`E9999/E0020` > 0. Emergency stop: `svc.controls.disable(actor=…, reason=…)` (mutations and plan release refused,
reads continue). Scoped: `freeze("tenant/env")`, `quarantine("tenant")`. Release: `enable/unfreeze/release` with reason.
Rollback of the binary: stop, redeploy previous version — safe because 4.3 → 4.2 has no durable state to migrate;
for later versions, restore the pre-upgrade backup (downgrade of format is refused by design).

## Day 2 procedures
### plan-latency
Check `intent_graph_nodes`, recent large fan-outs; confirm perf gate on host; shard by tenant if > 0.8 × max_nodes.
### store-integrity
`DurableStore(state_dir, keys).verify()`. On `StoreIntegrityError`: **do not edit files**. Freeze plane (`disable`),
preserve the directory, restore latest good backup to a clean dir (`DurableStore.restore(..., expected_sha256=…)`),
verify, repoint, enable. Open SEV1 per governance/INCIDENT_RESPONSE.md.
### identity-down
Plane fails closed by design. Confirm PLN-07 status; no bypass exists — do not set `require_authentication=false` in prod.
### overload
Check `pln01_bulkhead_saturation`, top `E0011` tenants; raise per-tenant override or capacity via config change.
### drift
`svc.plan()` → `drift`, `stale_sites`; confirm reporter freshness (`svc.site_status()`), then executor health (PLN-02).
### failover
Standby acquires lease after TTL (`FileLease.acquire`), opens the store, replays WAL. Old primary is fenced
(E0019). Never delete `LEASE` by hand.
### stall
Restart the process; recovery replays WAL; verify graph_version continuity in metrics.

## Backup / restore / DR
Backup: `svc.store.backup("/backups/pln01-<ts>.tgz")` → writes `.manifest.json` with sha256. Schedule hourly, keep 30 days,
copy off-host. Restore drill monthly to a clean host; success = `verify()` ok and `graph_version` equals manifest.
RPO: last acknowledged mutation (primary disk) / last backup (site loss). RTO targets in docs/STATE_MODEL.md.

## Key rotation
`keys.rotate()` quarterly or on suspicion; keep previous version until all tokens expire (≤ 1 h) and a snapshot has
been re-sealed with the new key (`svc.store.snapshot()`), then `keys.destroy(old)`.
