# INV-04 Current Orchestration — Audit Report

**Audited input version:** 4.1.0  
**Hardened output version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** archive structure, Python model semantics, failure atomicity, deterministic behavior, validation, interface artifacts, tests, version consistency, documentation integrity, and residual production gaps.

## Executive result

The v4.1.0 archive was syntactically valid but had a material state-safety defect in `Cluster.drain()`: the method removed a node and its resident pods before calling `reconcile()`. If reconciliation then raised `NoCapacity`, the drain failed **after** destructive mutation, leaving the in-memory cluster in a partially drained state. The reconcile path also validated desired counts incrementally, allowing an invalid later workload to fail only after earlier workloads had already been modified.

Version 4.2.0 replaces those mutation paths with plan-then-commit semantics, strengthens state/configuration invariants, separates the dependency-free orchestration model from the optional `pk_core` conformance adapter, adds standalone optimized-mode tests, supplies concrete v1 JSON Schemas for the declared interfaces, and removes a false README claim about an absent `MASTER.md` file.

## Findings and disposition

### F-01 — Drain failure was not atomic — **High — Fixed**

**v4.1 behavior:** `Cluster.drain()` removed the node and victim pods, then invoked `reconcile()`. A `NoCapacity` exception could therefore leave state mutated even though the drain failed.

**v4.2 correction:** drain now validates, evaluates disruption budgets, constructs post-drain copies, proves reconciliation on the copies, and commits `nodes`/`pods` only after the complete plan succeeds.

**Verification:** `test_no_capacity_drain_is_atomic` and `test_budget_breach_is_atomic`.

### F-02 — Reconcile validation could fail after partial mutation — **High — Fixed**

**v4.1 behavior:** desired counts were validated one workload at a time inside the mutating loop. A valid early workload could be scaled before a later invalid count raised an exception.

**v4.2 correction:** all node, desired, budget, and observed-pod invariants are validated before planning; the plan is built on a copy and committed only after successful completion.

**Verification:** `test_invalid_desired_is_rejected_before_any_mutation`.

### F-03 — Core safety tests were effectively optional — **High — Fixed for model; integrated gate still external**

**v4.1 behavior:** all three shipped tests lived under a class skipped when `pk_core` was unavailable. In the audit environment the test command reported `OK (skipped=3)`, so no runtime orchestration behavior was exercised.

**v4.2 correction:** `model.py` has no `pk_core` dependency and `tests/test_model.py` always runs. The estate conformance adapter remains optional and its integration tests still skip when `pk_core` is not installed.

**Audit limitation:** the 100-item `pk_core` assessment could not be independently executed in this archive because `pk_core` was not included or importable.

### F-04 — README referenced a nonexistent `MASTER.md` — **Medium — Fixed**

**v4.1 behavior:** README asserted that `MASTER.md` and 100 per-item master prompt/workflow documents were carried in the package, but no such file existed.

**v4.2 correction:** the false completeness claim is removed and the missing master-prompt corpus is recorded as a residual artifact gap if the distribution is expected to contain it.

### F-05 — Insufficient configuration and state-integrity validation — **Medium — Fixed**

v4.2 now rejects:

- duplicate or blank node names;
- negative, boolean, or non-integer replica/budget counts;
- `min_available` for unmanaged workloads;
- `min_available` greater than desired replicas;
- malformed pod tuples;
- pods on unknown nodes;
- running workloads absent from desired state, which a drain could otherwise silently evict without a reconstruction source.

### F-06 — Workload planning depended on mapping insertion order — **Medium — Fixed**

**v4.1 behavior:** reconcile iterated `desired.items()`. When several workloads scaled simultaneously, node placement could vary with dictionary construction order.

**v4.2 correction:** planning iterates sorted workload names and uses deterministic node-load/name tie-breaking.

### F-07 — Interface failures had no stable machine-readable error code — **Medium — Fixed at model layer**

v4.2 exceptions expose stable codes (`ORCH_CONFIGURATION_INVALID`, `ORCH_STATE_INTEGRITY`, `ORCH_BUDGET_BREACH`, `ORCH_UNKNOWN_NODE`, `ORCH_NO_CAPACITY`, `ORCH_RUNTIME_ERROR`) via `as_dict()`.

A transport-specific HTTP/gRPC/Kubernetes Status mapping is still missing.

### F-08 — Declared versioned interfaces had no concrete schemas — **Medium — Fixed at logical-contract layer**

v4.2 adds JSON Schema 2020-12 artifacts for:

