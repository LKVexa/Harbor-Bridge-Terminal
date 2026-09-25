# INV-61 Architecture (4.3.0)

## Module map

| Module | Checklist items | Role |
|---|---|---|
| `wit_model.py` | M04 | Strict WIT-subset parser, normalised interface digest |
| `codec.py` | M04, M24 | Canonical value codec, `PK_WRPC_FRAME/2` header, envelope types |
| `negotiation.py` + `COMPAT_MATRIX.json` | M05 | Version selection, transcript MAC (downgrade protection) |
| `security.py` | M06, M07, M08, M09, M13 | Key ring, envelope MAC, replay guard, capability policy, chained audit |
| `resilience.py` | M10, M11 | Cancellation, retry, idempotency, token buckets, admission, breakers |
| `config.py` | M12 | Schema, overlays, secret references, provenance, atomic activation/rollback |
| `observability.py` | M14–M18 | Health, metrics exporter, structured logs, trace context, telemetry policy |
| `state.py` | M19, M20 | Lease authority + fencing, durable checkpoint |
| `server.py` | all | Transport-neutral request pipeline |
| `transport.py` | M03, M08, M10 | TCP / mutual-TLS server and multiplexing client |
| `rpc.py` | legacy | 4.2.0 in-process reference (`PK_WRPC_FRAME/1`), kept for compatibility |
| `component.py`, `contract.py` | M01 | Optional `pk_core` gate integration (lazy) |

## Trust boundaries

```
 caller process            network (untrusted)            INV-61 node
┌──────────────┐   TLS1.3 mTLS + HMAC envelope   ┌─────────────────────────────────┐
│ RpcClient    │ ───────────────────────────────▶│ B1 socket: header check, caps   │
│  key ring    │                                 │ B2 HELLO: key lookup, negotiate │
└──────────────┘                                 │ B3 envelope decode (bounded)    │
                                                 │ B4 MAC + TLS-CN binding         │
                                                 │ ── authenticated ───────────────│
                                                 │ B5 replay, disable/drain, dl    │
                                                 │ B6 iface/version/fingerprint    │
                                                 │ B7 authz (default deny)         │
                                                 │ B8 fence, breaker, admission    │
                                                 │ B9 arg decode → callee (pool)   │
                                                 └─────────────────────────────────┘
```

Nothing left of B4 can observe interface names, function existence or argument contents.

## Connection lifecycle (C015)

`ACCEPTED → TLS → AWAIT_HELLO → READY → (DRAINING) → CLOSED`. Legal transitions only; any protocol violation from any state → `CLOSED`. `AWAIT_HELLO` is bounded by `handshake_timeout_s`; `READY` by `idle_timeout_s`.

## Call lifecycle

`RECEIVED → AUTHENTICATED → ADMITTED → DISPATCHED → {OK | TRAPPED | DEADLINE | CANCELLED}`. Rejections are terminal at the stage that produced them and carry that stage's status.

## Failure domains (C051)

| Domain | Failure | Behaviour |
|---|---|---|
| Callee | exception | `callee-trap`, breaker counts it |
| Callee | hang | abandoned at deadline, token cancelled |
| Process | crash/restart | idempotency results, fence epoch, disable flag and audit head restored from checkpoint |
| Node | loss | clients see `unavailable` / `ambiguous`; only keyed calls retried |
| Network | partition | lease expires → other node acquires higher epoch → stale node's mutations `fenced` |
| Key service | unavailable | keys cannot be loaded → node not ready (fail closed) |
| Time | skew > window | `replay` (stale-or-future) → fail closed |
| Telemetry sink | down | logs/spans dropped and counted; data path unaffected |

## Deployment tiers (C012)

The runtime is pure Python ≥ 3.10 stdlib and runs unchanged on cloud, datacenter, near-edge and far-edge nodes that can run CPython. Unsupported patterns (C008): shared global singleton across sites; plaintext production traffic; running mutating exports without a lease authority; embedding in a Wasm guest (the runtime is host-side).
