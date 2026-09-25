# GAP-15 Runtime Compatibility Certification
## Missing Components — Professional Engineering Checklist

**Checklist version:** 1.0.0  
**Source assessment:** GAP-15 v4.2.0  
**Source gap count:** 51 components  
**Purpose:** Implementation, hardening, verification, operational-readiness, and production-exit criteria for the missing components identified in the GAP-15 v4.2.0 audit.

> This checklist is intentionally implementation-grade. A checked box means the requirement is implemented and evidenced, not merely designed or documented.

## Control conventions

- **P0 — Production blocker:** must be complete before the subsystem is represented as a production certification authority.
- **P1 — Core capability:** required for full compatibility semantics, safe integration, observability, and scaled operation.
- **P2 — Verification / release / governance:** required to prove, operate, release, and sustain the service professionally.
- Each control uses `GAP15-MC-<component>-<item>` identifiers so it can be imported into an RTM, issue tracker, or release gate.
- “Evidence” means immutable or verifiable machine-readable evidence linked to the exact build/configuration/revision under evaluation.

## Global completion gates

- [ ] **GAP15-GLOBAL-001** All P0 components are implemented, integrated, tested, monitored, recoverable, and represented in the production release gate.
- [ ] **GAP15-GLOBAL-002** Certification never grants compatibility from missing, expired, revoked, quarantined, malformed, unsigned, unauthenticated, or policy-disallowed evidence.
- [ ] **GAP15-GLOBAL-003** Every allow/deny/unknown decision is reconstructable from immutable evidence, lifecycle state, policy revision, trust-store/revocation state, and exact software build.
- [ ] **GAP15-GLOBAL-004** Identity, artifact provenance, node attestation, trusted time, authorization, and site/environment boundaries are cryptographically or transactionally bound to decisions where required.
- [ ] **GAP15-GLOBAL-005** Cross-process races, crashes, partitions, stale replicas/caches, restore/rollback, and dependency outages have explicit deterministic behavior and automated tests.
- [ ] **GAP15-GLOBAL-006** Supported API/schema/runtime compatibility is versioned, machine-validated, and covered by integration/conformance fixtures.
- [ ] **GAP15-GLOBAL-007** Security controls have threat-model coverage plus adversarial, fuzz, replay, privilege, resource-exhaustion, and key/time failure testing.
- [ ] **GAP15-GLOBAL-008** Production observability includes bounded-cardinality metrics, structured logs, traces, immutable audit, actionable alerts, and tested runbooks.
- [ ] **GAP15-GLOBAL-009** Backup, restore, migration, disaster recovery, and canary/rollback procedures are executable and validated on release-candidate artifacts.
- [ ] **GAP15-GLOBAL-010** The formal production gate consumes signed/immutable evidence and blocks promotion when mandatory requirements are missing or stale.

# P0 — 01. Durable compatibility-matrix store

**Objective:** Provide transactional, recoverable, revision-aware persistence for compatibility state across sites/environments.
**Primary source references:** C032, C037, C057, C095

### Implementation and hardening checklist

- [ ] **GAP15-MC-01-01** Define the canonical persistence model for artifact digest, runtime identity/version, profile identity, environment/site partition, verdict, evidence-set reference, lifecycle revision, matrix revision, created/updated timestamps, and tombstone/revocation state.
- [ ] **GAP15-MC-01-02** Select a transactional storage engine and document consistency guarantees, isolation level, durability mode, replication model, maximum tolerated RPO/RTO, and behavior during quorum loss or single-node operation.
- [ ] **GAP15-MC-01-03** Implement compare-and-swap or serializable revision updates so every matrix mutation advances a monotonic matrix revision and rejects lost updates with an explicit conflict result.
- [ ] **GAP15-MC-01-04** Enforce compound uniqueness/indexes for exact certification keys while supporting historical lookup by artifact, runtime, profile, environment, site, signer, verdict, and time range.
- [ ] **GAP15-MC-01-05** Implement atomic write boundaries spanning evidence acceptance, verdict materialization, matrix revision update, and audit-event emission; prohibit partially committed certification state.
- [ ] **GAP15-MC-01-06** Define schema-migration semantics with forward-only migration IDs, preflight compatibility checks, rollback/restore strategy, and validation of mixed-version readers/writers.
- [ ] **GAP15-MC-01-07** Implement crash-consistent journaling/WAL settings and verify restart recovery after process kill, host reset, disk-full, and interrupted migration scenarios.
- [ ] **GAP15-MC-01-08** Provide encrypted backup, restore, point-in-time recovery where supported, backup integrity verification, retention policy, and scheduled restore drills.
- [ ] **GAP15-MC-01-09** Enforce site/environment partitioning at the storage key and query-plan layer, not only in application filtering, with tests for cross-partition leakage.
- [ ] **GAP15-MC-01-10** Define retention/compaction rules that preserve authoritative history and referenced evidence while preventing unbounded hot-table growth.
- [ ] **GAP15-MC-01-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-01-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-01-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-01-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-01-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-01-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-01-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-01-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-01-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-01-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 02. Append-only certification evidence ledger

**Objective:** Retain immutable, replayable certification evidence and supersession history.
**Primary source references:** C004, C020, C036, C049, C090

### Implementation and hardening checklist

- [ ] **GAP15-MC-02-01** Define an append-only evidence envelope containing evidence ID, event type, artifact/runtime/profile/site keys, producer identity, observed-at/ingested-at timestamps, payload digest, signature metadata, schema version, and prior/superseded evidence links.
- [ ] **GAP15-MC-02-02** Prohibit in-place mutation or deletion of accepted evidence; represent corrections, withdrawals, supersession, revocation, and quarantine as new ledger events.
- [ ] **GAP15-MC-02-03** Choose a tamper-evident ordering mechanism such as hash chaining, Merkle batching, signed checkpoints, or an append-only database primitive and document verification semantics.
- [ ] **GAP15-MC-02-04** Implement deterministic historical reconstruction so any prior certification verdict can be reproduced from ledger position/checkpoint plus policy/lifecycle revision.
- [ ] **GAP15-MC-02-05** Define idempotency keys and duplicate-ingestion behavior for retried producers while retaining detection/audit data for conflicting payloads under the same producer event ID.
- [ ] **GAP15-MC-02-06** Store canonical payload bytes or canonicalized structured form so signature and digest verification remains stable across serialization libraries and platform versions.
- [ ] **GAP15-MC-02-07** Implement ledger checkpoint/export format for offline verification, incident response, legal/compliance retention, and disaster recovery.
- [ ] **GAP15-MC-02-08** Provide query paths for evidence lineage, supersession chain, signer, artifact digest, runtime/profile, rejection reason, and verdict provenance without weakening append-only guarantees.
- [ ] **GAP15-MC-02-09** Define retention/legal-hold policy; if physical pruning is allowed, require checkpointed cryptographic proof and preserve enough metadata to verify continuity.
- [ ] **GAP15-MC-02-10** Validate ledger reconstruction against intentionally reordered, duplicated, truncated, and corrupted event streams.
- [ ] **GAP15-MC-02-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-02-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-02-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-02-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-02-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-02-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-02-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-02-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-02-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-02-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 03. Cryptographic evidence signing and verification

**Objective:** Cryptographically authenticate every accepted test result and its provenance.
**Primary source references:** C045, C049, C090

### Implementation and hardening checklist

- [ ] **GAP15-MC-03-01** Define the signed payload canonicalization format and domain-separation string so signatures cannot be replayed across message types, environments, or protocol versions.
- [ ] **GAP15-MC-03-02** Select approved signature algorithms, key sizes, digest algorithms, provider/FIPS requirements where applicable, and an explicit algorithm-agility/deprecation policy.
- [ ] **GAP15-MC-03-03** Bind signer identity, key ID/version, certificate or trust-anchor reference, signature algorithm, digest, signing time, and verification result into the evidence envelope.
- [ ] **GAP15-MC-03-04** Implement verification before persistence/materialization; reject unknown, expired, revoked, weak, malformed, or policy-disallowed signing keys with stable reason codes.
- [ ] **GAP15-MC-03-05** Integrate key rotation using overlapping validity windows and trust-store versioning without invalidating historically valid evidence unless an explicit compromise revocation requires it.
- [ ] **GAP15-MC-03-06** Implement signer authorization so a valid signature is insufficient unless that signer is permitted to attest the claimed test suite/runtime/profile/environment.
- [ ] **GAP15-MC-03-07** Protect private signing keys with an HSM/KMS/TPM or equivalent controlled boundary; prohibit plaintext private keys in configuration, source, logs, crash dumps, or test fixtures.
- [ ] **GAP15-MC-03-08** Define offline verification bundles containing trust roots, intermediate metadata, revocation status/checkpoints, and canonicalization version needed to independently verify evidence.
- [ ] **GAP15-MC-03-09** Add negative tests for signature malleability, algorithm substitution, key-ID confusion, truncated signatures, altered canonicalization, replay, and stale/revoked keys.
- [ ] **GAP15-MC-03-10** Emit immutable verification audit records with signer, trust decision, trust-store revision, policy revision, and cryptographic failure category.
- [ ] **GAP15-MC-03-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-03-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-03-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-03-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-03-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-03-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-03-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-03-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-03-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-03-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 04. Artifact provenance binding

**Objective:** Bind certification to immutable artifact identity, SBOM, and build provenance rather than a mutable string.
**Primary source references:** C003, C044, C045, C078

### Implementation and hardening checklist

- [ ] **GAP15-MC-04-01** Define artifact identity as a cryptographic digest over the deployable unit and require digest algorithm plus normalized artifact media/type metadata.
- [ ] **GAP15-MC-04-02** Integrate GAP-07 provenance attestations and verify subject digest, builder identity, source repository/revision, build invocation, dependency/material digests, and attestation signature.
- [ ] **GAP15-MC-04-03** Validate SBOM subject identity against the same artifact digest; reject mismatched or ambiguous SBOM/provenance subjects.
- [ ] **GAP15-MC-04-04** Define accepted provenance formats (for example DSSE/in-toto/SLSA-compatible envelopes) and schema/version negotiation rules without silently accepting unknown fields as trusted.
- [ ] **GAP15-MC-04-05** Persist provenance statement digest and verification result with certification evidence so later verdict reconstruction does not depend on a mutable external registry.
- [ ] **GAP15-MC-04-06** Handle multi-artifact releases explicitly: image index/manifest list, platform-specific binaries, sidecars, plugins, firmware, and configuration bundles must have deterministic subject relationships.
- [ ] **GAP15-MC-04-07** Define provenance freshness/revocation behavior when a build signer, dependency, or source revision is later compromised; connect to quarantine/revocation workflows.
- [ ] **GAP15-MC-04-08** Prevent tag/name substitution by resolving mutable registry tags to immutable digests before certification and admission decisions.
- [ ] **GAP15-MC-04-09** Add cross-system correlation IDs so artifact provenance events, certification events, admission decisions, and deployment records can be traced end-to-end.
- [ ] **GAP15-MC-04-10** Test forged provenance, digest mismatch, subject confusion, nested manifest mismatch, missing SBOM, revoked builder keys, and registry race/tag-mutation scenarios.
- [ ] **GAP15-MC-04-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-04-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-04-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-04-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-04-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-04-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-04-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-04-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-04-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-04-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 05. Node identity and attestation binding

**Objective:** Bind certification and deployment decisions to measured node hardware, firmware, and security state.
**Primary source references:** C003, C044, C048

### Implementation and hardening checklist

- [ ] **GAP15-MC-05-01** Define a stable node identity model with device ID, attestation key identity, hardware root-of-trust type, platform serial/instance identity handling, and privacy boundaries.
- [ ] **GAP15-MC-05-02** Integrate GAP-02/device identity evidence and validate quote/signature, nonce freshness, PCR/measurement set, firmware/boot state, secure-boot status, and attestation trust chain.
- [ ] **GAP15-MC-05-03** Derive the runtime profile from verified measurements/capabilities rather than trusting a caller-provided profile string.
- [ ] **GAP15-MC-05-04** Define attestation freshness windows and re-attestation triggers for reboot, firmware update, hypervisor/runtime change, security-policy update, or suspicious behavior.
- [ ] **GAP15-MC-05-05** Bind attestation evidence to the certification request nonce/session to prevent replay from a different node or prior security state.
- [ ] **GAP15-MC-05-06** Create policy for nodes that cannot provide hardware-backed attestation, including explicit reduced-trust profiles or rejection rather than silent downgrade.
- [ ] **GAP15-MC-05-07** Handle virtualized/containerized nodes by modeling host, guest, hypervisor, confidential-compute, and nested trust relationships explicitly.
- [ ] **GAP15-MC-05-08** Integrate attestation revocation/quarantine so compromised endorsement keys, firmware versions, or measurement baselines invalidate affected decisions quickly.
- [ ] **GAP15-MC-05-09** Protect node identifiers and attestation material in logs/telemetry according to privacy and retention policy while retaining sufficient forensic traceability.
- [ ] **GAP15-MC-05-10** Test replayed quotes, nonce mismatch, cloned identities, untrusted roots, changed PCRs, firmware downgrade, clock uncertainty, and cross-node evidence substitution.
- [ ] **GAP15-MC-05-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-05-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-05-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-05-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-05-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-05-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-05-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-05-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-05-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-05-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 06. Trusted time / clock-skew policy

