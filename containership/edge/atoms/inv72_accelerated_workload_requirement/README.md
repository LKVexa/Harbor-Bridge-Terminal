# INV-72 - Accelerated workload requirement

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

An accelerated workload requirement describes the accelerator hardware a job
needs: accelerator class, device memory, device count, interconnect requirement,
tenant, and isolation mode. The matcher is strict about class and memory and
fails closed for partition use unless `isolation="shared"` is explicit.

## Responsibility

Own the accelerator requirement schema, deterministic strict matching against a
discovered inventory, interconnect constraints, partition-sharing rules, and
human-readable refusal reasons.

## Owns

- Accelerator requirement validation
- Strict class and minimum-memory matching
- Deterministic multi-device selection
- Interconnect-group constraints
- Partition isolation decisions
- Explained non-matches

## Explicitly does not own

- Device discovery
- Scheduling queues or job lifecycle
- Driver management
- Model code
- Power policy
- Durable allocation or distributed reservation state

## Runtime interfaces

| Schema | Where | Notes |
|---|---|---|
| `PK_ACCEL_REQ/1` | `schemas/PK_ACCEL_REQ-1.schema.json` | `class`, `mem_gb`, `tenant`; optional `count`, `interconnect`, `isolation`, `workload`, `idempotency_key`, `deadline_ms`, `allowed_nodes` |
| `PK_ACCEL_INVENTORY/1` | `schemas/PK_ACCEL_INVENTORY-1.schema.json` | sealed discovery snapshot (digest + HMAC, monotonic generation) |
| `PK_ACCEL_MATCH/1` | `schemas/PK_ACCEL_MATCH-1.schema.json` | decision with outcome, reason codes, rationale, reservation, generations, trace id |
| `PK_ACCEL_ERROR/1` | `schemas/PK_ACCEL_ERROR-1.schema.json` | registered code (`errors.REGISTRY`), outcome class, retryable |
| `PK_ACCEL_CONFIG/1`, `PK_ACCEL_STATUS/1`, `PK_ACCEL_AUDIT_EVENT/1` | `schemas/` | configuration, health/readiness, tamper-evident audit |

Library API (v4.2.0-compatible): `match(req, devices, reserve=True)` still returns
`(selected_ids | None, reasons)`; `decide()` returns the structured decision.
Governed API (v4.3.0): `service.AcceleratorService.request / release / quarantine / drain / disable /
enable / status / explain` — see `ops/BOUNDARIES.md` for every boundary and its auth/limits.

Security-sensitive defaults: isolation defaults to `dedicated`; unknown values rejected; NaN/inf,
booleans-as-numbers, oversize payloads and duplicate ids rejected; whole devices exclusive per
reservation; every failure fails closed. Details: `docs/SECURITY.md`, `ops/THREAT_MODEL.md`.

## Ownership

Owners, RACI and escalation: [`ops/OWNERS.md`](ops/OWNERS.md). Every role is currently UNASSIGNED,
which blocks release by design.

## Layout

| Path | What |
|---|---|
| `matcher.py` | pure, bounded, deterministic matcher (`match`, `decide`) |
| `service.py` | governed pipeline composing every control |
| `state.py` | atomic, fenced, idempotent reservation store with write-ahead journal |
| `discovery.py` | authenticated inventory intake, freshness, offline grace, failover |
| `trust.py` | caller authentication (HMAC tokens, replay cache) and capability authorization |
| `config.py` + `config/` | declarative profiles per tier, overlays, validation, generations, rollback |
| `resilience.py` | deadlines, cancellation, admission, retry, circuit breaker |
| `audit.py`, `telemetry.py`, `redaction.py`, `explain.py` | audit chain, metrics/logs/traces, redaction, operator explain view |
| `errors.py`, `lifecycle.py`, `compat.py`, `precedence.py`, `capacity.py`, `adapters.py` | codes, state machines, versioning, precedence, capacity, neighbour adapters |
| `ops/` | SPEC, threat model, boundaries, runbook, incident, owners, waivers, reviews, EOL, RTM |
| `tools/` | rtm, governance, deps/SBOM, manifest, perf gate, pk_core gate, release gate, bootstrap |
| `bench/perf_suite.py` | reproducible performance baseline |
| `_vendor/pk_core` | the owner's PK framework, vendored unchanged (provenance file beside it) |
| `evidence/` | generated evidence (tests, perf, gates, RTM, SBOM, samples) |

## Verification

```text
python -B  inv72_accelerated_workload_requirement/tests/run_all.py
python -O -B inv72_accelerated_workload_requirement/tests/run_all.py
python -B -m inv72_accelerated_workload_requirement.tools.rtm --check
python -B -m inv72_accelerated_workload_requirement.tools.deps_check
python -B -m inv72_accelerated_workload_requirement.tools.manifest --verify
python -B -m inv72_accelerated_workload_requirement.tools.pk_gate
python -B -m inv72_accelerated_workload_requirement.tools.release_gate --skip-perf-run
```

`run_all.py` fails on any skip: with pk_core vendored there are no declared skip lanes left.

## Status

See `POST_REMEDIATION_AUDIT.md` and `evidence/RTM.json`. Release verdict: **NO_GO** until the
human inputs listed there exist. Operations: `ops/RUNBOOK.md` (day 0/1/2, rollout, rollback,
emergency disable), `ops/INCIDENT.md`.
