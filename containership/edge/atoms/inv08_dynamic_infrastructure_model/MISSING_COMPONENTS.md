# INV-08 v4.2.0 - Missing Components

This inventory records components that are absent from the supplied archive or
not demonstrated by package-local executable evidence. It intentionally does
not count a contract declaration as an implementation.

Priority meanings: **P0** = production blocker, **P1** = required for robust
production operation, **P2** = maturity/optimization or documentation debt.

## Package, dependency, and release foundation

1. **P0 - Reproducible `pk_core` dependency package and pin.** No `pk_core` source,
   wheel, lockfile, version constraint, or integrity digest is included, so the
   100-item conformance path cannot be reproduced from this ZIP alone.
2. **P0 - Installable project metadata.** No `pyproject.toml`/build metadata,
   dependency declaration, supported-Python matrix, wheel configuration, or
   package-data rules are present.
3. **P0 - Production acceptance evidence bundle.** No signed machine-readable
   gate result, evidence ledger, test report, or certification artifact is bundled.
4. **P0 - Release provenance and artifact signing.** No SBOM, SLSA/provenance
   statement, signature, trusted publisher identity, or verification policy exists.
5. **P1 - License/NOTICE policy.** The archive does not identify redistribution
   terms, third-party notices, or dependency license obligations.
6. **P2 - Master prompt/workflow corpus.** The prior README referenced
   `MASTER.md`, but the file was absent. Version 4.2.0 corrects the documentation;
   the underlying master prompt/workflow corpus remains external if it is still
   intended to be part of the deliverable.

## Architecture and scope (C001-C010)

7. **P0 - Architecture Decision Record (ADR).** A reviewed ADR for the selected
   dynamic-infrastructure architecture, including System Initiative/live graph,
   digital twin, dependency inference, and simulation choices, is absent (C010).
8. **P0 - Accountable owner and escalation map.** No named service owner,
   operational owner, security owner, or escalation chain exists (C009).
9. **P1 - Deployment topology specification.** No authoritative cloud,
   datacenter, near-edge, far-edge, multi-site, or multi-tenant topology document
   maps the component into the larger control plane (C003, C005-C006).
10. **P1 - Source-of-truth persistence architecture.** The contract names a lease
    table, but no database/consensus/replication technology or durability model is
    implemented (C004).

## Requirements and semantics (C011-C020)

11. **P0 - SHALL-level requirements specification.** The checklist states what
    must be defined, but no normative functional requirements document translates
    continuous infrastructure intent/control into precise state-machine behavior (C011-C015).
12. **P0 - Requirements traceability matrix.** There is no requirement -> design
    -> code -> test -> evidence mapping (C020).
13. **P0 - Failure/result taxonomy.** Success, partial success, degraded,
    retryable failure, terminal failure, and operator-required states are not
    represented by stable machine-readable semantics (C014).
14. **P0 - Lifecycle state machine.** Joining, leased, draining, quarantined,
    reclaiming, terminated, orphaned, and recovery transitions are not modeled (C015).
15. **P1 - Compatibility policy.** Package/protocol/version compatibility,
    deprecation windows, and upgrade/downgrade rules are not defined (C016).
16. **P1 - Quota and fairness engine.** There is one pool-level min/max bound but
    no tenant/workload quotas, fairness, priority, reservations, or starvation
    protection (C017).
17. **P1 - Disconnected-operation semantics.** Network-partition behavior,
    lease grace periods, stale-control handling, and reconciliation after reconnect
    are not implemented (C018).
18. **P1 - Constraint precedence engine.** Security, residency, SLO, topology,
    capacity, and cost conflicts have no explicit deterministic precedence (C019).

## Interfaces and integration (C021-C030)

19. **P0 - Versioned wire schemas for `PK_DYN_LEASE/1`, `PK_DYN_SCALE/1`, and
    `PK_DYN_COST/1`.** Names exist, but no Protobuf/JSON Schema/WIT/OpenAPI/event
    schema or canonical encoding is present (C021-C022).
