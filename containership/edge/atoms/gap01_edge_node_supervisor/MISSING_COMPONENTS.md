> **v5.0.0 status note.** This is the v4.2.0 assessment, kept as the input to the v5.0.0 overhaul.
> See `CHECKLIST_STATUS.md` for where each component stands now, and `EXCEPTIONS.md` for what remains open.

# GAP-01 Edge Node Supervisor — Missing Components After v4.2.0

This list distinguishes the implemented reference lifecycle model from components still required for a production edge-node supervisor and for credible closure of the 100-item checklist.

## P0 — Core production gaps

1. **Node bootstrap controller** — deterministic boot phases, startup dependency ordering, recovery mode, bootstrap failure policy, and boot-complete attestation.
2. **Hardware/resource inventory adapter** — CPU, memory, NUMA, accelerators, disks, NICs, device topology, firmware and capability snapshots, even if authoritative discovery remains delegated to GAP-02.
3. **Workload runtime manager** — adapters and lifecycle controls for Wasm runtimes, microVMs, and unikernels, including launch, stop, kill, inspect, reconcile, and cleanup.
4. **Durable supervisor state store** — crash-safe persistence of lifecycle state, admitted workloads, drain intent, deadlines, breach history, monotonic generation, and recovery metadata.
5. **Crash/restart reconciliation** — reconstruct local truth after supervisor or host restart and reconcile runtime-resident workloads against persisted intent.
6. **Versioned external schemas** — machine-readable definitions for `PK_NODE_LIFECYCLE/1`, `PK_DRAIN/1`, and `PK_NODE_HEALTH/1`, with compatibility tests and example fixtures.
7. **Authenticated control endpoint** — local IPC/RPC transport with caller authentication, authorization/capability checks, replay protection, and request identity.
8. **Authorization policy engine** — explicit permissions for lifecycle transitions, cordon/uncordon, drain, health publication, runtime launch/termination, and emergency actions.
9. **Health signal registry/policy** — required-vs-optional signal definitions, quorum/aggregation policy, per-signal staleness bounds, trust provenance, and anti-spoofing controls.
10. **Process watchdog/self-supervision** — supervisor liveness monitoring, restart behavior, watchdog integration, hung-loop detection, and safe failure mode.
11. **Runtime isolation integration** — hooks to the execution/isolation plane proving that a drained workload is actually terminated and resources are reclaimed.
12. **Cordon propagation acknowledgement** — handshake proving placement has stopped rather than relying only on local state.
13. **Drain deadline scheduler** — asynchronous per-workload deadlines, grace periods, cancellation, escalation policy, forced termination policy, and operator overrides.
14. **Concurrency control** — locking/serialization for simultaneous admission, health, transition, and drain requests; race tests for state and workload mutation.
15. **Idempotency/request journal** — request IDs, replay-safe transition/drain semantics, deduplication window, and durable completion records.

## P1 — Security, integrity, and resilience

16. **Secure configuration subsystem** — typed configuration, schema validation, secure defaults, provenance, atomic activation, rollback, and environment/site overlays.
17. **Secret/credential boundary** — integration with an approved secret provider; no credentials in ordinary config, logs, or diagnostics.
18. **Node identity and attestation** — cryptographic node identity, key lifecycle, optional measured-boot/TPM attestation, and trust renewal/rotation.
19. **Signed artifact/config verification** — integrity and provenance verification before activating binaries, runtime bundles, policies, or configuration.
20. **Disconnected-operation policy** — explicit lease, autonomy, cached-policy validity, reconnect reconciliation, and split-brain behavior with GAP-04.
21. **Control-plane partition state machine** — deterministic behavior for disconnect, degraded mode, reconnect, stale commands, and conflict resolution.
22. **Resource pressure handling** — memory/disk/PID/FD pressure policy, admission shutoff, eviction coordination, and emergency drain behavior.
23. **Power-loss and abrupt-reset recovery** — journal replay, partial-drain recovery, orphan cleanup, and bounded restart loops.
24. **Rate limiting/backpressure** — bounded queues and concurrency for control requests, health reports, runtime operations, and telemetry export.
25. **Structured error model** — stable machine-readable error codes, retryability, fault domain, causal chain, and operator-safe messages.
26. **Audit log** — tamper-evident records for transitions, admission, cordon, drain, overrides, failed authorization, and security-relevant configuration changes.
27. **Threat-model-derived controls/tests** — concrete tests for forged health, supervisor impersonation, cordon bypass, stuck workload abuse, replay, malformed requests, and privilege escalation.
28. **Least-privilege runtime boundary** — OS account/capability profile, filesystem restrictions, device access policy, syscall profile, and privilege drop.
29. **Input fuzzing/property tests** — state-machine invariants, malformed schemas, timestamp extremes, workload identity edge cases, and drain ordering.
30. **Fail-safe emergency mode** — operator-controlled containment that stops new admission and preserves diagnostic/evidence state without falsely declaring clean shutdown.

