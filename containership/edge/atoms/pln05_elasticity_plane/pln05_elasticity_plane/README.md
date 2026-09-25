# PLN-05 - Elasticity plane

**Version:** 4.2.0 (see `CHANGELOG.md`)
**Group:** 02_Synthesis_Planes
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Scope decision:** `docs/adr/ADR-0001-pln05-authoritative-scope.md` (PROPOSED)
**Checklist:** 100 requirements in `CHECKLIST.json`; traceability in `traceability/REQUIREMENTS_MATRIX.md`
**Audit:** `AUDIT_REPORT_4.2.0.md` (post-remediation); `AUDIT_REPORT_4.1.1.md` (history)
**Workflow:** `MASTER.md`
**License:** pending owner decision (`LICENSE-PENDING.md`) · **Security:** `SECURITY.md` · **Owners:** `ops/oncall.json`

The elasticity plane decides how much capacity exists, including the scale-to-zero case that container orchestration handles badly. It converts observed demand into a capacity target with explicit hysteresis, so the estate does not oscillate.

## Responsibility

Own capacity targets per workload: convert observed demand into a bounded, hysteretic scale decision including scale-to-zero, and never emit a target outside the declared floor and ceiling.

## Owns

- Capacity targets per workload
- Scale-up and scale-down hysteresis
- Scale-to-zero and cold-start admission
- Floor and ceiling enforcement
- Oscillation suppression

## Explicitly does not own

- Placement of new capacity
- Node provisioning
- Workload isolation
- The demand signal itself
- Cost accounting

## Non-goals

- Placing or provisioning capacity
- Deciding node count
- Guaranteeing cold-start latency
- Overriding an externally lowered ceiling

## Interfaces

- `limits` - PK_CAPACITY_LIMITS/1 (`schemas/pk_capacity_limits_v1.json`) - declared floor, ceiling, and hysteresis parameters
- `observe` - PK_DEMAND/1 (`schemas/pk_demand_v1.json`) - demand samples per workload
- `target` - PK_CAPACITY_TARGET/1 (`schemas/pk_capacity_target_v1.json`) - emitted capacity target with the reason
- errors - PK_ERROR/1 (`schemas/error_v1.json`); reliability contract in `spec/interface_reliability.md`

## Service-level objectives

- **target bounds** - zero targets outside the declared floor/ceiling (error budget: no budget)
- **reaction time** - p95 scale-up decision within two demand samples of threshold breach (error budget: 5% may take a third sample)
- **stability** - no more than one direction change per workload per grace period (error budget: 1% of workloads may exceed under demand step changes)

Measurable NFRs and their tests: `spec/pln05_nfr.json`.

## Layout

| Path | What |
|---|---|
| `controller.py` | the deterministic hysteretic controller (unchanged algorithm since 4.1.1, plus snapshot/restore) |
| `plane.py` | service boundary: decode → authn/z → controls → freshness → idempotency → lease → decide → persist → fenced publish → explain/telemetry |
| `wire.py`, `schemas/` | boundary codec over the released JSON Schemas |
| `iam.py`, `keys.py`, `security/` | credentials, capabilities, key ring, transport policy, threat model |
| `configuration.py`, `config/` | layered, validated, atomically activated configuration with rollback |
| `state.py` | durable HMAC-sealed state, lease/epoch coordination, fenced reference consumer |
| `reliability.py`, `health.py` | retry/admission/circuit breaker; health, readiness, stall detection |
| `audit.py`, `telemetry.py` | tamper-evident audit; metrics, structured logs, trace context |
| `supplychain.py`, `tools/build_release.py` | SBOM, provenance, digests, approved versions |
| `component.py`, `contract.py` | `pk_core` framework adapter (loaded lazily; needs `pk_core`) |

## Running it

```
python3 tools/ci.py                          # presubmit: every tier, evidence in evidence/4.2.0/
python3 tools/ci.py --release                # release tier: refuses skips, builds wheel/sdist/SBOM/provenance
python3 tools/gate.py                        # production exit gate over the evidence
python3 -m pln05_elasticity_plane version    # local CLI (validate, validate-config, inspect-state, verify-audit)
python3 pln05_elasticity_plane/tests/test_controller.py   # the original standalone controller tests still run alone
```

Framework conformance (`tests/test_component.py::ConformanceTest`, `python -m pk_core ...`) needs `pk_core>=4.0,<5.0`, which is not supplied or resolvable; the release tier therefore fails by design until it is.

## Day-0 / day-1 / day-2

Runbooks: `docs/runbooks/day0-bootstrap.md`, `docs/runbooks/day1-operations.md`, `docs/runbooks/day2-incidents.md`, `docs/runbooks/backup-restore.md`; release and rollback policy in `docs/release-policy.md`. Emergency stop without uninstalling: `control(..., "freeze" | "quarantine" | "disable")`; resume needs two different emergency administrators.