**Objective:** Establish trustworthy temporal semantics for evidence freshness, TTLs, lifecycle, and replay defenses.
**Primary source references:** C014, C048, C051, C089

### Implementation and hardening checklist

- [ ] **GAP15-MC-06-01** Define authoritative time sources and trust hierarchy for online and disconnected operation, including NTS/NTP/PTP/GPS/hardware-clock options as applicable.
- [ ] **GAP15-MC-06-02** Specify maximum allowed wall-clock skew, monotonic-clock requirements, leap-second handling, rollback detection, and behavior when the trusted time source is unavailable.
- [ ] **GAP15-MC-06-03** Use monotonic time for local elapsed-duration/timeout logic and wall time only for externally meaningful timestamps, documenting conversion and persistence boundaries.
- [ ] **GAP15-MC-06-04** Attach time-confidence metadata to evidence when exact synchronized time is unavailable, and prohibit high-trust certification if required confidence cannot be established.
- [ ] **GAP15-MC-06-05** Detect clock rollback/forward jumps and quarantine or re-evaluate evidence whose freshness or lifecycle interpretation would change materially.
- [ ] **GAP15-MC-06-06** Define offline grace periods that cannot extend certification beyond configured hard expiry/EOL limits without an explicit signed waiver.
- [ ] **GAP15-MC-06-07** Persist observed-at, signed-at, ingested-at, and evaluated-at times separately to distinguish producer delay from verifier delay and replay.
- [ ] **GAP15-MC-06-08** Integrate lifecycle effective dates and certificate TTL calculations with the same trusted-time policy to avoid subsystem-specific interpretations.
- [ ] **GAP15-MC-06-09** Instrument time-offset, source reachability, uncertainty, rollback events, and freshness rejection metrics.
- [ ] **GAP15-MC-06-10** Test boundary conditions around expiry, EOL transitions, leap events, large skew, monotonic reset after reboot, partitioned sites, and restored snapshots.
- [ ] **GAP15-MC-06-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-06-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-06-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-06-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-06-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-06-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-06-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-06-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-06-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-06-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 07. Authentication layer

**Objective:** Strongly authenticate every human, workload, node, producer, and service interacting with certification.
**Primary source references:** C023, C044

### Implementation and hardening checklist

- [ ] **GAP15-MC-07-01** Define principal types and credential mechanisms for users, services, test producers, nodes, automation, and break-glass operators; avoid one shared credential class.
- [ ] **GAP15-MC-07-02** Prefer workload identity/mTLS or short-lived signed tokens over static API keys; document bootstrap and trust-root distribution.
- [ ] **GAP15-MC-07-03** Validate issuer, audience, subject, expiry, not-before, token binding/certificate identity, and nonce/session requirements before request processing.
- [ ] **GAP15-MC-07-04** Implement credential rotation and revocation with bounded cache TTLs so revoked credentials are not trusted indefinitely during control-plane partitions.
- [ ] **GAP15-MC-07-05** Protect authentication endpoints and token-verification paths against enumeration, brute force, replay, downgrade, and confused-deputy flows.
- [ ] **GAP15-MC-07-06** Integrate node/device authentication with attestation where required instead of treating possession of a token as proof of platform state.
- [ ] **GAP15-MC-07-07** Define emergency/break-glass authentication with stronger logging, explicit time limits, approval requirements, and post-use review.
- [ ] **GAP15-MC-07-08** Ensure authentication context propagates across RPC hops and asynchronous ingestion so downstream authorization/audit uses the original actor plus delegated service identity.
- [ ] **GAP15-MC-07-09** Keep secrets and tokens out of logs, metrics labels, traces, exceptions, crash dumps, and exported evidence bundles.
- [ ] **GAP15-MC-07-10** Test expired/revoked tokens, wrong audience/issuer, stolen-token replay, mTLS chain failure, key rotation, clock skew, identity-provider outage, and proxy/header spoofing.
- [ ] **GAP15-MC-07-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-07-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-07-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-07-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-07-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-07-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-07-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-07-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-07-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-07-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 08. Authorization/capability policy

**Objective:** Enforce least privilege for evidence, lifecycle, certification, revocation, and administrative operations.
**Primary source references:** C024, C042, C043

### Implementation and hardening checklist

- [ ] **GAP15-MC-08-01** Define explicit permissions for evidence submit/read, matrix read, lifecycle mutate, reactivation, revocation/quarantine, policy update, trust-store update, backup/restore, and administrative diagnostics.
- [ ] **GAP15-MC-08-02** Model authorization attributes including principal, tenant/site/environment, artifact namespace, runtime family, operation, requested lifecycle transition, and emergency/waiver context.
- [ ] **GAP15-MC-08-03** Choose RBAC/ABAC/capability semantics and document deny-overrides/allow-overrides, inheritance, default-deny behavior, and policy versioning.
- [ ] **GAP15-MC-08-04** Enforce authorization at every service entry point and privileged internal operation; do not rely on UI visibility or caller-side checks.
- [ ] **GAP15-MC-08-05** Require separation of duties for high-impact actions such as EOL reactivation, signer trust changes, revocation reversal, policy overrides, and production GO approval.
- [ ] **GAP15-MC-08-06** Use short-lived scoped capabilities for automation where practical and prevent confused-deputy escalation across services.
- [ ] **GAP15-MC-08-07** Version and sign policy bundles, validate before activation, support deterministic rollback, and record the exact policy revision used for each verdict/action.
- [ ] **GAP15-MC-08-08** Define break-glass authorization with explicit expiry, reason, ticket/incident reference, additional authentication, and immutable audit.
- [ ] **GAP15-MC-08-09** Continuously test for privilege expansion caused by new roles/resources/actions and maintain policy coverage tests.
- [ ] **GAP15-MC-08-10** Add adversarial tests for horizontal/vertical privilege escalation, site escape, wildcard mistakes, stale policy cache, policy rollback, and delegated-token misuse.
- [ ] **GAP15-MC-08-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-08-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-08-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-08-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-08-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-08-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-08-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-08-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-08-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-08-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 09. Schema definitions and validators

**Objective:** Provide normative, versioned machine schemas for all certification contracts.
**Primary source references:** C021, C022, C026, C027

### Implementation and hardening checklist

- [ ] **GAP15-MC-09-01** Create authoritative schemas for PK_CERTIFICATION/1, PK_COMPATIBILITY_MATRIX/1, and PK_RUNTIME_LIFECYCLE/1 using JSON Schema, Protobuf, WIT, or the selected IDL and publish generated artifacts.
- [ ] **GAP15-MC-09-02** Define required/optional fields, types, formats, ranges, enums, identifier grammar, timestamp format, canonicalization rules, and maximum lengths/sizes.
- [ ] **GAP15-MC-09-03** Encode cross-field invariants where possible and implement semantic validators for constraints not expressible in the IDL.
- [ ] **GAP15-MC-09-04** Define unknown-field behavior, duplicate-field handling, numeric precision, Unicode normalization, map ordering/canonicalization, and null/absent semantics.
- [ ] **GAP15-MC-09-05** Version schemas independently from service implementation and specify backward/forward compatibility guarantees, deprecation windows, and breaking-change procedure.
- [ ] **GAP15-MC-09-06** Generate validators/clients from a single source of truth where practical and pin generator/compiler versions for reproducibility.
- [ ] **GAP15-MC-09-07** Fail closed on malformed, ambiguous, unsupported-version, or non-canonical security-sensitive payloads with stable machine-readable error codes.
- [ ] **GAP15-MC-09-08** Publish conformance fixtures for valid/invalid edge cases and use them across all supported language/runtime implementations.
- [ ] **GAP15-MC-09-09** Fuzz parsers/validators for nesting depth, huge collections, Unicode edge cases, duplicate keys, integer overflow, NaN/Inf, malformed timestamps, and type confusion.
- [ ] **GAP15-MC-09-10** Gate releases on schema-compatibility diffing and require explicit approval for any backward-incompatible contract change.
- [ ] **GAP15-MC-09-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-09-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-09-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-09-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-09-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-09-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-09-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-09-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-09-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-09-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 10. Evidence-ingestion boundary

**Objective:** Securely ingest, validate, deduplicate, and atomically commit test evidence.
**Primary source references:** C021-C026, C034, C037

### Implementation and hardening checklist

- [ ] **GAP15-MC-10-01** Define supported ingestion transports (RPC/HTTP/event/file) and one canonical evidence envelope independent of transport.
- [ ] **GAP15-MC-10-02** Authenticate and authorize producer identity before parsing expensive payloads where possible; apply connection/request rate limits and payload-size limits early.
- [ ] **GAP15-MC-10-03** Validate schema, canonicalization, artifact provenance, node attestation, signature, trusted time, test-suite identity/version, and environment/site scope before acceptance.
- [ ] **GAP15-MC-10-04** Implement idempotency keys and deterministic duplicate detection; distinguish exact retries from conflicting resubmissions under the same producer/event identity.
- [ ] **GAP15-MC-10-05** Commit accepted evidence, ledger append, matrix update, revision increment, and audit event in one atomic transaction or a provably recoverable transactional workflow.
- [ ] **GAP15-MC-10-06** Define backpressure, queue limits, producer retry guidance, dead-letter/quarantine handling, and overload behavior that cannot silently drop evidence.
- [ ] **GAP15-MC-10-07** Return stable error categories separating client-fixable validation failures, authorization failures, transient dependency failures, conflicts, and internal faults.
- [ ] **GAP15-MC-10-08** Capture rejection evidence safely for forensics without persisting untrusted secrets or oversized raw payloads indefinitely.
- [ ] **GAP15-MC-10-09** Support batch ingestion only with explicit atomicity semantics and per-item status; prohibit partial success ambiguity.
- [ ] **GAP15-MC-10-10** Test replay, duplicate storm, malformed compression/content-type, zip-bomb-equivalent payloads, partial network writes, dependency outage, transaction abort, and retry-after-crash behavior.
- [ ] **GAP15-MC-10-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-10-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-10-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-10-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-10-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-10-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-10-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-10-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-10-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-10-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 11. Cross-process concurrency control

**Objective:** Prevent lost updates and inconsistent certification state under concurrent writers/readers.
**Primary source references:** C025, C037, C058, C086

### Implementation and hardening checklist

- [ ] **GAP15-MC-11-01** Define authoritative concurrency token(s), preferably matrix/lifecycle/evidence revisions, and require writers to state the revision they observed.
- [ ] **GAP15-MC-11-02** Use transactions, compare-and-swap, serializable isolation, or explicit distributed locks with fencing tokens; document why the chosen mechanism prevents stale writers.
- [ ] **GAP15-MC-11-03** Ensure lifecycle transition, evidence acceptance, revocation, and reactivation races resolve deterministically according to policy precedence.
- [ ] **GAP15-MC-11-04** Prevent ABA problems by using monotonic revisions/event IDs rather than a Boolean or mutable state value alone.
- [ ] **GAP15-MC-11-05** Define retry behavior for optimistic conflicts with bounded exponential backoff, jitter, idempotency, and a maximum retry budget.
- [ ] **GAP15-MC-11-06** Make snapshot/read APIs expose the revision used so callers can detect stale reads and tie decisions to an immutable view.
- [ ] **GAP15-MC-11-07** Handle multi-replica lag explicitly; prohibit a stale replica from authorizing a deployment after revocation/EOL if strong freshness is required.
- [ ] **GAP15-MC-11-08** Emit conflict metrics and structured events with actor, resource key, expected/current revision, and resolution path.
- [ ] **GAP15-MC-11-09** Load-test hot keys and high-contention runtime/profile transitions to validate lock/transaction behavior and fairness.
- [ ] **GAP15-MC-11-10** Build deterministic race tests using barriers/fault injection for simultaneous writers, writer-vs-revocation, lifecycle transitions, snapshot reads, and failover.
- [ ] **GAP15-MC-11-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-11-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-11-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-11-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-11-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-11-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-11-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-11-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-11-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-11-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 12. Tamper-evident security audit stream

**Objective:** Create immutable, attributable security/audit records for all trust-affecting operations.
**Primary source references:** C049, C073, C078

### Implementation and hardening checklist

