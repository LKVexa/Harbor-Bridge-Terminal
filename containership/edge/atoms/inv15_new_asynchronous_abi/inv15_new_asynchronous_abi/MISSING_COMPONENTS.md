# INV-15 v4.2.0 Missing Components

This inventory lists components still absent or only represented as contracts/reference behavior after the v4.2.0 hardening pass. Items explicitly owned by INV-15 are separated from integration dependencies and production-certification infrastructure.

## A. ABI specification and wire contract

1. **Canonical WIT/IDL definition for `PK_ASYNC_CALL/1`** — typed function signatures, discriminated immediate/subtask result, stable field numbering, version negotiation, and canonical encoding rules.
2. **Canonical WIT/IDL definition for `PK_WAITABLE_SET/1`** — set construction, readiness result schema, ordering guarantees, duplicate semantics, maximum cardinality, and invalid-handle behavior.
3. **Canonical WIT/IDL definition for `PK_SUBTASK_CANCEL/1`** — cancellation request, acknowledgment state, reason code, already-complete semantics, and idempotency rules.
4. **Machine-readable error envelope** — stable numeric/string error codes for not-ready, foreign/forged handle, consumed handle, budget exhaustion, timeout, cancellation, trap, host failure, and unsupported version.
5. **Opaque-handle binary representation** — fixed-width or canonical variable-width encoding for token/sequence, endianness, serialization, redaction, and parsing rules.
6. **Handle version tag / feature bits** — forward-compatible decoding and explicit rejection of unsupported handle formats.
7. **Formal lifecycle state machine specification** — pending, ready, cancelled, consumed, abandoned, trapped, timed-out, and host-invalidated transitions with forbidden edges.
8. **Conformance vectors** — known-good and known-bad encoded calls, waits, cancellations, handles, and failure envelopes for every implementation.

## B. Timing, cancellation, and backpressure semantics

9. **Deadline propagation** — absolute/relative deadline representation, host clock source, overflow handling, and inheritance across nested async calls.
10. **Timeout behavior** — distinction between wait timeout, call timeout, deadline expiry, and cancellation; exact post-timeout handle state.
11. **Cancellation acknowledgment protocol** — observable states for requested, accepted, propagated, completed-before-cancel, and unable-to-cancel.
12. **Cancellation cause taxonomy** — bounded stable reason codes rather than free-form strings at the ABI boundary.
13. **Nested cancellation tree** — parent/child subtask propagation and deterministic handling of detached child work.
14. **Idempotency metadata** — call identifiers or keys allowing safe retry where the invoked operation supports it.
15. **Retry contract** — explicit statement that retry is host/caller policy, plus the metadata required to prevent duplicate execution.
16. **Hierarchical budgets** — instance, workload, tenant, process, node, and global outstanding-call ceilings.
17. **Fairness policy hooks** — per-tenant/per-workload admission classes or scheduler hints preventing one workload from monopolizing waitable capacity.
18. **Drain/quiesce mode** — stop-admitting-new-work while allowing or cancelling existing subtasks during upgrade/shutdown.

## C. Host waitable-table implementation

19. **Production host-side table backend** — replacement for the in-process Python reference map using runtime-native memory/accounting primitives.
20. **Generation-safe handle registry** — host-native slot/generation scheme or equivalent preventing stale-handle aliasing after slot reuse.
21. **Cryptographically strong token source binding** — platform RNG integration and failure policy if secure randomness is unavailable.
22. **Wakeup registration primitive** — atomic subscribe/check sequence that proves no lost wakeup between readiness publication and wait registration.
23. **Ready-queue implementation** — lock-efficient/MPSC or scheduler-native delivery path instead of scanning a Python table.
24. **Batched readiness delivery** — bounded batch interface and fairness semantics for large ready sets.
25. **Completion publication API** — runtime-facing producer interface with exactly-once completion/trap/cancel resolution.
26. **Trap/fault completion state** — structured propagation when a callee traps, aborts, or the host terminates execution mid-subtask.
27. **Instance teardown invalidation** — bulk invalidation of all handles and deterministic behavior for late completions after teardown.
28. **Runtime restart semantics** — explicit invalidation, reconstruction, or migration behavior across host process restarts.
29. **Memory accounting** — per-row byte accounting, payload ownership rules, tombstone memory accounting, and hard ceilings.
30. **Payload ownership/zero-copy contract** — who owns returned buffers/resources, when ownership transfers, and safe reclamation after cancel/abandon.

## D. Scheduler and adjacent-layer integration

31. **SCH-01 scheduler adapter** — translate ready-table events into runnable component instances without polling or blocked guest stacks.
32. **INV-16 async component function adapter** — guest-visible lowering/lifting of async function results onto this ABI.
33. **INV-17 streaming adapter** — stream item readiness, backpressure, close, error, and cancellation semantics layered on subtask readiness.
34. **INV-18 completion adapter** — one-shot completion primitive and typed result/error lifting.
35. **INV-11 contract-language bindings** — async annotations lowered into generated ABI stubs with version checks.
36. **INV-12 language interop bindings** — canonical lowering/lifting for handles, payloads, errors, cancellation, and deadlines.
37. **INV-14 migration shim** — compatibility bridge from the previous pollable model, including deprecation telemetry and cutover rules.
38. **Cross-runtime interop harness** — at least two independent runtime implementations proving ABI equivalence.

