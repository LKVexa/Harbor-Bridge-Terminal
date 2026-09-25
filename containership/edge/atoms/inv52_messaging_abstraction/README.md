# INV-52 - Messaging abstraction

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-52 defines a broker-independent publish/subscribe contract. Every message uses a versioned envelope (`id`, `source`, `type`, `time`, `data`), subscriptions route by explicit predicates, publishing is scoped per topic, and messages that no route can accept are sent to a bounded dead-letter path in the local reference runtime.

## What is in this repository

| Area | Files |
|---|---|
| Core runtime (stdlib only) | `runtime.py` — `PubSub`, envelope validation, limits, idempotency window, topic states, decision records/`explain`, tracing, health, metrics |
| Trust | `security.py` — signed tokens, `TenantBus` (authenticated, capability-scoped, tenant-isolated), audit chain, redaction, artifact admission |
| Resilience | `resilience.py` — deadlines, bounded retry with jitter, quota admission, circuit breaker, fencing |
| Configuration | `config.py` — `PK_MSG_CONFIG/1`, secure defaults, overlays, validation, atomic activation, provenance, rollback |
| Lifecycle | `lifecycle.py` — component state machine, dependency-aware `ManagedBus`, `bootstrap`, emergency disable |
| Adapters | `adapters.py` — CloudEvents mapping, Dapr HTTP adapter, delivery-status mapping, fault-injection broker, `Outbox` |
| Observability | `observability.py` — structured logs, Prometheus text, trace helpers, alert classifier, telemetry policy |
| Contracts | `schemas.py`, `schemas/*.schema.json` (6 contracts) |
| Evidence tooling | `bench.py`, `gate.py`, `verify_integrity.py`, `tools/cleanroom.py`, `tools/sbom.py`, `__main__.py` |
| Docs | `docs/` — REQUIREMENTS, SCOPE, INTERFACES, CONFIGURATION, SECURITY, THREAT_MODEL, RELIABILITY, PERFORMANCE, OBSERVABILITY, OPERATIONS, COMPATIBILITY, SUPPORT_POLICY, VERSIONING, `adr/ADR-0001` |
| Governance | `governance/` — requirements (RTM source), RTM.md, owners, waivers, reviews, threats, dependencies; `OWNERS.md`, `CODEOWNERS`, `LICENSE-STATUS.md`, `THIRD-PARTY-NOTICES.md` |
| Deploy | `deploy/dapr/` (component, subscription, resiliency), `deploy/observability/` (dashboard, alerts) |
| Tests | `tests/` — runtime, runtime_ext, security, resilience_config, integration (Dapr HTTP emulator, chaos), adversarial (fuzz), governance, optional pk_core |
| Audit | `POST_UPDATE_AUDIT.{md,json}`, `MISSING_COMPONENTS.md` (4.3.0); `*_4.2.0.*` preserved |

## Responsibility

Own the publish/subscribe contract: the message envelope, topic/subscription model, content-based routing rules, dead-letter routing semantics, and topic-level publishing scope. Broker durability, redelivery, transport, and application payload schemas remain outside this component.

## Local runtime example

```python
from inv52_messaging_abstraction import PubSub, envelope

bus = PubSub()
bus.allow("orders", "shop")
large = []
bus.subscribe("orders", lambda m: m["data"]["total"] >= 100, large)
bus.publish("shop", "orders", envelope("shop", "order.placed", {"total": 250}))
```

The runtime uses UUID-backed message IDs, UTC timestamps when `time` is omitted, deep-copy subscriber isolation, fail-closed topic authorization, bounded routes/dead-letter retention, and stable machine-readable error codes.

## Verification

From the directory that contains the `inv52_messaging_abstraction` package:

```text
python -B -m unittest discover -s inv52_messaging_abstraction/tests -p "test_*.py" -v
python -B -O -m unittest discover -s inv52_messaging_abstraction/tests -p "test_*.py"
python -B -m inv52_messaging_abstraction gate            # engineering verdict + production verdict
python -B inv52_messaging_abstraction/tools/cleanroom.py # isolated re-run from the manifest
python -B -m inv52_messaging_abstraction config-check inv52_messaging_abstraction/examples/config/base.json
```

The optional `pk_core` tests still skip when the audit framework is absent; the gate reports that skip rather than counting it as a pass.

A successful local unit suite is **not** a production certification. External broker integration, identity, encryption, durable reliability, performance qualification, observability, release governance, and formal gate evidence are tracked in `POST_UPDATE_AUDIT.md`.

## Day-0 / day-1 / day-2

- **Day 0:** import the package, run the standalone tests, validate deployment-specific identity/broker configuration, then establish the first external evidence baseline.
- **Day 1:** run the surrounding platform gate before rollout; reject deployment when required external dependencies or evidence are absent.
- **Day 2:** re-run tests and the production gate on every runtime/schema/configuration change, verify evidence continuity, and preserve the previous approved release for rollback.

The reference `PubSub` is intentionally in-memory. Process restart reconstructs it from application/platform configuration; durable messages and dead letters must be owned by the selected reliability/broker layer.