- [ ] **GAP15-MC-12-01** Define audit event schema with event ID, timestamp/time confidence, actor, delegated identity, action, resource, site/environment, old/new revision, result, reason, trace ID, and security classification.
- [ ] **GAP15-MC-12-02** Capture accepted/rejected evidence, lifecycle changes, EOL reactivation, policy/trust-store changes, revocation/quarantine, backup/restore, administrative access, and break-glass actions.
- [ ] **GAP15-MC-12-03** Make the audit stream append-only and tamper-evident using signed batches, hash chains, WORM storage, or equivalent controls with independent verification.
- [ ] **GAP15-MC-12-04** Separate audit durability from ordinary application logs so log-level changes or retention tuning cannot erase security history.
- [ ] **GAP15-MC-12-05** Enforce strict access controls and dual-control for audit deletion/retention-policy changes; document legal/compliance retention where applicable.
- [ ] **GAP15-MC-12-06** Redact secrets while retaining sufficient identity, digest, and decision metadata for forensic reconstruction.
- [ ] **GAP15-MC-12-07** Export audit checkpoints to an independent trust/storage domain to reduce single-system compromise risk.
- [ ] **GAP15-MC-12-08** Provide sequence-gap, signature/checkpoint, duplicate-event, and clock-anomaly detection.
- [ ] **GAP15-MC-12-09** Integrate audit events with SIEM/SOC pipelines using stable event types and severity mappings without making the external SIEM the sole source of truth.
- [ ] **GAP15-MC-12-10** Test tampering, truncation, reordering, replay, disk-full, exporter outage, and restore scenarios and prove that detection or fail-closed behavior occurs.
- [ ] **GAP15-MC-12-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-12-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-12-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-12-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-12-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-12-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-12-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-12-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-12-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-12-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 13. Revocation/quarantine subsystem

**Objective:** Immediately invalidate unsafe artifacts, runtimes, profiles, signers, nodes, or evidence.
**Primary source references:** C041, C048, C059, C092

### Implementation and hardening checklist

- [ ] **GAP15-MC-13-01** Define revocable subject types and immutable subject identifiers: artifact digest, runtime version/build, profile, node identity, signer key, producer, evidence ID, policy bundle, and certificate/verdict.
- [ ] **GAP15-MC-13-02** Model revocation status, scope, reason code, severity, effective time, issuer/approver, expiry if temporary, superseding record, and supporting incident/advisory references.
- [ ] **GAP15-MC-13-03** Propagate revocation to all admission/certification decision caches within a defined maximum staleness SLO and specify behavior when propagation cannot be confirmed.
- [ ] **GAP15-MC-13-04** Ensure revocation overrides otherwise valid compatibility evidence and cannot be bypassed by stale matrix snapshots or offline caches beyond explicitly bounded emergency rules.
- [ ] **GAP15-MC-13-05** Provide quarantine distinct from permanent revocation for disputed/under-investigation evidence, with a conservative decision policy while quarantined.
- [ ] **GAP15-MC-13-06** Require privileged, separated authorization for revocation reversal/unquarantine and preserve the full immutable history.
- [ ] **GAP15-MC-13-07** Integrate signer/key compromise handling so all affected evidence can be enumerated and re-evaluated without deleting history.
- [ ] **GAP15-MC-13-08** Provide bulk revocation targeting predicates with mandatory dry-run/impact preview and guardrails against accidentally quarantining an entire fleet.
- [ ] **GAP15-MC-13-09** Emit high-priority metrics/alerts and audit events for creation, propagation lag, cache misses, overrides, and reversal.
- [ ] **GAP15-MC-13-10** Test revocation during network partition, stale replica/cache, concurrent admission, node offline operation, rollback/restore, and large-scale emergency invalidation.
- [ ] **GAP15-MC-13-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-13-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-13-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-13-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-13-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-13-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-13-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-13-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-13-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-13-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 14. Production service/API host

**Objective:** Expose certification as a hardened, deployable service boundary.
**Primary source references:** C021, C025-C028, C052, C054, C067, C071

### Implementation and hardening checklist

- [ ] **GAP15-MC-14-01** Define RPC/HTTP/WIT API contracts for evidence ingestion, certification query, matrix snapshot, lifecycle state, explain, revocation, and administrative health operations.
- [ ] **GAP15-MC-14-02** Implement explicit request deadlines, cancellation propagation, server-side timeouts, bounded work queues, connection limits, and per-principal/site rate limits.
- [ ] **GAP15-MC-14-03** Provide readiness distinct from liveness; readiness must reflect required dependencies and must not advertise ready when authoritative writes/critical trust checks cannot be performed.
- [ ] **GAP15-MC-14-04** Implement graceful shutdown that stops new work, drains bounded in-flight requests, flushes audit/evidence transactions, and terminates within a configured deadline.
- [ ] **GAP15-MC-14-05** Use structured, stable machine-readable error codes with safe human detail; map validation, authn/authz, conflict, rate-limit, dependency, timeout, and internal failures consistently.
- [ ] **GAP15-MC-14-06** Apply memory/CPU/file-descriptor/thread limits and safe parser/body limits; test under overload rather than relying on platform defaults.
- [ ] **GAP15-MC-14-07** Terminate TLS/mTLS with modern cipher/protocol policy, certificate rotation, hostname/SAN validation, and peer identity propagation.
- [ ] **GAP15-MC-14-08** Define version negotiation and deprecation for APIs; reject unsupported major versions rather than silently coercing behavior.
- [ ] **GAP15-MC-14-09** Expose health, metrics, build/version/schema/policy revision, and dependency state without leaking secrets or sensitive topology.
- [ ] **GAP15-MC-14-10** Package reproducibly with secure defaults, non-root/least-privilege execution where applicable, immutable filesystem expectations, and deployment manifests.
- [ ] **GAP15-MC-14-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-14-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-14-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-14-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-14-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-14-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-14-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-14-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-14-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-14-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P0 — 15. State recovery and disaster procedures

**Objective:** Recover authoritative certification state without accepting corrupt or stale trust decisions.
**Primary source references:** C055-C060, C089, C095

### Implementation and hardening checklist

- [ ] **GAP15-MC-15-01** Define RPO/RTO targets separately for matrix materialized state, immutable evidence ledger, audit stream, trust/policy state, and revocation state.
- [ ] **GAP15-MC-15-02** Implement automated backups/snapshots with integrity hashes/signatures, encryption, key-recovery procedure, geographic/administrative separation, and retention tiers.
- [ ] **GAP15-MC-15-03** Build crash recovery that replays or reconciles incomplete transactions and verifies ledger/matrix revision continuity before declaring the service ready.
- [ ] **GAP15-MC-15-04** Define authoritative conflict resolution after partition/reconnect, including stale replicas, duplicate evidence, divergent lifecycle changes, and revocation ordering.
- [ ] **GAP15-MC-15-05** Require post-restore consistency checks that reconstruct sampled/all verdicts from evidence and verify audit/checkpoint continuity.
- [ ] **GAP15-MC-15-06** Provide version-aware restore/migration tooling for backups created by supported prior releases and reject unsupported downgrade paths safely.
- [ ] **GAP15-MC-15-07** Exercise dependency-outage modes for identity, KMS/HSM, time, provenance, attestation, database, message bus, and observability backends with explicit degraded/fail-closed behavior.
- [ ] **GAP15-MC-15-08** Document and automate disaster failover/failback, including DNS/service discovery, trust-store synchronization, replication catch-up, and operator approval points.
- [ ] **GAP15-MC-15-09** Run scheduled restore drills and chaos/fault-injection exercises with measured RPO/RTO evidence, not tabletop claims alone.
- [ ] **GAP15-MC-15-10** Gate production readiness on a signed disaster-recovery test report showing backup verification, restore success, data reconciliation, and post-recovery certification correctness.
- [ ] **GAP15-MC-15-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-15-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-15-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-15-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-15-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-15-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-15-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-15-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-15-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-15-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 16. WASI/WIT/component/runtime negotiation engine

**Objective:** Negotiate supported execution contracts instead of exact-string triple matching.
**Primary source references:** C010-C016, C027, C084, C093

### Implementation and hardening checklist

- [ ] **GAP15-MC-16-01** Define the negotiation input model: artifact requirements, runtime capabilities, WASI preview/version, component-model version, WIT worlds/interfaces, feature flags, ABI constraints, and policy context.
- [ ] **GAP15-MC-16-02** Normalize version identifiers and feature names against authoritative registries/specifications; reject ambiguous aliases and unsupported syntax.
- [ ] **GAP15-MC-16-03** Implement deterministic set/range intersection for required vs provided capabilities with explicit mandatory, optional, forbidden, and mutually exclusive features.
- [ ] **GAP15-MC-16-04** Model adapters/shims/polyfills as explicit transformation capabilities with version, trust, performance, and security implications; never infer compatibility because a shim might exist.
- [ ] **GAP15-MC-16-05** Produce a negotiation transcript showing each constraint, candidate runtime capability, rule applied, and final accepted/rejected subset.
- [ ] **GAP15-MC-16-06** Guarantee stable results for identical normalized inputs/policy revisions and include an engine semantic-version identifier in every decision.
- [ ] **GAP15-MC-16-07** Define precedence between spec-version compatibility, runtime vendor extensions, policy prohibitions, lifecycle status, and security revocations.
- [ ] **GAP15-MC-16-08** Handle prerelease/experimental WASI/component features explicitly and require opt-in policy rather than automatic widening.
- [ ] **GAP15-MC-16-09** Create exhaustive conformance vectors for common/edge combinations, including version gaps, feature conflicts, optional interfaces, and runtime-specific extensions.
- [ ] **GAP15-MC-16-10** Benchmark negotiation complexity and bound pathological input cardinality so untrusted manifests cannot cause combinatorial CPU/memory exhaustion.
- [ ] **GAP15-MC-16-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-16-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-16-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-16-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-16-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-16-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-16-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-16-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-16-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-16-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 17. Typed runtime capability model

**Objective:** Represent runtime/node execution characteristics as validated typed data.
**Primary source references:** C011-C016, C021, C084

### Implementation and hardening checklist

- [ ] **GAP15-MC-17-01** Define typed fields for CPU architecture/ISA level, OS/kernel, hypervisor/container, runtime name/build, WASI preview, component-model version, WIT worlds/interfaces, ABI, sandbox mode, filesystem/network/clock/thread capabilities, and accelerators.
- [ ] **GAP15-MC-17-02** Separate immutable hardware facts, measured security state, runtime-advertised capabilities, operator policy labels, and dynamically available resources so trust levels are not conflated.
- [ ] **GAP15-MC-17-03** Define canonical enums/registries plus extension namespaces; reject unknown core values while preserving forward-compatible vendor extensions as explicitly untrusted until policy recognizes them.
- [ ] **GAP15-MC-17-04** Include capability provenance for each field: measured, attested, discovered, configured, inferred, or claimed; certification rules must be able to require specific provenance strength.
- [ ] **GAP15-MC-17-05** Model capability version/range and feature parameters rather than Boolean flags when behavior varies by version, size, or limits.
- [ ] **GAP15-MC-17-06** Normalize CPU/OS/runtime aliases deterministically to prevent equivalent profiles from fragmenting the matrix or bypassing policy.
- [ ] **GAP15-MC-17-07** Define serialization, canonicalization, hashing, and stable profile identity derivation from normalized trusted fields.
- [ ] **GAP15-MC-17-08** Add explicit unknown/unavailable states instead of using null/empty values that could be interpreted as wildcard support.
- [ ] **GAP15-MC-17-09** Provide compatibility migration rules when the capability schema gains fields; older records must not accidentally imply support for new mandatory features.
- [ ] **GAP15-MC-17-10** Validate model fixtures against real supported platforms/runtimes and against deliberately malformed/self-contradictory capability advertisements.
- [ ] **GAP15-MC-17-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-17-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-17-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-17-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-17-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-17-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-17-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-17-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-17-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-17-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 18. Version/range compatibility policy

**Objective:** Apply explicit, testable version-range semantics without unsafe implicit widening.
**Primary source references:** C016, C027, C093

### Implementation and hardening checklist

- [ ] **GAP15-MC-18-01** Select version semantics per namespace (SemVer, spec revision, date/version, vendor build) rather than assuming one comparison algorithm fits all identifiers.
- [ ] **GAP15-MC-18-02** Define inclusive/exclusive range operators, wildcard behavior, prerelease ordering, build metadata significance, epoch handling, and malformed-version rejection.
- [ ] **GAP15-MC-18-03** Document backward/forward compatibility rules for WASI, WIT/interface revisions, component model, ABI, runtime builds, and policy/schema versions separately.
- [ ] **GAP15-MC-18-04** Prohibit implicit major-version widening and require explicit policy for any compatibility inferred across unspecified/minor/patch ranges.
- [ ] **GAP15-MC-18-05** Model known-bad version exclusions and security revocations as first-class constraints that override broad positive ranges.
- [ ] **GAP15-MC-18-06** Version the compatibility-rule set and include the exact policy/rule revision in every certification verdict.
- [ ] **GAP15-MC-18-07** Provide a deterministic range-normalization representation to make caching, comparison, audit, and test fixtures stable.
- [ ] **GAP15-MC-18-08** Detect contradictory constraints early and return explainable unsatisfiable reasons rather than selecting an arbitrary candidate.
- [ ] **GAP15-MC-18-09** Create property-based tests for interval boundaries, prereleases, overflow/large numbers, malformed strings, and equivalent normalized expressions.
- [ ] **GAP15-MC-18-10** Gate rule changes with regression analysis showing which existing artifact/runtime combinations change verdict and why.
- [ ] **GAP15-MC-18-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-18-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-18-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-18-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-18-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-18-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-18-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-18-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-18-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-18-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 19. Feature-subset certification model

