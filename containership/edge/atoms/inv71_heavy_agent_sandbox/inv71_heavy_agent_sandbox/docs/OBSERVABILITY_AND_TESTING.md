# Observability policy and test strategy (C071-C090)

## Observability

- **Status endpoint (C071):** `SandboxController.status(privileged=...)` returns `schemas/PK_HEAVYBOX_STATUS_v1.schema.json`. It separates liveness, readiness for new sessions, `DEGRADED` (noncritical dependency down) and `QUARANTINED`. Session counts and owner appear only for privileged callers.
- **Metrics (C072):** the catalog is `docs/generated/METRICS.md`. Labels are bounded by construction.
- **Logs and audit (C073):** security events go to the durable audit stream, with stable fields (`REQUIRED` in `control/audit_log.py`), a `clock` quality field, correlation ids and field redaction. Event classes (`telemetry.EVENT_CLASSES`) separate security rejection, dependency failure, resource rejection, guest failure, internal defect, lifecycle and operator action.
- **Tracing (C074):** W3C `traceparent`. It is accepted only from an authenticated control-plane peer. Anything the guest supplies starts a new trace. Errors and security flows are always sampled (`force_sample`).
- **Diagnostics (C075):** the explain view is authenticated and tenant-scoped, and bounded (1024 records by default). Detail is never exported as metrics.
- **Decisions (C076, C077):** every allow or deny records a registry reason code, the decision inputs by digest, and the correlation id. Free-text reasons are refused. Records are point-in-time, so a later policy change does not rewrite them.
- **Lineage (C078):** a session create carries `release` (the application release digest). Session records carry `config_digest` and `base_digest`. Integration with a CMDB or infrastructure graph is BLOCKED because none exists.

### Retention and sampling (C079, PROPOSED)

| Class | Retention | Sampling | Residency / access |
|---|---|---|---|
| security audit + anchors | 400 days, WORM, legal hold capable | never sampled | region of the node; security team only |
| operational logs | 30 days | errors 100%, info 10% | region; SRE |
| traces | 7 days | errors and security 100%, else 1% | region; SRE |
| metrics | 13 months (downsampled after 30 days) | n/a | global aggregate without tenant ids |
| benchmark and evidence bundles | life of release + 2 years | n/a | release store |
| high-cardinality diagnostics | 72 hours | on demand | privileged, tenant-scoped |

Tenant deletion removes tenant-scoped diagnostics and logs. Audit records keep only the tenant-safe identifiers the retention policy allows.

### Alerts and dashboards (C080)

Rules are in `governance/alerts.yaml`. Every rule names its severity, runbook section and owner (UNASSIGNED). Dashboards (to be built on GAP-09) are split into load and saturation, degraded dependencies, policy and security rejections, attack indicators (replays, revoked credentials, egress deny spikes, private-range resolution), guest-caused failures, and internal defects.

## Test strategy (C082-C090)

| Layer | What runs here | Evidence file | Production-equivalent gap |
|---|---|---|---|
| contract (C082) | schema fixtures valid and invalid, error-registry contract, idempotency, deadlines, authz, transitions | `evidence/tests.json`, `fixtures/MANIFEST.json` | per-version-pair client/server runs need released versions |
| integration (C083) | fake adjacent layers (INV-69, INV-24, INV-26, GAP-09) through the reference controller | `fixtures/valid/adjacent_harness.json` | real scheduler, Firecracker, snapshot and network: BLOCKED |
| compatibility (C084) | negotiation and skew tests; matrix blocks untested rows | `docs/generated/COMPATIBILITY.md` | hardware matrix: BLOCKED |
| fuzzing (C085) | `tools/fuzz.py`: 6 targets, seeded, time-limited, minimized findings | `evidence/security/fuzz.json` | coverage-guided and sanitizer runs on native code: not applicable here, required for the node agent |
| concurrency (C086) | 64-way duplicate create, 16-way teardown, 8×200 admission churn, 3000 lifecycle random walks | tests | thread sanitizer and deterministic scheduler for the production language |
| threat-derived (C087) | `docs/THREAT_MODEL.md` rows map to test ids | `evidence/traceability.json` | escape, side-channel and penetration testing: BLOCKED |
| performance (C088) | `tools/bench.py` reference layer only | `evidence/performance/bench.json` | microVM benchmark, soak and fleet scale: BLOCKED |
| disaster (C089) | partition/fencing, resolver flap, trust outage, audit outage, create-phase faults | tests | site loss and restore drills: BLOCKED |
| release evidence (C090) | `tools/build_evidence.py` plus `tools/production_gate.py` (offline, reproducible) | `evidence/release-manifest.json`, `evidence/gate-result.json` | signing with a managed key: BLOCKED |

Every discovered defect becomes a regression test. This pass found five defects, and each has one (see `CHANGELOG.md`).
