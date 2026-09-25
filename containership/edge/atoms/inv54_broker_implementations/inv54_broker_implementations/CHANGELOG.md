# Changelog - INV-54

## 4.3.0 - 2026-09-22

Missing-component overhaul against `INV54_v4.2.0_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST.md`
(100 components, junkyard chop-shop pass). Reference brokers unchanged; everything below is additive.

### Added
- Production layer, stdlib-only: `errors.py` (stable `INV54-E*` code namespace + outcome taxonomy),
  `lifecycle.py` (legal-transition state machine, quarantine), `resilience.py` (deadlines, cancellation,
  bounded retry with full jitter, idempotency cache, circuit breaker, token bucket, admission control),
  `config.py` (schema, fail-closed validation, overlays, provenance, CAS commit, rollback, secret refs),
  `security.py` (HMAC tokens with replay protection + key rotation, deny-by-default grants, tenant checks,
  HMAC hash-chained audit, artifact digest allow-list), `quota.py`, `negotiation.py`, `telemetry.py`
  (metrics with cardinality cap, JSON logs with redaction, W3C trace context, decision log + explain),
  `storage.py` (durable CRC-framed log, crash recovery, retention, compaction, AES-256-GCM at rest,
  backup/restore), `ha.py` (quorum replication, leases, epoch fencing, residency-aware failover),
  `service.py` (multi-tenant `BrokerService` composing all of the above; `OfflineBuffer`).
- Provider adapters: Kafka (confluent-kafka), RabbitMQ (pika), AWS SQS (boto3) with error translation;
  shared conformance suite; reference adapters.
- Schemas (generated, drift-checked), config base + overlays, benchmark harness + gate, CI workflow,
  ownership/ADR/requirements/threat-model/runbook/incident/SLO/rollout/waiver documents, evidence generator.

### Fixed (found by this pass's own tests)
- Name validation used `re.match` with `$`, so `"orders\n"` passed; all grammars now use `fullmatch`.
- `BrokerService._size` serialised with `default=str`, so non-JSON payloads were silently accepted.
- `config.validate` raised `AttributeError` when a section was not an object (property test); it now
  reports a problem instead.
- Test fake for RabbitMQ redelivered unacked messages inside the same fetch (double delivery);
  corrected to broker semantics (redeliver only after nack/requeue or channel loss).

### Not done (see `evidence/component_status.json`)
- No real Kafka/RabbitMQ/SQS certification, no pk_core run, no edge-hardware or soak data,
  no backup owner/on-call, no license decision, no independent review. Production exit gate: NO_GO.

## 4.2.0 - 2026-09-22

Second-pass audit, correctness fixes, hardening, test expansion, and repository-gap audit.

### Correctness and hardening

- Extracted dependency-free broker primitives to `brokers.py`; package import no longer eagerly requires external `pk_core`.
- Fan-out now creates independent deep copies per subscriber and is failure-atomic if a message cannot be copied.
- Internal broker state is no longer constructor-injectable, and the partition-count configuration cannot be rebound after construction.
- Added strict validation for subscriber/consumer identifiers, keys, partition indices, limits, offsets, and partition count; `bool` is rejected where an integer index/count is required.
- Added in-process locking around shared mutable broker state and explicit `unsubscribe`, `committed_offset`, and `end_offset` helpers.
- Preserved compatibility: `FanoutBroker` and `PartitionedLog` remain importable from `component.py` while also being exported by the package.

### Verification and audit

- Added dependency-free behavioural tests covering alias isolation, atomic failure, constructor-state injection, validation, replay/offset independence, and concurrent append integrity.
- Corrected README drift: the archive does not contain `MASTER.md`; `CHECKLIST.json` is the shipped audit source.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md` with the second-pass findings.
- External `pk_core` conformance remains supported but cannot be independently re-certified when `pk_core` is not supplied.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::PartitionedLog.poll/seek: a negative partition silently read another partition through Python negative indexing -> _check_partition raises IndexError
- component.py::PartitionedLog.poll: a negative limit returned the wrong slice and moved the offset -> this now raises ValueError
- component.py::PartitionedLog.__post_init__: partitions < 1 caused ZeroDivisionError later -> it is now validated up front

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