**Objective:** Certify only the exact capability subset demonstrated by evidence.
**Primary source references:** C007, C014, C027

### Implementation and hardening checklist

- [ ] **GAP15-MC-19-01** Define hierarchical feature identifiers and dependency relationships so a passing subfeature cannot imply an untested parent/sibling capability.
- [ ] **GAP15-MC-19-02** Represent certification scope as an explicit set of required/tested/passed/failed/not-tested capabilities with version/parameter constraints.
- [ ] **GAP15-MC-19-03** Prevent whole-runtime or whole-profile certification when evidence covers only a subset; the verdict object must expose partial scope unambiguously.
- [ ] **GAP15-MC-19-04** Define aggregation rules for combining multiple evidence records into one subset decision, including contradictory and differently aged results.
- [ ] **GAP15-MC-19-05** Attach evidence IDs to each asserted certified feature so explain/reconstruction can trace feature-level provenance.
- [ ] **GAP15-MC-19-06** Model feature dependencies/conflicts and invalidate dependent features when a prerequisite is failed, revoked, EOL, or expired.
- [ ] **GAP15-MC-19-07** Allow admission callers to specify their required feature set and return compatible only if that complete requirement set is certified and policy-allowed.
- [ ] **GAP15-MC-19-08** Define caching keys that include the required feature set hash to avoid reusing a broader/narrower decision incorrectly.
- [ ] **GAP15-MC-19-09** Create fixtures for partial pass, mixed pass/fail, missing prerequisite, optional feature, forbidden feature, and feature-version boundary cases.
- [ ] **GAP15-MC-19-10** Add UI/API representations that clearly distinguish full profile coverage from partial capability certification.
- [ ] **GAP15-MC-19-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-19-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-19-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-19-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-19-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-19-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-19-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-19-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-19-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-19-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 20. Lifecycle metadata model

**Objective:** Represent deprecation, EOL, replacement, waiver, and reactivation as governed state.
**Primary source references:** C015, C036, C094, C099

### Implementation and hardening checklist

- [ ] **GAP15-MC-20-01** Define lifecycle states and legal transition graph (for example active, deprecated, blocked-for-new, EOL, revoked, reactivated-by-waiver) with no hidden implicit transitions.
- [ ] **GAP15-MC-20-02** Persist effective time, announced time, deprecation/EOL deadlines, reason code, source advisory, approver, replacement runtime/version, and policy revision for each transition.
- [ ] **GAP15-MC-20-03** Model lifecycle at appropriate granularity: runtime family, version/range, platform/profile, environment/site, and artifact interaction where necessary.
- [ ] **GAP15-MC-20-04** Define how lifecycle state interacts with otherwise valid compatibility evidence and whether existing deployments differ from new admissions.
- [ ] **GAP15-MC-20-05** Require signed/authorized reactivation records with scope, expiration, justification, risk acceptance, and owner; never overwrite the original EOL event.
- [ ] **GAP15-MC-20-06** Provide advance-warning queries and event hooks for approaching deprecation/EOL deadlines and unresolved replacements.
- [ ] **GAP15-MC-20-07** Ensure lifecycle time evaluation uses the trusted-time subsystem and survives offline/partitioned operation conservatively.
- [ ] **GAP15-MC-20-08** Version lifecycle policy and preserve historical views so prior admission decisions can be reconstructed under the policy then in force.
- [ ] **GAP15-MC-20-09** Test transition races, backdated/future-dated events, overlapping version ranges, conflicting authorities, expired waivers, and restored stale snapshots.
- [ ] **GAP15-MC-20-10** Expose lifecycle rationale/replacement guidance through explain APIs and operational dashboards.
- [ ] **GAP15-MC-20-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-20-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-20-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-20-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-20-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-20-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-20-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-20-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-20-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-20-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 21. Negative-evidence ageing policy

**Objective:** Define when failed compatibility evidence remains authoritative or must be re-tested.
**Primary source references:** C014-C016, C094

### Implementation and hardening checklist

- [ ] **GAP15-MC-21-01** Classify negative evidence by failure type: deterministic incompatibility, transient infrastructure failure, security-policy failure, performance threshold failure, flaky/indeterminate, or test-harness defect.
- [ ] **GAP15-MC-21-02** Define TTL/retest rules per failure class, runtime/artifact change, test-suite version, policy revision, and environment/site context.
- [ ] **GAP15-MC-21-03** Keep deterministic spec incompatibilities authoritative until relevant inputs/rules change; do not periodically forget a known hard incompatibility without cause.
- [ ] **GAP15-MC-21-04** Require shorter revalidation for transient/operational failures and encode minimum backoff to prevent retest storms.
- [ ] **GAP15-MC-21-05** Invalidate or supersede negative evidence when a relevant artifact/runtime/profile/test-suite/policy change occurs, with explicit causal linkage.
- [ ] **GAP15-MC-21-06** Handle contradictory later positive evidence using confidence/authority/recency rules and conflict workflow rather than simply newest-wins.
- [ ] **GAP15-MC-21-07** Include negative-evidence age and next eligible/required retest time in explain/certification responses.
- [ ] **GAP15-MC-21-08** Prevent offline caches from aging-out a negative result into an implicit positive/unknown deployment authorization.
- [ ] **GAP15-MC-21-09** Instrument stale-negative backlog, retest rate, contradiction rate, and repeated failure clusters for operational analysis.
- [ ] **GAP15-MC-21-10** Test exact TTL boundaries, clock uncertainty, changed test suite, unchanged deterministic failure, transient dependency recovery, and conflicting producers.
- [ ] **GAP15-MC-21-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-21-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-21-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-21-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-21-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-21-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-21-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-21-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-21-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-21-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 22. Automatic recertification scheduler

**Objective:** Schedule evidence refresh without inferring certification from scheduling state.
**Primary source references:** C007, C052, C069, C092

### Implementation and hardening checklist

- [ ] **GAP15-MC-22-01** Define recertification triggers for impending TTL expiry, lifecycle deadline, artifact/runtime/profile change, policy revision, trust-root/key change, revocation advisory, or coverage gap.
- [ ] **GAP15-MC-22-02** Maintain a durable idempotent work queue keyed by certification scope and trigger revision so duplicate scheduler scans do not create uncontrolled work.
- [ ] **GAP15-MC-22-03** Prioritize work using expiry urgency, deployment criticality, fleet population, security severity, coverage gap, and configured fairness across sites/tenants.
- [ ] **GAP15-MC-22-04** Apply per-runtime/test-lab concurrency, rate, CPU/memory, network, and accelerator quotas to prevent recertification storms from destabilizing test infrastructure.
- [ ] **GAP15-MC-22-05** Use leases/fencing for workers and define retry/dead-letter behavior for crashes, timeouts, indeterminate tests, and unavailable target runtimes.
- [ ] **GAP15-MC-22-06** Never convert queued/running/failed-to-run status into a positive verdict; retain previous verdict only within explicit validity rules.
- [ ] **GAP15-MC-22-07** Support cancellation/supersession when a newer artifact/runtime/policy revision makes queued work obsolete.
- [ ] **GAP15-MC-22-08** Expose queue depth, oldest age, deadline risk, throughput, failure reason, retries, saturation, and estimated expiry-miss metrics.
- [ ] **GAP15-MC-22-09** Provide operator controls for pause/drain/prioritize/retry with authorization, audit, and protection against bypassing required tests.
- [ ] **GAP15-MC-22-10** Test massive simultaneous expiry, worker loss, duplicate delivery, partition, stale scheduler leader, priority inversion, and emergency revocation-triggered recertification.
- [ ] **GAP15-MC-22-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-22-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-22-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-22-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-22-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-22-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-22-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-22-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-22-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-22-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 23. Policy-precedence engine

**Objective:** Resolve compatibility, security, lifecycle, residency, SLO, cost, emergency, and waiver policies deterministically.
**Primary source references:** C019, C024, C048, C099

### Implementation and hardening checklist

- [ ] **GAP15-MC-23-01** Define a typed policy-decision model with domains, priorities/precedence, effect (allow/deny/require), scope, effective period, issuer, and revision.
- [ ] **GAP15-MC-23-02** Establish explicit precedence rules; security revocation and hard EOL/unsupported states should not be accidentally overridden by lower-priority cost or convenience policies.
- [ ] **GAP15-MC-23-03** Define how approved waivers can override specific controls and which controls are non-waivable; require exact scope and expiration.
- [ ] **GAP15-MC-23-04** Use deterministic evaluation with a decision trace containing every matched rule, precedence comparison, and final effect.
- [ ] **GAP15-MC-23-05** Validate policy bundles for cycles, contradictory equal-priority rules, unreachable rules, overly broad wildcards, and references to unknown attributes.
- [ ] **GAP15-MC-23-06** Sign/version policy bundles and bind each certification/admission decision to the policy revision actually evaluated.
- [ ] **GAP15-MC-23-07** Implement safe rollout/canary of policy changes with impact simulation against historical/current decision sets before global activation.
- [ ] **GAP15-MC-23-08** Define behavior when the policy engine or policy source is unavailable, including which decisions fail closed and which bounded cached policies are permitted offline.
- [ ] **GAP15-MC-23-09** Provide differential/regression tests demonstrating decision changes across policy revisions and preventing silent behavior drift.
- [ ] **GAP15-MC-23-10** Instrument deny reasons, waiver use, conflicting-rule detection, policy latency/errors, stale-policy age, and rollback events.
- [ ] **GAP15-MC-23-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-23-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-23-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-23-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-23-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-23-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-23-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-23-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-23-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-23-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 24. Offline/disconnected decision cache

**Objective:** Allow bounded offline decisions without extending trust beyond safe limits.
**Primary source references:** C018, C048, C056, C089

### Implementation and hardening checklist

- [ ] **GAP15-MC-24-01** Define exactly which decision artifacts may be cached: signed certification verdict, policy revision, lifecycle snapshot, revocation checkpoint, trust roots, and required evidence digests.
- [ ] **GAP15-MC-24-02** Sign or MAC cache bundles with anti-rollback version/counter data and bind them to site/node/environment scope so a cache copied elsewhere is not automatically trusted.
- [ ] **GAP15-MC-24-03** Enforce hard expiry based on trusted/monotonic time and prohibit cache use beyond EOL, revocation freshness, or policy maximum-offline windows.
- [ ] **GAP15-MC-24-04** Distinguish positive, negative, unknown, revoked, and quarantined entries; never turn absence/expiration into positive authorization.
- [ ] **GAP15-MC-24-05** Define revocation-checkpoint freshness requirements and conservative behavior when the node cannot prove it has a sufficiently recent checkpoint.
- [ ] **GAP15-MC-24-06** Use atomic cache updates with crash-safe write/rename/fsync semantics and validate signature/hash before replacing the last known-good cache.
- [ ] **GAP15-MC-24-07** Limit cache size and eviction so critical deny/revocation information is not evicted preferentially to positive entries.
- [ ] **GAP15-MC-24-08** Reconcile offline decisions and newly observed evidence on reconnect, emitting audit events for decisions taken under disconnected mode.
- [ ] **GAP15-MC-24-09** Expose offline-mode status, cache age, last successful sync, revision IDs, and reason when a decision is denied due to stale/insufficient offline state.
- [ ] **GAP15-MC-24-10** Test clock rollback, snapshot restore, cache tampering, revoked signer, long partition, partial cache write, stale policy, and reconnect conflict scenarios.
- [ ] **GAP15-MC-24-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-24-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-24-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-24-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-24-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-24-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-24-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-24-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-24-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-24-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 25. Environment/site partition enforcement

**Objective:** Make environment/site isolation a storage and authorization invariant.
**Primary source references:** C006, C035, C046, C055

### Implementation and hardening checklist

- [ ] **GAP15-MC-25-01** Define canonical tenant/site/environment identifiers and their hierarchy, normalization, ownership, and lifecycle; reject ambiguous or caller-controlled free-form variants.
- [ ] **GAP15-MC-25-02** Include partition identity in primary/foreign keys, evidence signatures/domain separation, cache keys, audit events, and authorization context.
- [ ] **GAP15-MC-25-03** Enforce row/key-level partition filtering in the persistence layer or separate stores where risk requires; do not depend solely on application query predicates.
- [ ] **GAP15-MC-25-04** Prohibit cross-partition evidence reuse unless an explicit policy defines portable evidence and verifies all environmental assumptions remain equivalent.
- [ ] **GAP15-MC-25-05** Define replication/export rules across sites, including data residency, encryption domain, redaction, and conflict semantics.
- [ ] **GAP15-MC-25-06** Ensure backups/restores preserve partition metadata and cannot accidentally restore one site into another without an explicit remap process.
- [ ] **GAP15-MC-25-07** Apply per-partition quotas and fairness to ingestion, query, recertification, and storage to prevent one site from exhausting shared resources.
- [ ] **GAP15-MC-25-08** Propagate partition context through traces/logs while preventing sensitive site identifiers from leaking to unauthorized consumers.
- [ ] **GAP15-MC-25-09** Build negative authorization tests for horizontal site/tenant escape across every API and asynchronous worker path.
- [ ] **GAP15-MC-25-10** Perform disaster/reconnect tests where partitions diverge independently and later synchronize without cross-contaminating certification state.
- [ ] **GAP15-MC-25-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-25-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-25-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-25-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-25-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-25-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-25-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-25-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-25-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-25-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 26. Metrics exporter

