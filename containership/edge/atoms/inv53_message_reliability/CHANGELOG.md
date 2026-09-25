# Changelog - INV-53

## 5.1.0 - 2026-09-22

Additive missing-components release (checklist of 96 components). No breaking change to the 5.0.0 API.

### Added
- `durable.DurableQueue`: write-ahead, hash-chained, fsynced journal; replay recovery; torn-tail truncation;
  corruption refusal; fail-stop on write/fsync errors; OS lock + epoch fencing; compaction; backup/restore
  with manifest; durable redrive/purge; idempotent put; explain view.
- `service.Broker`: authenticated, authorized, tenant-isolated data path with freeze/emergency-disable/drain,
  storage circuit breaker, tenant token buckets, load shedding, health/readiness/stall detection.
- `security`: HMAC-SHA256 request signing, key rotation/retirement, principal→key binding, replay protection,
  tenant-scoped grants, fail-closed key providers, hash-chained audit log with external anchoring.
- `protocol` (`inv53.wire/1`), `errors` (`inv53.errors/1`), generated JSON Schemas, 14 conformance fixtures.
- `config`: schema with secure defaults, layered overrides with provenance, atomic CAS updates, rollback.
- `observability`: Prometheus exporter with series cap, redacting structured logs, W3C traceparent.
- `bench`, `gate`, `tools/ci.py`, `tools/lint.py`, `tools/build_release.py`; governance, spec, security,
  architecture, performance, observability and ops documents; restored `MASTER.md`; pinned `pk_core`.

### Changed
- Wire field `now` is deprecated and ignored: the broker times leases with its own clock (a client-chosen
  time could expire another consumer's lease). Relaxing a required field to optional is minor-compatible.
- Wire `health` shows only the caller's tenant.

### Fixed during this pass (13 defects; 3 found by this pass's own tests/self-review, 10 by an adversarial review and re-review, each with a reproducer)
- AuditLog.__init__ leaked a raw OSError (IsADirectoryError) when the sink was unreadable instead of failing closed as SecurityDependencyError — found by test_sink_outage_raises_security_dependency.
- A restarted Broker opened queues lazily only on put, so receive/ack against a queue persisted by the previous process answered OK_EMPTY / E_LEASE_STALE while messages sat on disk. The first version of test_graceful_shutdown_then_restart_preserves_state encoded that behaviour as expected; it was caught on self-review, the test rewritten to demand the correct behaviour, and the broker fixed to reopen any store present on disk.
- Broker._ctl ran outside the typed error handling, so the per-tenant queue limit, a store corrupted on disk before open, and a store held by another live writer all surfaced as E_INTERNAL instead of E_CAPACITY / E_CORRUPT / E_EPOCH_FENCED. Found on self-review; regression test OpenFailureTest added.
- [adversarial review] A crash between compaction's snapshot write and journal reset bricked the store: recovery chain-checked already-folded records against the snapshot head. Fixed (records at or below the snapshot seq are skipped); compaction failure now fail-stops.
- [adversarial review] Removing the last complete journal record, or tampering it and stripping its newline, passed silently as a torn write. Fixed with a clean-shutdown head marker (CLEAN) and an optional external anchored_head; after a crash, tail completeness is reported as provable only by an external anchor.
- [adversarial review] The epoch fast path (stat identity cache) could be bypassed by inode reuse with an equal mtime. Withdrawn; the epoch is read on every append.
- [adversarial review] The wire health op exposed every tenant's queue names and depths. Now filtered to the caller's tenant; deployment-wide fields are operator-only.
- [adversarial review] A client-supplied `now` let any consumer expire another consumer's lease early and burn its attempt budget. The broker now times leases with its own clock; `now` is deprecated and ignored on the wire.
- [adversarial review] A non-object `message.headers` produced E_INTERNAL (retryable). Now E_VALIDATION.
- [adversarial review] Refusals were not side-effect free: a refused put created the queue directory, shed refusals consumed quota tokens, and a quota refusal could strand the breaker's half-open probe. Every refusal is now decided before any state is created or consumed (TokenBucket.peek).
- [adversarial review] The exit gate returned GO for a waived MISSING component with empty CI lanes. Now: all nine lanes required, passing tests required, waivers only for IMPLEMENTED_LOCAL/PARTIAL and only when verified.
- [adversarial review] AuditLog.verify accepted a malformed anchor ({} compared None == None) and crashed on a non-object line. Fixed. Tenant/queue names "." and ".." are now refused.
- [adversarial re-review] compact() and backup() skipped the writer guard, so a closed or fenced writer could rewrite the snapshot over a newer owner's journal (bricking it), and a fail-stopped writer could snapshot untrusted memory over a durable ack. compact() now applies the same closed/fail-stopped/epoch guard as every append.

### Not done (see governance/COMPONENTS.json)
No owners, approvals, KMS, payload encryption, cross-host consensus, INV-52/54 integration, production
telemetry backend, license choice or signed release. The exit gate is NO_GO.

## 5.0.0 - 2026-09-22

Breaking reliability-hardening release.

### Safety fixes

- Replaced message-ID-only settlement with opaque per-delivery lease fencing tokens.
- `ack()` now requires an explicit logical time and rejects expired, unknown, missing-token, and superseded-token acknowledgements.
- Added defensive deep-copy isolation so publisher or consumer mutation cannot corrupt broker-owned redelivery state.
- Reject duplicate active message IDs rather than allowing attempt/in-flight state collisions.
- Dead-letter immediately when a visibility expiration exhausts the attempt cap; dead-letter records now carry a terminal reason and last lease token.
- Added fail-closed capacity checks that preserve the current state transition if the target ready/DLQ capacity is unavailable.
- Added finite numeric validation, stronger message-ID validation, and strict configuration validation.

### Concurrency and bounded state

- Replaced O(n) list head removal with `collections.deque`.
- Added `RLock` protection around queue and deduplication state transitions.
- Added optional ready, in-flight, and dead-letter hard limits.
- Reworked the idempotent consumer into a scoped, bounded, thread-safe reference that raises before admitting an untracked effect when its dedupe set is full.

### Semantics and diagnostics

- Added explicit `Delivery` and `DeadLetter` records.
- Added `nack()` with requeue/terminal disposition.
- Added `extend_visibility()` and explicit `expire()` operations.
- Added a low-cardinality `snapshot()` for ready/in-flight/DLQ depth, redeliveries, acks, rejected acks, NACKs, and tracked attempts.
- Extended the contract threat/failure model to include stale ACKs, caller mutation, capacity exhaustion, and lease-token semantics.

### Verification

- Decoupled package import from `pk_core`: reliability primitives import normally while framework bindings load lazily only when requested.
- Added `tests/test_reliability.py`, runnable without `pk_core`, covering stale and late ACK rejection, mutation isolation, bounded attempts, DLQ transitions, NACK, lease extension, capacity fail-closed behavior, scoped dedupe, validation, and concurrent enqueue safety.
- Retained the 100-item `pk_core` conformance suite, version-pinned to 5.0.0. It remains dependent on an external `pk_core` installation.
- Corrected README auditability: removed the prior claim that a `MASTER.md` file was bundled when it was not.

### Versioning

The major version bump is intentional because secure acknowledgement now requires a lease fencing token and explicit logical time; message-ID-only ACK behavior is no longer accepted.

## 4.1.0 - 2026-09-22

- Replaced optimizer-strippable behavioural assertions with `_verify()` in the `pk_core` component evidence path.
- Added the original conformance test, VERSION file, and basic input validation.
- Removed settled attempt entries to avoid one source of unbounded state growth.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
