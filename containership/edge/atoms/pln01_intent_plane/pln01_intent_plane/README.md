# PLN-01 - Intent plane

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 02_Synthesis_Planes  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Post-update audit:** `POST_UPDATE_AUDIT.md` and `AUDIT_RESULTS.json`

> **4.3.0** closes the v4.2.0 residual-component checklist (51 components, 969 tasks) as far as a repository can:
> 36 components closed with code + tests, 15 partial pending external systems, staffing or owner approval under
> proposed waivers. The exit gate (`tools/exit_gate.py`) currently returns **NO_GO** only because those waivers
> await approval — see `conformance/EXIT_GATE.json`. `MASTER.md` is now present (reconstructed; see its provenance note).

## What 4.3.0 adds

| Area | Module / artifact |
|---|---|
| Production request path (auth → authz → controls → lease → quota → bulkhead → secrets → precedence → artifacts → admission → WAL → audit) | `service.py` |
| Interface schemas + validator + fixtures; stable error codes | `schemas/`, `validation.py`, `errors.py`, `tests/fixtures/` |
| Config overlays with provenance | `config.py` |
| Quotas, deadlines, retries, bulkhead, circuit breaker, freeze/quarantine/disable | `controls.py` |
| Authn (fail-closed), capabilities, artifact trust, key rotation | `trust.py` |
| Secret refusal and redaction | `secret_guard.py` |
| Durable WAL + snapshots, sealed audit, backup/restore, migration, fenced lease | `store.py` |
| Metrics, JSON logs, W3C tracing, health/readiness | `telemetry.py` |
| Constraint precedence | `precedence.py` |
| Governance, ADRs, requirements, runbook, alerts | `docs/`, `governance/`, `ops/`, `MASTER.md` |
| Gates: tests (normal and -O), perf, manifest/SBOM, exit gate | `tools/` |

The intent plane holds desired estate state as a live dependency graph instead of disconnected Terraform state and Kubernetes YAML. It accepts declarations, resolves them into a deterministic dry-run reconciliation plan, and hands that plan to downstream planes. It deliberately never executes plan steps.

## Responsibility

Own the authoritative desired-state graph for the estate, admit or reject declarations against local boundary rules and optional policy, and emit a dependency-ordered, dry-runnable reconciliation plan for downstream planes to execute.

## Hardened core in 4.2.0

The standard-library-only `graph.py` module now provides:

- strict node/dependency validation and defensive copying of untrusted specs;
- same-tenant **and same-environment** dependency isolation;
- deterministic O(V+E log V) topological ordering;
- optimistic concurrency through `expected_version`;
- bounded replay protection through `request_id`;
- bounded graph, dependency, spec, history, replay, and audit capacities;
- idempotent declarations that do not spuriously advance graph version;
- dependency-safe retraction with explicit cascading;
- bounded delta history, deterministic diffing, and rollback as a new monotonic version;
- thread-serialized graph mutations and atomic stale-writer checks;
- hash-chained in-memory audit events with a bounded retention window;
- deterministic dry-run plan fingerprints (`plan_id`);
- standalone unit tests that run without `pk_core`.

Since 4.3.0, authentication, durable storage, artifact verification and telemetry are implemented around this core (table above). Distributed consensus, at-rest encryption/KMS, and external audit anchoring are still open (`governance/WAIVERS.json`).

## Core API

```python
from pln01_intent_plane import IntentGraph, plan

graph = IntentGraph()
network = graph.declare(
    "tenant-a", "prod", "network", {"cidr": "10.0.0.0/16"},
    expected_version=0, request_id="chg-0001", actor="operator@example",
)
app = graph.declare(
    "tenant-a", "prod", "app", {"image": "svc:1"}, after=[network],
    expected_version=1, request_id="chg-0002", actor="operator@example",
)

dry_run = plan(graph, actual={})
assert dry_run["dry_run"] is True
```

## Owns

- The desired-state graph and its schema
- Declaration admission and validation
- Dependency resolution and plan ordering
- Drift detection against reported actual state
- Plan versioning, diffing, and rollback targets

## Explicitly does not own

- Execution of any plan step
- Workload placement decisions
- Runtime or node lifecycle
- Data-plane transport
- Secret material

## Non-goals

- Executing plan steps
- Acting as a general-purpose configuration database
- Reconciling state the estate does not declare
- Replacing GitOps as the change entry point

## Interfaces

- `declare` - `PK_DECLARATION/1` - submit or retract a declaration
- `graph` - `PK_INTENT_GRAPH/1` - read-only node and edge projection
- `plan` - `PK_RECONCILIATION_PLAN/1` - dependency-ordered plan with dry-run results
- `report` - `PK_ACTUAL_STATE/1` - reported actual state ingested for drift detection

JSON Schemas for every interface are in `schemas/` and are enforced at the service boundary (`docs/INTERFACES.md`).

## Service-level objectives

- **plan latency** - p99 plan emission under 2 s for graphs up to 10k nodes (error budget: 0.5% of plans may exceed)
- **admission correctness** - zero admitted declarations violating policy (error budget: no budget; any breach is a blocker)
- **drift detection** - drift surfaced within one reconciliation interval of a report (error budget: 1% of reports may lag one interval)

## Verification

From the directory that contains this package:

```text
python pln01_intent_plane/tools/run_checks.py     # all suites, normal and -O
python pln01_intent_plane/tools/perf_gate.py      # benchmark + regression gate
python pln01_intent_plane/tools/exit_gate.py      # build archive, re-test from archive, emit decision
```

All suites run on the standard library alone. If `pk_core` is installed (or `PK_CORE_PATH` points to it), the additional monorepo conformance tests activate automatically:

```text
python -m pk_core list
python -m pk_core run PLN-01 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-01 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

The source archive does not bundle `pk_core`, so those integration/gate commands cannot be certified from this standalone repository alone.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the standard-library core and run its tests; in the complete monorepo, import `pk_core` and establish the first evidence ledger.
- **Day 1 (deployment):** in the complete monorepo, run the production gate and refuse rollout on a `NO_GO` result; record any accepted conditions explicitly.
- **Day 2 (operation):** re-run conformance on every contract or implementation change and preserve evidence-chain continuity.

Rollback inside the local graph restores a retained state as a new monotonically increasing version. Durable backup/restore, crash recovery and fenced failover: `docs/RUNBOOK.md`.