**Objective:** Expose bounded-cardinality operational/security metrics for certification health.
**Primary source references:** C061-C070, C071-C072

### Implementation and hardening checklist

- [ ] **GAP15-MC-26-01** Define RED/USE metrics for API, ingestion, storage, queueing, negotiation, policy evaluation, cryptographic verification, attestation/provenance checks, and cache operations.
- [ ] **GAP15-MC-26-02** Export verdict counts/rates by coarse dimensions, matrix coverage, evidence age, expiry backlog, EOL-in-service, revocation propagation lag, conflict rate, and rejection categories.
- [ ] **GAP15-MC-26-03** Measure p50/p95/p99/worst-case latency and throughput for certification query and evidence ingestion under representative load.
- [ ] **GAP15-MC-26-04** Export resource saturation: CPU, memory, thread/worker pools, file descriptors, database connections, queue depth, storage capacity/IO, and network where relevant.
- [ ] **GAP15-MC-26-05** Design labels for bounded cardinality; prohibit raw artifact IDs, node IDs, trace IDs, signer IDs, or unbounded error strings as metric labels.
- [ ] **GAP15-MC-26-06** Publish metric names, units, types, collection intervals, reset semantics, and SLO calculations in an operations contract.
- [ ] **GAP15-MC-26-07** Protect metrics endpoints with network/auth controls appropriate to deployment and avoid exposing secrets or sensitive topology.
- [ ] **GAP15-MC-26-08** Add synthetic/self metrics for exporter failure, scrape age, dropped samples, and internal observation gaps.
- [ ] **GAP15-MC-26-09** Validate metric correctness under retries, duplicate ingestion, restarts, multi-replica aggregation, and clock changes.
- [ ] **GAP15-MC-26-10** Create alert-ready recording rules or equivalent aggregations for expiry storms, elevated rejection, dependency outage, storage saturation, and SLO burn.
- [ ] **GAP15-MC-26-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-26-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-26-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-26-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-26-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-26-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-26-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-26-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-26-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-26-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 27. Structured logging and distributed tracing

**Objective:** Provide causally linked diagnostics without leaking trust material or secrets.
**Primary source references:** C073-C075, C078-C079

### Implementation and hardening checklist

- [ ] **GAP15-MC-27-01** Define a structured log schema with timestamp, severity, event name, service/build, trace/span ID, operation, partition, decision/evidence/artifact/runtime/profile identifiers (hashed or classified as needed), result, and reason code.
- [ ] **GAP15-MC-27-02** Propagate W3C Trace Context or selected equivalent across RPCs, asynchronous queues, test workers, storage operations, policy calls, and admission integrations.
- [ ] **GAP15-MC-27-03** Create spans around expensive/trust-critical operations including schema validation, signature verification, provenance/attestation verification, DB transaction, policy evaluation, and negotiation.
- [ ] **GAP15-MC-27-04** Define sampling that preserves errors/security events and supports head/tail sampling without losing rare certification failures.
- [ ] **GAP15-MC-27-05** Redact credentials, signatures/private material, raw attestation secrets, authorization headers, and untrusted payload bodies by default.
- [ ] **GAP15-MC-27-06** Prevent log injection by structured encoding and normalization of untrusted strings; cap field lengths and nesting.
- [ ] **GAP15-MC-27-07** Correlate logs/traces with immutable audit event IDs while keeping audit records independently durable.
- [ ] **GAP15-MC-27-08** Include build version, schema revision, policy revision, matrix revision, and trust-store revision needed to reproduce behavior.
- [ ] **GAP15-MC-27-09** Define retention/access controls and privacy treatment for node/site identifiers and provenance metadata.
- [ ] **GAP15-MC-27-10** Test trace continuity across retries/failover/queues and verify diagnostic output remains usable under overload without causing backpressure collapse.
- [ ] **GAP15-MC-27-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-27-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-27-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-27-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-27-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-27-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-27-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-27-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-27-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-27-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 28. Operator explain endpoint/UI

**Objective:** Explain each verdict using exact evidence, policy, lifecycle, and trust inputs.
**Primary source references:** C076-C077

### Implementation and hardening checklist

- [ ] **GAP15-MC-28-01** Define an explain model containing normalized request, final verdict, matrix revision, policy revision, lifecycle state, evidence IDs/digests, evidence age, signer/provenance/attestation status, and negotiation transcript.
- [ ] **GAP15-MC-28-02** Provide reason codes and remediation actions that distinguish missing evidence, incompatibility, expiry, EOL, revocation, policy denial, signature failure, attestation failure, conflict, and system unavailability.
- [ ] **GAP15-MC-28-03** Ensure explain output is generated from the same decision trace as the actual verdict, not a separately reimplemented approximation.
- [ ] **GAP15-MC-28-04** Apply authorization/redaction so operators see only partitions/artifacts/nodes/evidence they are permitted to inspect.
- [ ] **GAP15-MC-28-05** Expose historical explain for a prior decision/revision to support incident reconstruction and audit.
- [ ] **GAP15-MC-28-06** Provide links/identifiers to superseding evidence, replacement runtimes, active waivers, and required recertification jobs without modifying state implicitly.
- [ ] **GAP15-MC-28-07** Define stable machine-readable explain schema alongside human-readable rendering for automation and UI clients.
- [ ] **GAP15-MC-28-08** Prevent explain calls from re-evaluating against current policy unless explicitly requested; default to explaining the recorded decision context.
- [ ] **GAP15-MC-28-09** Instrument explain latency/errors and test very large evidence histories with pagination/bounds.
- [ ] **GAP15-MC-28-10** Validate explanations with golden fixtures so every verdict/reason category has complete, non-contradictory, actionable output.
- [ ] **GAP15-MC-28-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-28-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-28-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-28-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-28-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-28-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-28-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-28-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-28-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-28-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 29. Alerting/dashboard pack

**Objective:** Deliver actionable operational views and alerts tied to runbooks/SLOs.
**Primary source references:** C080

### Implementation and hardening checklist

- [ ] **GAP15-MC-29-01** Create dashboards for service SLO, certification query/ingestion latency, verdict/rejection trends, coverage, evidence age/expiry, lifecycle/EOL exposure, revocation lag, and queue/resource saturation.
- [ ] **GAP15-MC-29-02** Define alerts for high error/timeout rate, SLO burn, expiry storms, recertification backlog, EOL runtime still admitted/in service, and insufficient matrix coverage.
- [ ] **GAP15-MC-29-03** Add security/trust alerts for signature verification spikes, unknown/revoked signers, attestation/provenance failure, audit-chain gaps, replay detection, and unauthorized administrative attempts.
- [ ] **GAP15-MC-29-04** Alert on database/storage faults, replication lag, backup failure, restore-verification failure, disk capacity, queue growth, and dependency outage.
- [ ] **GAP15-MC-29-05** Use multi-window burn-rate or equivalent anti-noise alerting for SLOs and define severity/owner/escalation for every alert.
- [ ] **GAP15-MC-29-06** Attach a concrete runbook link, diagnostic queries, and expected first actions to each page/alert.
- [ ] **GAP15-MC-29-07** Define maintenance/silence controls with authorization and audit; prevent indefinite silent suppression of critical security/EOL alerts.
- [ ] **GAP15-MC-29-08** Validate alert thresholds using load/fault tests and replay historical incidents or synthetic conditions.
- [ ] **GAP15-MC-29-09** Monitor alert pipeline health so notification failure itself is detectable.
- [ ] **GAP15-MC-29-10** Review dashboards/alerts at each major schema/policy/runtime expansion to ensure new failure categories and dimensions are represented.
- [ ] **GAP15-MC-29-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-29-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-29-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-29-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-29-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-29-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-29-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-29-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-29-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-29-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 30. Admission-control integration

**Objective:** Use certification verdicts as a deterministic deployment/placement gate.
**Primary source references:** C003, C030, C083

### Implementation and hardening checklist

- [ ] **GAP15-MC-30-01** Define the admission request contract containing immutable artifact digest, target runtime/profile/node/site/environment, required feature set, and deployment intent.
- [ ] **GAP15-MC-30-02** Require an exact or policy-approved compatibility decision scoped to the requested artifact/runtime/profile/features; prohibit fuzzy artifact names or unbound tags.
- [ ] **GAP15-MC-30-03** Fail closed on revoked/quarantined artifact/runtime/node/signer, hard EOL, invalid attestation/provenance, stale decision beyond policy, or unavailable authoritative state when required.
- [ ] **GAP15-MC-30-04** Bind admission decision to matrix/policy/lifecycle/revocation revisions and return these in the admission record for later reconstruction.
- [ ] **GAP15-MC-30-05** Integrate GAP-08/SCH-01/PLN-04 using an idempotent stable API and define retry/timeout behavior so scheduler retries do not create inconsistent placements.
- [ ] **GAP15-MC-30-06** Define cache semantics and maximum staleness for high-volume admission; revocation and EOL updates must invalidate or outrank cached allows.
- [ ] **GAP15-MC-30-07** Provide clear denial reason/remediation suitable for scheduler/operator action without exposing sensitive internal details.
- [ ] **GAP15-MC-30-08** Emit immutable admission audit events linking deployment/workload identity to the certification verdict and evidence set used.
- [ ] **GAP15-MC-30-09** Test TOCTOU scenarios where state changes between scheduling and actual launch; define final pre-start recheck where required.
- [ ] **GAP15-MC-30-10** Build end-to-end tests proving unsupported/expired/EOL/revoked combinations cannot be launched through any supported execution tier.
- [ ] **GAP15-MC-30-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-30-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-30-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-30-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-30-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-30-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-30-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-30-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-30-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-30-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 31. Conflict-resolution workflow

**Objective:** Resolve contradictory evidence safely without silent newest-wins behavior.
**Primary source references:** C014, C026, C059, C097

### Implementation and hardening checklist

- [ ] **GAP15-MC-31-01** Define conflict types: same producer/event ID different payload, different trusted producers disagree, later result reverses prior result, test-suite versions disagree, and provenance/attestation mismatch.
- [ ] **GAP15-MC-31-02** Automatically quarantine affected certification scope when conflict severity exceeds configured thresholds; do not continue emitting an allow from ambiguous high-impact evidence.
- [ ] **GAP15-MC-31-03** Assign evidence authority/confidence dimensions based on producer authorization, test-suite version, environment equivalence, attestation/provenance strength, and recency.
- [ ] **GAP15-MC-31-04** Define deterministic auto-resolution only for well-understood cases; route ambiguous/security-sensitive conflicts to human review with separation of duties.
- [ ] **GAP15-MC-31-05** Preserve all conflicting evidence and review actions in the append-only ledger/audit stream; never delete the losing record.
- [ ] **GAP15-MC-31-06** Provide a case object with owner, severity, SLA, linked evidence, affected deployments/sites, containment status, decision, rationale, and follow-up recertification.
- [ ] **GAP15-MC-31-07** Integrate revocation/quarantine and admission control so unresolved critical conflicts block new deployment and optionally trigger existing-fleet actions per policy.
- [ ] **GAP15-MC-31-08** Notify affected test producers/operators and support producer dispute/correction through signed superseding evidence.
- [ ] **GAP15-MC-31-09** Measure conflict rate, time-to-contain, time-to-resolve, recurring producer/test issues, and false-positive/false-negative postmortem outcomes.
- [ ] **GAP15-MC-31-10** Test simultaneous contradictory submissions, stale replicas, producer key compromise, withdrawn evidence, and resolution during disconnected operation.
- [ ] **GAP15-MC-31-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-31-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-31-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-31-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-31-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-31-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-31-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-31-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-31-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-31-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P1 — 32. Capacity and resource controls

**Objective:** Bound resource use and preserve service fairness/availability under load or abuse.
**Primary source references:** C017, C028, C054, C067, C069

### Implementation and hardening checklist

