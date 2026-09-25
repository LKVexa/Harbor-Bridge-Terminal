# Changelog - INV-52

## 4.3.0 - 2026-09-22

Execution of `inv52_messaging_abstraction_v4.2.0_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST.md` (91 unresolved items) through the junkyard chop shop, work order `INV52-20260922`.

### New modules (stdlib only)

- `resilience.py` — deadlines/cancellation, bounded idempotent retry with full jitter, token-bucket quota admission with per-publisher fairness, circuit breaker + `GuardedSink`, fencing tokens.
- `security.py` — signed caller tokens, tamper-evident audit chain, secret detection/redaction, artifact digest admission (adapted from sibling INV-46) plus the new `TenantBus`: authenticated, capability-scoped, tenant-namespaced facade.
- `config.py` — `PK_MSG_CONFIG/1` declarative config with secure defaults, base/env/site layering, validation, secret rejection, atomic activation, provenance, rollback and health-checked auto-rollback.
- `lifecycle.py` — component state machine, `ManagedBus` with dependency probes (security deps fail closed, noncritical degrade), emergency disable, deterministic `bootstrap`.
- `observability.py` — structured logs with stable ids and release lineage, deterministic sampling that never drops failures, Prometheus exposition with bounded labels, trace helpers, alert classifier, telemetry policy.
- `adapters.py` — CloudEvents 1.0 mapping, Dapr v1.0 HTTP publish adapter, Dapr delivery-status mapping, fault-injection broker, bounded ordered `Outbox`.
- `schemas.py` + five new JSON Schemas; `bench.py`; `gate.py`; `verify_integrity.py`; `tools/cleanroom.py`; `tools/sbom.py`; `__main__.py`.

### Runtime (backward compatible)

- Every error has `retryable`; new codes for frozen/disabled topics, overload, invalid transitions.
- Payload size, JSON depth and topic-count bounds; optional id de-duplication window; topic states ACTIVE/FROZEN/QUARANTINED/DISABLED; admission hook; decision record for every publish and `explain()`; `traceparent` validation/propagation; latency histogram; `health()`; `subscribe()` returns an id; `unsubscribe()`; optional read-only predicate view.
- Behaviour change: a malformed `traceparent` field is now rejected (4.2.0 ignored unknown fields including it).

### Defects found and fixed during this pass

- Replay-cache eviction copied the whole nonce cache on every token verify (O(cache)); inherited from INV-46; found by the per-tenant benchmark (+436 µs → +62 µs p50).
- Deep-nesting check visited every scalar; now visits containers only.
- Dapr 404 (no such pubsub component) was first mapped to retryable; it is a configuration error and is now terminal.
- `INTERFACES.md` omitted `PK_MSG_ARTIFACT_REJECTED` (caught by `test_every_error_code_is_documented`).

### Governance

- 91-row RTM (`governance/requirements.json`, `RTM.md`): 55 EVIDENCED_LOCAL, 20 DOCUMENTED, 16 BLOCKED, 0 IMPLEMENTED.
- Owners, waivers, reviews, threat map, dependencies; gate reports production **NO_GO**.
- 4.2.0 audit files preserved as `*_4.2.0.*`.

## 4.2.0 - 2026-09-22

Second audit, hardening, and evidence-integrity pass.

### Runtime and security fixes

- Split the broker-independent runtime into `runtime.py` so the package can be imported and exercised without the optional `pk_core` audit framework.
- Replaced process-local incremental message IDs with UUID-backed IDs and automatic UTC timestamps when a caller omits `time`.
- Added strict envelope validation plus stable structured error codes/details for topic denial, malformed envelopes, invalid subscriptions, and resource limits.
- Added fail-closed topic/app validation and retained source-spoof prevention.
- Added deep-copy canonical/subscriber isolation so a caller, predicate, or subscriber cannot mutate another subscriber's view.
- Isolated predicate and sink failures so one broken route does not abort unrelated routes.
- Added thread-safe internal state, per-topic route limits, bounded dead-letter retention, eviction accounting, and stable in-process metrics.

### Packaging, interfaces, and tests

- Added `pyproject.toml`, dependency-free package metadata, versioned envelope JSON Schema, interface/security/reliability/versioning documentation, and a runnable example.
- Added standalone unit tests for imports, versioning, envelope uniqueness, authorization, spoofing, routing isolation, copy isolation, limits, dead-letter bounds, and concurrent publishing.
- Changed the optional `pk_core` integration test from claiming all requirements pass to verifying only that all 100 are assessed once; production readiness is now reported separately.
- Corrected stale README claims about a nonexistent `MASTER.md`; README now distinguishes local unit success from production certification.

### Post-update audit

- Added an exhaustive 100-requirement local evidence/gap matrix in `POST_UPDATE_AUDIT.md`, machine-readable `POST_UPDATE_AUDIT.json`, and the action-oriented `MISSING_COMPONENTS.md`.
- Production broker, identity, cryptography, durable reliability, performance lab, observability backend, release governance, and formal gate evidence remain external or missing and are not falsely marked complete.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::PubSub.publish: the envelope source was never compared with the publishing app, so an allowed app could spoof another source, contradicting the "traced back" claim -> a source that does not match the app raises TopicDenied
- component.py::PubSub.publish: a predicate that raised aborted publish partway through delivery -> a failing predicate counts as no match, so the other routes and the dead-letter topic still work

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
