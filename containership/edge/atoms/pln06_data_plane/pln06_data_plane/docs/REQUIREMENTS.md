# PLN-06 requirements (normative) — v4.3.0

Work packages #4, #5, #6, #9, #10, #13, #25. Keywords SHALL/MUST follow RFC 2119. Each requirement names the test that proves it.

## 1. Functional requirements (source function → SHALL)

| ID | Requirement | Proof |
|---|---|---|
| FR-01 | PLN-06 SHALL refuse any transfer whose classification is not permitted at the destination, before reserving capacity. | `test_runtime`, `test_service_integration::test_authn_authz_label_residency_refusals_are_audited` |
| FR-02 | PLN-06 SHALL route in-process transfers through the Component-Model interface `pk:data-plane/transfer@1.0.0` with zero network authority. | `test_transports::test_inprocess_zero_copy_readonly_and_no_network_authority` |
| FR-03 | PLN-06 SHALL route cross-node transfers through the authenticated network adapter (`pk06-rpc/1`, the wRPC profile — W-003). | `test_transports::NetworkRpcTest` |
| FR-04 | PLN-06 SHALL carry only VM-control verbs (`start stop pause resume snapshot health configure`) at inline size over vsock; non-inline bytes SHALL NOT be routable to the control transport. | `test_transports::VsockControlTest`, `test_service_integration::test_inv36_*` |
| FR-05 | Large same-node data SHALL move over shared memory with tenant-namespaced, always-unlinked segments; RDMA SHALL be used only when probed available, else an explicit recorded fallback. | `test_transports::test_shared_memory_*`, `RdmaAndSelectionTest` |
| FR-06 | Every payload SHALL be bound to a SHA-256 chunk manifest and verified by the receiver; mismatches SHALL be quarantined and never auto-retried. | `test_transports::test_in_flight_tamper_is_quarantined`, `test_inv37_*` |
| FR-07 | Admission SHALL require an authenticated, tenant-scoped principal holding `transfer.submit` and `transport.use.<tier>`. | `test_security`, `test_service_integration` |
| FR-08 | Classification claims SHALL be verified against a signed, digest- and tenant-bound label. | `test_security::LabelTest` |

## 2. Deployment contexts and connectivity (#4, C012/C018)

Declared in `config.DEPLOYMENT_CONTEXTS`:

| Context | Offline allowed | Max policy age | Localities | Bulk adapters | Behaviour when disconnected |
|---|---|---|---|---|---|
| cloud | no | 300 s | all | rdma, network-rpc, shm | policy older than 300 s → admission refused |
| datacenter | no | 300 s | all | rdma, network-rpc, shm | same as cloud |
| near_edge | yes | 3600 s | all | network-rpc, shm | serves last verified policy up to 1 h; remote transfers fail fast with retryable errors |
| far_edge | yes | 86400 s | in_process, same_node, same_host_vm | shm | remote locality not permitted; residency still enforced offline with last verified policy |

Residency is never relaxed because a dependency is unreachable.

## 3. Outcome and degraded-state semantics (#6, C014/C056)

`lifecycle.OUTCOMES` defines `completed / failed / quarantined / cancelled / expired / partial`, each with *delivered*, *verified* and *caller action*. Retryability is carried by every structured error (`retryable`). `lifecycle.DEGRADED_MODES` states what remains available when a dependency is lost; security dependencies (key service, label authority, journal) fail closed; telemetry loss never blocks admission.

## 4. Constraint precedence (#10, C019)

`precedence.PRECEDENCE`: **security > residency > integrity > isolation > capacity > SLO > cost > locality**. Hard constraints (the first five) deny; soft constraints only rank candidates; locality/gravity can promote a tier but never change destination or override a hard constraint. Unknown constraint names raise. Proof: `PrecedenceTest`.

## 5. Timeouts, retries, idempotency (#13, C025/C053)

* `RetryPolicy`: attempts ∈ [1,10], exponential backoff with **full jitter**, overall deadline, per-attempt timeout.
* Only errors whose class declares `retryable=True` are retried (backpressure, transport/network failures, deadline, key outage, policy unavailable, PLN-03 hand-off). Residency, auth, integrity, and invalid input are terminal.
* Cancellation propagates immediately (`threading.Event`).
* Completion is idempotent (duplicate/unknown IDs are no-ops; mutated live records fail closed).

## 6. Fairness and limits (#9, C017/C028)

`FairScheduler` implements weighted deficit round-robin: a backlogged tenant is served at least once per round; weights give proportional share; global and per-tenant queue bounds raise retryable backpressure. Interface limits: inline ≤ 64 KiB; local ≤ 64 MiB; bulk ≤ 64 GiB; RPC frame ≤ 4 MiB (header ≤ 64 KiB); control frame ≤ 4 KiB header; shm segment and live-segment pins configurable; replay cache, stall tracker, quarantine store, log ring, span buffer and metric series are all bounded.

## 7. Non-functional requirements (#5, C013/C062/C091)

Thresholds below are **proposed** and become binding when the owner approves ADR-0002 (W-002). Measured values are from `bench/baseline.json` on the audit sandbox (x86_64, Python 3.11).

| Metric | p50 | p95 | p99 | worst | Budget | Measured (baseline) |
|---|---|---|---|---|---|---|
| Runtime admission latency | ≤ 50 µs | ≤ 200 µs | ≤ 2 ms | ≤ 20 ms | SLO ceiling p99 2 ms (gate) | p50 ≈ 6 µs, p99 ≈ 18 µs |
| Governed inline submit (auth+label+audit+journal fsync) | ≤ 5 ms | ≤ 20 ms | ≤ 50 ms | ≤ 250 ms | SLO ceiling p99 50 ms (gate) | p99 ≈ 2.7 ms |
| Shared-memory throughput (8 MiB) | — | — | — | — | ≥ 50% of baseline | ≈ 222 MB/s |
| Network RPC throughput (16 MiB, loopback) | — | — | — | — | ≥ 50% of baseline | ≈ 203 MB/s |

* **Availability SLO:** 99.9 % monthly admission availability (error budget 43 min/month), excluding refusals that are correct policy outcomes.
* **Durability:** every admitted transfer's lifecycle is journaled with fsync before acknowledgement; audit ledger fsync per record.
* **Consistency:** single-writer per journal enforced by fencing epoch; policy activation atomic.
* **Isolation:** per-tenant quotas; tenant-namespaced shared memory; cross-tenant labels/credentials refused.
* **Determinism:** tier selection is a pure function of (size, locality); fuzz/fault seeds are fixed.
* **Support commitments:** see `docs/RUNBOOKS.md` §Incident severities and `docs/VULNERABILITY_POLICY.md`.

## 8. Failure model and stall detection (#25, C051/C052)

`resilience.FAILURE_MODEL` catalogues process, VM, node, site, provider, control-plane, partition, stall, integrity and key-service failures with detection signal, recovery action and RTO. Stall threshold: `stall_timeout_s` (default 60 s); `GovernedDataPlane.reap_stalled()` expires stalled transfers and releases capacity. Health turns not-ready when key service, audit ledger or authoritative policy is unavailable.

## 9. Non-goals

PLN-06 does not store payloads, does not decide residency policy (GAP-13 does), does not schedule compute (PLN-03 does), and does not provide OS-level sandboxing (deployment control, W-011).
