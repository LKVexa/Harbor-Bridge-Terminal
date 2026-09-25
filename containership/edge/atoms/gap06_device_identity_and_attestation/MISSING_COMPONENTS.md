> **v5.0.0 note:** this list is now tracked item-by-item in `CHECKLIST_STATUS.md` against the 781-item professional checklist. The text below is the v4.2.0 inventory, kept verbatim for traceability.

# GAP-06 Missing Components - post-audit v4.2.0

The supplied archive contains a hardened **reference state machine**, not the complete production subsystem implied by the 100-item checklist. Items below are missing or materially incomplete after the v4.2.0 repair.

## P0 - required before production trust decisions

1. **Real hardware attestation verifier** (`C044`, `C045`) - TPM 2.0/TPM2 quote verification, vTPM support, TEE/platform-specific attestation adapters, signature verification, PCR/event-log validation, and freshness binding. Current `hardware_identity` matching is only a reference guard.
2. **Endorsement/attestation certificate-chain validation** (`C044`, `C045`) - EK/AK certificate parsing, trust anchors, revocation/OCSP/CRL policy, manufacturer roots, and key-usage validation.
3. **Cryptographic node identity enrollment protocol** (`C021-C024`, `C044`) - authenticated enrollment ceremony, proof-of-possession, key rotation, replacement, revocation, recovery, and anti-cloning controls.
4. **Workload identity attestation** (`C006`, `C011`, `C044`, `C046`) - the contract says node/workload identity, but implementation only models nodes.
5. **Typed external schemas/transports** (`C021-C030`) - actual definitions for `PK_NODE_IDENTITY/1`, `PK_ATTESTATION/1`, and `PK_ACCEPTED_MEASUREMENTS/1` (e.g. protobuf/WIT/OpenAPI), stable error codes, compatibility semantics, and conformance fixtures.
6. **Authenticated/authorized service boundary** (`C023`, `C024`, `C042-C047`) - mTLS or equivalent peer authentication, capability/role checks, operator authorization, and transport encryption.
7. **Durable security state** (`C032`, `C057`, `C095`) - crash-consistent persistence for enrollment, revocation, challenge/replay state, verdicts, quarantine, and measurement policy; restart must not reopen replay windows.
8. **Distributed replay protection / HA consistency** (`C055`, `C057`, `C058`) - multi-replica nonce ownership, atomic consume semantics, fencing/leader rules, split-brain protection, and site failover behavior.
9. **Signed measurement-policy publication** (`C036-C039`, `C045`) - policy provenance, authorized approvers, signature verification, atomic activation, staged rollout, rollback, and poisoning prevention.
10. **Authoritative time source** (`C048`, `C057`) - monotonic/secure clock integration, boot/restart semantics, skew budgets, and behavior when trusted time is unavailable. Logical ticks are test scaffolding only.
11. **Quarantine/cordon enforcement integration** (`C059`) - current quarantine is local in-memory state; no scheduler/node-supervisor enforcement path exists.
12. **Re-attestation scheduler** (`C018`, `C048`, `C091`) - renew before verdict expiry, jittered scheduling, disconnected-site behavior, retry policy, and fail-closed expiry enforcement.
13. **Tamper-evident security audit ledger** (`C049`, `C073`, `C076`) - append-only signed events for enrollment, challenge, verdict, policy change, revocation, replay rejection, and quarantine.
14. **Secrets/KMS/HSM integration** (`C039`, `C047`) - managed trust-anchor/key storage, rotation, access control, zeroization, backup/recovery, and hardware-backed service keys.
15. **Threat model + adversarial certification** (`C041`, `C050`, `C087`) - formal attack-surface analysis covering spoofing, replay, relay/cuckoo attacks, malicious firmware, cloned identity, side channels, resource exhaustion, policy compromise, and control-plane abuse.

## P1 - required for a resilient production service

