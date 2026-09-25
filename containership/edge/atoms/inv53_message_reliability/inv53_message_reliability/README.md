# INV-53 - Message reliability

**Version:** 5.1.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-53 defines message-delivery reliability semantics: at-least-once delivery, visibility leases, bounded attempts, dead-lettering, and consumer-side deduplication. The included `ReliableQueue` is a **framework-independent, in-memory semantic reference**, not a durable production broker. Durable persistence, replication, distributed ownership, and broker integration remain downstream responsibilities.

## 5.0.0 safety model

A delivery is represented by `Delivery(message, lease_id, deadline, attempt)`. `lease_id` is an opaque fencing token. The queue rejects an acknowledgement when the token is missing, stale, superseded by a redelivery, or expired at the supplied logical time. This prevents an old consumer from settling a newer delivery of the same message.

The reference implementation also provides:

- defensive copy isolation for accepted and delivered messages;
- active-message ID collision rejection;
- finite numeric and identifier validation;
- thread-safe queue and deduplication state transitions;
- `nack()` with requeue or terminal dead-letter disposition;
- `extend_visibility()` for active-lease heartbeats;
- immediate dead-lettering when the attempt cap is exhausted;
- optional hard limits for ready, in-flight, and dead-letter state;
- fail-closed deduplication capacity limits and scope-aware dedupe keys;
- low-cardinality `snapshot()` counters for local verification.

## 5.1.0 additions (missing-components pass)

5.1.0 applies the *Comprehensive Missing-Component Implementation Checklist* (96 components) to 5.0.0.
The in-memory `ReliableQueue` is unchanged; everything below is additive and stdlib-only:

| Module | What it adds |
|---|---|
| `durable.py` | `DurableQueue`: hash-chained write-ahead journal, fsync, crash recovery, torn-tail repair, fail-stop on write errors, OS lock + epoch fencing, compaction, backup/restore, DLQ redrive/purge, explain view |
| `service.py` | `Broker.handle(request)`: validation → authn → authz → disable/freeze/drain → breaker → quota → shedding → op; health/readiness/stall; degraded modes |
| `security.py` | HMAC request auth with rotation, least-privilege tenant-scoped grants, fail-closed key providers, hash-chained audit log |
| `protocol.py`, `errors.py`, `schemas/` | versioned wire protocol `inv53.wire/1`, JSON Schemas, error taxonomy, conformance fixtures |
| `config.py` | declarative config with secure defaults, layered overrides with provenance, atomic CAS update and rollback |
| `observability.py` | Prometheus exporter with cardinality cap, redacting JSON logs, W3C trace propagation, decision events |
| `bench.py` | reproducible benchmark harness, capacity model, regression gate |
| `gate.py`, `tools/ci.py` | digest-bound CI evidence, component register, generated traceability, production exit gate |

**Status is not "done".** `governance/COMPONENTS.json` records every one of the 96 components as
IMPLEMENTED_LOCAL, PARTIAL or BLOCKED with named blockers; **none is COMPLETE**, because completion needs
owners and approvals that do not exist yet. `python -m inv53_message_reliability gate` returns **NO_GO**
(exit 3) and lists why. See `docs/TRACEABILITY.md`.

## Responsibility

Own delivery guarantees: acknowledgement, visibility timeouts, lease fencing, redelivery, bounded attempts, dead-lettering of poison messages, and consumer idempotency by message ID.

## Explicit non-goals

Routing, message-envelope ownership, durable broker storage, business retry policy, and ordering are not owned by this component.

## Reference API

```python
q = ReliableQueue(visibility=30, max_attempts=5)
q.put({"id": "msg-123", "payload": {"value": 1}})

delivery = q.receive(now=100.0)
if delivery is not None:
    # process delivery.message
    accepted = q.ack(delivery, now=101.0)
```

`receive`, `ack`, `nack`, `extend_visibility`, and `expire` use an explicit logical clock so tests can deterministically prove deadline behavior. At the 5.1.0 wire boundary (`Broker`) leases are timed by the broker's own clock; a client-supplied `now` is ignored. Production broker adapters should bind equivalent semantics to their own authoritative clock and durable lease table.

## Tests and CI

```text
python inv53_message_reliability/tools/ci.py --pk-core <folder containing pk_core>
```
runs compile, lint, schema-drift, unit (all suites), `python -O`, pinned pk_core conformance, perf gate and a
reproducible-release lane, and writes `evidence/CI_EVIDENCE.json` bound to the source digest.


The package can import its reliability primitives without the external framework; framework bindings are loaded lazily. The standalone primitives are also testable without `pk_core`:

```text
python inv53_message_reliability/tests/test_reliability.py
```

The framework conformance suite additionally requires `pk_core`:

```text
python inv53_message_reliability/tests/test_component.py
```

Set `PK_CORE_PATH` if `pk_core` lives outside the normal import path. In an environment containing `pk_core`, the intended project-level commands remain:

```text
python -m pk_core list
python -m pk_core run INV-53 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-53 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Operator CLI

`python -m inv53_message_reliability {version|errors|schemas|config|store|audit|bench|gate|traceability}` —
see `docs/ops/RUNBOOKS.md`.

## Operational note

The repository contains semantic reference code and a checklist contract, but it does **not** yet contain all production artifacts required by that checklist. `MISSING_COMPONENTS.md` is the post-hardening gap audit. No external `pk_core`, broker, observability, identity, KMS, deployment, or CI behavior is credited as locally verified unless its evidence is actually bundled or executable in this archive.