- `PK_ORCH_RECONCILE/1`;
- `PK_ORCH_DRAIN/1`;
- `PK_ORCH_INVENTORY/1`;
- `PK_ORCH_ERROR/1`.

Runtime schema validation and generated client/server bindings are still missing.

### F-09 — Production orchestration parity is much broader than the in-memory model — **High — Open by design**

The reference model does not implement real Kubernetes watches, eviction APIs, controller queues, resource versions, leader election, native PodDisruptionBudget semantics, workload-kind-specific behavior, persistent state, or production telemetry. These are enumerated in `MISSING_COMPONENTS.md` and must not be inferred as implemented merely because a checklist item has descriptive contract text.

## Validation performed on v4.2.0

- Python bytecode compilation: **PASS**.
- Dependency-free model tests: **12/12 PASS**.
- Dependency-free model tests under `python -O`: **12/12 PASS**.
- JSON parse validation of all four interface schemas: **PASS**.
- Version synchronization (`VERSION`, `__version__`, component conformance test): **PASS**.
- Estate-level `pk_core` tests: **NOT EXECUTED; 3/3 skipped because `pk_core` is not present in the archive/audit environment**.

## Hardening characteristics after the pass

- Mutation failures are atomic at the in-memory model boundary.
- Model behavior is deterministic for the same state and desired configuration.
- Invalid observed state fails closed instead of being silently normalized.
- Core tests no longer depend on the estate framework.
- Optimized Python mode does not remove behavioral verification.
- Public logical contracts have versioned schema artifacts.
- Error classes expose stable machine-readable identifiers.
- Documentation no longer claims absent source artifacts are included.

## Residual risk

The package remains a **reference behavior model**, not a production orchestrator/controller. Its strongest unresolved risks are integration/concurrency correctness, true Kubernetes disruption semantics, persistent controller state, security boundaries, observability/SLO measurement, failure recovery, and evidence quality at the `pk_core` gate. See `MISSING_COMPONENTS.md` for the prioritized implementation inventory.


# Addendum — v4.3.0 missing-components pass (2026-09-22)

**Input:** `INV04_v4.2.0_Missing_Components_Professional_Checklist.md` (80 components, about 1,700 checklist lines).

**Result:** a stdlib-only `runtime/` layer, 106 dependency-free tests, release tooling, and governance artifacts. Component state is recorded in `COMPONENT_STATUS.json`.

## Findings closed or reduced

- **F-07** (no transport error mapping): **fixed**. See `runtime/errors.py::TRANSPORT_MAP` and `runtime/service.py::problem`.
- **F-08** (no runtime schema validation): **fixed**. See `runtime/validation.py`, with 19 fixtures.
- **F-09** (production parity): **reduced, still open**. Watches, work queue, resourceVersion CAS, leader election with fencing, persistent journal, PDB semantics, workload-kind policies and telemetry now exist as tested reference implementations. The real Kubernetes adapter, real-cluster matrix, mTLS, IdP integration and signing remain `OPEN_EXTERNAL`.

## New findings in this pass

- **F-10, simulator defect (fixed).** The in-memory controller used live pods as the template, so a workload whose last replica was evicted was never recreated. The parity harness found it. Templates are now held per controller.
- **F-11, semantic decision (documented, ADR-0001 §5).** Budget preflight keeps v4.2 parity: a drain is refused when off-node healthy pods are already below desiredHealthy. This is stricter than `kubectl drain`'s evict-and-wait loop.
- **F-12, authorization scope (fixed).** Node drain is cluster-scoped, so the default RBAC grants `drain` only to `inv04:site-operators` and never through a tenant's own-scope rule.

## Validation performed on v4.3.0 (this environment: CPython 3.11, Linux)

- All 9 test modules: 106 tests run, 103 pass and 3 are skipped (`pk_core` conformance, which is absent) under both normal and `python -O`.
- `ruff check` (E, F, W, B, S): clean. `mypy` on the runtime: clean. `tools/lint_gate.py`: OK.
- `tools/evidence_gate.py`: OK (80 components; 0 PASS claims).
- `tools/release.py --verify`: OK.
- `tools/bench.py` (50 nodes / 1,000 pods): see the work-order `05-APPLIED.md`. These numbers are not release evidence.

## Residual risk

This is still not a production controller. It becomes one only after the `OPEN_EXTERNAL` items are integrated and the `OPEN_GOVERNANCE` items get named owners. `docs/OWNERS.md` has every role UNASSIGNED.