16. **Persistent enrollment/measurement policy API with transactional updates** (`C033-C038`).
17. **Rate limiting, quotas, fairness, and per-principal admission control** (`C017`, `C025`, `C054`, `C067`).
18. **Bounded replay-cache lifecycle design** (`C067`) - `spent_nonces` is intentionally fail-closed but unbounded in the reference model; production needs durable bounded retention without reopening replay.
19. **Structured machine-readable errors** (`C026`) - stable reason codes and safe details for clients/operators.
20. **Retry/idempotency/backpressure contract** (`C025`) for enrollment, attestation, and policy publication.
21. **Environment/site/tenant isolation enforcement** (`C006`, `C046`) beyond a string field on the in-memory attestor.
22. **Disconnected/offline attestation mode** (`C018`, `C048`, `C056`) with cached trust anchors/policy, maximum offline age, reconciliation, and conflict semantics.
23. **Health/readiness/dependency endpoints** (`C052`, `C071`) with explicit degraded/unready states.
24. **Metrics/logging/tracing implementation** (`C072-C080`) - the contract names signals, but no exporter, trace propagation, redaction, retention, dashboards, or alerts exist.
25. **Decision explain API** (`C076`, `C077`) linking verdicts to exact quote, measurement policy version, trust anchor, reason, and expiry.
26. **Fleet-scale persistence and sharding model** (`C013`, `C061-C069`) with capacity planning and saturation signals.
27. **Failover / disaster recovery implementation** (`C051-C060`, `C095`) including backup, restore, region/site loss, reconnect, and split-brain tests.
28. **Compatibility matrix** (`C016`, `C027`, `C084`, `C093`) across TPM versions, CPU architectures, hypervisors, OS/firmware families, edge tiers, and protocol versions.
29. **Integration adapters/tests for GAP-01/GAP-02/GAP-07/PLN-07/SCH-01** (`C003`, `C030`, `C083`).
30. **Production configuration model** (`C032-C040`) separating immutable code from signed mutable config/state with validation and provenance.
31. **Algorithm agility** (`C045`) - named digest/signature algorithms, deprecation policy, FIPS/organization policy hooks, and migration support.
32. **Measurement semantics/event-log parser** - PCR bank selection, boot component mapping, IMA/runtime measurements, firmware/kernel/container/workload measurements, and approved composite policy rules.
33. **Identity cloning/relay detection** - locality/channel binding, device uniqueness controls, anti-cuckoo/relay measures, and duplicate-active-identity detection.
34. **Policy conflict/precedence engine** (`C019`) for security vs residency/SLO/cost constraints.

## P2 - release, quality, and governance completeness

35. **`MASTER.md` source artifact** - README 4.1.0 claimed it was included; it was absent from the supplied archive.
36. **Architecture Decision Record** (`C010`) documenting selected hardware roots, trust model, persistence/HA technologies, and alternatives.
37. **Named owner and escalation path** (`C009`, `C097`).
38. **SHALL-level specification + requirements traceability matrix** (`C011`, `C020`).
39. **Performance baselines and release thresholds** (`C061-C070`) for latency, throughput, CPU, memory, storage, network, power, and tail latency.
40. **Fuzz/property tests** (`C085`) for schemas, evidence/event logs, certificate parsing, and state-machine invariants.
41. **Concurrency/race tests** (`C086`) beyond the in-process lock, including multi-process/distributed races.
42. **Benchmark/soak/burst/fleet tests** (`C088`).
43. **Disaster/partition/reconnect/degraded-control-plane tests** (`C089`).
44. **Machine-readable acceptance evidence bundle** (`C090`) generated by CI and cryptographically tied to the release.
45. **Canary/staged rollout/rollback/emergency-disable procedures** (`C092`).
46. **Patch/vulnerability/EOL policy** (`C094`).
47. **Incident severity/paging/containment/recovery runbook** (`C097`).
48. **Recurring access/policy/dependency/architecture review process** (`C098`).
49. **Exception/waiver/technical-debt register with owners/expiry** (`C099`).
50. **Formal production exit gate** (`C100`) that consumes objective evidence rather than checklist declarations alone.
51. **Packaging/build metadata and dependency pinning** (`C031`) for reproducible installation and release artifacts.
52. **SBOM, provenance, release signing, and dependency vulnerability scanning** (`C045`, `C090`).
53. **License/notice/security disclosure policy** for redistribution and vulnerability reporting.
54. **Complete operational day-0/day-1/day-2 runbooks** (`C096`) with commands, rollback, validation, and recovery procedures.

## Important interpretation

The 100-entry `CHECKLIST.json` is a requirements manifest; it is **not evidence that all 100 requirements are implemented**. The v4.2.0 package now makes that distinction explicit. A production gate should mark requirements as satisfied only when corresponding implementation and machine-verifiable evidence are present.
