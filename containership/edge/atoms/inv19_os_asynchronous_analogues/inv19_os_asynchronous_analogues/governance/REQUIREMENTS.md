# INV-19 requirements specification (v5.0.0)

Each requirement names the executable evidence that proves it; `tools/run_gate.py` resolves these references and fails the check if the evidence is missing or failing.

## C011 — Testable requirements from "efficient asynchronous I/O models"
| ID | Requirement | Evidence |
|---|---|---|
| R-11.1 | Real host I/O completes through io_uring when available | `IoUringTest.test_real_pipe_io_success_and_eof` |
| R-11.2 | Real host I/O through epoll/kqueue/portable via readiness + syscall | `EpollTest`, `PortableTest`, `ParityTest` |
| R-11.3 | Selection derives from operational probes | `CapabilityTest.*` |
| R-11.4 | p99 submit→resolve ≤ 1 ms (one scheduler tick) | `evidence/bench.json` |

## C012 — Functional requirements across tiers
Cloud / datacenter: io_uring or IOCP fast path. Near-edge: epoll/kqueue. Far-edge / restricted sandboxes (seccomp denies io_uring): portable. The same component-visible behaviour is required in every tier (`ParityTest`).

## C013 — Non-functional
Latency: p99 ≤ 1 ms (bench). Availability: portable fallback 100% (cannot be disabled; `ConfigTest.test_invalid_cannot_partially_activate`). Durability: INV-19 holds no durable state except the audit log (hash-chained). Consistency: exactly-once terminal resolution (`FutureTest`). Isolation: per-tenant quotas and capability checks. Determinism: deterministic selection (`test_selection_is_deterministic`).

## C014 — Outcome semantics
| Outcome | Representation |
|---|---|
| success | `("value", result)`; EOF is `("value", b"")` / CQE res 0 |
| partial success | a short read/write count in `value` (caller continues with new credit) |
| degraded operation | health `degraded`; fallback engaged with reason |
| retryable failure | `CanonicalError.retryable = True` (WOULD_BLOCK, INTERRUPTED, TIMED_OUT, RESOURCE_EXHAUSTED, …) |
| terminal failure | `CanonicalError.retryable = False`; CANCELLED carries `cancel_cause` |

## C015 — Lifecycle states
Operation: `SUBMITTED → INFLIGHT → COMPLETED | FAILED | CANCELLED | TIMED_OUT` (`hostio/ops.py::LEGAL`); terminal states immutable. Backend health: `healthy → degraded → unhealthy → (recover) healthy | quarantined`. Future: `PENDING → VALUE | ERROR | CANCELLED`.

## C016 / C027 — Versioning and compatibility
Interfaces `PK_ASYNC_{BACKEND,ARM,REAP,ERROR}/1` are JSON Schema documents in `schemas/`; frozen copies in `schemas/v1_frozen/` are permanent. Additive fields allowed; unknown fields ignored; unknown enum values rejected by v1 readers (needs minor + negotiation); breaking changes need a new major (`SchemaTest.test_breaking_change_is_detected`, `test_no_breaking_change_against_frozen_v1`). Peers negotiate highest common minor within the same major (`test_negotiation`).

## C017 / C028 — Capacity, quotas, limits
Global/tenant/workload/backend quotas for every exhaustible resource (`hostio/resources.py::RESOURCES`); configurable limits: `quota.*`, `ring.sq_entries ≤ 32768`, `ring.cq_entries ≤ 65536`, event batch ≤ 65536, read size ≤ 16 MiB, schema payload ≤ 1 MiB, 1 op in flight per descriptor. Fairness: quotas bound any one tenant; event-array rotation prevents starvation.

## C018 — Intermittent / absent network
INV-19 has no network dependency in its data path. Socket errors surface as canonical errors (HOST_UNREACHABLE, NETWORK_DOWN retryable). Control dependencies (key service, audit sink) follow `security.OUTAGE_POLICY`.

## C019 — Precedence on conflict
Security > isolation > correctness (no lost errors) > residency > SLO > cost. Example: audit sink loss makes security-relevant actions fail closed even though that costs availability.

## C025 — Timeout, cancellation, retry, idempotency, backpressure
Deadlines are monotonic (`policy.deadline_after`, max 7 days). Cancellation is exactly-once; completion wins if it was reaped first. Retries only for retryable codes on idempotent ops with bounded attempts, budget, capped exponential backoff with jitter. Backpressure: admission control + credit pool + quotas, each refusal carries a reason code.

## C051 — Failure enumeration
| Failure | Effect | Handling |
|---|---|---|
| component (driver exception) | op fails | canonical error, no state leak (accounting returns to baseline) |
| process crash | in-flight lost | stateless restart (`soak.py` forced-restart check) |
| VM/node loss | all ops on node lost | caller retries elsewhere (idempotent) |
| site/network | socket errors | canonical retryable codes |
| provider / kernel (io_uring disabled) | backend unavailable | probe rejects; fallback with reason |
| dependency (key/audit/telemetry) | per `OUTAGE_POLICY` | fail-closed / fail-open as declared |
| control plane (bad config) | rejected atomically | `ConfigError`, no partial apply |

## C057 / C058 / C095 — Crash consistency, duplicates, backup
The only mutable state is in-memory (op table, quotas) plus the append-only audit log. Restart = empty state; no replay. Duplicate execution is prevented by generation-tagged op ids and the exactly-once table. Backup/restore applies only to the audit log: copy JSONL + checkpoints; verify with `hostio.audit.verify_file(path, head)`.

## C065 / C066 — Avoidable overhead and optimisations
Measured (bench): per-op cost is dominated by the Python control plane (capability HMAC, audit hash-chain, metrics) at ~100 µs p50, so io_uring shows no latency advantage over epoll in this implementation. Batching, registered buffers/files, SQPOLL and multishot are explicitly disabled until measured to preserve semantics.

## C069 — Capacity model and saturation signals
Saturation point = configured `quota.max_inflight` (bench overload: accepted exactly the quota, rest rejected with reason). Leading signals: `inv19_quota_utilisation_ratio` (soft warning at 0.8), `inv19_queue_depth`, reap p99.

## C079 — Telemetry retention/sampling/privacy/export
See `hostio/observability.py::TELEMETRY_POLICY` and `hostio/audit.py::RETENTION`.