- [ ] **GAP15-MC-32-01** Define tested hard/soft limits for request body, batch size, identifier length, evidence history, matrix cardinality, query page size, concurrent requests, and queued jobs.
- [ ] **GAP15-MC-32-02** Apply rate limits per principal/site/producer plus global protection with clear retry-after semantics and separate limits for expensive cryptographic/negotiation operations.
- [ ] **GAP15-MC-32-03** Use bounded queues and worker pools; reject/shear load predictably before memory or thread exhaustion.
- [ ] **GAP15-MC-32-04** Implement storage quotas/retention policies with alarms and emergency headroom; never evict authoritative deny/revocation/audit data merely to preserve positive cache entries.
- [ ] **GAP15-MC-32-05** Protect database pools, connection counts, prepared statement/query complexity, and scan ranges; require pagination/index use for potentially unbounded queries.
- [ ] **GAP15-MC-32-06** Bound parser recursion/nesting, decompression ratio, attachment sizes, and canonicalization work to mitigate CPU/memory exhaustion.
- [ ] **GAP15-MC-32-07** Ensure one tenant/site/runtime/test producer cannot monopolize scheduler/test-lab capacity; implement weighted fairness or quotas where shared.
- [ ] **GAP15-MC-32-08** Create overload modes that preserve health/admin/revocation paths even when ordinary certification traffic is saturated.
- [ ] **GAP15-MC-32-09** Continuously export capacity/saturation metrics and define scaling thresholds tied to measured performance rather than arbitrary defaults.
- [ ] **GAP15-MC-32-10** Run stress/soak/adversarial tests beyond expected peak, including hot-key contention and bursty expiry storms, and document safe operating envelope.
- [ ] **GAP15-MC-32-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-32-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-32-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-32-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-32-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-32-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-32-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-32-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-32-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-32-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 33. Real adjacent-layer integration tests

**Objective:** Verify live contracts with GAP-02, GAP-07, GAP-08, SCH-01, PLN-04, and execution tiers.
**Primary source references:** C030, C083

### Implementation and hardening checklist

- [ ] **GAP15-MC-33-01** Create version-pinned integration environments for each adjacent subsystem and every supported execution tier instead of mocks only.
- [ ] **GAP15-MC-33-02** Exercise identity/attestation intake from GAP-02 with valid, stale, revoked, malformed, and unavailable attestation cases.
- [ ] **GAP15-MC-33-03** Exercise artifact provenance/SBOM verification from GAP-07 including digest mismatch, revoked signer, and multi-platform artifacts.
- [ ] **GAP15-MC-33-04** Exercise GAP-08 rollout/admission and SCH-01/PLN-04 scheduling/placement gates with allow, deny, unknown, expired, EOL, revoked, and conflict verdicts.
- [ ] **GAP15-MC-33-05** Validate propagation of artifact/runtime/profile/site identifiers and trace/audit correlation across system boundaries.
- [ ] **GAP15-MC-33-06** Pin and test schema/API compatibility across supported version combinations and fail the build on undocumented breaking changes.
- [ ] **GAP15-MC-33-07** Inject realistic latency, retries, duplicate delivery, cancellation, timeout, and partial dependency outage between layers.
- [ ] **GAP15-MC-33-08** Run tests against actual persistence/authn/authz/trust-store components used in production-like deployment.
- [ ] **GAP15-MC-33-09** Capture machine-readable evidence linking each integration test to requirements and build IDs.
- [ ] **GAP15-MC-33-10** Add release-gate coverage requiring all critical adjacent-layer scenarios to pass before production promotion.
- [ ] **GAP15-MC-33-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-33-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-33-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-33-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-33-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-33-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-33-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-33-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-33-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-33-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 34. Runtime compatibility test matrix/fixtures

**Objective:** Maintain authoritative test coverage across supported execution combinations.
**Primary source references:** C029, C084

### Implementation and hardening checklist

- [ ] **GAP15-MC-34-01** Inventory supported CPU architectures/ISA levels, OS/kernel/hypervisor modes, runtimes/builds, WASI previews, component-model versions, WIT interfaces/worlds, providers, and protocol versions.
- [ ] **GAP15-MC-34-02** Derive a risk-based combinatorial matrix defining mandatory full coverage vs pairwise/orthogonal-array coverage for lower-risk dimensions.
- [ ] **GAP15-MC-34-03** Create immutable fixture artifacts with known requirements/behaviors and signed provenance so test failures are attributable to runtime compatibility rather than fixture drift.
- [ ] **GAP15-MC-34-04** Include positive, expected-negative, boundary-version, deprecated/EOL, optional-feature, forbidden-feature, and malformed-capability fixtures.
- [ ] **GAP15-MC-34-05** Version test suites and store harness/toolchain/container/runtime digests with each result.
- [ ] **GAP15-MC-34-06** Automate matrix generation from supported-version manifests so newly added runtime/profile combinations create visible coverage gaps by default.
- [ ] **GAP15-MC-34-07** Define environment parity requirements for lab vs production hardware/security mode to avoid certifying on materially different configurations.
- [ ] **GAP15-MC-34-08** Capture deterministic seeds, environment variables, resource limits, and timing thresholds needed for reproducible reruns.
- [ ] **GAP15-MC-34-09** Publish coverage metrics by criticality and block release/admission expansion when required cells lack fresh evidence.
- [ ] **GAP15-MC-34-10** Retire fixtures/runtimes through lifecycle policy while preserving historical evidence needed to reconstruct prior decisions.
- [ ] **GAP15-MC-34-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-34-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-34-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-34-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-34-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-34-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-34-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-34-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-34-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-34-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 35. Parser/schema fuzzing suite

**Objective:** Continuously fuzz every untrusted parser and validator boundary.
**Primary source references:** C050, C085

### Implementation and hardening checklist

- [ ] **GAP15-MC-35-01** Enumerate fuzz targets for JSON/Protobuf/WIT/IDL decoders, identifier/version parsers, evidence envelopes, lifecycle events, signatures, provenance/attestation metadata, query filters, and import/export files.
- [ ] **GAP15-MC-35-02** Build harnesses that call production parser/validator code directly with sanitizers/instrumentation where language/runtime supports it.
- [ ] **GAP15-MC-35-03** Seed corpora with valid/invalid schema fixtures, historical bugs, edge encodings, deep nesting, huge lengths/counts, duplicate keys, and version corner cases.
- [ ] **GAP15-MC-35-04** Use coverage-guided mutation and maintain corpus minimization/reproducible crashing inputs.
- [ ] **GAP15-MC-35-05** Assert fail-closed behavior, bounded CPU/memory, no panic/uncaught exception, no out-of-bounds access, no infinite loops, and stable error classification.
- [ ] **GAP15-MC-35-06** Fuzz canonicalization/digest/signature preprocessing to detect semantic differentials where two encodings produce inconsistent verification outcomes.
- [ ] **GAP15-MC-35-07** Run differential tests across supported language implementations/generated clients where applicable.
- [ ] **GAP15-MC-35-08** Integrate fuzzing into CI for short runs and scheduled longer campaigns with crash artifact retention and deduplication.
- [ ] **GAP15-MC-35-09** Define triage SLA/severity for parser crashes, hangs, memory blowups, and validation bypasses.
- [ ] **GAP15-MC-35-10** Regress every discovered fuzz bug with a permanent unit/conformance test before closure.
- [ ] **GAP15-MC-35-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-35-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-35-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-35-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-35-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-35-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-35-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-35-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-35-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-35-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 36. Security/adversarial suite

**Objective:** Validate trust boundaries against realistic attacker behaviors.
**Primary source references:** C041, C050, C087

### Implementation and hardening checklist

- [ ] **GAP15-MC-36-01** Build replay scenarios for evidence, attestation quotes, tokens, signed cache bundles, lifecycle events, and revocation checkpoints across node/site/environment boundaries.
- [ ] **GAP15-MC-36-02** Test spoofing/identity confusion across signer IDs, key IDs, producer identities, artifact tags vs digests, node IDs, and delegated service identities.
- [ ] **GAP15-MC-36-03** Test signature/algorithm confusion, canonicalization ambiguity, weak/unknown algorithms, revoked keys, trust-root rollback, and compromised signer blast radius.
- [ ] **GAP15-MC-36-04** Attempt horizontal/vertical privilege escalation for evidence submission, lifecycle change, reactivation, revocation reversal, policy/trust-store administration, backup, and explain/audit access.
- [ ] **GAP15-MC-36-05** Test injection classes relevant to selected stack: SQL/NoSQL/query language, header/log, path, command/process execution in test runners, template/UI, and deserialization.
- [ ] **GAP15-MC-36-06** Exercise resource exhaustion with oversized/nested payloads, duplicate storms, expensive negotiation sets, hot keys, connection floods, and recertification storms.
- [ ] **GAP15-MC-36-07** Test tenant/site isolation and cross-partition cache/database leakage using malicious identifiers and stale authorization context.
- [ ] **GAP15-MC-36-08** Exercise stale-control-plane and dependency-outage scenarios for KMS/HSM, identity, time, provenance, attestation, policy, database, and revocation services.
- [ ] **GAP15-MC-36-09** Run threat-model-driven red-team scenarios around offline mode, restore/rollback, break-glass, emergency waiver, and operator conflict resolution.
- [ ] **GAP15-MC-36-10** Require documented remediation/regression evidence for every high/critical finding before production gate approval.
- [ ] **GAP15-MC-36-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-36-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-36-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-36-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-36-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-36-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-36-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-36-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-36-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-36-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 37. Concurrency/race suite

**Objective:** Prove correctness under interleaving writes, reads, transitions, and failover.
**Primary source references:** C058, C086

### Implementation and hardening checklist

- [ ] **GAP15-MC-37-01** Create deterministic race harnesses using barriers/hooks to force interleavings rather than relying only on probabilistic stress tests.
- [ ] **GAP15-MC-37-02** Test concurrent identical and conflicting evidence submissions against the same certification key and verify idempotency/revision semantics.
- [ ] **GAP15-MC-37-03** Test lifecycle transitions racing certification queries, evidence acceptance, EOL reactivation, and waiver expiry.
- [ ] **GAP15-MC-37-04** Test revocation/quarantine racing admission checks and cached positive verdict use, proving revocation precedence.
- [ ] **GAP15-MC-37-05** Test simultaneous policy/trust-store revision changes and in-flight certification operations with explicit snapshot semantics.
- [ ] **GAP15-MC-37-06** Test cross-replica writes/read-after-write behavior through leader failover, replica lag, retry, and network partition.
- [ ] **GAP15-MC-37-07** Test backup/snapshot/restore or migration while writes are active according to supported operational procedure.
- [ ] **GAP15-MC-37-08** Assert no lost updates, duplicate ledger sequence IDs, torn transactions, negative revision movement, or unexplained verdict nondeterminism.
- [ ] **GAP15-MC-37-09** Instrument and assert conflict/retry budgets to detect livelock/starvation under hot-key contention.
- [ ] **GAP15-MC-37-10** Run long-duration randomized concurrency stress in addition to deterministic cases and retain seeds for any discovered failure.
- [ ] **GAP15-MC-37-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-37-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-37-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-37-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-37-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-37-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-37-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-37-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-37-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-37-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 38. Fault-injection and disaster suite

**Objective:** Validate correct failure/recovery under infrastructure and dependency faults.
**Primary source references:** C060, C089

### Implementation and hardening checklist

- [ ] **GAP15-MC-38-01** Inject process kill/crash at every durable transaction stage: before ledger append, after append, before matrix materialization, before audit, and during response delivery.
- [ ] **GAP15-MC-38-02** Inject disk-full, read-only filesystem, fsync failure, slow IO, corruption, unavailable volume, and database transaction abort/timeout conditions.
- [ ] **GAP15-MC-38-03** Inject network partition, packet loss, duplication, delay, reordering, DNS/service-discovery failure, and TLS/certificate errors between critical dependencies.
- [ ] **GAP15-MC-38-04** Inject stale replica/leader failover/split-brain conditions and verify strong-freshness operations do not authorize from unsafe stale state.
- [ ] **GAP15-MC-38-05** Inject KMS/HSM, time, identity, provenance, attestation, policy, message-bus, and observability outages individually and in combinations.
- [ ] **GAP15-MC-38-06** Restore from verified backup at supported prior schema versions and validate automatic/manual migrations plus verdict reconstruction.
- [ ] **GAP15-MC-38-07** Simulate site loss and failover/failback including revocation/policy synchronization and disconnected decisions produced during the incident.
- [ ] **GAP15-MC-38-08** Measure achieved RPO/RTO and compare against service objectives; capture data loss/inconsistency explicitly.
- [ ] **GAP15-MC-38-09** Verify readiness remains false until authoritative state/audit/ledger consistency checks complete after recovery.
- [ ] **GAP15-MC-38-10** Produce signed machine-readable disaster test evidence for the release gate.
- [ ] **GAP15-MC-38-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-38-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-38-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-38-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-38-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-38-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-38-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-38-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-38-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-38-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 39. Benchmark/soak/fleet-scale suite

**Objective:** Characterize latency, throughput, resource use, and stability at production scale.
**Primary source references:** C061-C070, C088

### Implementation and hardening checklist

