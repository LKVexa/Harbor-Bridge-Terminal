# INV-31 — Function execution architecture

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-31 models the request-scoped lifecycle of function instances. An invocation receives an instance, runs within a tenant-and-version-bound lifecycle, and leaves no invocation-scoped scratch state behind. Warm reuse is permitted only when tenant and code version match exactly.

## Responsibility

Own function-instance lifecycle around a single invocation: make the warm-versus-cold decision, enforce exact tenant/version reuse, bound per-instance concurrency and total pool growth, clear invocation-scoped state, expose a bounded pool view, and retire unsafe or aged instances.

## Runtime hardening in 4.2.0

- The lifecycle engine is isolated in `runtime.py` and is testable without the external `pk_core` framework.
- Concurrent invocations receive separate scratch scopes; one invocation cannot clear another invocation's state.
- Instance identity (`name`, `tenant`, `version`, `created_at`) becomes immutable after creation.
- Pool and instance state transitions are guarded by re-entrant locks.
- Pool growth is bounded by `max_instances`; a fully busy pool fails closed with `PoolCapacityExceeded`.
- Identifier length/control-character checks and strict non-negative integer time validation are enforced.
- Clock rollback is fail-closed for warm reuse: idle negative-age instances are destroyed.
- `destroy_idle()` provides a safe drain/quarantine primitive without killing in-flight work.
- `pool_snapshot()` implements the `PK_FUNCTION_POOL/1` diagnostic surface without exposing scratch contents.
- Every invocation returns a stable `decision_reason` explaining warm versus cold selection.

## Remediation in 4.3.0

4.3.0 applies the *INV-31 v4.2.0 Comprehensive Missing-Component Remediation Checklist*
(85 items). Status per item, with evidence and named blockers, is in
`REMEDIATION_STATUS.json`: **36 IMPLEMENTED_UNREVIEWED · 37 PARTIAL · 12 BLOCKED · 0 DONE**,
production gate **NO_GO**. `POST_AUDIT.json` is the unmodified 4.2.0 audit.

New layers (all standard-library only):

- `boundary.py` — `Gateway`: HMAC-signed caller assertions (keys injected, none built in),
  capability/tenant authorization, replay refusal, idempotency keys, deadlines and
  cancellation, per-tenant quotas, critical vs noncritical dependency handling, hash-chained
  audit, structured pseudonymous logs, W3C trace context, metrics, health, explain,
  emergency disable; `bounded_retry` with full-jitter backoff.
- `errors.py` — stable `PK_INV31_ERROR/1` codes.
- `config.py` — declarative `PK_INV31_CONFIG/1`, whole-generation activation, provenance,
  automatic and operator rollback.
- `adapters.py` — Protocols for PLN-04 / INV-26 / PLN-05 / GAP-09 plus reference *test doubles*.
- `pkcompat.py` — the package now imports without `pk_core`; absence/incompatibility is
  `INV31-E-PKCORE-UNAVAILABLE`.
- `tools/bench.py`, `tools/make_evidence.py`, `ci.sh`, `pyproject.toml`, `docs/`.

Run everything: `sh ci.sh` (clean-venv install, tests normal and `-O`, schemas, bench, evidence).

## Public interfaces

- `PK_INVOCATION/1` — returned by `FunctionPool.invoke()`; schema: `schemas/PK_INVOCATION_1.schema.json`.
- `PK_FUNCTION_POOL/1` — returned by `FunctionPool.pool_snapshot()`; schema: `schemas/PK_FUNCTION_POOL_1.schema.json`.

The public Python runtime types are `FunctionPool`, `Instance`, `ConcurrencyExceeded`, `PoolCapacityExceeded`, `InstanceDestroyed`, and `InstanceExpired`.

## Defaults

- `CONCURRENCY_LIMIT = 4`
- `MAX_AGE = 300` logical ticks
- `MAX_POOL_INSTANCES = 1024`
- maximum identifier length = 256 characters

These are defaults, not deployment targets. `FunctionPool` accepts validated runtime overrides for concurrency, age, and pool size. Capacity planning remains outside this component's production ownership.

## Running validation

From the directory that contains this package:

```text
python inv31_function_execution_architecture/tests/test_component.py -v
python -O inv31_function_execution_architecture/tests/test_component.py -v
python -m compileall -q inv31_function_execution_architecture
```

The standalone runtime and remediation tests require only Python (`python -B tests/test_remediation.py`). The 100-item framework conformance tests additionally require the external `pk_core` package. If it is stored elsewhere, set `PK_CORE_PATH` before running the test file.

When `pk_core` is available, the parent system can also run its normal commands, for example:

```text
python -m pk_core list
python -m pk_core run INV-31 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-31 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Scope and non-goals

This package owns the lifecycle/reuse decision. It does **not** implement the isolation tier, scheduler/placement, routing/load balancing, function source execution engine, identity provider, KMS, control-plane transport, or elasticity controller.

Cross-tenant instance sharing, persistent invocation state, and guaranteed warm starts are explicit non-goals.

## Packaging note

The previous README stated that `MASTER.md` was bundled. It is not present in the supplied archive, so that claim has been removed rather than reconstructing source material that was not provided. The post-hardening gap inventory is in `MISSING_COMPONENTS.md`, with machine-readable status in `POST_AUDIT.json`.

## Day 0 / day 1 / day 2

- **Day 0:** run the standalone tests; provide `pk_core`; run the framework gate; archive the evidence ledger.
- **Day 1:** deploy through the parent platform only after dependency, schema, security, and compatibility prerequisites are satisfied.
- **Day 2:** re-run standalone and framework gates on every change; drain unsafe idle instances with `destroy_idle()` and roll back through the parent release system when necessary.

The parent platform remains responsible for rollout orchestration, evidence sealing, external telemetry export, and release rollback.
