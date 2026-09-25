# INV-04 — Current orchestration

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`; 80 missing-component states in `COMPONENT_STATUS.json`

INV-04 is the reference model for the incumbent orchestration behavior that a successor scheduler must preserve during migration. It models desired replica reconciliation, maintenance drains, disruption-budget enforcement, and deterministic workload inventory for hand-off.

## Responsibility

Own the behavioral model of the incumbent orchestrator: replica reconciliation, atomic node drain with disruption budgets, and the hand-off surface to a successor scheduler.

## Owns

- Replica reconciliation model.
- Atomic node-drain procedure.
- `min_available` disruption-budget enforcement.
- Workload inventory snapshot for hand-off.
- Behavioral parity hooks for the estate-level `pk_core` conformance framework.
- Versioned JSON Schemas for the three exposed logical interfaces.

## Explicitly does not own

- Cluster provisioning.
- Kubernetes/API-server operation.
- Networking, CNI, service mesh, or ingress implementation.
- Image construction or registry operation.
- Successor-platform scheduling.
- The production Kubernetes API adapter (official-client implementation of `runtime/api.py::ClusterAPI`), mTLS termination, and the identity provider. These are integration points; see ADR-0001.

## Runtime model

The dependency-free model is in `model.py`. Mutating operations use **plan-then-commit** semantics: configuration, state-integrity, budget, and capacity checks complete against copies before the live in-memory state is changed. A rejected reconcile or drain therefore leaves the cluster unchanged.

Important invariants enforced by v4.2.0:

- Node names are unique, non-empty strings.
- Desired replica and disruption-budget values are non-negative integers; booleans are rejected.
- `min_available` may not reference an unmanaged workload or exceed its desired count.
- Running pods may not reference unknown nodes or unmanaged workloads.
- Reconciliation is deterministic across workload dictionary insertion order.
- A node drain is atomic if a disruption budget blocks it or if no remaining node can host required replacement replicas.
- Failures expose stable machine-readable codes through `as_dict()`.

## Interfaces

| Interface | Purpose | Schema |
|---|---|---|
| `PK_ORCH_RECONCILE/1` | Desired-versus-running state input | `schemas/PK_ORCH_RECONCILE_v1.schema.json` |
| `PK_ORCH_DRAIN/1` | Budget-respecting drain request | `schemas/PK_ORCH_DRAIN_v1.schema.json` |
| `PK_ORCH_INVENTORY/1` | Workload-to-node hand-off snapshot | `schemas/PK_ORCH_INVENTORY_v1.schema.json` |
| `PK_ORCH_ERROR/1` | Stable error envelope | `schemas/PK_ORCH_ERROR_v1.schema.json` |

These schemas define the logical wire contracts. A production transport/API adapter is intentionally not included in this inventory component and is listed in `MISSING_COMPONENTS.md`.

## Service-level objectives declared by the contract

- **Availability:** zero drains that breach a disruption budget.
- **Convergence:** replicas match desired state within 30 seconds, with a 1% exceedance budget.
- **Inventory completeness:** every running managed workload is included in hand-off inventory.

The current package models the behavior but does **not** itself provide clocks, metrics emission, durable SLO accounting, or production telemetry. Those remain implementation gaps.

## Testing

Dependency-free safety tests always run:

```text
python inv04_current_orchestration/tests/test_model.py
python -O inv04_current_orchestration/tests/test_model.py
```

Estate-level conformance tests require `pk_core`:

```text
python inv04_current_orchestration/tests/test_component.py
python -O inv04_current_orchestration/tests/test_component.py
```

If `pk_core` is not importable, only the conformance tests are skipped; the core orchestration tests still execute. Set `PK_CORE_PATH` when the framework is stored outside the import path.

Typical integrated commands are:

```text
python -m pk_core list
python -m pk_core run INV-04 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-04 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Audit artifacts

- `AUDIT_REPORT.md` — findings, applied fixes, validation evidence, and residual risk.
- `MISSING_COMPONENTS.md` — prioritized components still required for production-grade current-orchestrator parity.
- `CHECKLIST.json` — original 100-item requirements inventory.

The previous README referenced a `MASTER.md` file that was not present in the archive. v4.2.0 removes that false completeness claim rather than fabricating missing master-prompt content.

## Day 0 / Day 1 / Day 2

- **Day 0:** import the package, run the dependency-free tests, then run `pk_core run INV-04` in an integrated estate and archive the emitted evidence ledger as baseline evidence.
- **Day 1:** run `pk_core gate INV-04`; do not treat a local model-only pass as proof of production Kubernetes interoperability.
- **Day 2:** re-run the gate on every contract or implementation change, verify the evidence chain, and exercise failure/rollback paths in an environment that includes the real orchestration adapter.

## Production runtime layer (v4.3.0)

`runtime/` is a stdlib-only implementation of the 80 components in `MISSING_COMPONENTS.md` wherever they can be built inside the package. Components that need an external system are exposed as typed ports with in-memory reference implementations. The live state of each component is in `COMPONENT_STATUS.json`, which `tools/evidence_gate.py` checks.

| Area | Module |
|---|---|
| API port, discovery, reference API server with Eviction semantics | `runtime/api.py` |
| Versioned store (CAS), informer (list/watch/relist/tombstones) | `runtime/store.py` |
| Work queue, leader election and fencing | `runtime/workqueue.py`, `runtime/lease.py` |
| Journal, idempotency, audit trail | `runtime/journal.py` |
| PDB evaluator, pod/node policy | `runtime/policy.py` |
| Capacity, constraints, preemption | `runtime/scheduling.py` |
| Drain transaction coordinator and crash recovery | `runtime/drain.py` |
| Schema validation, negotiation | `runtime/validation.py` |
| AuthN/Z, admission, tenancy, quotas, secrets | `runtime/security.py` |
| Hand-off snapshot/stream/ack/ownership | `runtime/handoff.py` |
| Config load/provenance/rollback | `runtime/config.py` |
| Metrics, logs, traces, health, SLO, alerts | `runtime/observability.py` |
| Deadlines, retry, rate limit, breaker, stall | `runtime/resilience.py` |
| HTTP service | `runtime/service.py` |

Run everything (no network, no third-party packages):

```text
for t in inv04_current_orchestration/tests/test_*.py; do python "$t" && python -O "$t"; done
python inv04_current_orchestration/tools/evidence_gate.py
python inv04_current_orchestration/tools/lint_gate.py
python inv04_current_orchestration/tools/pk_core_gate.py      # fails until pk_core is supplied
python inv04_current_orchestration/tools/release.py --out dist && python inv04_current_orchestration/tools/release.py --out dist --verify
```

Governance: `docs/ADR-0001-runtime-architecture.md`, `docs/ADR-0002-master-corpus.md`, `docs/THREAT_MODEL.md`, `docs/RUNBOOK.md`, `docs/OWNERS.md`, `docs/ROLLBACK.md`, `docs/TRACEABILITY.md`.

## Limitations

No component is PASS. `OPEN_EXTERNAL` items need systems this package cannot contain: the official-client Kubernetes adapter, a kind/k3s integration matrix, mTLS, an OIDC/JWKS identity provider, an external secret manager, an OTLP exporter, a signing identity, pk_core, and the SCH-01 successor. `OPEN_GOVERNANCE` items need named owners and approvers; every role in `docs/OWNERS.md` is currently UNASSIGNED. The v4.2.0 `model.Cluster` remains the behavioural reference, and the v4.3.0 runtime is checked against it by the parity harness.
