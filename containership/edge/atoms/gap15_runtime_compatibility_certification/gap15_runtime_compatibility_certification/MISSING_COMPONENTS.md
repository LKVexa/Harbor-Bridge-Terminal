# GAP-15 - Missing Components

**Assessed version:** 4.2.0  
**Scope:** components not present in the supplied archive, even when the 100-item checklist or inherited `pk_core` assessment may describe the requirement.

The current package is a small reference/domain model. The following components are still required for a production-grade runtime compatibility certification subsystem.

## P0 - production blockers

1. **Durable compatibility-matrix store** - transactional persistence for test results, lifecycle state, matrix revision, environment/site partitioning, crash consistency, backup, restore, and migration. Maps primarily to C032, C037, C057, C095.
2. **Append-only certification evidence ledger** - immutable history rather than latest-value-only state, including supersession links and reconstruction of any historical verdict. C004, C020, C036, C049, C090.
3. **Cryptographic evidence signing and verification** - signature, digest, signer identity, key ID, signature algorithm, verification status, and key-rotation handling for every accepted result. C045, C049, C090.
4. **Artifact provenance binding** - integration with GAP-07 so a certification is bound to an immutable artifact digest/SBOM/provenance statement rather than an arbitrary artifact string. C003, C044, C045, C078.
5. **Node identity and attestation binding** - integration with GAP-02/device identity so the certified profile is tied to measured hardware/firmware/security state rather than a free-form profile string. C003, C044, C048.
6. **Trusted time / clock-skew policy** - authenticated time source, maximum skew, monotonicity rules, offline behavior, and audit handling for time uncertainty. C014, C048, C051, C089.
7. **Authentication layer** - authenticated callers, test producers, nodes, runtimes, control-plane actors, and service identities. C023, C044.
8. **Authorization/capability policy** - least-privilege permissions for recording evidence, changing lifecycle, reactivating EOL runtimes, reading matrices, and issuing certification decisions. C024, C042, C043.
9. **Schema definitions and validators** - actual JSON Schema/Protobuf/WIT (or equivalent) artifacts for `PK_CERTIFICATION/1`, `PK_COMPATIBILITY_MATRIX/1`, and `PK_RUNTIME_LIFECYCLE/1`, including compatibility rules. C021, C022, C026, C027.
10. **Evidence-ingestion boundary** - authenticated API/event/file interface that accepts test evidence, validates schema/provenance/attestation, enforces idempotency, and commits atomically. C021-C026, C034, C037.
11. **Cross-process concurrency control** - optimistic locking/CAS or transactions keyed by matrix revision so two writers cannot race lifecycle or evidence state. C025, C037, C058, C086.
12. **Tamper-evident security audit stream** - append-only audit events for test recording, lifecycle transitions, reactivation, rejection, revocation, and administrative access. C049, C073, C078.
13. **Revocation/quarantine subsystem** - immediately invalidate compromised artifacts, runtimes, profiles, signers, or evidence independently of normal TTL/EOL flow. C041, C048, C059, C092.
14. **Production service/API host** - deployable RPC/HTTP/WIT service with health/readiness, deadlines, cancellation, backpressure, resource limits, structured errors, and graceful shutdown. C021, C025-C028, C052, C054, C067, C071.
15. **State recovery and disaster procedures** - journal/WAL or equivalent crash recovery, backup verification, restore drills, partition/reconnect rules, and disaster testing. C055-C060, C089, C095.

## P1 - core capability gaps

16. **WASI/WIT/component/runtime negotiation engine** - the source function says “negotiate and certify WASI/WIT/component/runtime versions,” but the package currently performs exact-string triple lookup only. C010-C016, C027, C084, C093.
17. **Typed runtime capability model** - structured CPU architecture, OS/kernel, hypervisor, WASI preview, component-model version, WIT world/interface versions, runtime feature flags, ABI details, sandbox/isolation mode, and accelerator capabilities. C011-C016, C021, C084.
18. **Version/range compatibility policy** - SemVer/spec-version range handling, backward/forward compatibility rules, prerelease policy, feature gates, and prohibited implicit widening. C016, C027, C093.
19. **Feature-subset certification model** - represent partial compatibility by feature/capability subset without turning partial evidence into whole-runtime certification. C007, C014, C027.
20. **Lifecycle metadata model** - lifecycle effective dates, deprecation deadline, EOL deadline, reason, source, approver, replacement version, waiver, and reactivation record. C015, C036, C094, C099.
21. **Negative-evidence ageing policy** - explicit rule for when an old `incompatible` test must be re-run versus remaining authoritative indefinitely. C014-C016, C094.
22. **Automatic recertification scheduler** - queue expiring/expired certifications for new testing and prioritize coverage gaps without certifying by inference. C007, C052, C069, C092.
23. **Policy-precedence engine** - deterministic handling when compatibility conflicts with security, residency, lifecycle, SLO, cost, emergency policy, or approved waiver. C019, C024, C048, C099.
24. **Offline/disconnected decision cache** - bounded, signed, expiry-aware local cache defining exactly which decisions remain valid without control-plane connectivity. C018, C048, C056, C089.
25. **Environment/site partition enforcement** - storage keys and authorization that enforce environment/site boundaries; current `environment` is informational only. C006, C035, C046, C055.
26. **Metrics exporter** - rates by verdict, matrix coverage, certificate age, expiry backlog, EOL-in-service, latency, errors, saturation, storage, CPU, memory, and rejection reasons. C061-C070, C071-C072.
27. **Structured logging and distributed tracing** - stable artifact/runtime/profile/environment/node/operation identifiers and propagated trace context. C073-C075, C078-C079.
28. **Operator explain endpoint/UI** - explain why a verdict was issued, which exact evidence/lifecycle revision/policy produced it, and what action is required. C076-C077.
29. **Alerting/dashboard pack** - alerts and views for expiry storms, EOL runtimes, evidence rejection, signer/attestation failure, lag, saturation, storage failure, and attack indicators. C080.
30. **Admission-control integration** - concrete adapter used by GAP-08/SCH-01/PLN-04 so only deployable exact-triple verdicts can authorize rollout/placement. C003, C030, C083.
31. **Conflict-resolution workflow** - operator and automated path for contradictory newer evidence, disputed test producers, false positives/negatives, and evidence quarantine. C014, C026, C059, C097.
32. **Capacity and resource controls** - limits for matrix size, evidence retention, ingestion rate, concurrency, payload size, queue depth, and per-tenant/site fairness where applicable. C017, C028, C054, C067, C069.