- [ ] **GAP15-MC-39-01** Define representative and worst-case workload models for certification reads, evidence writes, explain queries, lifecycle changes, revocations, and recertification bursts.
- [ ] **GAP15-MC-39-02** Measure p50/p95/p99/max latency, sustainable throughput, error rate, queue delay, startup/recovery time, and dependency call distribution.
- [ ] **GAP15-MC-39-03** Measure CPU, memory/GC, thread/task counts, database connections, storage bytes/IOPS, network, and accelerator/power/thermal metrics where applicable.
- [ ] **GAP15-MC-39-04** Benchmark cold vs warm caches, small vs large evidence histories, low/high matrix cardinality, and hot-key contention.
- [ ] **GAP15-MC-39-05** Include cryptographic verification, provenance/attestation checking, negotiation complexity, and policy evaluation in realistic end-to-end paths.
- [ ] **GAP15-MC-39-06** Run fleet-scale tests matching projected artifact/runtime/profile/site cardinalities plus documented growth headroom.
- [ ] **GAP15-MC-39-07** Run multi-hour/day soak tests to detect leaks, fragmentation, queue drift, cache growth, revision lag, and time-dependent failures.
- [ ] **GAP15-MC-39-08** Define hard performance regression budgets and compare builds automatically against a versioned baseline on controlled hardware.
- [ ] **GAP15-MC-39-09** Capture exact build/config/hardware/runtime/database versions and deterministic load-generator parameters with every benchmark artifact.
- [ ] **GAP15-MC-39-10** Publish safe operating envelope and capacity model used to size production and alert thresholds.
- [ ] **GAP15-MC-39-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-39-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-39-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-39-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-39-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-39-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-39-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-39-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-39-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-39-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 40. Release acceptance evidence bundle

**Objective:** Emit a signed machine-readable bundle proving every release gate.
**Primary source references:** C020, C090, C100

### Implementation and hardening checklist

- [ ] **GAP15-MC-40-01** Define a release-evidence manifest with product version/build digest, source revision, reproducible-build/provenance references, SBOM digest, schema/API versions, policy compatibility, and supported-runtime manifest.
- [ ] **GAP15-MC-40-02** Link unit/integration/conformance/fuzz/security/concurrency/fault/benchmark results using immutable artifact IDs and hashes rather than mutable CI URLs only.
- [ ] **GAP15-MC-40-03** Include vulnerability/dependency scan results, accepted exceptions, remediation status, and scan-tool/database versions.
- [ ] **GAP15-MC-40-04** Include database migration/rollback/restore evidence and compatibility results against all supported upgrade paths.
- [ ] **GAP15-MC-40-05** Include signed performance/SLO results with environment description and regression comparison.
- [ ] **GAP15-MC-40-06** Include canary/staged rollout plan, emergency disable/rollback proof, and disaster-recovery verification.
- [ ] **GAP15-MC-40-07** Include requirements traceability/gate summary proving every mandatory GAP-15 control has implementation/test/evidence linkage.
- [ ] **GAP15-MC-40-08** Sign the bundle with authorized release identity and timestamp/trust metadata; verify signature before deployment tooling consumes it.
- [ ] **GAP15-MC-40-09** Preserve bundle immutably for each production release and ensure operators can independently verify it offline.
- [ ] **GAP15-MC-40-10** Make production promotion consume and validate the bundle automatically rather than relying on a manually checked document.
- [ ] **GAP15-MC-40-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-40-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-40-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-40-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-40-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-40-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-40-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-40-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-40-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-40-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 41. Requirements traceability matrix artifact

**Objective:** Map every GAP-15 requirement to design, code, tests, evidence, ownership, and status.
**Primary source references:** C020

### Implementation and hardening checklist

- [ ] **GAP15-MC-41-01** Create one authoritative row for each GAP-15-C### requirement with stable requirement ID and normative requirement text.
- [ ] **GAP15-MC-41-02** Add design/ADR references, implementation repository/path/symbol, configuration/policy references, and schema/API elements implementing the control.
- [ ] **GAP15-MC-41-03** Link unit, integration, conformance, security, fault, performance, and operational tests that demonstrate the requirement.
- [ ] **GAP15-MC-41-04** Link the most recent machine-readable runtime/release evidence proving those tests passed on the candidate build.
- [ ] **GAP15-MC-41-05** Record accountable owner, reviewer, implementation status, evidence freshness, applicable environments, and waiver/exception IDs.
- [ ] **GAP15-MC-41-06** Distinguish not-applicable from not-implemented and require rationale/approval for N/A status.
- [ ] **GAP15-MC-41-07** Automatically detect orphan requirements, implementation with no test, tests with no current evidence, and stale evidence beyond policy.
- [ ] **GAP15-MC-41-08** Version the RTM with the product release and preserve historical versions for audit/reconstruction.
- [ ] **GAP15-MC-41-09** Generate human-readable and machine-readable representations from the same data source to avoid drift.
- [ ] **GAP15-MC-41-10** Gate production GO on zero unresolved mandatory rows except explicitly approved unexpired waivers.
- [ ] **GAP15-MC-41-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-41-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-41-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-41-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-41-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-41-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-41-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-41-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-41-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-41-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 42. Architecture Decision Record

**Objective:** Capture approved architectural decisions and their tradeoffs as durable engineering records.
**Primary source references:** C010

### Implementation and hardening checklist

- [ ] **GAP15-MC-42-01** Create ADRs for storage engine/consistency model, append-only ledger strategy, cryptographic trust model, identity/attestation integration, and artifact provenance model.
- [ ] **GAP15-MC-42-02** Document API/IDL choice, schema evolution, version negotiation, canonicalization, and compatibility semantics.
- [ ] **GAP15-MC-42-03** Document lifecycle/EOL/waiver rules and policy precedence, including fail-open/fail-closed decisions for dependency outages/offline mode.
- [ ] **GAP15-MC-42-04** Document runtime capability/negotiation model and reasons for any supported adapters/shims or excluded compatibility assumptions.
- [ ] **GAP15-MC-42-05** Document partitioning/multi-site topology, consistency requirements, replication and disaster recovery architecture.
- [ ] **GAP15-MC-42-06** Document observability/audit separation, data classification, retention, and privacy implications.
- [ ] **GAP15-MC-42-07** For each ADR record context, considered alternatives, decision, consequences, security/reliability impacts, owner, approvers, and date/version.
- [ ] **GAP15-MC-42-08** Link ADRs to requirements and implementation modules, and mark superseded ADRs without deleting historical rationale.
- [ ] **GAP15-MC-42-09** Require architecture/security review for changes that invalidate an accepted ADR assumption.
- [ ] **GAP15-MC-42-10** Include ADR conformance checks in release review so implementation drift becomes visible.
- [ ] **GAP15-MC-42-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-42-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-42-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-42-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-42-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-42-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-42-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-42-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-42-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-42-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 43. Accountable owner/escalation metadata

**Objective:** Assign operational accountability and incident escalation for the certification service.
**Primary source references:** C009, C091, C097

### Implementation and hardening checklist

- [ ] **GAP15-MC-43-01** Define service owner, technical owner, product/control owner, security owner, data/storage owner, and backup delegates with current contact/escalation mechanisms.
- [ ] **GAP15-MC-43-02** Define on-call rotation and severity-based escalation path for outage, incorrect allow/deny, evidence/signature incident, revocation failure, and data integrity event.
- [ ] **GAP15-MC-43-03** Publish support hours, response/acknowledgement objectives, and decision authority boundaries for production changes and emergency actions.
- [ ] **GAP15-MC-43-04** Assign ownership for runtime/test-matrix coverage, lifecycle notices, signer/trust-store administration, and policy review.
- [ ] **GAP15-MC-43-05** Assign incident roles for commander, operations, security, communications, evidence/forensics, and recovery approval.
- [ ] **GAP15-MC-43-06** Connect every alert/runbook and exception/waiver to an accountable owner and expiration/review date.
- [ ] **GAP15-MC-43-07** Automate periodic validation that owner/contact references are resolvable and not stale.
- [ ] **GAP15-MC-43-08** Define handoff/offboarding process for privileged roles, credentials, keys, and unresolved incidents/waivers.
- [ ] **GAP15-MC-43-09** Record ownership metadata in release evidence and operational documentation, not only a transient ticket system.
- [ ] **GAP15-MC-43-10** Exercise escalation through game days/tabletops and capture action items/response-time evidence.
- [ ] **GAP15-MC-43-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-43-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-43-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-43-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-43-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-43-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-43-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-43-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-43-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-43-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 44. Deployment/bootstrap artifacts

**Objective:** Provide reproducible, secure, validated installation and startup artifacts.
**Primary source references:** C031-C040

### Implementation and hardening checklist

- [ ] **GAP15-MC-44-01** Create pinned package/dependency manifests with lockfiles and cryptographic hashes where ecosystem supports them.
- [ ] **GAP15-MC-44-02** Provide deployment manifests/service definitions for supported targets with explicit CPU/memory/storage/network/security-context limits.
- [ ] **GAP15-MC-44-03** Define configuration schema with required values, types, ranges, secret references, defaults, environment overrides, and deprecated settings.
- [ ] **GAP15-MC-44-04** Implement a bootstrap/preflight validator for filesystem permissions, ports, database/schema version, trust roots, identity credentials, clock health, storage headroom, and dependency reachability.
- [ ] **GAP15-MC-44-05** Default to secure settings: TLS/auth required, no anonymous admin, conservative offline cache, bounded payloads/queues, non-debug logging, least privilege, and no sample secrets.
- [ ] **GAP15-MC-44-06** Use external secret stores/files with restrictive permissions; prohibit secrets in images, source, CLI arguments, logs, or example configs.
- [ ] **GAP15-MC-44-07** Build reproducible/immutable artifacts where practical and embed build version/source revision/SBOM/provenance identifiers.
- [ ] **GAP15-MC-44-08** Define startup ordering and migration ownership to avoid multiple replicas racing schema migrations.
- [ ] **GAP15-MC-44-09** Provide upgrade/downgrade/rollback procedures with preflight compatibility checks and automatic refusal of unsafe version combinations.
- [ ] **GAP15-MC-44-10** Test clean install, repeated/idempotent bootstrap, upgrade from every supported version, failed bootstrap, missing dependency, bad config, and Windows/Linux/container-specific paths as applicable.
- [ ] **GAP15-MC-44-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-44-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-44-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-44-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-44-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-44-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-44-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-44-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-44-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-44-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 45. Supply-chain artifacts

**Objective:** Secure and document the software build/dependency supply chain.
**Primary source references:** C031, C045, C094

### Implementation and hardening checklist

- [ ] **GAP15-MC-45-01** Generate an SBOM for each release artifact including direct/transitive dependencies, versions, package URLs/identifiers, and artifact digest linkage.
- [ ] **GAP15-MC-45-02** Produce signed build provenance identifying source revision, builder identity, build workflow/configuration, materials/dependencies, and resulting artifact digests.
- [ ] **GAP15-MC-45-03** Sign release artifacts and publish verifiable signature/key/trust information with rotation/revocation procedures.
- [ ] **GAP15-MC-45-04** Pin dependency versions/hashes and define policy for floating registries/tags, vendored code, generated code, and external toolchains.
- [ ] **GAP15-MC-45-05** Run vulnerability/license/malware or integrity scanning as appropriate and capture tool/database versions with findings.
- [ ] **GAP15-MC-45-06** Define severity-based patch SLA, supported-version window, end-of-support policy, and emergency dependency replacement process.
- [ ] **GAP15-MC-45-07** Protect CI build identities/secrets with least privilege, ephemeral runners where feasible, branch/review protections, and controlled release authorization.
- [ ] **GAP15-MC-45-08** Verify downloaded tools/dependencies and isolate network access during build where practical to improve reproducibility.
- [ ] **GAP15-MC-45-09** Publish a supported-runtime/dependency manifest consumed by deployment/bootstrap and release-gate tooling.
- [ ] **GAP15-MC-45-10** Test compromised/revoked signing key workflow, dependency yanking, registry outage, malicious package substitution, and provenance verification failure.
- [ ] **GAP15-MC-45-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-45-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-45-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-45-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-45-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-45-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-45-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-45-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-45-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-45-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 46. Canary/staged rollout and emergency-disable automation

**Objective:** Automate safe promotion, rollback, and kill/disable procedures.
**Primary source references:** C092

### Implementation and hardening checklist

- [ ] **GAP15-MC-46-01** Define rollout stages (dev/test/canary/site subset/percentage/global) with measurable promotion criteria and maximum observation windows.
- [ ] **GAP15-MC-46-02** Automate health/SLO/security/decision-correctness checks that gate progression; do not require operators to manually infer whether the canary is safe.
- [ ] **GAP15-MC-46-03** Define automatic halt/rollback triggers for error/SLO burn, incorrect verdict detection, signature/attestation failures, replication lag, resource saturation, or audit gaps.
- [ ] **GAP15-MC-46-04** Provide emergency disable controls for new admissions, evidence ingestion, specific runtime/artifact/signers, or the service itself with least required blast radius.
- [ ] **GAP15-MC-46-05** Require authentication/authorization, reason, incident reference, expiry where appropriate, and immutable audit for all emergency actions.
- [ ] **GAP15-MC-46-06** Make rollback compatible with database/schema evolution; use expand/contract or equivalent so application rollback cannot corrupt newer state.
- [ ] **GAP15-MC-46-07** Preserve revocation/security state during rollback; an older binary must not resurrect revoked artifacts/signers or bypass newer deny policy.
- [ ] **GAP15-MC-46-08** Verify canary partition isolation and prevent unintentional cross-site rollout from shared configuration errors.
- [ ] **GAP15-MC-46-09** Rehearse emergency disable/rollback in non-production and production game days, measuring time-to-contain/recover.
- [ ] **GAP15-MC-46-10** Include tested rollout/rollback artifact versions and evidence in the release acceptance bundle.
- [ ] **GAP15-MC-46-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-46-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-46-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-46-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-46-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-46-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-46-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-46-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-46-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-46-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 47. Backup/restore/migration tooling

