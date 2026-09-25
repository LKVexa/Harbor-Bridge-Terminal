# INV-63 - Wasm deployment manager

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** not included in the supplied archive; see `MISSING_COMPONENTS.md`.

The Wasm deployment manager holds desired state -- which components, how many, spread across which labels -- and reconciles the lattice toward it. Its guarantees are convergence (repeated reconciliation reaches the desired state and then does nothing) and safe rollout (never more than the allowed number of instances unavailable while a version changes).

## Responsibility

Own declarative deployment: desired-state storage, reconciliation diffs, spread constraints, idempotent convergence and bounded-unavailability rollouts.

## Owns

- Desired-state storage
- Reconciliation diff computation
- Spread across host labels
- Idempotent convergence
- Rolling updates with a max-unavailable bound

## Explicitly does not own

- The application manifest format
- Running components
- Artifact signing
- Host provisioning
- Provider implementations

## Non-goals

- Defining manifests
- Running components
- Provisioning hosts

## Interfaces

- `desired` - PK_DEPLOY_DESIRED/1 - component, version, count, spread
- `diff` - PK_DEPLOY_DIFF/1 - start and stop actions
- `rollout` - PK_DEPLOY_ROLLOUT/1 - batched update plan

## Service-level objectives

- **convergence** - a second reconcile after convergence emits zero actions (error budget: no budget)
- **availability** - never more than max-unavailable instances down in rollout (error budget: no budget)
- **reconcile time** - p99 diff under 10ms for 1000 instances (error budget: 1% may exceed)

## Running it

```
pip install -r inv63_wasm_deployment_manager/requirements.lock        # cryptography==46.0.7
python -m unittest discover -s inv63_wasm_deployment_manager/tests    # 110 tests (3 skip without pk_core)
python inv63_wasm_deployment_manager/perf/bench.py --gate --out inv63_wasm_deployment_manager/perf/results.json
python inv63_wasm_deployment_manager/audit.py                         # regenerates AUDIT_RESULTS.json, MISSING_COMPONENTS.md, traceability
python inv63_wasm_deployment_manager/gate.py                          # signed PK_DEPLOY_GATE/1 verdict
python inv63_wasm_deployment_manager/tools/bootstrap.py --help        # day-0 bootstrap
```

## Package map (4.3.0)

| Layer | Files |
|---|---|
| Reconciliation core | `manager.py` (unchanged API; `eligible_hosts` added; heap placement) |
| Production service | `service.py` (`DeploymentService`), `lifecycle.py`, `errors.py` |
| Contracts | `schema.py`, `schemas/*.json`, `fixtures/`, `docs/interfaces/` |
| Security | `security.py` (tokens, capabilities, Ed25519 artifacts, AES-GCM sealing, redaction) |
| State | `store.py` (fsync'd, hash-chained, fenced, sealed journal; backup/restore/compact) |
| Resilience | `resilience.py` (deadlines, retry, breaker, admission, stall detection, controls) |
| Config | `config.py`, `deploy/config/` overlays |
| Observability | `observability.py`, `observability/` dashboards + alerts |
| Lattice | `adapter.py` (`InMemoryLattice` fixture, `WadmAdapter` over an injected transport) |
| Evidence | `audit.py`, `gate.py`, `evidence.py`, `perf/`, `release/GATE_POLICY.json` |
| Governance | `OWNERS.yaml`, `CODEOWNERS`, `governance/`, `ops/runbooks/`, `docs/architecture/`, `docs/requirements/` |

## Day-0 / day-1 / day-2

- **Day 0:** `ops/runbooks/DAY0_BOOTSTRAP.md` (`tools/bootstrap.py`: config compose → secret refs → sealed journal → preflight → status).
- **Day 1:** `ops/runbooks/DAY1_DEPLOY.md` + `CANARY_ROLLBACK.md` (tests → bench gate → audit → signed gate; canary rollout with auto-rollback).
- **Day 2:** `ops/runbooks/DAY2_OPERATIONS.md`, `INCIDENT.md`, `BACKUP_RESTORE.md` (status/explain, freeze/quarantine/emergency disable, compaction, backup/restore).

When `pk_core` is installed, `tests/test_component.py` additionally runs the inventory-framework conformance
(`python -m pk_core ...`); without it those tests are skipped and the gate reports G-09 BLOCKED.

## Certification status

Run `audit.py` then `gate.py`. The gate verdict is **BLOCKED**, and it should be: roughly a quarter of the
requirements depend on evidence that only the owners can supply. That evidence is named owners, a pinned and live
Wadm, approved perf thresholds, KMS, node attestation, multi-arch CI, game days, human reviews and a gate signing key.
Every such item is listed with its role in `MISSING_COMPONENTS.md` and `governance/EXTERNAL_EVIDENCE.json`. A missing
`pk_core` is reported as BLOCKED and never treated as a pass.