## P2 - verification, release, and governance gaps

33. **Real adjacent-layer integration tests** - GAP-02, GAP-07, GAP-08, SCH-01, PLN-04, and every supported execution tier. C030, C083.
34. **Runtime compatibility test matrix/fixtures** - actual fixtures across supported CPU architectures, WASI/WIT/component-model versions, runtimes, hypervisors, providers, and protocol versions. C029, C084.
35. **Parser/schema fuzzing suite** - fuzz untrusted identifiers, schema payloads, evidence envelopes, lifecycle events, and any future RPC/WIT parsers. C050, C085.
36. **Security/adversarial suite** - replay, spoofing, signature confusion, privilege escalation, injection, resource exhaustion, tenant escape, stale-control-plane, and key/time service outage scenarios. C041, C050, C087.
37. **Concurrency/race suite** - simultaneous result writers, lifecycle transitions, reactivation, revocation, snapshot reads, and revision conflicts. C058, C086.
38. **Fault-injection and disaster suite** - process crash, disk failure, partial commit, network partition, stale replica, restore, reconnect, and dependency outage tests. C060, C089.
39. **Benchmark/soak/fleet-scale suite** - p50/p95/p99/worst-case certification and ingestion latency, throughput, startup, memory, storage, network, and power/thermal measurements. C061-C070, C088.
40. **Release acceptance evidence bundle** - machine-readable gate artifact linking build identity, tests, security scan, schema compatibility, performance, rollback proof, and signed approval. C020, C090, C100.
41. **Requirements traceability matrix artifact** - explicit 100-row mapping from every `GAP-15-C###` item to design, implementation symbol, test, runtime evidence, owner, and status. C020.
42. **Architecture Decision Record** - approved ADR for technologies, storage model, evidence trust model, API choices, lifecycle rules, and negotiation semantics. C010.
43. **Accountable owner/escalation metadata** - real owner, on-call/escalation path, support commitment, and incident roles rather than only generic contract prose. C009, C091, C097.
44. **Deployment/bootstrap artifacts** - reproducible package metadata, dependency pins, container/service manifests as applicable, configuration schema, bootstrap validator, and secure defaults. C031-C040.
45. **Supply-chain artifacts** - SBOM, build provenance, release signing, dependency vulnerability policy, patch SLA, and supported-version manifest. C031, C045, C094.
46. **Canary/staged rollout and emergency-disable automation** - actual scripts/manifests/runbook automation rather than descriptive text only. C092.
47. **Backup/restore/migration tooling** - executable tools plus restore verification and version migration tests for persistent matrix/evidence state. C095.
48. **Operational runbooks** - concrete day-0/day-1/day-2 commands, failure trees, incident containment/recovery, and dependency-outage procedures. C096-C097.
49. **Exception/waiver registry** - owned, expiring, reviewable exceptions for lifecycle reactivation, unsupported combinations, security waivers, and temporary policy bypass. C099.
50. **Formal production exit-gate implementation** - machine-enforced GO/NO_GO gate that consumes real evidence from all preceding domains rather than assuming checklist text equals implementation. C100.
51. **Original source `MASTER.md`** - the v4.1 README said the 100 per-item master prompt/workflow document was bundled, but it was absent from the supplied archive. It should be restored from the authoritative source if it is required for the series; it should not be regenerated and mislabeled as verbatim source material.

## Recommended build order

1. Implement P0 items 1-15 first, with durable signed evidence and real identity/provenance bindings as the trust foundation.
2. Implement negotiation and typed capability/version semantics (16-25) before widening certification beyond exact triples.
3. Add observability/admission/capacity integrations (26-32).
4. Build the production verification and release system (33-50).
5. Restore the authoritative `MASTER.md` only from its original source if needed (51).

Until the P0 set is implemented, GAP-15 should be described as a hardened reference certification model rather than a complete production certification service.