20. **P0 - Authentication boundary.** No node/controller/provider identity model,
    certificate/token format, trust roots, or mutual-authentication mechanism (C023).
21. **P0 - Authorization/capability model.** No RBAC/ABAC/capability schema or
    least-privilege operation matrix exists (C024).
22. **P0 - Idempotency/retry/backpressure contract.** No operation IDs,
    deduplication keys, timeout budgets, cancellation rules, retry classes, or
    queue pressure semantics are implemented (C025).
23. **P0 - Structured error model.** No stable error codes, retryability flags,
    causal details, or remediation hints are exposed (C026).
24. **P1 - Mixed-version interoperability rules and fixtures.** No N/N-1 matrix or
    protocol negotiation tests exist (C027, C029).
25. **P1 - Interface resource limits.** Payload, queue, connection, concurrency,
    and request-rate limits are not specified or enforced (C028).
26. **P0 - Adjacent-layer integration adapters/tests.** No executable integration
    with INV-06, INV-68, PLN-05, INV-32, or real provider/control-plane APIs is
    included (C030).

## Implementation and configuration (C031-C040)

27. **P0 - Real infrastructure reconciliation controller.** `Pool.tick()` decides
    desired membership but no controller converts intent into create/drain/delete
    operations against infrastructure (C031, C040).
28. **P0 - Provider adapters.** No cloud, hypervisor, bare-metal, edge, or
    datacenter provisioning/reclamation drivers are present.
29. **P0 - Durable distributed lease store.** Current leases are in-process memory
    only; no persistence, replication, transaction, fencing, or recovery layer exists.
30. **P0 - Declarative configuration schema.** No typed site/environment config,
    secure defaults, schema validation, provenance, or activation workflow exists
    (C032-C036).
31. **P0 - Atomic configuration deployment/rollback.** No transactional config
    activation, staged validation, rollback point, or last-known-good mechanism
    exists (C037-C038).
32. **P1 - Secrets boundary.** No secret-reference mechanism, redaction policy, or
    integration with a secret manager exists (C039).
33. **P1 - Deterministic bootstrap automation.** README describes a conceptual
    path, but no bootstrap executable or infrastructure seed process exists (C040).

## Security, trust, and isolation (C041-C050)

34. **P0 - Formal threat model.** No attack-tree/STRIDE-style model covers hostile
    tenants, compromised nodes, control-plane abuse, replay, spoofing, or supply
    chain compromise (C041).
35. **P0 - Node/workload attestation integration.** No hardware/software
    attestation, trust policy, freshness proof, or quarantine decision exists (C044, C048).
36. **P0 - Artifact/policy verification.** No signature/digest/provenance checks
    are performed before executing or applying external artifacts/policies (C045).
37. **P0 - Tenant/workload isolation enforcement.** Boundaries are documented but
    not enforced across compute, memory, state, network, or devices (C046).
38. **P0 - Encryption/key-rotation implementation.** No transport security,
    at-rest encryption, KMS integration, or rotation lifecycle exists (C047).
39. **P0 - Tamper-evident security audit log.** No append-only signed/hash-chained
    audit event stream exists (C049).
40. **P1 - Adversarial/fuzz security suite.** No replay, injection, privilege,
    spoofing, resource-exhaustion, parser-fuzz, or side-channel tests exist (C050, C085, C087).

## Resilience and distributed correctness (C051-C060)

41. **P0 - Health/stall detector.** No controller heartbeat, stuck-operation,
    dependency-health, or lease-store-health detector exists (C052).
42. **P0 - Bounded retry/circuit-breaker/load-shedding layer.** The reference
    model has no dependency calls, so production retry and cascade-protection
    semantics remain absent (C053-C054).
43. **P0 - Failover and leader/fencing design.** No leader election, fencing token,
    duplicate-controller prevention, split-brain handling, or stale-writer defense
    exists (C055, C058).