**Objective:** Provide executable, validated tools for persistent state backup, restore, and version migration.
**Primary source references:** C095

### Implementation and hardening checklist

- [ ] **GAP15-MC-47-01** Implement authenticated CLI/automation for consistent backup of matrix, evidence ledger, audit/checkpoints, lifecycle, policy/trust metadata, and revocation state.
- [ ] **GAP15-MC-47-02** Generate backup manifest with source service version, schema version, revision/checkpoint IDs, file/object hashes, encryption metadata, and creation time.
- [ ] **GAP15-MC-47-03** Encrypt backups with managed keys and verify key recovery/rotation procedures independent of the live service.
- [ ] **GAP15-MC-47-04** Implement restore into isolated staging by default, validating checksums/signatures/schema and refusing corrupted/incompatible backups.
- [ ] **GAP15-MC-47-05** Provide migration commands with dry-run, preflight capacity/compatibility checks, progress reporting, resumability/idempotency where feasible, and deterministic failure codes.
- [ ] **GAP15-MC-47-06** Test migrations from every supported source version, including large datasets, interruption, restart, insufficient space, and malformed legacy records.
- [ ] **GAP15-MC-47-07** Implement post-restore/migration invariants: ledger continuity, matrix revision monotonicity, referential integrity, sampled/full verdict reconstruction, and audit consistency.
- [ ] **GAP15-MC-47-08** Provide rollback plan for migration failures, including when reverse migration is unsupported and restore is required.
- [ ] **GAP15-MC-47-09** Restrict backup/restore/migration privileges and record full audit metadata without logging secrets.
- [ ] **GAP15-MC-47-10** Run periodic automated restore verification and alert on missing, stale, unverifiable, or un-restorable backups.
- [ ] **GAP15-MC-47-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-47-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-47-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-47-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-47-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-47-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-47-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-47-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-47-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-47-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 48. Operational runbooks

**Objective:** Provide executable day-0/day-1/day-2 operating procedures and incident trees.
**Primary source references:** C096-C097

### Implementation and hardening checklist

- [ ] **GAP15-MC-48-01** Create day-0 installation/bootstrap runbook with prerequisites, secure configuration, trust/identity setup, database migration, health validation, and initial backup.
- [ ] **GAP15-MC-48-02** Create day-1 routine operations for adding runtimes/profiles, signer rotation, lifecycle updates, policy deployment, matrix coverage review, and capacity scaling.
- [ ] **GAP15-MC-48-03** Create day-2 maintenance for upgrades, schema migrations, key rotation, restore drills, retention/compaction, dependency patching, and decommissioning.
- [ ] **GAP15-MC-48-04** Document failure trees for elevated deny/error rate, stale/expired evidence, EOL exposure, revocation lag, signature/attestation/provenance failures, storage faults, queue overload, and time-service issues.
- [ ] **GAP15-MC-48-05** Provide incident containment/recovery steps for compromised signer/producer/node, incorrect certification allow, data corruption, partition, and dependency outage.
- [ ] **GAP15-MC-48-06** Include exact diagnostic commands/queries, expected outputs, decision points, safe rollback actions, and escalation contacts where deployment model permits.
- [ ] **GAP15-MC-48-07** Define evidence-preservation steps before destructive repair so forensic/audit history is not lost.
- [ ] **GAP15-MC-48-08** Include disconnected-site and restore/failover procedures with explicit rules for when admissions must stop.
- [ ] **GAP15-MC-48-09** Version runbooks alongside the service and test them in game days; update based on real incident/postmortem findings.
- [ ] **GAP15-MC-48-10** Link every critical alert to the relevant runbook section and validate links during release checks.
- [ ] **GAP15-MC-48-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-48-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-48-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-48-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-48-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-48-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-48-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-48-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-48-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-48-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 49. Exception/waiver registry

**Objective:** Govern temporary deviations with explicit scope, ownership, risk, and expiry.
**Primary source references:** C099

### Implementation and hardening checklist

- [ ] **GAP15-MC-49-01** Define waiver types for lifecycle reactivation, unsupported runtime/artifact combinations, security controls, temporary policy bypass, and operational constraints.
- [ ] **GAP15-MC-49-02** Require immutable waiver ID, exact scope/subjects, requested exception, business/technical justification, risk statement, compensating controls, owner, approvers, created/effective/expiry times, and ticket/incident references.
- [ ] **GAP15-MC-49-03** Define non-waivable controls (for example certain revocations/cryptographic integrity requirements) and enforce them in policy evaluation.
- [ ] **GAP15-MC-49-04** Require separation-of-duties approval for high-risk waivers and stronger approval for production/global scope.
- [ ] **GAP15-MC-49-05** Automatically expire waivers and remove their policy effect without relying on a manual cleanup task.
- [ ] **GAP15-MC-49-06** Provide advance-expiry alerts and prevent renewal from silently extending a waiver without fresh review/approval.
- [ ] **GAP15-MC-49-07** Bind every decision affected by a waiver to the exact waiver ID/revision and expose it in explain/audit output.
- [ ] **GAP15-MC-49-08** Maintain waiver history append-only, including supersession, rejection, early revocation, and compensating-control changes.
- [ ] **GAP15-MC-49-09** Report active/high-risk/near-expiry waivers and recurring waiver patterns as governance debt metrics.
- [ ] **GAP15-MC-49-10** Test expired, revoked, over-broad, wrong-site, wrong-artifact, conflicting, and stale-cached waiver behavior.
- [ ] **GAP15-MC-49-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-49-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-49-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-49-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-49-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-49-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-49-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-49-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-49-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-49-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 50. Formal production exit-gate implementation

**Objective:** Machine-enforce GO/NO_GO using authoritative evidence from all required domains.
**Primary source references:** C100

### Implementation and hardening checklist

- [ ] **GAP15-MC-50-01** Define gate inputs as signed/immutable references to build provenance/SBOM, RTM status, test suites, security/fuzz results, performance/SLO evidence, migration/restore proof, DR evidence, policy/schema compatibility, and waiver registry.
- [ ] **GAP15-MC-50-02** Express gate rules in version-controlled machine-readable policy with mandatory/optional controls and environment-specific thresholds.
- [ ] **GAP15-MC-50-03** Reject missing, stale, unverifiable, mismatched-build, revoked, or superseded evidence; do not treat checklist text or manually entered “pass” labels as evidence.
- [ ] **GAP15-MC-50-04** Require every critical requirement/RTM row to resolve to passing evidence or an authorized unexpired waiver permitted by gate policy.
- [ ] **GAP15-MC-50-05** Bind the gate decision to exact artifact digest, source revision, configuration/policy versions, evidence bundle digest, and gate-policy revision.
- [ ] **GAP15-MC-50-06** Sign the GO/NO_GO result with authorized release identity and preserve it immutably for audit/reconstruction.
- [ ] **GAP15-MC-50-07** Integrate deployment automation so production promotion requires a valid GO token/attestation and cannot be bypassed through an alternate ordinary pipeline.
- [ ] **GAP15-MC-50-08** Define emergency override separately with stronger authorization, bounded scope/time, explicit risk acceptance, and immutable audit.
- [ ] **GAP15-MC-50-09** Provide explain output listing every satisfied/failed/waived control and direct immutable evidence references.
- [ ] **GAP15-MC-50-10** Test evidence substitution, stale evidence, mismatched build, revoked signer, expired waiver, policy rollback, partial CI outage, and attempted pipeline bypass.
- [ ] **GAP15-MC-50-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-50-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-50-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-50-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-50-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-50-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-50-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-50-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-50-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-50-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# P2 — 51. Original source MASTER.md

**Objective:** Restore the authoritative source master prompt/workflow document without fabricating provenance.
**Primary source references:** README/source integrity

### Implementation and hardening checklist

- [ ] **GAP15-MC-51-01** Locate the authoritative original MASTER.md from the same source/version lineage as the supplied v4.1.0 package; do not regenerate content and label it as original.
- [ ] **GAP15-MC-51-02** Verify the candidate source using repository history, release archive, signed tag/checksum, known manifest, or other provenance evidence sufficient to establish authenticity.
- [ ] **GAP15-MC-51-03** Compare README/manifest references against the recovered file name, expected location, version, and purpose.
- [ ] **GAP15-MC-51-04** Compute and record a cryptographic digest for the recovered file and add it to the package integrity manifest.
- [ ] **GAP15-MC-51-05** Preserve original text/line endings/encoding unless a separate normalized derivative is intentionally created and clearly labeled.
- [ ] **GAP15-MC-51-06** If multiple historical variants exist, document selection criteria and retain provenance references rather than merging content silently.
- [ ] **GAP15-MC-51-07** If the authoritative file cannot be found, update documentation to state it is absent/unrecovered instead of inventing a replacement.
- [ ] **GAP15-MC-51-08** Ensure packaging/release checks fail when documentation claims MASTER.md is bundled but the artifact manifest lacks it.
- [ ] **GAP15-MC-51-09** If a new replacement master document is created later, name/version it as a new derived artifact and document that it is not the missing original.
- [ ] **GAP15-MC-51-10** Add source-integrity verification to future release acceptance so README, manifest, and archive contents remain synchronized.
- [ ] **GAP15-MC-51-11** Publish a configuration/contract section for this component with secure defaults, validation rules, versioning strategy, and explicit unsupported states.
- [ ] **GAP15-MC-51-12** Add component-specific metrics, structured logs, trace spans, and immutable audit hooks sufficient to detect failure, saturation, abuse, and trust-decision changes without high-cardinality leakage.
- [ ] **GAP15-MC-51-13** Complete a threat model covering assets, trust boundaries, attacker capabilities, abuse cases, fail-open/fail-closed decisions, and required mitigations for this component.
- [ ] **GAP15-MC-51-14** Implement unit, negative, integration, fault-injection, upgrade/rollback, and concurrency tests appropriate to this component; permanently regress every discovered defect.
- [ ] **GAP15-MC-51-15** Document operator procedures, dependency assumptions, recovery actions, and escalation points; link alerts and failure modes to the relevant runbook steps.
- [ ] **GAP15-MC-51-16** Link implementation symbols, tests, configuration, and runtime/release evidence to the corresponding GAP-15 requirements in the requirements traceability matrix.
- [ ] **GAP15-MC-51-17** Assign an accountable owner/reviewer, define SLO/SLA or control objective where applicable, and require signed review before production enablement or material policy change.

### Exit criteria

- [ ] **GAP15-MC-51-EXIT-01** Implementation is present in the production code path and cannot be bypassed through an alternate supported API, worker, deployment path, or offline mode.
- [ ] **GAP15-MC-51-EXIT-02** All mandatory tests and fault/adversarial cases pass on the release candidate with machine-readable evidence tied to the exact build digest.
- [ ] **GAP15-MC-51-EXIT-03** Operational telemetry, runbooks, ownership, rollback/recovery, and release-gate evidence are complete and current; no unresolved critical/high finding remains without an authorized unexpired waiver.

---

# Final production-readiness sign-off

- [ ] **GAP15-SIGNOFF-001** P0 checklist completion = 100%, with no open production-blocking defects.
- [ ] **GAP15-SIGNOFF-002** P1 checklist completion = 100% for every capability advertised as supported in production.
- [ ] **GAP15-SIGNOFF-003** P2 release/verification controls required by the production gate are complete and evidenced.
- [ ] **GAP15-SIGNOFF-004** All waivers are explicitly permitted by policy, narrowly scoped, approved, compensating-controlled, and unexpired.
- [ ] **GAP15-SIGNOFF-005** RTM contains implementation/test/evidence/owner links for every applicable GAP-15 requirement.
- [ ] **GAP15-SIGNOFF-006** Release evidence bundle is signed and independently verifiable against the exact production artifact digest.
- [ ] **GAP15-SIGNOFF-007** Disaster restore and emergency rollback/disable have been exercised on the current major release line.
- [ ] **GAP15-SIGNOFF-008** Security review confirms no known critical/high unmitigated trust-boundary defect.
- [ ] **GAP15-SIGNOFF-009** Adjacent-layer admission integration proves unsupported/expired/EOL/revoked combinations cannot deploy.
- [ ] **GAP15-SIGNOFF-010** Authorized release approvers issue a machine-verifiable GO decision for the candidate build.

## Version history

- **1.0.0** — Initial professional-grade checklist derived from the 51 missing components identified during the GAP-15 v4.2.0 audit.