## P1 — Observability and operations

31. **Metrics exporter** — node state, placement eligibility, drain remaining, deadline breaches, health staleness, illegal transitions, queue depth, operation latency, and restart counters.
32. **Structured logging** — stable event IDs, request correlation, node/workload identity fields, redaction policy, bounded log volume, and severity taxonomy.
33. **Distributed tracing hooks** — lifecycle/drain/runtime spans and context propagation across supervisor/control-plane/runtime boundaries.
34. **Readiness/liveness endpoints** — separate process liveness from node readiness and expose explicit degraded-state reasons.
35. **Diagnostic snapshot bundle** — bounded support bundle with state, config metadata, runtime inventory, recent events, health evidence, and redaction.
36. **SLO measurement implementation** — actual measurement windows and alerting for transition legality, drain completeness, and cordon latency.
37. **Alert rules/runbooks** — actionable alarms for stale health, drain breach, illegal transition bursts, reconciliation mismatch, control-plane partition, and crash loops.
38. **Backup/reconstruction procedure** — what state must be backed up versus reconstructed, recovery point objectives, and restore validation.
39. **Upgrade/migration engine** — state/schema migrations, compatibility checks, staged rollout, downgrade constraints, and rollback safety.
40. **Emergency-disable mechanism** — explicit disable/quarantine workflow rather than registry removal alone.

## P2 — Verification, packaging, and governance

41. **Pinned dependency manifest** — package metadata and supported Python/`pk_core` compatibility matrix with hashes or lock data where appropriate.
42. **Build/release manifest** — reproducible artifact inventory, hashes, build provenance, version metadata, and release signature.
43. **CI pipeline** — lint, type checking, unit tests, optimized-mode tests, schema checks, security checks, packaging tests, and artifact verification.
44. **Static type enforcement** — type-check configuration and typed interfaces for lifecycle, workload, health, drain, and integration objects.
45. **Code quality/lint configuration** — formatter/linter rules and automated enforcement.
46. **Coverage reporting** — branch/condition coverage with explicit thresholds for state-machine and failure paths.
47. **Integration test harness** — fake control plane, fake scheduler, fake runtime, disconnect/reconnect simulation, and failure injection.
48. **Concurrency/race test harness** — deterministic multi-request tests and stress testing around admission/drain/health mutation.
49. **Soak/burst/fleet-scale tests** — long-run stability, high churn, large workload inventories, and many-node control-plane interaction.
50. **Performance benchmarks** — transition latency, admission decision latency, drain throughput, persistence overhead, telemetry overhead, and restart recovery time.
51. **Chaos/fault-injection suite** — process kill, disk full, clock anomalies, corrupt state, network partition, runtime hang, and partial writes.
52. **Schema conformance fixtures** — valid/invalid examples and backward/forward compatibility fixtures for every public contract.
53. **Requirements traceability matrix** — each of the 100 checklist requirements mapped to source code, test/evidence, owner, and status.
54. **Machine-readable evidence output** — locally generated evidence artifacts that do not merely depend on undocumented external behavior.
55. **Architecture decision record** — authority boundaries, delegated discovery/execution responsibilities, runtime choices, persistence choice, transport choice, and failure model.
56. **Deployment manifests/service definition** — OS/service-manager integration, filesystem layout, permissions, restart policy, limits, and dependency ordering.
57. **Supported-platform matrix** — OS/kernel/architecture/hypervisor/runtime combinations and explicit unsupported combinations.
58. **Capacity and quota model** — supervisor-side ceilings for workloads, request rates, queue sizes, health signals, evidence retention, and memory usage.
59. **Tenant/fairness semantics implementation** — if multi-tenant operation is in scope, deterministic fairness and anti-starvation behavior during drain/admission.
60. **Formal production exit gate** — automated release gate requiring required tests, evidence, ownership, rollback, security review, and unresolved-exception accounting.

## Documentation/package gaps observed in v4.1.0

61. `MASTER.md` was referenced by README but absent from the archive; either include the authoritative document in a future distribution or keep the reference removed.
62. No license/notice file is present in this component archive.
63. No dependency installation or environment specification is present for `pk_core`.
64. No public schema files accompany the named `PK_*` interfaces.
65. No production deployment/service configuration is present.
66. No machine-readable SBOM or dependency inventory is present.
67. No security policy, vulnerability-reporting process, or support/EOL policy is present.
68. No examples directory demonstrates control requests, health reports, drain responses, or recovery sequences.
69. No operator runbooks exist beyond brief README day-0/day-1/day-2 notes.
70. No compatibility/migration notes define how a v4.x node interacts with differing adjacent component versions.
