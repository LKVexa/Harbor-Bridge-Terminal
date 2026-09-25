# ADR-0001: Wadm as the downstream control plane for the INV-63 deployment manager

| Field | Value |
|---|---|
| Document ID | INV63-ADR-0001 |
| INV-63 C-IDs covered | C010 (with C001, C004, C031) |
| Status | DRAFT — pending approval. ADR status: **Proposed** |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Architecture reviewer (role), Security reviewer (role), SRE lead (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change (including a Wadm pin in `pins.json` or a new adapter). |

## Context
INV-63 owns desired-state storage, diff computation, spread across host labels, idempotent convergence and bounded-unavailability rollouts (`contract.py::build`). It does **not** run components, define manifests, sign artifacts or provision hosts. It needs a downstream actuator for INV-60 (Wasm application fabric) on a wasmCloud lattice.

## Decision
- Actuate through Wadm using OAM `core.oam.dev/v1beta1` `Application` manifests with a `spreadscaler` trait, rendered by `adapter.py::wadm_manifest` and sent by `adapter.py::WadmAdapter` (which implements `ping`, `deploy`, `list_instances`, `start`, `stop`, `healthy`, `capabilities` as transport ops) over an **injected** transport (NATS / `wash app deploy` in production; not bundled).
- The service depends only on the `adapter.LatticeAdapter` protocol (`ping`, `list_instances`, `start`, `stop`, `healthy`); `adapter.InMemoryLattice` is the conformance/fault-injection fixture.
- Wadm version: **UNPINNED** (`pins.json` → `wadm.version = "UNPINNED"`, `digest: null`, `approved: false`). Without a transport `WadmAdapter._send` raises `INV63-E-DEPENDENCY-UNAVAILABLE` and `ping()` returns False.

## Alternatives considered

| Option | Pros | Cons | Verdict |
|---|---|---|---|
| Kubernetes controller (CRD + operator) | mature reconcile tooling, RBAC, etcd | requires K8s on every edge site; not native to wasmCloud lattice; heavy for far-edge | rejected |
| HashiCorp Nomad | lightweight scheduler, multi-region | second scheduler competing with lattice placement; Wasm drivers immature | rejected |
| Bespoke scheduler talking to hosts | full control | duplicates Wadm; larger attack surface; must reimplement lattice discovery | rejected |
| Direct wasmCloud host API (per-host start/stop) | no Wadm dependency; fine-grained | loses Wadm's own reconciliation; INV-63 would own per-host liveness; more calls per action | retained as possible future adapter (the `LatticeAdapter` protocol allows it); not chosen |
| **Wadm OAM via adapter** | native to lattice; declarative; spreadscaler matches spread model | external unpinned dependency; two reconcilers in series (INV-63 and Wadm) | **chosen** |

## Boundaries
See `docs/architecture/BOUNDARIES.md` and `docs/interfaces/BOUNDARIES.json` (B-10 lattice adapter; B-11 state journal). INV-63 decides; Wadm/INV-60 execute.

## Data ownership
- Source of truth: the journaled desired-state record (`store.py::Journal`, `journal.jsonl`, records `desired_set`/`desired_deleted`). Lattice state is observed (`service.py::_observe` → `manager.actual`) and corrected toward it.
- Wadm's stored application is a derived projection; on disagreement INV-63 wins at next reconcile.
- Controller leadership: `epoch` file fencing in `state_dir` (`Journal.acquire` / `append`).

## Failure model
- Lattice/Wadm unreachable: degrade within `offline_autonomy_s` (intent journaled, outcome `DEGRADED`); beyond it `INV63-E-CONTROL-PLANE-OFFLINE` (RETRYABLE). Rollouts refused while offline.
- Start failures: `PARTIAL`, lifecycle `DEGRADED`, same-version stops skipped to keep capacity.
- Rollout health failure: automatic rollback (`service.py::_rollback`), `INV63-E-ROLLOUT-FAILED`.
- Retries bounded (`RetryPolicy`, `retry_max_attempts`), circuit breaker (`circuit_failure_threshold`, 10 s reset).
- Stale controller: `INV63-E-STALE-EPOCH`. Full matrix in `FAILURE_MATRIX.md`.

## Acceptance criteria
1. Wadm release and digest pinned and approved in `pins.json` (open).
2. Conformance tests pass against a live Wadm (evidence key `wadm-live`, open); today only `tests/test_contracts.py::CompatibilityTest::test_wadm_manifest_rendering` checks manifest shape.
3. Second reconcile after convergence emits zero actions (`tests/test_service.py::SemanticsTest::test_desired_reconcile_converges_and_rests`) — passes against `InMemoryLattice` only.
4. Rollout never exceeds `max_unavailable` (`tests/test_service.py::RolloutTest::test_canary_then_bounded_batches`).
5. Architecture review sign-off (evidence key `arch-review`, open).

## Consequences
- Production readiness is blocked on an external, currently unpinned Wadm.
- Two reconcilers in series: Wadm spreadscaler weights (`100 // len(spread_labels)`) must not fight INV-63 per-host placement; `WadmAdapter` satisfies `LatticeAdapter`, but the transport op semantics are unverified against a real Wadm (open, `wadm-live`).
- Swapping actuators is contained to `adapter.py`.
