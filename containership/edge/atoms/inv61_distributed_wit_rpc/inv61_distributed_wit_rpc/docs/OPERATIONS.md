# Operations, release and governance (M14, M19, M20, M29, M31, M32)

## 1. Bootstrap (M31)
```
python -m venv .venv && .venv/bin/pip install -r requirements.lock
export INV61_PSK=<64 hex chars, from your secret store>      # referenced as psk_ref=env:INV61_PSK
python -B -m unittest discover -s tests                       # must be green before first start
python -B tools/sbom.py --out evidence/sbom.cdx.json --sums SHA256SUMS
```
Configuration is layered defaults < file < environment (`wrpc/ops.py::ConfigStore`); the
active digest and per-key source are exposed as provenance. Secrets are only ever references.

## 2. Health (M14)
`Node.health.live()` → process up. `Node.health.ready()` → `pass | warn | fail`; `fail` when a
critical dependency check (listener, audit-writable) fails or the node is draining; checks are
time-boxed (0.5 s). Orchestrators: liveness → restart; readiness → remove from rotation.
`drain(timeout_s)` fails readiness, refuses new connections, answers new calls `unavailable`
(retryable) and waits for in-flight calls; then `stop()` tears down remaining sessions.

## 3. Metrics / logs / traces (M15–M17) — see TELEMETRY_POLICY.md
Key series: `inv61_calls_total{interface,outcome}`, `inv61_handle_seconds` (histogram),
`inv61_handshakes_total{outcome}`, `inv61_record_rejects_total{outcome}`,
`inv61_connections_rejected_total`, `inv61_metric_series_dropped_total`.
Alerts (proposed thresholds, not yet agreed with an owner):
* `signature-mismatch` or `version-mismatch` rate > 0 for 5 min → deploy skew page.
* `record_rejects_total` > 0 → security page (replay/tamper on the wire).
* `overloaded` > 1 % of calls for 10 min → capacity ticket.
* `inv61_handle_seconds` p99 > 50 ms → latency ticket.

## 4. Failover and state (M19, M20)
INV-61 is stateless per call except for the idempotency cache. With `journal=Journal(path)`
completed *final* outcomes survive restart (schema `INV61_JOURNAL/2`, torn tail tolerated,
mid-file corruption fails closed). The journal is written before the outcome is published; a
crash between the callee finishing and the journal write can still re-execute (needs the
callee's own outbox to close). The journal has no compaction yet (OPEN). Memory: the cache
holds up to 100 000 entries and evicts oldest first — the 60 s soak's RSS growth to ~90 MB is
this cache filling, bounded by that cap. `LeaseTable` is a library primitive: `Node` does not
consult fencing tokens on dispatch (OPEN).
Mutable keys that need a single writer use `LeaseTable` fencing tokens; `freeze(key)` is the
quarantine switch during split-brain investigation. Multi-node shared idempotency state is
**not implemented** (each node journals locally) — a retry landing on another node can
re-execute. Status OPEN; route retries with the same request id to the same node meanwhile.

## 5. Rollout and rollback (M32)
1. CI matrix green, bench regression gate ≤ 25 % p99, SBOM regenerated.
2. Canary: one node, 5 % traffic, 30 min; abort on any `signature-mismatch`/`record_rejects`.
3. Staged: 25 % → 50 % → 100 %, 30 min each.
4. Rollback: redeploy previous sealed release (its `SHA256SUMS`); config rollback is
   `ConfigStore.rollback()`. Wire major is unchanged within 4.x so mixed fleets interoperate.
5. Emergency disable: `drain()` then remove the component from the registry package; the
   gate reports a reduced element count rather than a silent pass.

## 6. Incidents
SEV1 cross-tenant data or authentication bypass · SEV2 sustained call failure > 5 % ·
SEV3 degraded latency. Paging roster: **UNASSIGNED**.

## 7. Registers
| Register | Entries |
|---|---|
| Waivers | none granted — every open item is listed as OPEN/BLOCKED/PARTIAL in `CHECKLIST_STATUS.json` at the package root |
| Technical debt | no forward secrecy (T-11); no mTLS (T-12); per-node idempotency (§4); no per-IP limits (T-08); CI matrix not yet executed |
| Vulnerability SLA (proposed) | critical 7 days, high 30 days |
| Review cadence (proposed) | quarterly architecture, monthly dependency |

## 8. Production exit gate
Production use is **NOT authorised** by this release. Blocking: M01 pk_core, M02 master
source, M22 owner/approver, M27 CI matrix execution, independent security review (M23),
long-running fuzz/soak (M24/M29).