## E. Security, trust, and isolation

39. **Capability-boundary threat model** — explicit attacker model for guest code, same-instance modules, cross-tenant callers, compromised host extensions, and forged serialized handles.
40. **Handle redaction policy** — logging/tracing rules ensuring opaque tokens never appear in ordinary logs or user-visible diagnostics.
41. **Replay protection across serialized boundaries** — nonce/generation/instance epoch semantics if handles ever cross process or machine boundaries.
42. **Tenant identity binding** — host-enforced association of a handle with tenant/workload identity beyond process-local object ownership.
43. **Security audit events** — tamper-evident records for foreign/forged handle attempts, repeated use-after-consume, budget abuse, and cancellation anomalies.
44. **Resource-exhaustion adversarial suite** — handle spray, wait-set abuse, cancellation storms, completion storms, reason-cardinality abuse, and tombstone churn.
45. **Side-channel review** — timing/error-message analysis for cross-tenant existence probing and readiness leakage.
46. **Supply-chain attestation** — signed release artifact, provenance statement, dependency lock, and SBOM for the production implementation.

## F. Observability and SLO instrumentation

47. **Metrics exporter** — production counters/gauges/histograms for open subtasks, ready subtasks, refusals, cancellations, abandoned results, wakeup latency, wait size, and host-table memory.
48. **Cancellation latency histogram** — scheduler-tick or wall-clock measurement needed to verify the declared p99 cancellation SLO.
49. **Readiness-to-resume latency histogram** — host-ready timestamp through scheduler resume, with p50/p95/p99/worst-case reporting.
50. **Structured event log schema** — stable instance/tenant/workload/operation IDs with secret-safe handle correlation identifiers.
51. **Distributed trace propagation** — trace context across call creation, async suspension, readiness publication, and resumption.
52. **Explain/debug endpoint** — bounded operator view of live counts, states, budgets, refusal causes, and dependency health without exposing handle tokens or payloads.
53. **Dashboard and alert pack** — saturation, stuck-ready, cancellation-latency, refusal-rate, unexpected foreign-handle, and wakeup-loss indicators.
54. **Telemetry retention/sampling policy** — high-cardinality controls and privacy-safe export behavior.

## G. Verification and performance certification

55. **Property-based state-machine tests** — randomized legal/illegal operation sequences validating lifecycle invariants.
56. **Protocol/handle fuzzing** — malformed encodings, truncated handles, invalid versions, oversized sets, and random failure envelopes.
57. **Concurrency race suite** — complete/wait/take/cancel/cancel-all/teardown interleavings under high thread/task counts.
58. **Lost-wakeup stress test** — millions of readiness/subscription races proving no indefinite stall.
59. **Soak and churn test** — long-duration create/complete/cancel cycles proving bounded memory and tombstone behavior.
60. **Overload test** — sustained budget exhaustion and recovery with fairness and tail-latency measurements.
61. **Benchmark suite** — call allocation, completion publication, wait, take, cancel, and teardown latency/throughput baselines.
62. **Architecture compatibility matrix** — supported CPU architectures, OS/runtime versions, host runtimes, and ABI versions.
63. **Fault-injection suite** — callee trap, host crash, scheduler stall, clock failure, RNG failure, teardown race, and dependency loss.
64. **Independent implementation conformance test** — same vectors executed against the reference model and each production runtime.

## H. Release, packaging, and operations

65. **Package/build metadata** — explicit Python/runtime compatibility and dependency metadata for this reference package or its production equivalent.
66. **CI pipeline** — compile, unit, optimized-mode, fuzz, race, benchmark-regression, SBOM, signing, and gate stages.
67. **Version compatibility matrix** — supported combinations of INV-11/12/14/16/17/18 and SCH-01 interface versions.
68. **Canary rollout procedure** — staged enablement with measurable abort thresholds tied to refusals, stalls, latency, and errors.
69. **Automated rollback hook** — restore prior runtime/ABI implementation and invalidate incompatible live handles safely.
70. **Emergency disable/drain control** — operator mechanism to stop admission, drain/cancel live subtasks, and preserve diagnostics.
71. **Incident runbook** — lost wakeup, runaway subtasks, cancellation failure, handle-forgery alarms, and scheduler integration failure.
72. **Patch/vulnerability/EOL policy** — ownership, severity SLA, supported release window, deprecation schedule, and migration obligations.

## Priority order

For the next implementation pass, the highest-value sequence is: **wire/WIT contracts (1-8) → deadline/cancellation semantics (9-18) → production host table and wakeup path (19-30) → scheduler/adjacent integration (31-38) → security and observability (39-54) → certification and operations (55-72).**
