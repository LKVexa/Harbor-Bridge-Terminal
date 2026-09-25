# INV-65 architecture (4.3.0)

## Layers (request path, fail-closed at every step)

```
transport/http_adapter.py  (M04: bounded JSON surface, catalogued HTTP statuses)
   -> authn/authenticator.py      (M07: signed workload token, issuer/audience/expiry/replay)
   -> runtime call metadata       (M14: schema call_metadata/v1, deadline)
   -> lifecycle/state_machines.py (M11: provider must be ready|degraded; link must be active)
   -> authz/decision.py           (M08: signed external decision, exact scope/action/resource/op)
   -> identity-scoped lookup      (M06: key = tenant/env/site/workload/component/link)
   -> runtime/admission.py        (M15: rate, fair share, global ceiling) + quotas
   -> runtime/idempotency.py      (M14)
   -> runtime/circuit_breaker.py  (M15)
   -> secret_refs/resolver.py     (M09: resolve in caller scope, audited secret.use)
   -> runtime/call_control.py     (M14: bounded pool, deadline, cancel, safe retry)
   -> backend adapter             (M38 fixtures: keyvalue / http / broker)
```
Mutations add residency (M40), config history (M10), lease fencing (M17) and the durable WAL store (M05) before ack; every allow/deny is an audit event (M18).

## Boundaries enumerated (C021)
| Boundary | Contract | Module |
|---|---|---|
| HTTP `/v1/link`, `/v1/unlink`, `/v1/call` | PK_PROVIDER_LINK/1, call_metadata/v1, PK_PROVIDER_ERROR/1 | transport/http_adapter.py |
| HTTP `/livez`, `/readyz` | PK_PROVIDER_HEALTH/1 | health/ |
| HTTP `/metrics` | Prometheus text 0.0.4 | observability/telemetry.py |
| HTTP `/v1/contract` | PK_PROVIDER_CONTRACT/1 | transport/http_adapter.py |
| Backend adapter (in-process) | `fixtures/providers/base.Backend` | service.py |
| Secret backend (INV-55) | `secret_refs.resolver.SecretBackend` | secret_refs/ |
| Policy plane | PK_AUTHZ_DECISION/1 | authz/ |
| Identity plane | signed token claims -> identity_context/v1 | authn/ |
| Durable state | WAL + snapshot (schema_version 2) | state/ |
| Audit sink | PK_AUDIT_EVENT/1 JSONL | audit/ |
| Registry | provider_registration/v1 | registry/ |
| WIT/RPC (INV-61) | **not implemented here** — INV-61 carries calls; the JSON envelope is the mapping target | — |

## Precedence when requirements conflict (C019)
security > residency > isolation > correctness/durability > SLO > cost. Concretely: a residency denial is never overridden by failover; a secret-backend outage fails closed even if that burns the availability SLO.

## Functional scope per tier (C011/C012)
Cloud/datacenter: full host with durable store. Near-edge: same host, smaller quotas. Far-edge/intermittent (C018): links and state survive restart locally; with the identity or policy plane unreachable, calls fail closed (no cached-allow). **Edge tiers are not exercised in this archive.**

## Unsupported patterns / non-goals (C008)
Shared config across links; provider-owned authorization policy; implementing backends; scheduling providers; plaintext transport outside loopback tests; multi-writer state stores (single writer enforced by lease fencing).

## Single-writer note
`LinkStateStore` is single-writer. Two hosts must never write the same state dir concurrently; lease fencing (M17) refuses the stale writer. Shared-storage replication is out of scope.