44. **P0 - Crash-consistent recovery/replay.** In-memory state has no journal,
    snapshot format, replay cursor, or restart reconciliation protocol (C057).
45. **P1 - Quarantine/freeze/emergency-disable controls.** No API or policy path
    can isolate unsafe nodes/controllers or freeze scale decisions (C059).
46. **P1 - Fault-injection/partition test harness.** No provider failure, process
    crash, network partition, dependency outage, or recovery objective tests exist
    (C060, C089).

## Performance and efficiency (C061-C070)

47. **P1 - Benchmark harness and baselines.** No reproducible latency, throughput,
    startup, CPU, memory, storage, network, or power baseline exists (C061-C063).
48. **P1 - Tail-latency/SLO thresholds and regression gate.** No p50/p95/p99/worst
    case limits or release-blocking performance budgets exist (C062, C070).
49. **P1 - Fleet-scale capacity model.** The arithmetic pool target is not backed
    by measured provisioning latency, quota ceilings, failure rates, saturation
    signals, or predictive capacity planning (C069).
50. **P2 - Edge power/thermal model.** No constrained-node power or thermal
    measurement path exists (C068).

## Observability and explainability (C071-C080)

51. **P0 - Metrics exporter.** The contract lists signal names, but no metrics
    endpoint/exporter, labels, histograms, or cardinality policy is implemented
    (C071-C072).
52. **P0 - Structured logging and trace propagation.** No stable tenant/workload/
    operation IDs, trace context, structured event schema, or cross-boundary
    propagation exists (C073-C074).
53. **P1 - Decision journal/explain API.** `TickResult` now exposes target,
    renewed, reclaimed, and accounting values, but no durable reason graph tying a
    decision to policies, topology, constraints, and live graph state exists (C076-C078).
54. **P1 - Telemetry governance.** No retention, sampling, privacy, export, or
    high-cardinality safety policy exists (C075, C079).
55. **P1 - Dashboards and differentiated alerts.** No operational views distinguish
    load, degradation, policy rejection, attack, dependency failure, and software
    defects (C080).

## Testing, certification, and operations (C081-C100)

56. **P0 - Contract/interface test suite.** Local unit tests cover the pool model,
    but there are no protocol contract tests for declared public interfaces (C082).
57. **P0 - Environment compatibility matrix/tests.** No CPU/runtime/hypervisor/
    provider/protocol matrix or automated qualification exists (C084, C093).
58. **P0 - Concurrency/race test suite.** No shared/distributed state currently
    exists in-package, and no race/fencing tests cover a future lease store (C086).
59. **P1 - Soak/burst/fleet-scale test system.** No long-run or large-fleet
    harness validates memory growth, churn, saturation, and recovery (C088).
60. **P0 - Canary/staged rollout and rollback automation.** Procedures and tooling
    are absent (C092).
61. **P0 - Backup/restore/migration/reconstruction tooling.** No persistent-state
    backup format, restore validation, schema migration, or disaster reconstruction
    process exists (C095).
62. **P0 - Incident response package.** Severity levels, paging, escalation,
    containment, recovery, and post-incident evidence procedures are absent (C097).
63. **P1 - Vulnerability/patch/EOL policy.** No response SLA, supported-version
    window, dependency update policy, or EOL process exists (C094).
64. **P1 - Recurring governance review automation.** No scheduled access, policy,
    dependency, configuration, or architecture review evidence exists (C098).
65. **P1 - Exception/waiver/debt registry.** No owner/expiry-governed ledger exists
    for accepted gaps, deprecations, and temporary risk (C099).
66. **P0 - Formal production exit gate.** A reproducible gate that consumes
    architecture, requirements, security, resilience, performance, observability,
    rollback, ownership, and signed evidence is not included (C100).

## Summary

The v4.2.0 archive now has a safer and independently testable **reference model**,
but the principal missing component is still the production control-plane system
around that model: durable distributed state, authenticated/authorized interfaces,
real reconciliation/provider integrations, security and observability plumbing,
failure handling, certification evidence, and operational governance.
