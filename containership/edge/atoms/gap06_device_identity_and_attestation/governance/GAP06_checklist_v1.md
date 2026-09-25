# GAP-06 Device Identity & Attestation
## Missing Components — Highly Detailed Technical Implementation & Production-Readiness Checklist

**Checklist ID:** `GAP06-MISSING-COMPONENTS-CHECKLIST/1`  
**Baseline package:** GAP-06 v4.2.0 Audited & Hardened  
**Checklist version:** 1.0.0  
**Scope:** The 54 components identified as missing or materially incomplete after the v4.2.0 audit.  

This document is an engineering execution and certification checklist. A checked box means the requirement is implemented **and backed by objective evidence**. Design intent, comments, a passing happy-path demo, or the existence of a checklist entry does not by itself satisfy a control.

## Status convention

- `[ ]` Not started / no acceptable evidence.
- `[~]` In progress / partial implementation; do not count as production-ready.
- `[x]` Implemented, reviewed, tested, and linked to evidence.
- `[!]` Blocked or failed; owner and remediation required.
- `[W]` Waived by approved exception; waiver ID, approver, compensating control, and expiry required.

## Priority interpretation

- **P0 — Production trust blocker:** must be implemented before the subsystem is authorized to make production trust decisions.
- **P1 — Production resilience requirement:** required for a resilient, operable production service.
- **P2 — Release / quality / governance completeness:** required for controlled release, assurance, supportability, and long-term governance.

## Universal completion gate — applies to every component below

Every component-specific checklist is **in addition to** the following universal gate:

- [ ] **U01.** Assign a unique implementation work-item ID and named engineering owner; record security and operations reviewers.
- [ ] **U02.** Define explicit in-scope and out-of-scope behavior, trust assumptions, supported deployment modes, and dependency boundaries.
- [ ] **U03.** Convert the component objective into SHALL-level requirements with measurable acceptance criteria and stable traceability IDs.
- [ ] **U04.** Produce or update architecture/data-flow/state diagrams showing trust boundaries, authoritative state, failure domains, and external dependencies.
- [ ] **U05.** Document all externally observable API/schema/state changes and backward/forward compatibility impact.
- [ ] **U06.** Define configuration parameters with types, defaults, safe bounds, provenance, mutability, and restart requirements.
- [ ] **U07.** Perform threat analysis for spoofing, tampering, replay/rollback, privilege escalation, information leakage, resource exhaustion, and dependency compromise relevant to the component.
- [ ] **U08.** Implement deny-by-default behavior for ambiguous, malformed, unauthorized, stale, or unverifiable inputs whenever the component affects a trust decision.
- [ ] **U09.** Use bounded parsing/queues/caches/retries and explicit input/resource limits; demonstrate that hostile inputs cannot cause unbounded memory, CPU, storage, thread, or connection growth.
- [ ] **U10.** Protect sensitive data in transit and at rest as appropriate; redact logs and prohibit secret/private-key material in diagnostics.
- [ ] **U11.** Add deterministic unit tests for normal, boundary, invalid, stale, duplicate, and failure cases.
- [ ] **U12.** Add integration tests against production-equivalent dependencies and schemas rather than relying only on mocks.
- [ ] **U13.** Add concurrency/fault-injection/negative security tests for race conditions, partial failure, retry duplication, restart, and dependency outage.
- [ ] **U14.** Define required metrics, structured logs, traces, security events, health signals, dashboards, alerts, and cardinality/redaction controls.
- [ ] **U15.** Define operational limits/SLOs, saturation thresholds, load-shedding or fail-closed behavior, and capacity assumptions.
- [ ] **U16.** Document deployment, upgrade, rollback, backup/restore (if stateful), incident response, and recovery procedures.
- [ ] **U17.** Generate machine-verifiable acceptance evidence tied to source commit, build artifact digest, configuration/policy version, test result, and tool/environment versions.
- [ ] **U18.** Update the requirements traceability matrix so every claimed satisfied requirement links to implementation and passing evidence.
- [ ] **U19.** Review open vulnerabilities, waivers, and technical debt; ensure every exception has owner, approver, compensating controls, and expiry.
- [ ] **U20.** Require independent code/security/operations review and satisfy the formal production exit gate before marking the component complete.

## Component-specific checklists


---

# 01. Real hardware attestation verifier

**Priority:** P0  
**Source controls:** `C044, C045`  
**Objective:** Implement production-grade verification of hardware-rooted attestation evidence across TPM 2.0, vTPM, and supported TEE/platform mechanisms.


### Architecture & contract

- [ ] **01.01.** Define a supported-attester matrix covering discrete TPM 2.0, firmware TPM, vTPM, and each TEE/platform adapter, including minimum firmware/API versions and explicitly unsupported modes.
- [ ] **01.02.** Define a canonical quote/evidence envelope that binds verifier challenge nonce, attesting key identity, PCR selection, PCR digest, clock/reset/restart counters, firmware/security-version metadata, and device identity.
- [ ] **01.03.** Parse TPM2B_ATTEST/TPMS_ATTEST structures with a bounds-checked parser; reject trailing bytes, duplicate fields, illegal lengths, unsupported magic/type values, and ambiguous encodings.

### Implementation & data/state

- [ ] **01.04.** Verify quote signatures using the enrolled attestation key and an allow-listed algorithm/profile; reject SHA-1 and other deprecated algorithms unless an explicitly approved migration policy permits them.
- [ ] **01.05.** Recompute PCR digests from the exact quoted PCR selection and compare them byte-for-byte to the quote; support required PCR banks and reject unexpected bank/selection combinations.
- [ ] **01.06.** Parse and replay platform event logs against quoted PCRs; surface the first divergent event and retain the validated event-log digest as evidence.

### Security & failure semantics

- [ ] **01.07.** Add IMA/runtime-measurement verification where supported, including template parsing, file-digest algorithm validation, and policy-controlled treatment of unknown templates.
- [ ] **01.08.** Bind quote freshness to a server-issued challenge with explicit issuance time, expiry, intended node, intended service/tenant, and one-time consumption semantics.
- [ ] **01.09.** Validate TPM clockInfo resetCount/restartCount/safe semantics and define fail-closed behavior for counter rollback or unsafe clock state.

### Verification & interoperability

- [ ] **01.10.** For TEE adapters, verify vendor-specific attestation signatures/certificates, security version numbers, debug state, TCB status, and report-data/channel-binding fields.
- [ ] **01.11.** Implement anti-cuckoo/relay controls such as channel binding, AK-to-device enrollment binding, locality checks where available, and duplicate-active-attester detection.
- [ ] **01.12.** Use hardened cryptographic libraries rather than custom signature primitives; enforce strict public-key sizes, curves, encodings, and signature format validation.

### Operations, evidence & exit

- [ ] **01.13.** Create positive test vectors from at least two hardware/vendor families plus vTPM, and negative vectors for tampered nonce, PCR digest, signature, event log, clock counters, and unsupported algorithms.
- [ ] **01.14.** Expose verifier result codes that distinguish malformed evidence, authentication failure, freshness failure, PCR/event-log mismatch, unsupported platform, TCB failure, and internal verifier error without leaking secrets.
- [ ] **01.15.** Record machine-verifiable evidence containing verifier version, trust-anchor set, policy version, raw-evidence digest, parsed claims digest, decision, reason code, and decision timestamp.

### Component Definition of Done

- [ ] **01.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **01.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **01.D3.** Traceability links `Real hardware attestation verifier` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 02. Endorsement/attestation certificate-chain validation

**Priority:** P0  
**Source controls:** `C044, C045`  
**Objective:** Validate EK/AK certificate paths, key purpose, revocation state, manufacturer roots, and certificate policy before accepting attestation keys.


### Architecture & contract

- [ ] **02.01.** Define authoritative manufacturer/vendor trust stores and a governed process for importing, reviewing, versioning, activating, and retiring roots/intermediates.
- [ ] **02.02.** Parse EK/AK certificates using a strict X.509 implementation; reject malformed DER, duplicate critical extensions, unknown critical extensions, illegal key sizes, and policy-incompatible algorithms.
- [ ] **02.03.** Validate full path construction to an approved trust anchor, including Basic Constraints, path length, name constraints where applicable, validity periods, and signature algorithms.

### Implementation & data/state

- [ ] **02.04.** Validate EK certificate EKU/key-usage/SAN fields and vendor-specific TPM identity attributes according to TCG/vendor profiles.
- [ ] **02.05.** Validate AK certification/proof linking the attestation key to the enrolled hardware root; do not treat an arbitrary self-signed AK as equivalent to hardware-backed identity.
- [ ] **02.06.** Implement OCSP and/or CRL checking policy with responder authentication, freshness limits, stapling/cache behavior, and explicit soft-fail versus hard-fail rules.

### Security & failure semantics

- [ ] **02.07.** Maintain revocation cache persistence across restart and ensure stale revocation data cannot silently become trusted.
- [ ] **02.08.** Enforce certificate time validation against the authoritative time policy and define behavior when trusted time is degraded/unavailable.
- [ ] **02.09.** Capture certificate serials, subject key identifiers, issuer identifiers, trust-anchor IDs, and revocation evidence in the decision record without logging private key material.

### Verification & interoperability

- [ ] **02.10.** Add trust-anchor rollover support with overlap windows, staged activation, rollback, and tests preventing accidental trust-store widening.
- [ ] **02.11.** Add negative tests for expired/not-yet-valid certificates, revoked EK/AK, wrong EKU, invalid chain, untrusted manufacturer root, weak signature algorithm, and malformed extensions.
- [ ] **02.12.** Add manufacturer-root supply-chain validation: provenance metadata, checksum/signature verification, change approval, and periodic root-store reconciliation.

### Operations, evidence & exit

- [ ] **02.13.** Publish a machine-readable certificate-validation policy and compatibility matrix that can be pinned by release and audited independently.

### Component Definition of Done

- [ ] **02.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **02.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **02.D3.** Traceability links `Endorsement/attestation certificate-chain validation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 03. Cryptographic node identity enrollment protocol

**Priority:** P0  
**Source controls:** `C021-C024, C044`  
**Objective:** Create an authenticated lifecycle for node enrollment, proof-of-possession, key rotation, replacement, revocation, recovery, and anti-cloning.


### Architecture & contract

- [ ] **03.01.** Define enrollment states (unseen, pending, enrolled, suspended, revoked, replaced, recovery-pending) and legal state transitions with explicit authorization requirements.
- [ ] **03.02.** Require proof-of-possession for every enrolled identity key and attestation key; bind enrollment to the presented hardware attestation rather than accepting public-key registration alone.
- [ ] **03.03.** Authenticate the enrolling principal/service using mTLS or equivalent workload identity and authorize enrollment by site/tenant/environment policy.

### Implementation & data/state

- [ ] **03.04.** Generate a unique enrollment transaction ID and bind all enrollment messages to node ID, hardware identity, nonce, policy version, and requestor identity.
- [ ] **03.05.** Prevent cloning by detecting duplicate active use of the same hardware root/AK identity from conflicting node identities, sites, or channels.
- [ ] **03.06.** Define key-rotation protocol with overlap, old/new key proof, atomic activation, rollback rules, and revocation of superseded keys.

### Security & failure semantics

- [ ] **03.07.** Define hardware replacement/reimage workflows that preserve auditability without silently transferring trust from old hardware to new hardware.
- [ ] **03.08.** Implement emergency revocation and suspension, including propagating status to verifiers, scheduler/quarantine systems, caches, and disconnected sites.
- [ ] **03.09.** Implement controlled recovery that requires stronger authorization than routine enrollment and cannot bypass proof-of-possession or hardware-root verification.

### Verification & interoperability

- [ ] **03.10.** Protect enrollment against replay using expiring nonces, idempotency keys, transaction-state persistence, and one-time finalization.
- [ ] **03.11.** Encrypt sensitive enrollment traffic in transit; never transmit private keys; zeroize temporary secrets and redact security logs.
- [ ] **03.12.** Create negative tests for duplicate identity, wrong proof key, stale enrollment nonce, revoked hardware, unauthorized operator, cross-tenant enrollment, and partial-transaction replay.

### Operations, evidence & exit

- [ ] **03.13.** Persist a complete lifecycle audit trail linking every key/identity version to its predecessor, approver, evidence, timestamps, and reason code.
- [ ] **03.14.** Define enrollment SLOs, retry semantics, disaster recovery, and fail-closed behavior when the authoritative enrollment store is unavailable.

### Component Definition of Done

- [ ] **03.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **03.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **03.D3.** Traceability links `Cryptographic node identity enrollment protocol` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 04. Workload identity attestation

**Priority:** P0  
**Source controls:** `C006, C011, C044, C046`  
**Objective:** Extend trust decisions from physical/virtual nodes to workloads and bind workload identity to a verified execution environment.


### Architecture & contract

- [ ] **04.01.** Define workload identity types to support (process, service, container, pod, VM, confidential VM/enclave) and the claim set required for each.
- [ ] **04.02.** Define the chain of trust from hardware/node attestation to workload launch evidence, including orchestrator identity and image/artifact provenance.
- [ ] **04.03.** Bind workload identity to immutable image digest, signer/provenance identity, runtime configuration digest, namespace/tenant, and node attestation verdict.

### Implementation & data/state

- [ ] **04.04.** Integrate workload identity issuance with a short-lived credential mechanism (for example SPIFFE-compatible SVID semantics or an equivalent internal contract).
- [ ] **04.05.** Prevent credential transfer by binding issued workload credentials to workload key proof-of-possession and, where possible, the attested execution environment.
- [ ] **04.06.** Validate container/VM launch measurements and reject mutable tag-only references when an immutable digest is required.

### Security & failure semantics

- [ ] **04.07.** Propagate node re-attestation failure/revocation to dependent workload identities according to explicit grace and termination policy.
- [ ] **04.08.** Define workload migration semantics so credentials cannot outlive or detach from the newly attested destination environment.
- [ ] **04.09.** Enforce tenant/site/environment isolation in workload identity namespaces and authorization policy.

### Verification & interoperability

- [ ] **04.10.** Add revocation and forced credential expiry for compromised workloads, nodes, signers, or artifact digests.
- [ ] **04.11.** Create positive/negative integration tests covering node trust loss, workload image substitution, namespace spoofing, replayed launch evidence, and credential theft attempts.
- [ ] **04.12.** Expose explainable workload verdicts linking the workload claim to node evidence, artifact provenance, policy versions, and credential issuance event.

### Operations, evidence & exit

- [ ] **04.13.** Define scale targets for credential issuance/rotation across fleet-wide workload churn and burst scenarios.

### Component Definition of Done

- [ ] **04.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **04.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **04.D3.** Traceability links `Workload identity attestation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 05. Typed external schemas and transports

**Priority:** P0  
**Source controls:** `C021-C030`  
**Objective:** Define versioned, interoperable wire contracts for node identity, attestation, measurement policy, errors, and compatibility behavior.


### Architecture & contract

- [ ] **05.01.** Create normative schemas for PK_NODE_IDENTITY/1, PK_ATTESTATION/1, and PK_ACCEPTED_MEASUREMENTS/1 using protobuf, WIT, OpenAPI/JSON Schema, or another approved IDL.
- [ ] **05.02.** Define field types, required/optional semantics, canonical byte encodings, maximum sizes, default handling, and unknown-field behavior.
- [ ] **05.03.** Define stable enum/error namespaces and prohibit reuse of numeric IDs or semantic meaning across versions.

### Implementation & data/state

- [ ] **05.04.** Include explicit schema_version, policy_version, evidence_format, algorithm identifiers, tenant/site context, timestamps, and correlation IDs where applicable.
- [ ] **05.05.** Define compatibility rules for additive fields, reserved/deprecated fields, breaking changes, minimum/maximum peer versions, and downgrade prevention.
- [ ] **05.06.** Generate client/server bindings from the authoritative schemas and prohibit hand-maintained divergent DTOs.

### Security & failure semantics

- [ ] **05.07.** Apply strict input size/depth/repetition limits to prevent parser amplification and resource exhaustion.
- [ ] **05.08.** Define canonical serialization for all data that is hashed, signed, or placed in tamper-evident logs.
- [ ] **05.09.** Create conformance fixtures with golden binary/JSON encodings and negative malformed examples.

### Verification & interoperability

- [ ] **05.10.** Add cross-language round-trip tests for every supported implementation language and architecture.
- [ ] **05.11.** Add fuzzing for decoders and semantic validators, including unknown fields, duplicate map keys, oversized lengths, invalid UTF encodings, and numeric overflow.
- [ ] **05.12.** Publish transport mappings for gRPC/HTTP/IPC/offline bundles, including content types, timeouts, retries, idempotency keys, and authentication context.

### Operations, evidence & exit

- [ ] **05.13.** Version the schema package independently and record the exact schema artifact digest in release evidence.

### Component Definition of Done

- [ ] **05.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **05.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **05.D3.** Traceability links `Typed external schemas and transports` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 06. Authenticated and authorized service boundary

**Priority:** P0  
**Source controls:** `C023, C024, C042-C047`  
**Objective:** Protect every remote/local API with strong peer authentication, authorization, transport confidentiality, and policy-enforced privilege boundaries.


### Architecture & contract

- [ ] **06.01.** Require mutually authenticated transport for service-to-service calls using mTLS, platform workload identity, or an equivalently strong mechanism.
- [ ] **06.02.** Define distinct identities and roles for nodes, verifier services, policy publishers, operators, auditors, automation, and break-glass administrators.
- [ ] **06.03.** Implement deny-by-default authorization at each RPC/operation, not only at the listener or ingress layer.

### Implementation & data/state

- [ ] **06.04.** Bind authorization decisions to tenant/site/environment and resource identifiers to prevent confused-deputy and cross-tenant access.
- [ ] **06.05.** Validate peer certificate/SVID/token audience, issuer, expiry, revocation status, and proof-of-possession/channel binding where available.
- [ ] **06.06.** Define short-lived credential rotation and ensure servers hot-reload credentials without dropping trust validation.

### Security & failure semantics

- [ ] **06.07.** Enforce TLS protocol/cipher/curve policy and disable legacy renegotiation, weak algorithms, plaintext fallback, and unauthenticated local TCP modes.
- [ ] **06.08.** Protect privileged policy/enrollment/revocation endpoints with stronger authorization and, where required, multi-party approval.
- [ ] **06.09.** Implement request-level security context propagation without trusting caller-supplied identity headers.

### Verification & interoperability

- [ ] **06.10.** Add per-principal rate limits and authorization-failure throttling to reduce credential-stuffing/resource-exhaustion attacks.
- [ ] **06.11.** Redact secrets, credentials, certificate private material, and raw sensitive evidence from logs/traces.
- [ ] **06.12.** Create authorization matrix tests for every endpoint × role × tenant/site combination, including explicit negative tests.

### Operations, evidence & exit

- [ ] **06.13.** Emit auditable authentication/authorization decisions with principal ID, operation, target, policy revision, outcome, and reason code.
- [ ] **06.14.** Define break-glass access with time-bound grants, immutable audit, post-event review, and no permanent bypass path.

### Component Definition of Done

- [ ] **06.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **06.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **06.D3.** Traceability links `Authenticated and authorized service boundary` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 07. Durable security state

**Priority:** P0  
**Source controls:** `C032, C057, C095`  
**Objective:** Persist security-critical state crash-consistently so restart, failover, or recovery cannot reopen replay or trust windows.


### Architecture & contract

- [ ] **07.01.** Define authoritative persistent records for enrollment, identity versions, revocations, outstanding challenges, spent challenges, verdicts, quarantine state, trust anchors, and measurement-policy revisions.
- [ ] **07.02.** Choose a transactional persistence engine with documented durability guarantees, fsync/commit semantics, consistency model, backup strategy, and HA behavior.
- [ ] **07.03.** Make challenge issuance and consumption atomic with respect to persistence; a crash after acceptance must not make a consumed challenge reusable.

### Implementation & data/state

- [ ] **07.04.** Persist revocation and quarantine changes before acknowledging success to callers.
- [ ] **07.05.** Define schema migration strategy with forward/backward compatibility, transactional migration, backup, dry-run validation, and rollback rules.
- [ ] **07.06.** Encrypt sensitive state at rest and separate encryption keys from the database/storage system using managed KMS/HSM controls.

### Security & failure semantics

- [ ] **07.07.** Implement database integrity constraints for uniqueness, foreign keys/references, version monotonicity, and legal state transitions.
- [ ] **07.08.** Protect against rollback to stale snapshots by recording monotonic generation/epoch metadata and validating it during restore/startup.
- [ ] **07.09.** Define retention and compaction policies that preserve replay safety and required forensic history.

### Verification & interoperability

- [ ] **07.10.** Create crash-injection tests at each write boundary for challenge issuance/consume, enrollment, revocation, policy activation, and quarantine.
- [ ] **07.11.** Create backup/restore tests proving restored state rejects previously consumed challenges and retains revocations/quarantine.
- [ ] **07.12.** Expose persistence health, replication lag, transaction latency, storage capacity, corruption/integrity errors, and backup age.

### Operations, evidence & exit

- [ ] **07.13.** Document RPO/RTO targets and validate them with scheduled restore exercises.
- [ ] **07.14.** Fail closed or enter an explicitly defined degraded read-only mode when authoritative security state cannot be durably written.

### Component Definition of Done

- [ ] **07.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **07.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **07.D3.** Traceability links `Durable security state` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 08. Distributed replay protection and HA consistency

**Priority:** P0  
**Source controls:** `C055, C057, C058`  
**Objective:** Guarantee single-consumption freshness semantics across replicas, partitions, failover, and multi-site operation.


### Architecture & contract

- [ ] **08.01.** Define a globally unique challenge identifier and authoritative ownership record including intended node, issuing epoch, expiry, site/tenant, and status.
- [ ] **08.02.** Use linearizable compare-and-set/transactional consume semantics or an equivalent design that prevents two replicas from accepting the same challenge.
- [ ] **08.03.** Define leader/lease/fencing behavior and reject writes from stale leaders after failover.

### Implementation & data/state

- [ ] **08.04.** Persist replica epoch/generation numbers and include them in replay-sensitive operations to detect stale state after restart or failback.
- [ ] **08.05.** Define consistency behavior under network partition: which side can issue/consume challenges, how minority replicas fail, and when fail-closed is mandatory.
- [ ] **08.06.** Prevent nonce issuance collisions across replicas using CSPRNG plus uniqueness enforcement and collision handling.

### Security & failure semantics

- [ ] **08.07.** Define bounded challenge/spent-record retention consistent with maximum evidence replay window, audit requirements, and restore scenarios.
- [ ] **08.08.** Define site failover semantics so challenges issued in one site cannot be erroneously reaccepted after traffic shifts.
- [ ] **08.09.** Implement clock-independent or secure-time-assisted expiry semantics that remain safe under wall-clock skew.

### Verification & interoperability

- [ ] **08.10.** Create concurrency tests with simultaneous consume attempts from multiple replicas and verify exactly one successful commit.
- [ ] **08.11.** Create chaos tests for leader loss, split brain, replication lag, delayed messages, retry storms, and failback.
- [ ] **08.12.** Expose metrics for duplicate consume attempts, fencing failures, stale leader writes, replication lag, conflict retries, and partition mode.

### Operations, evidence & exit

- [ ] **08.13.** Produce formal invariants for challenge lifecycle and verify them with property/state-machine tests.
- [ ] **08.14.** Document operator procedures for partition recovery that do not clear replay state or reset epochs unsafely.

### Component Definition of Done

- [ ] **08.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **08.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **08.D3.** Traceability links `Distributed replay protection and HA consistency` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 09. Signed measurement-policy publication

**Priority:** P0  
**Source controls:** `C036-C039, C045`  
**Objective:** Provide authenticated, provenance-tracked, transactional publication and rollout of accepted measurement policy.


### Architecture & contract

- [ ] **09.01.** Define a canonical signed policy bundle containing policy ID/version, target scope, accepted measurements, algorithms, signer identity, activation window, and rollback metadata.
- [ ] **09.02.** Sign policy bundles with managed offline/online publication keys whose usage is restricted separately from ordinary service credentials.
- [ ] **09.03.** Verify signature, signer authorization, policy schema, semantic invariants, and monotonic version rules before staging.

### Implementation & data/state

- [ ] **09.04.** Require multi-party approval or change-control evidence for high-impact policy changes according to governance requirements.
- [ ] **09.05.** Prevent policy rollback below a minimum trusted version unless an explicitly authorized emergency rollback procedure is invoked.
- [ ] **09.06.** Implement staged rollout by environment/site/ring with canary validation and automatic halt on defined error/attestation-failure thresholds.

### Security & failure semantics

- [ ] **09.07.** Make activation atomic: verifiers must never observe a partially written policy or mixed component set.
- [ ] **09.08.** Cache prior policy versions for deterministic verdict explanation and controlled rollback.
- [ ] **09.09.** Define conflict and precedence rules for overlapping policy scopes and reject ambiguous policy combinations.

### Verification & interoperability

- [ ] **09.10.** Protect against poisoning by validating artifact provenance, signer chain, content digest, expected target scope, and approval metadata.
- [ ] **09.11.** Add offline/disconnected distribution format with signature validation and maximum-staleness rules.
- [ ] **09.12.** Create tests for tampered policy, unauthorized signer, stale version, wrong target scope, partial bundle, rollback attempt, and conflicting policy.

### Operations, evidence & exit

- [ ] **09.13.** Emit publication/activation/rollback events into the tamper-evident audit ledger with signer, approver, digest, and affected scope.
- [ ] **09.14.** Publish machine-readable rollout status and exact active policy digest per verifier/site.

### Component Definition of Done

- [ ] **09.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **09.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **09.D3.** Traceability links `Signed measurement-policy publication` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 10. Authoritative time source

**Priority:** P0  
**Source controls:** `C048, C057`  
**Objective:** Use secure monotonic time semantics for challenge expiry, certificate validity, verdict lifetime, and rollback detection.


### Architecture & contract

- [ ] **10.01.** Define which decisions require monotonic elapsed time versus trusted wall-clock time and prohibit implicit mixing of the two.
- [ ] **10.02.** Integrate an OS monotonic clock for process-local intervals and an authenticated time source for wall-clock validation where required.
- [ ] **10.03.** Define maximum tolerated skew, drift, leap behavior, NTP/PTP source requirements, and alert thresholds.

### Implementation & data/state

- [ ] **10.04.** Persist boot/session epoch metadata so restart cannot cause old challenges/verdicts to regain validity.
- [ ] **10.05.** Use TPM/TEE monotonic counters or trusted clock claims where available and define validation against server time.
- [ ] **10.06.** Detect backward wall-clock jumps and enter a defined degraded/fail-closed state for operations that depend on trusted time.

### Security & failure semantics

- [ ] **10.07.** Detect excessive forward jumps that could prematurely expire policy/certificates and require controlled recovery.
- [ ] **10.08.** Ensure certificate/OCSP/CRL validation uses the same authoritative time policy as attestation freshness.
- [ ] **10.09.** Define disconnected-site time behavior, including holdover duration, maximum offline age, and conditions requiring local rejection.

### Verification & interoperability

- [ ] **10.10.** Add deterministic clock abstraction for tests while preventing test clocks from being enabled in production builds/configuration.
- [ ] **10.11.** Create tests for backward/forward jumps, restart, daylight-saving changes, leap seconds, drift, unavailable time sources, and multi-replica skew.
- [ ] **10.12.** Expose time-source health, offset, uncertainty, sync age, rollback detections, and degraded-mode metrics.

### Operations, evidence & exit

- [ ] **10.13.** Document recovery procedure after time integrity failure without manually bypassing freshness checks.

### Component Definition of Done

- [ ] **10.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **10.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **10.D3.** Traceability links `Authoritative time source` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 11. Quarantine and cordon enforcement integration

**Priority:** P0  
**Source controls:** `C059`  
**Objective:** Turn an attestation failure into enforced scheduler/node-supervisor isolation with deterministic recovery.


### Architecture & contract

- [ ] **11.01.** Define a typed quarantine command/event containing node identity, reason, attestation verdict ID, severity, policy version, creation time, expiry/review state, and correlation ID.
- [ ] **11.02.** Integrate with GAP-01 node supervisor and scheduling control planes so quarantined nodes cannot receive new workloads.
- [ ] **11.03.** Define treatment of already-running workloads: drain, migrate, terminate, isolate network, or preserve for forensics based on reason/severity.

### Implementation & data/state

- [ ] **11.04.** Make quarantine enforcement idempotent and durable across verifier, scheduler, and supervisor restarts.
- [ ] **11.05.** Require explicit trusted re-attestation and/or authorized operator action before clearing quarantine; never clear solely on timeout unless policy explicitly allows it.
- [ ] **11.06.** Propagate revocation and severe policy failures to quarantine immediately with bounded control-plane latency.

### Security & failure semantics

- [ ] **11.07.** Define behavior when enforcement dependencies are unavailable: fail closed for new placement and queue reconciliation work.
- [ ] **11.08.** Prevent a node from self-clearing or spoofing quarantine state through untrusted telemetry.
- [ ] **11.09.** Add signed/correlated audit events for request, enforcement acknowledgement, workload action, operator override, and release.

### Verification & interoperability

- [ ] **11.10.** Create integration tests for scheduler race conditions where placement is attempted concurrently with quarantine.
- [ ] **11.11.** Create recovery tests for supervisor disconnect, scheduler restart, duplicate quarantine events, partial drains, and stale release messages.
- [ ] **11.12.** Expose fleet metrics for quarantined nodes, enforcement latency, pending drains, failed cordons, overrides, and mean time to trusted recovery.

### Operations, evidence & exit

- [ ] **11.13.** Define operator runbooks for forensic hold, false-positive review, emergency capacity pressure, and safe reintegration.

### Component Definition of Done

- [ ] **11.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **11.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **11.D3.** Traceability links `Quarantine and cordon enforcement integration` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 12. Re-attestation scheduler

**Priority:** P0  
**Source controls:** `C018, C048, C091`  
**Objective:** Continuously renew trust before verdict expiry with bounded jitter, retry, disconnected-site, and fail-closed semantics.


### Architecture & contract

- [ ] **12.01.** Define attestation validity period by risk class/platform and compute renewal deadline with a safety margin before hard expiry.
- [ ] **12.02.** Use randomized jitter to avoid synchronized fleet-wide re-attestation storms while preserving maximum-expiry guarantees.
- [ ] **12.03.** Persist next-due/retry state or reconstruct it deterministically after restart without extending trust lifetime.

### Implementation & data/state

- [ ] **12.04.** Define retry schedule with exponential/backoff limits, maximum attempts, transient/permanent error classification, and deadline-aware escalation.
- [ ] **12.05.** Prioritize nodes nearing hard expiry over routine refresh work and apply per-site/global concurrency caps.
- [ ] **12.06.** Define disconnected-site mode with cached policy/trust anchors, maximum offline trust age, and explicit transition to quarantine/limited mode after expiry.

### Security & failure semantics

- [ ] **12.07.** Trigger immediate re-attestation on policy change, trust-anchor change, key rotation, suspicious telemetry, firmware update, migration, or administrative request.
- [ ] **12.08.** Invalidate or shorten dependent workload credentials when node verdict approaches/enters expiry according to policy.
- [ ] **12.09.** Prevent stale scheduler jobs from renewing superseded/revoked identities or old node epochs.

### Verification & interoperability

- [ ] **12.10.** Create simulated-fleet tests for millions of nodes to validate jitter distribution, queue depth, capacity, and expiry miss rate.
- [ ] **12.11.** Create failure tests for verifier outage, storage outage, network partition, time skew, repeated bad evidence, and restart.
- [ ] **12.12.** Expose due/overdue counts, renewal latency, retry depth, hard-expiry events, queue saturation, per-site throughput, and failure reasons.

### Operations, evidence & exit

- [ ] **12.13.** Define an SLO such as maximum percentage of healthy nodes that may reach hard expiry due to control-plane failure and verify it in load tests.

### Component Definition of Done

- [ ] **12.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **12.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **12.D3.** Traceability links `Re-attestation scheduler` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 13. Tamper-evident security audit ledger

**Priority:** P0  
**Source controls:** `C049, C073, C076`  
**Objective:** Create an append-only integrity-protected event record for trust lifecycle and security decisions.


### Architecture & contract

- [ ] **13.01.** Define a versioned security-event schema for enrollment, challenge issuance/consume, attestation verdict, policy change, trust-anchor change, revocation, quarantine, override, and administrative access.
- [ ] **13.02.** Include stable event ID, sequence/epoch, timestamp/time-quality, actor, target, tenant/site, request correlation ID, policy/evidence digests, outcome, and reason code.
- [ ] **13.03.** Chain event records cryptographically (hash chain/Merkle structure or equivalent) and periodically sign checkpoints with an HSM/KMS-protected key.

### Implementation & data/state

- [ ] **13.04.** Store ledger data in append-only/WORM-capable storage with retention and legal/compliance controls appropriate to the deployment.
- [ ] **13.05.** Ensure service operators cannot silently edit or delete past records; separate write, read, export, and administrative privileges.
- [ ] **13.06.** Protect sensitive evidence using redaction/tokenization/encryption while retaining enough hashes/metadata for forensic correlation.

### Security & failure semantics

- [ ] **13.07.** Define ordering semantics across replicas/sites and include replica/site sequence metadata to detect omission/reordering.
- [ ] **13.08.** Implement integrity verification tooling that validates chain continuity, signatures, checkpoint coverage, and record schema.
- [ ] **13.09.** Export signed evidence bundles for incident response and certification without requiring direct production-database access.

### Verification & interoperability

- [ ] **13.10.** Create tamper tests covering record mutation, deletion, insertion, reordering, checkpoint substitution, and stale-ledger replay.
- [ ] **13.11.** Create durability tests for crash during append, storage outage, partial replication, and restore.
- [ ] **13.12.** Expose ledger append failures, signing/checkpoint failures, lag, storage utilization, verification errors, and export failures.

### Operations, evidence & exit

- [ ] **13.13.** Define fail behavior for security operations when the audit ledger cannot accept required events; document which operations must halt versus buffer.

### Component Definition of Done

- [ ] **13.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **13.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **13.D3.** Traceability links `Tamper-evident security audit ledger` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 14. Secrets, KMS, and HSM integration

**Priority:** P0  
**Source controls:** `C039, C047`  
**Objective:** Protect service signing keys, trust-anchor management, encryption keys, and sensitive secrets with managed key infrastructure.


### Architecture & contract

- [ ] **14.01.** Inventory every secret/key class: service TLS keys, policy-signing keys, audit-checkpoint keys, database encryption keys, API credentials, trust-anchor administration keys, and recovery keys.
- [ ] **14.02.** Assign each key a purpose, owner, algorithm, protection class, rotation period, backup/escrow policy, and authorized workload/principal set.
- [ ] **14.03.** Use HSM-backed or managed KMS non-exportable keys for high-value signing operations; prohibit private-key material in source code, images, logs, or ordinary config files.

### Implementation & data/state

- [ ] **14.04.** Implement workload identity based authentication to KMS/HSM and avoid static long-lived cloud/API credentials.
- [ ] **14.05.** Enforce separate keys and IAM policies by environment/tenant/risk domain to limit blast radius.
- [ ] **14.06.** Implement key rotation with overlapping validation windows, atomic signer activation, verifier trust update, and rollback procedure.

### Security & failure semantics

- [ ] **14.07.** Implement key revocation/disable and emergency compromise workflow with propagation to all dependent services and policies.
- [ ] **14.08.** Zeroize in-process sensitive buffers where feasible and bound secret lifetime/caching; never write secret material to crash dumps.
- [ ] **14.09.** Encrypt persisted sensitive state with envelope encryption and record key version/KEK metadata required for recovery.

### Verification & interoperability

- [ ] **14.10.** Create backup/restore tests for keys according to policy without violating non-exportability requirements.
- [ ] **14.11.** Create negative IAM tests proving unauthorized services/operators cannot sign, decrypt, rotate, or modify trust anchors.
- [ ] **14.12.** Enable KMS/HSM audit logging and correlate key-use events with attestation/policy publication actions.

### Operations, evidence & exit

- [ ] **14.13.** Define behavior for KMS/HSM outage, throttling, partial region outage, and key disablement; avoid unsafe local fallback keys.

### Component Definition of Done

- [ ] **14.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **14.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **14.D3.** Traceability links `Secrets, KMS, and HSM integration` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 15. Threat model and adversarial certification

**Priority:** P0  
**Source controls:** `C041, C050, C087`  
**Objective:** Formally model attacker capabilities and validate controls against spoofing, replay, relay, firmware compromise, cloning, side channels, exhaustion, policy compromise, and control-plane abuse.


### Architecture & contract

- [ ] **15.01.** Define assets, trust boundaries, security objectives, assumptions, external dependencies, privileged actors, and deployment variants.
- [ ] **15.02.** Enumerate attacker classes including remote unauthenticated, authenticated malicious node, compromised workload, malicious operator, supply-chain attacker, network MITM, and compromised site control plane.
- [ ] **15.03.** Model spoofing/tampering/repudiation/information-disclosure/DoS/elevation threats for each data flow and state transition.

### Implementation & data/state

- [ ] **15.04.** Explicitly analyze replay, quote substitution, nonce theft, relay/cuckoo attacks, cloned AK/device identity, stale policy, and rollback attacks.
- [ ] **15.05.** Analyze malicious/compromised firmware and cases where PCRs measure an approved-but-vulnerable image; distinguish integrity from security posture.
- [ ] **15.06.** Analyze parser/certificate/event-log attack surface for memory/CPU exhaustion, malformed inputs, algorithm confusion, and differential interpretation.

### Security & failure semantics

- [ ] **15.07.** Analyze tenant boundary failure, confused-deputy behavior, privilege escalation, break-glass misuse, and policy-signing compromise.
- [ ] **15.08.** Analyze side channels and metadata leakage appropriate to the service and deployed TEE/TPM adapters.
- [ ] **15.09.** Map every threat to preventive/detective/recovery controls and to an executable verification artifact where feasible.

### Verification & interoperability

- [ ] **15.10.** Assign residual-risk severity/likelihood, owner, acceptance authority, and expiration/review date.
- [ ] **15.11.** Run adversarial test campaigns/penetration testing against the actual production architecture, not only the reference state machine.
- [ ] **15.12.** Add fuzzing/property tests and chaos cases directly derived from the threat model.

### Operations, evidence & exit

- [ ] **15.13.** Require threat-model review on protocol/schema/crypto/trust-boundary changes and before major releases.
- [ ] **15.14.** Produce a signed security assessment/certification package recording scope, versions tested, findings, remediations, waivers, and evidence.

### Component Definition of Done

- [ ] **15.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **15.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **15.D3.** Traceability links `Threat model and adversarial certification` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 16. Persistent enrollment and measurement-policy API with transactional updates

**Priority:** P1  
**Source controls:** `C033-C038`  
**Objective:** Provide durable CRUD/transaction semantics for enrollment and measurement-policy administration.


### Architecture & contract

- [ ] **16.01.** Define resource models, primary keys, immutable identifiers, revision numbers, lifecycle states, and authorization scope for enrollment and policy records.
- [ ] **16.02.** Expose create/read/update/revoke/publish operations with optimistic concurrency or transactional compare-and-swap guards.
- [ ] **16.03.** Require idempotency keys for mutating operations and persist their results for a bounded retry window.

### Implementation & data/state

- [ ] **16.04.** Validate all updates against schema, security invariants, scope/tenant rules, policy precedence, and signer/approver requirements before commit.
- [ ] **16.05.** Use atomic transactions so related records (policy + activation pointer + audit event, identity + key version + revocation state) cannot partially apply.
- [ ] **16.06.** Implement pagination/filtering with bounded limits and stable cursors; prevent unbounded scans from administrative APIs.

### Security & failure semantics

- [ ] **16.07.** Define retention, tombstone, and deletion restrictions for security/audit-relevant records.
- [ ] **16.08.** Emit change notifications/events only after durable commit and include revision identifiers for downstream idempotency.
- [ ] **16.09.** Create race tests for simultaneous updates, stale revision writes, revoke-vs-rotate, and publish-vs-rollback.

### Verification & interoperability

- [ ] **16.10.** Create failure tests for database timeout, partial transaction failure, event-publish failure, and client retry.
- [ ] **16.11.** Expose transaction latency, conflict rate, failed validations, idempotent replays, and database dependency health.
- [ ] **16.12.** Provide export/backup tooling and migration procedures that preserve revision history and provenance.

### Component Definition of Done

- [ ] **16.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **16.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **16.D3.** Traceability links `Persistent enrollment and measurement-policy API with transactional updates` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 17. Rate limiting, quotas, fairness, and per-principal admission control

**Priority:** P1  
**Source controls:** `C017, C025, C054, C067`  
**Objective:** Prevent overload and abuse while preserving capacity for critical attestation and recovery operations.


### Architecture & contract

- [ ] **17.01.** Define limits by principal, node, tenant, site, source network, endpoint, and operation cost rather than a single global request rate.
- [ ] **17.02.** Use token-bucket/leaky-bucket/concurrency controls with bounded queues and deterministic rejection behavior.
- [ ] **17.03.** Classify operations by cost, including certificate/event-log parsing, cryptographic verification, policy publication, enrollment, and decision explanation.

### Implementation & data/state

- [ ] **17.04.** Reserve capacity for re-attestation nearing hard expiry, revocation/quarantine actions, and control-plane recovery.
- [ ] **17.05.** Prevent one tenant/site from exhausting global verifier CPU, memory, storage, HSM throughput, or database transactions.
- [ ] **17.06.** Apply payload-size and evidence-complexity limits before expensive parsing/crypto work where safe.

### Security & failure semantics

- [ ] **17.07.** Define retry-after/backoff responses and avoid client retry synchronization storms.
- [ ] **17.08.** Rate-limit authentication failures and malformed evidence while preserving forensic visibility.
- [ ] **17.09.** Load-test normal, burst, abusive, and adversarial traffic to establish safe thresholds with headroom.

### Verification & interoperability

- [ ] **17.10.** Create fairness tests demonstrating sustained heavy load from one principal does not starve others.
- [ ] **17.11.** Expose accepted/rejected/queued requests, limiter saturation, per-class latency, cost-unit usage, and top offenders without high-cardinality explosions.
- [ ] **17.12.** Document emergency tuning and safe dynamic configuration with bounds/approval/audit.

### Component Definition of Done

- [ ] **17.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **17.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **17.D3.** Traceability links `Rate limiting, quotas, fairness, and per-principal admission control` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 18. Bounded replay-cache lifecycle design

**Priority:** P1  
**Source controls:** `C067`  
**Objective:** Bound replay-state growth without ever making previously consumed evidence valid again within the security window.


### Architecture & contract

- [ ] **18.01.** Define replay record key, scope, issue/consume timestamps, expiry, identity epoch, and maximum evidence lifetime that determines safe retention.
- [ ] **18.02.** Derive minimum retention from maximum challenge TTL, offline/retry windows, backup/restore age, clock uncertainty, and incident-forensics requirements.
- [ ] **18.03.** Use partitioning/TTL compaction only when deletion cannot reopen a valid replay window.

### Implementation & data/state

- [ ] **18.04.** Persist replay state across restart and include it in backup/restore/failover design.
- [ ] **18.05.** Prevent generation rollback after restore by using monotonic epochs/fencing markers that invalidate stale challenges.
- [ ] **18.06.** Bound outstanding unused challenges separately from spent-challenge history and garbage-collect them after safe expiry.

### Security & failure semantics

- [ ] **18.07.** Protect cache operations with atomic uniqueness/consume constraints at the authoritative store.
- [ ] **18.08.** Capacity-model worst-case adversarial issuance/consume rates and storage amplification.
- [ ] **18.09.** Create long-duration soak tests proving storage remains bounded under expected and attack traffic.

### Verification & interoperability

- [ ] **18.10.** Create replay tests across compaction boundaries, restart, restore from backup, site failover, and clock anomalies.
- [ ] **18.11.** Expose replay-state size, insertion/lookup latency, compaction lag, TTL deletions, duplicate hits, and storage pressure.
- [ ] **18.12.** Document emergency storage-pressure handling that never clears replay state indiscriminately.

### Component Definition of Done

- [ ] **18.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **18.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **18.D3.** Traceability links `Bounded replay-cache lifecycle design` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 19. Structured machine-readable errors

**Priority:** P1  
**Source controls:** `C026`  
**Objective:** Provide stable, safe, actionable error contracts for clients and operators.


### Architecture & contract

- [ ] **19.01.** Define an error envelope with stable code, category, retryability, safe message, correlation ID, optional field violations, and server version.
- [ ] **19.02.** Separate authentication/authorization, malformed request, unsupported capability, freshness failure, attestation failure, policy failure, dependency failure, conflict, throttling, and internal error namespaces.
- [ ] **19.03.** Ensure external messages do not reveal trust-store internals, private certificate material, secret policy details, stack traces, filesystem paths, or database structure.

### Implementation & data/state

- [ ] **19.04.** Define mapping to transport status codes without making clients depend solely on HTTP/gRPC codes.
- [ ] **19.05.** Version error codes additively and never silently reuse a code for a different semantic condition.
- [ ] **19.06.** Include retry-after/deadline hints only when retry is safe and meaningful.

### Security & failure semantics

- [ ] **19.07.** Provide operator-only diagnostics in protected logs/traces correlated by ID, separate from client-facing details.
- [ ] **19.08.** Create conformance tests for every documented error path and check safe redaction.
- [ ] **19.09.** Add fuzz/negative tests to ensure unexpected parser exceptions map to bounded generic errors rather than process crashes or data leakage.

### Verification & interoperability

- [ ] **19.10.** Publish an error catalog with remediation guidance and client retry behavior.

### Component Definition of Done

- [ ] **19.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **19.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **19.D3.** Traceability links `Structured machine-readable errors` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 20. Retry, idempotency, and backpressure contract

**Priority:** P1  
**Source controls:** `C025`  
**Objective:** Make client/server retry behavior safe under duplicates, timeouts, overload, and partial failure.


### Architecture & contract

- [ ] **20.01.** Classify every API operation as read-only, idempotent, conditionally idempotent, or non-idempotent and document retry rules.
- [ ] **20.02.** Require client-generated idempotency keys for enrollment, revocation, policy publication, and other mutating operations that may be retried.
- [ ] **20.03.** Persist idempotency outcome keyed by principal/scope/operation and reject key reuse with different request digests.

### Implementation & data/state

- [ ] **20.04.** Define server deadlines and propagate remaining deadline to downstream dependencies.
- [ ] **20.05.** Implement exponential backoff with jitter and upper bounds; avoid automatic retries on permanent validation/security failures.
- [ ] **20.06.** Apply bounded queues/concurrency limits and return explicit overload signals before resource exhaustion.

### Security & failure semantics

- [ ] **20.07.** Prevent duplicate challenge issuance/consumption and duplicate policy activation under client/network retries.
- [ ] **20.08.** Handle ambiguous commit outcomes by allowing safe status lookup/reconciliation via transaction ID.
- [ ] **20.09.** Create fault-injection tests for response loss after commit, connection reset mid-request, duplicate delivery, delayed response, and downstream timeout.

### Verification & interoperability

- [ ] **20.10.** Expose retry counts, idempotency hits/conflicts, queue depth, shed load, deadline exceeded, and ambiguous-outcome reconciliations.
- [ ] **20.11.** Document client SDK retry defaults and prohibit hidden infinite retries.

### Component Definition of Done

- [ ] **20.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **20.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **20.D3.** Traceability links `Retry, idempotency, and backpressure contract` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 21. Environment, site, and tenant isolation enforcement

**Priority:** P1  
**Source controls:** `C006, C046`  
**Objective:** Enforce administrative and data-plane isolation beyond string labels in the reference model.


### Architecture & contract

- [ ] **21.01.** Define authoritative tenant/site/environment identifiers and prohibit caller-controlled free-form trust domains.
- [ ] **21.02.** Bind authenticated principal identities to allowed tenant/site/environment scopes through authorization policy.
- [ ] **21.03.** Partition or strongly namespace enrollment records, policies, replay state, verdicts, caches, metrics, and audit views by scope.

### Implementation & data/state

- [ ] **21.04.** Ensure challenge issuance and evidence verification require exact scope binding and reject cross-scope reuse.
- [ ] **21.05.** Use separate trust anchors/signing keys/configuration where risk policy requires stronger cryptographic isolation.
- [ ] **21.06.** Prevent cross-tenant policy references, node-ID collisions, data export, and decision-explain access.

### Security & failure semantics

- [ ] **21.07.** Define global-admin actions explicitly and require stronger authentication/approval/audit.
- [ ] **21.08.** Add tests for horizontal privilege escalation using valid credentials from another tenant/site/environment.
- [ ] **21.09.** Add data-layer tests for missing scope predicates and cache-key collisions.

### Verification & interoperability

- [ ] **21.10.** Create backup/restore/export procedures that preserve isolation and access controls.
- [ ] **21.11.** Expose isolation-policy violations as security metrics/events without leaking other tenant identifiers.

### Component Definition of Done

- [ ] **21.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **21.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **21.D3.** Traceability links `Environment, site, and tenant isolation enforcement` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 22. Disconnected and offline attestation mode

**Priority:** P1  
**Source controls:** `C018, C048, C056`  
**Objective:** Support bounded operation during WAN/control-plane loss without silently extending trust indefinitely.


### Architecture & contract

- [ ] **22.01.** Define which verifier functions may run locally/offline and which require central authority.
- [ ] **22.02.** Provision signed cached trust anchors, measurement policies, revocation snapshots, schema versions, and local verifier keys before disconnection.
- [ ] **22.03.** Define maximum offline age separately for policy, revocation data, certificate status, node verdicts, and workload credentials.

### Implementation & data/state

- [ ] **22.04.** Use local secure/monotonic time and detect rollback across reboot where platform capabilities allow.
- [ ] **22.05.** Issue offline verdicts with explicit degraded/offline provenance and shorter validity when central freshness cannot be established.
- [ ] **22.06.** Prevent disconnected sites from enrolling new trust roots or performing unrestricted recovery unless a separately governed offline process exists.

### Security & failure semantics

- [ ] **22.07.** Queue signed local audit events and reconcile them centrally with duplicate/conflict detection after reconnect.
- [ ] **22.08.** Define conflict resolution when central policy/revocation changed during outage; central revocation must take precedence.
- [ ] **22.09.** Force re-attestation/reconciliation after reconnect before extending long-lived trust.

### Verification & interoperability

- [ ] **22.10.** Create tests for outages longer than each configured offline limit and verify deterministic transition to limited/fail-closed mode.
- [ ] **22.11.** Create partition/reconnect tests with conflicting policy versions, revoked identities, and clock drift.
- [ ] **22.12.** Expose offline duration, cached-policy age, revocation-snapshot age, local queue depth, and trust-expiry risk.

### Component Definition of Done

- [ ] **22.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **22.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **22.D3.** Traceability links `Disconnected and offline attestation mode` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 23. Health, readiness, and dependency endpoints

**Priority:** P1  
**Source controls:** `C052, C071`  
**Objective:** Expose accurate liveness/readiness/degraded state without turning health APIs into a security leak.


### Architecture & contract

- [ ] **23.01.** Define separate liveness (process can run), readiness (safe to serve trust decisions), and detailed dependency health models.
- [ ] **23.02.** Mark service unready when authoritative state, required trust stores, KMS/HSM, or secure time makes decisions unsafe, even if the process is alive.
- [ ] **23.03.** Define degraded modes explicitly for noncritical dependencies such as analytics exporters and distinguish them from trust-critical failures.

### Implementation & data/state

- [ ] **23.04.** Include version/build ID, schema compatibility, active policy generation, trust-anchor generation, and replica role in protected diagnostics.
- [ ] **23.05.** Avoid exposing secrets, certificate bodies, node identifiers, internal topology, or dependency credentials on unauthenticated health endpoints.
- [ ] **23.06.** Use bounded dependency probes with short deadlines and avoid cascading overload caused by health checks.

### Security & failure semantics

- [ ] **23.07.** Add startup readiness gates so the service does not accept traffic before migrations, trust stores, policy, replay state, and time checks complete.
- [ ] **23.08.** Add shutdown/drain readiness behavior that removes the instance before terminating in-flight work.
- [ ] **23.09.** Create tests for every dependency failure and verify the correct liveness/readiness/degraded classification.

### Verification & interoperability

- [ ] **23.10.** Integrate readiness with orchestration/load balancing and validate failover behavior.

### Component Definition of Done

- [ ] **23.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **23.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **23.D3.** Traceability links `Health, readiness, and dependency endpoints` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 24. Metrics, logging, and tracing implementation

**Priority:** P1  
**Source controls:** `C072-C080`  
**Objective:** Implement complete telemetry with bounded cardinality, security redaction, trace propagation, dashboards, alerts, and retention.


### Architecture & contract

- [ ] **24.01.** Define RED/USE metrics for API latency/rate/errors, crypto verifier latency, queue utilization, replay state, persistence, KMS/HSM, time sync, policy generation, and scheduler renewal.
- [ ] **24.02.** Define security counters for replay rejection, invalid signatures, certificate failures, PCR mismatches, revocations, quarantine actions, authz denials, and policy rollback attempts.
- [ ] **24.03.** Use structured logs with event name, severity, correlation/trace ID, component version, site/tenant-safe identifiers, reason code, and sanitized context.

### Implementation & data/state

- [ ] **24.04.** Adopt distributed tracing across ingress, verifier, policy store, replay store, KMS/HSM, scheduler, and quarantine integrations.
- [ ] **24.05.** Propagate trace context only through trusted headers/metadata and sanitize untrusted client-provided trace identifiers.
- [ ] **24.06.** Define redaction rules for raw evidence, public-key material where sensitive, certificate serials, node identifiers, secrets, and personal data.

### Security & failure semantics

- [ ] **24.07.** Control metric label cardinality; never place unbounded node IDs/challenge IDs into metric labels.
- [ ] **24.08.** Define telemetry retention, access control, encryption, export destinations, and incident preservation procedures.
- [ ] **24.09.** Create dashboards for availability, latency, fleet trust posture, policy rollout, replay anomalies, expiry risk, storage, and dependency health.

### Verification & interoperability

- [ ] **24.10.** Define actionable alerts with severity, thresholds, burn-rate logic, runbook links, and anti-flap behavior.
- [ ] **24.11.** Create telemetry tests asserting required events/metrics on success and key failure paths and verifying secret redaction.
- [ ] **24.12.** Capacity-test observability pipelines so telemetry cannot backpressure or crash the trust service.

### Component Definition of Done

- [ ] **24.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **24.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **24.D3.** Traceability links `Metrics, logging, and tracing implementation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 25. Decision explain API

**Priority:** P1  
**Source controls:** `C076, C077`  
**Objective:** Provide auditable, authorized explanations linking each verdict to exact evidence, policy, trust roots, and expiry.


### Architecture & contract

- [ ] **25.01.** Define a stable verdict ID and store the immutable decision context needed for later explanation.
- [ ] **25.02.** Include decision result, reason code tree, evidence digest, quote/report digest, measurement-policy ID/version/digest, trust-anchor generation, identity version, verifier version, issuance, and expiry.
- [ ] **25.03.** Provide claim-level explanation for which measurement/PCR/runtime rule passed or failed without exposing secrets or unrelated tenant data.

### Implementation & data/state

- [ ] **25.04.** Protect the API with authorization distinct from ordinary attestation submission; restrict forensic detail to approved operator/auditor roles.
- [ ] **25.05.** Support deterministic reconstruction so the same stored inputs/policy/verifier version can reproduce the decision or clearly report nondeterministic external dependencies.
- [ ] **25.06.** Link certificate/revocation evidence, policy publication event, challenge issuance/consume record, and quarantine action via correlation IDs.

### Security & failure semantics

- [ ] **25.07.** Define retention aligned with incident, compliance, and audit requirements.
- [ ] **25.08.** Provide machine-readable output suitable for SIEM/certification tooling and a human-readable operator rendering.
- [ ] **25.09.** Create tests for redaction, cross-tenant access, missing/expired evidence, old verifier versions, and policy rollback history.

### Verification & interoperability

- [ ] **25.10.** Ensure explanation generation cannot mutate verdict state or trigger re-evaluation silently.

### Component Definition of Done

- [ ] **25.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **25.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **25.D3.** Traceability links `Decision explain API` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 26. Fleet-scale persistence and sharding model

**Priority:** P1  
**Source controls:** `C013, C061-C069`  
**Objective:** Scale authoritative state and query paths to fleet size with predictable capacity, partitioning, and saturation behavior.


### Architecture & contract

- [ ] **26.01.** Estimate node/workload counts, attestation frequency, policy versions, audit-event rate, replay-state rate, retention, and worst-case burst factors.
- [ ] **26.02.** Define partition/shard keys that distribute load while preserving atomicity requirements for identity/challenge/policy operations.
- [ ] **26.03.** Avoid hotspots from global counters, active-policy pointers, tenant supernodes, or time-based keys.

### Implementation & data/state

- [ ] **26.04.** Define cross-shard transaction requirements and redesign operations to minimize them where safe.
- [ ] **26.05.** Plan index strategy and bounded query patterns for enrollment lookup, revocation lookup, challenge consume, verdict explanation, and audits.
- [ ] **26.06.** Define replication factor, consistency level, failover, rebalancing, backup, and restore per data class.

### Security & failure semantics

- [ ] **26.07.** Capacity-model storage growth including indexes, audit ledger, event logs/evidence retention, tombstones, and replication overhead.
- [ ] **26.08.** Define high-water marks and load-shedding behavior before disk, IOPS, connection, or transaction limits are exhausted.
- [ ] **26.09.** Benchmark representative read/write mixes at target and 2× burst load with realistic record sizes.

### Verification & interoperability

- [ ] **26.10.** Test online shard split/rebalance/failover while attestation traffic continues.
- [ ] **26.11.** Expose per-shard latency, size, hot-key indicators, replication lag, connection saturation, compaction, and error rates.
- [ ] **26.12.** Document scaling playbook and maximum supported fleet envelope per release.

### Component Definition of Done

- [ ] **26.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **26.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **26.D3.** Traceability links `Fleet-scale persistence and sharding model` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 27. Failover and disaster recovery implementation

**Priority:** P1  
**Source controls:** `C051-C060, C095`  
**Objective:** Provide tested recovery from instance, database, site, region, and dependency failure without weakening trust guarantees.


### Architecture & contract

- [ ] **27.01.** Define failure domains and RTO/RPO for verifier compute, state stores, audit ledger, KMS/HSM, policy distribution, time services, and site control planes.
- [ ] **27.02.** Implement automated instance/replica failover with fencing so stale instances cannot continue accepting security writes.
- [ ] **27.03.** Replicate critical state according to defined consistency and durability requirements; distinguish synchronous from asynchronous data classes.

### Implementation & data/state

- [ ] **27.04.** Create signed, encrypted backups with independent retention and access controls; regularly verify restoreability.
- [ ] **27.05.** Protect against backup rollback reopening replay/revocation windows using epochs/generations and post-restore reconciliation.
- [ ] **27.06.** Define region/site failover traffic routing and trust-anchor/policy synchronization prerequisites.

### Security & failure semantics

- [ ] **27.07.** Define behavior when KMS/HSM is region-scoped and ensure failover has authorized key access without copying private keys unsafely.
- [ ] **27.08.** Create DR tests for total database loss, corrupted snapshot, site loss, region loss, split brain, and prolonged WAN partition.
- [ ] **27.09.** Validate that revocations/quarantines and consumed challenges remain effective after restore/failover.

### Verification & interoperability

- [ ] **27.10.** Run scheduled game days and capture objective RTO/RPO measurements and remediation actions.
- [ ] **27.11.** Expose DR replication lag, backup age, restore-test status, fencing events, and failover state.
- [ ] **27.12.** Maintain step-by-step recovery and failback runbooks with command validation and rollback points.

### Component Definition of Done

- [ ] **27.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **27.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **27.D3.** Traceability links `Failover and disaster recovery implementation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 28. Compatibility matrix

**Priority:** P1  
**Source controls:** `C016, C027, C084, C093`  
**Objective:** Define and continuously verify supported combinations of hardware, virtualization, OS/firmware, architecture, and protocol versions.


### Architecture & contract

- [ ] **28.01.** List supported TPM versions/vendors/firmware lines, TEE technologies, vTPM implementations, hypervisors, CPU architectures, OS families, boot modes, and attestation protocols.
- [ ] **28.02.** Define minimum firmware/microcode/OS/runtime versions and explicitly unsupported/deprecated combinations.
- [ ] **28.03.** Map supported PCR banks/algorithms/event-log formats and platform-specific evidence fields.

### Implementation & data/state

- [ ] **28.04.** Define server/client/schema version compatibility ranges and downgrade behavior.
- [ ] **28.05.** Include edge/disconnected-site tiers and resource-constrained variants with their reduced capabilities.
- [ ] **28.06.** Build CI/hardware-lab jobs covering representative matrix cells and prioritize high-risk/vendor-specific paths.

### Security & failure semantics

- [ ] **28.07.** Use golden evidence fixtures for matrix cells that cannot run in every CI cycle and periodically refresh them from real hardware.
- [ ] **28.08.** Create regression tests for known vendor quirks without silently widening validation rules.
- [ ] **28.09.** Version and publish the compatibility matrix with each release and link it to test evidence.

### Verification & interoperability

- [ ] **28.10.** Define deprecation notice period, migration guidance, and hard removal gates for old algorithms/platforms.

### Component Definition of Done

- [ ] **28.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **28.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **28.D3.** Traceability links `Compatibility matrix` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 29. Integration adapters and tests for GAP-01/GAP-02/GAP-07/PLN-07/SCH-01

**Priority:** P1  
**Source controls:** `C003, C030, C083`  
**Objective:** Implement typed integrations with adjacent platform subsystems and prove end-to-end trust enforcement.


### Architecture & contract

- [ ] **29.01.** Define an explicit contract for each dependency, including API/schema version, authentication, authorization, retries, idempotency, and failure semantics.
- [ ] **29.02.** Integrate GAP-01 node supervisor for identity lifecycle, health state, and quarantine/cordon enforcement.
- [ ] **29.03.** Integrate GAP-02 hardware capability discovery to correlate attested hardware claims with discovered platform capabilities without trusting discovery alone.

### Implementation & data/state

- [ ] **29.04.** Integrate GAP-07 artifact provenance/signing so workload/boot artifact digests can be validated against authorized provenance.
- [ ] **29.05.** Integrate PLN-07/SCH-01 planning/scheduling so trust verdicts are mandatory placement inputs and stale/expired verdicts cannot be used.
- [ ] **29.06.** Define correlation IDs and stable node/workload identifiers across all systems to avoid identity ambiguity.

### Security & failure semantics

- [ ] **29.07.** Add circuit-breaker/degraded behavior for each dependency and document which failures require fail-closed placement.
- [ ] **29.08.** Create contract tests using versioned fixtures for each adapter and prevent deployment with incompatible peer versions.
- [ ] **29.09.** Create end-to-end tests: enroll → attest → schedule → policy change → re-attest → quarantine → recover.

### Verification & interoperability

- [ ] **29.10.** Create race/failure tests for concurrent scheduling and trust revocation, stale cache, delayed events, duplicate events, and partial dependency outage.
- [ ] **29.11.** Expose adapter latency/errors/version mismatch and reconciliation backlog metrics.

### Component Definition of Done

- [ ] **29.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **29.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **29.D3.** Traceability links `Integration adapters and tests for GAP-01/GAP-02/GAP-07/PLN-07/SCH-01` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 30. Production configuration model

**Priority:** P1  
**Source controls:** `C032-C040`  
**Objective:** Separate immutable code from signed mutable configuration/state with validation, provenance, safe rollout, and rollback.


### Architecture & contract

- [ ] **30.01.** Classify every setting as build-time immutable, startup immutable, dynamic safe, security-sensitive dynamic, or secret.
- [ ] **30.02.** Define a typed schema with defaults, ranges, enums, cross-field constraints, and unknown-key rejection.
- [ ] **30.03.** Assign each setting an owner, rationale, environment scope, security impact, restart requirement, and change mechanism.

### Implementation & data/state

- [ ] **30.04.** Keep secrets out of ordinary configuration and reference them through KMS/secret-manager handles.
- [ ] **30.05.** Cryptographically sign or integrity-protect security-sensitive configuration bundles and validate signer/scope/version before activation.
- [ ] **30.06.** Use monotonic configuration revisions and atomic activation; never combine partial files from different generations.

### Security & failure semantics

- [ ] **30.07.** Implement staged rollout/canary and automated rollback for dynamic configuration changes.
- [ ] **30.08.** Record provenance: source commit/artifact, author/automation identity, approver, timestamp, digest, and deployment scope.
- [ ] **30.09.** Validate startup configuration before serving traffic and fail with actionable errors on unsafe values.

### Verification & interoperability

- [ ] **30.10.** Create tests for missing/unknown keys, boundary values, conflicting settings, stale revision, unauthorized signer, and rollback.
- [ ] **30.11.** Expose active configuration generation/digest and drift detection without exposing secret values.

### Component Definition of Done

- [ ] **30.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **30.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **30.D3.** Traceability links `Production configuration model` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 31. Algorithm agility

**Priority:** P1  
**Source controls:** `C045`  
**Objective:** Make cryptographic algorithms explicit, governed, migratable, and resistant to downgrade/confusion.


### Architecture & contract

- [ ] **31.01.** Define an algorithm registry with unambiguous identifiers for hashes, signature schemes, key types, curves, certificate signatures, and evidence formats.
- [ ] **31.02.** Define approved/preferred/deprecated/prohibited states by environment/compliance profile and effective dates.
- [ ] **31.03.** Negotiate or select algorithms by policy rather than client preference; reject downgrade to weaker-but-supported options.

### Implementation & data/state

- [ ] **31.04.** Bind algorithm identifiers into signed/hashed structures to prevent algorithm-substitution attacks.
- [ ] **31.05.** Support multiple PCR banks/signature schemes during controlled migration and define precedence/dual-validation rules.
- [ ] **31.06.** Define minimum key sizes/curves and strict encoding rules for each supported algorithm.

### Security & failure semantics

- [ ] **31.07.** Add organization/FIPS policy hooks where required without assuming FIPS mode equals complete security.
- [ ] **31.08.** Create migration tooling to inventory fleet algorithm use and identify blockers before deprecation deadlines.
- [ ] **31.09.** Create negative tests for unknown algorithm IDs, mismatched identifiers, weak keys, downgrade attempts, and signature-format ambiguity.

### Verification & interoperability

- [ ] **31.10.** Publish cryptographic-policy changes with release notes, compatibility impact, and rollback strategy.

### Component Definition of Done

- [ ] **31.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **31.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **31.D3.** Traceability links `Algorithm agility` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 32. Measurement semantics and event-log parser

**Priority:** P1  
**Source controls:** `C036-C039, C045`  
**Objective:** Define how PCRs, firmware/boot events, IMA/runtime events, containers, and workloads map into enforceable measurement policy.


### Architecture & contract

- [ ] **32.01.** Define supported PCR banks and exact PCR roles per boot mode/platform, avoiding a universal hard-coded PCR set.
- [ ] **32.02.** Implement event-log parser for required TCG formats with strict bounds checking, event-type handling, digest-algorithm validation, and unknown-event policy.
- [ ] **32.03.** Replay event log into software PCR state and compare against quoted PCR digest/values.

### Implementation & data/state

- [ ] **32.04.** Normalize measurements into typed semantic components such as firmware, bootloader, Secure Boot variables, kernel, initrd, command line, drivers, IMA, container image, and workload.
- [ ] **32.05.** Define policy rules over component digests/version/signers rather than only opaque aggregate PCR values where explainability is required.
- [ ] **32.06.** Validate Secure Boot state, key databases, revocation databases, and relevant measured-boot variables where platform supports them.

### Security & failure semantics

- [ ] **32.07.** Parse IMA templates safely and define approved measurement/appraisal policies and handling of mutable files.
- [ ] **32.08.** Bind container/workload image measurements to signed artifact provenance and immutable digests.
- [ ] **32.09.** Define composite-policy semantics for optional components, version ranges, signer allow-lists, deny-lists, and emergency revocations.

### Verification & interoperability

- [ ] **32.10.** Create a corpus of real event logs across supported vendors/OS versions plus malformed/adversarial fixtures.
- [ ] **32.11.** Fuzz parsers and enforce CPU/memory/depth limits to prevent crafted-log denial of service.
- [ ] **32.12.** Provide explanation output showing which semantic component caused a policy mismatch.

### Component Definition of Done

- [ ] **32.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **32.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **32.D3.** Traceability links `Measurement semantics and event-log parser` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 33. Identity cloning and relay detection

**Priority:** P1  
**Source controls:** `C044-C047`  
**Objective:** Detect duplicated device identity and resist remote relay/cuckoo attacks that forward challenges to a legitimate attester.


### Architecture & contract

- [ ] **33.01.** Bind enrolled AK/EK identities to a unique node record, expected platform attributes, site, and lifecycle epoch.
- [ ] **33.02.** Use verifier challenge binding that includes node/service/session context and cannot be transparently replayed across sessions.
- [ ] **33.03.** Where supported, bind attestation to the authenticated transport/channel or workload key using report-data/channel-binding fields.

### Implementation & data/state

- [ ] **33.04.** Detect simultaneous active attestations or sessions using the same hardware identity from mutually exclusive locations/nodes.
- [ ] **33.05.** Incorporate TPM locality/credential activation/platform certificates where useful to strengthen proof that the attester is the enrolled device.
- [ ] **33.06.** Define network/time plausibility heuristics only as supplementary signals, not sole cryptographic proof.

### Security & failure semantics

- [ ] **33.07.** Flag identity moves/replacements that exceed allowed topology/location policy and require re-enrollment where appropriate.
- [ ] **33.08.** Correlate hardware capability discovery and attested platform attributes to detect impossible/abrupt identity changes.
- [ ] **33.09.** Create lab relay/cuckoo tests with a proxy forwarding quote challenges to another machine and verify detection/prevention mechanisms.

### Verification & interoperability

- [ ] **33.10.** Create clone tests using copied VM/vTPM state and define expected behavior after snapshot/restore/migration.
- [ ] **33.11.** Emit high-severity audit/security events for duplicate-active identity and relay indicators with protected forensic context.

### Component Definition of Done

- [ ] **33.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **33.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **33.D3.** Traceability links `Identity cloning and relay detection` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 34. Policy conflict and precedence engine

**Priority:** P1  
**Source controls:** `C019`  
**Objective:** Resolve overlapping security, residency, SLO, cost, and placement constraints deterministically with security-safe precedence.


### Architecture & contract

- [ ] **34.01.** Define policy domains and an explicit precedence model; security/trust constraints must not be silently weakened by cost/SLO preferences.
- [ ] **34.02.** Represent rules in a typed intermediate model with scope, priority, mandatory/preferential semantics, version, owner, and provenance.
- [ ] **34.03.** Detect contradictory mandatory constraints before activation and reject unsatisfiable policy sets.

### Implementation & data/state

- [ ] **34.04.** Define deterministic tie-breaking independent of input ordering or hash-map iteration.
- [ ] **34.05.** Expose an explain function showing which rules applied, which were overridden, and why.
- [ ] **34.06.** Prevent lower-authority scopes from overriding higher-authority security baselines unless delegation explicitly permits it.

### Security & failure semantics

- [ ] **34.07.** Integrate trust verdict expiry/quarantine as hard constraints in planning/scheduling decisions.
- [ ] **34.08.** Define residency/site constraints and ensure cross-tenant policies cannot reference unauthorized resources.
- [ ] **34.09.** Create property tests for determinism, monotonicity of security restrictions, and order independence.

### Verification & interoperability

- [ ] **34.10.** Create scenario tests combining security, residency, performance, and cost constraints including unsatisfiable cases.
- [ ] **34.11.** Version the precedence engine and record its version in placement/verdict explanations.

### Component Definition of Done

- [ ] **34.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **34.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **34.D3.** Traceability links `Policy conflict and precedence engine` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 35. MASTER.md source artifact

**Priority:** P2  
**Source controls:** `Documentation`  
**Objective:** Restore the missing authoritative master design artifact and prevent documentation/package drift.


### Architecture & contract

- [ ] **35.01.** Reconstruct MASTER.md from the current implemented architecture and explicitly mark aspirational versus implemented behavior.
- [ ] **35.02.** Include subsystem purpose, scope, trust boundaries, architecture, APIs/schemas, state model, lifecycle, failure modes, security assumptions, dependencies, and release gates.
- [ ] **35.03.** Cross-reference the 100-entry checklist and the missing-components checklist with stable IDs.

### Implementation & data/state

- [ ] **35.04.** Include version history and compatibility notes matching the package version.
- [ ] **35.05.** Add documentation validation in CI to fail if README claims bundled artifacts that are absent.
- [ ] **35.06.** Generate/check a file manifest and documentation link checker during packaging.

### Security & failure semantics

- [ ] **35.07.** Require architecture/security owner review for material master-document changes.
- [ ] **35.08.** Record the MASTER.md digest in release evidence so certification references an immutable document.

### Component Definition of Done

- [ ] **35.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **35.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **35.D3.** Traceability links `MASTER.md source artifact` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 36. Architecture Decision Record

**Priority:** P2  
**Source controls:** `C010`  
**Objective:** Document irreversible/high-impact technical choices, alternatives, consequences, and revisit triggers.


### Architecture & contract

- [ ] **36.01.** Create ADRs for hardware roots, attestation protocol, persistence engine, HA consistency model, replay strategy, policy distribution, audit ledger, KMS/HSM, secure time, and offline mode.
- [ ] **36.02.** Use a standard ADR template with context, decision, options considered, tradeoffs, security implications, operational implications, migration path, and status.
- [ ] **36.03.** Record quantitative decision drivers such as latency, fleet scale, RPO/RTO, evidence size, and vendor compatibility.

### Implementation & data/state

- [ ] **36.04.** Link each ADR to threat-model items, requirements, implementation components, and test evidence.
- [ ] **36.05.** Define supersession rules so later ADRs do not silently rewrite history.
- [ ] **36.06.** Review ADRs when assumptions change, dependencies reach EOL, cryptographic policy changes, or scale exceeds design bounds.

### Security & failure semantics

- [ ] **36.07.** Include rejected alternatives and reasons sufficient for future engineers to avoid repeating analysis.

### Component Definition of Done

- [ ] **36.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **36.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **36.D3.** Traceability links `Architecture Decision Record` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 37. Named owner and escalation path

**Priority:** P2  
**Source controls:** `C009, C097`  
**Objective:** Establish accountable ownership for engineering, security, operations, incidents, and release decisions.


### Architecture & contract

- [ ] **37.01.** Assign a primary engineering owner/team and backup owner for the subsystem.
- [ ] **37.02.** Assign security owner for trust model, crypto policy, threat model, and exception approval.
- [ ] **37.03.** Assign operational/on-call owner for production incidents and dependency health.

### Implementation & data/state

- [ ] **37.04.** Define escalation matrix by severity with paging targets, management/security escalation, and vendor escalation where needed.
- [ ] **37.05.** Publish ownership in repository metadata, runbooks, service catalog, and alert routing.
- [ ] **37.06.** Define handoff requirements during organizational change so no critical component becomes ownerless.

### Security & failure semantics

- [ ] **37.07.** Review ownership at least quarterly and after major incidents/reorganizations.

### Component Definition of Done

- [ ] **37.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **37.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **37.D3.** Traceability links `Named owner and escalation path` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 38. SHALL-level specification and requirements traceability matrix

**Priority:** P2  
**Source controls:** `C011, C020`  
**Objective:** Create normative, testable requirements and trace each to implementation and evidence.


### Architecture & contract

- [ ] **38.01.** Convert ambiguous goals into atomic SHALL/SHALL NOT requirements with unique stable IDs.
- [ ] **38.02.** Ensure every requirement states preconditions, actors, inputs, behavior, outputs, failure behavior, and measurable acceptance criteria where applicable.
- [ ] **38.03.** Distinguish normative requirements from rationale, examples, and implementation guidance.

### Implementation & data/state

- [ ] **38.04.** Create a traceability matrix mapping requirement → threat/control → design component → code/module → test(s) → release evidence.
- [ ] **38.05.** Mark requirement status as implemented/partial/not implemented/deferred/waived with owner and rationale.
- [ ] **38.06.** Prevent release gate from counting a requirement as satisfied without linked machine-verifiable evidence.

### Security & failure semantics

- [ ] **38.07.** Add CI validation for duplicate IDs, orphan tests, orphan implementation claims, and stale version references.
- [ ] **38.08.** Baseline/spec version must be immutable once used for certification; changes create a new revision.

### Component Definition of Done

- [ ] **38.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **38.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **38.D3.** Traceability links `SHALL-level specification and requirements traceability matrix` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 39. Performance baselines and release thresholds

**Priority:** P2  
**Source controls:** `C061-C070`  
**Objective:** Establish measurable performance envelopes and fail releases that regress critical limits.


### Architecture & contract

- [ ] **39.01.** Define latency percentiles for challenge issuance, attestation verification, enrollment, policy fetch/publish, replay consume, explanation, and quarantine propagation.
- [ ] **39.02.** Define sustained and burst throughput targets at service, site, and tenant level.
- [ ] **39.03.** Define CPU, memory, storage/IOPS, network, KMS/HSM, and database connection/transaction budgets.

### Implementation & data/state

- [ ] **39.04.** Define evidence-size distributions and worst-case event-log/certificate-chain sizes.
- [ ] **39.05.** Define cold-start, failover recovery, backlog-drain, and re-attestation-storm targets.
- [ ] **39.06.** Benchmark on representative hardware/VM profiles and record exact environment/tool versions.

### Security & failure semantics

- [ ] **39.07.** Include tail-latency and saturation curves rather than averages alone.
- [ ] **39.08.** Create automated regression thresholds in CI/performance pipelines with approved variance margins.
- [ ] **39.09.** Run burst and soak tests long enough to expose leaks, compaction effects, cache churn, and thermal/power limits where relevant.

### Verification & interoperability

- [ ] **39.10.** Publish baseline artifacts per release and document expected capacity envelope/headroom.

### Component Definition of Done

- [ ] **39.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **39.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **39.D3.** Traceability links `Performance baselines and release thresholds` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 40. Fuzz and property tests

**Priority:** P2  
**Source controls:** `C085`  
**Objective:** Systematically test parser robustness and state-machine invariants against malformed and generated inputs.


### Architecture & contract

- [ ] **40.01.** Fuzz all external schema decoders, certificate parsers, TPM/TEE evidence parsers, event-log/IMA parsers, policy bundle parsers, and audit import/export formats.
- [ ] **40.02.** Seed fuzzers with real valid corpora plus known malformed/corner-case fixtures.
- [ ] **40.03.** Use structure-aware generation where possible so tests reach semantic validation rather than only syntax rejection.

### Implementation & data/state

- [ ] **40.04.** Define properties for challenge uniqueness/single-consumption, revocation monotonicity, policy version monotonicity, tenant isolation, deterministic decision, and no trust increase on malformed input.
- [ ] **40.05.** Add state-machine/model-based tests that generate legal/illegal lifecycle transition sequences.
- [ ] **40.06.** Run fuzzing with sanitizers/instrumentation appropriate to implementation language and capture crashes, hangs, OOM, excessive CPU, and assertion failures.

### Security & failure semantics

- [ ] **40.07.** Convert every discovered bug into a minimized regression corpus entry.
- [ ] **40.08.** Run bounded fuzz smoke tests in normal CI and longer campaigns on scheduled/security pipelines.
- [ ] **40.09.** Track coverage and time-to-bug metrics without treating coverage percentage as sufficient proof.

### Component Definition of Done

- [ ] **40.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **40.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **40.D3.** Traceability links `Fuzz and property tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 41. Concurrency and race tests

**Priority:** P2  
**Source controls:** `C086`  
**Objective:** Validate correctness under multi-thread, multi-process, and distributed contention beyond the in-process lock.


### Architecture & contract

- [ ] **41.01.** Identify shared-state race points: challenge issue/consume, enrollment rotation/revocation, policy activation, verdict cache, quarantine, scheduler renewal, and audit sequencing.
- [ ] **41.02.** Create high-contention tests with synchronized barriers to force concurrent attempts at atomic operations.
- [ ] **41.03.** Run multi-process tests against the production persistence backend, not only an in-memory model.

### Implementation & data/state

- [ ] **41.04.** Run multi-replica tests across the actual HA/consensus configuration.
- [ ] **41.05.** Inject delays between read/validate/write phases to expose time-of-check/time-of-use flaws.
- [ ] **41.06.** Test revoke-vs-attest, rotate-vs-attest, quarantine-vs-schedule, policy-activate-vs-verify, and restore-vs-live-traffic races.

### Security & failure semantics

- [ ] **41.07.** Use language/runtime race detectors or sanitizers where supported.
- [ ] **41.08.** Assert invariants after each run: no duplicate challenge acceptance, no revoked identity reactivation, no mixed policy generation, no cross-tenant leakage.
- [ ] **41.09.** Retain deterministic seeds/traces for failing interleavings as regression artifacts.

### Component Definition of Done

- [ ] **41.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **41.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **41.D3.** Traceability links `Concurrency and race tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 42. Benchmark, soak, burst, and fleet tests

**Priority:** P2  
**Source controls:** `C088`  
**Objective:** Prove sustained correctness and capacity under realistic fleet behavior and adversarial bursts.


### Architecture & contract

- [ ] **42.01.** Build a workload generator modeling node populations, platform mix, attestation intervals, evidence sizes, enrollment churn, policy rollouts, and failure rates.
- [ ] **42.02.** Run baseline benchmarks for each core operation and full end-to-end flow.
- [ ] **42.03.** Run multi-hour/day soak tests to reveal leaks, unbounded caches, fragmentation, compaction stalls, and drift.

### Implementation & data/state

- [ ] **42.04.** Run synchronized burst scenarios such as site reconnect, verifier restart, policy-triggered re-attestation, and certificate rollover.
- [ ] **42.05.** Run failure-amplified load with slow database/KMS/time dependencies to validate backpressure.
- [ ] **42.06.** Validate fairness across tenants/sites under mixed heavy and light workloads.

### Security & failure semantics

- [ ] **42.07.** Capture latency percentiles, throughput, resource usage, queue depths, error reasons, GC/runtime behavior, and dependency saturation.
- [ ] **42.08.** Compare results against release thresholds and prior version baselines.
- [ ] **42.09.** Archive workload profiles, raw results, environment metadata, and pass/fail summary as release evidence.

### Component Definition of Done

- [ ] **42.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **42.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **42.D3.** Traceability links `Benchmark, soak, burst, and fleet tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 43. Disaster, partition, reconnect, and degraded-control-plane tests

**Priority:** P2  
**Source controls:** `C089`  
**Objective:** Exercise safety properties under infrastructure partitions and partial control-plane failure.


### Architecture & contract

- [ ] **43.01.** Define chaos scenarios for database partition, replica split brain, KMS/HSM outage, secure-time loss, policy distributor loss, audit sink outage, scheduler disconnect, and site WAN loss.
- [ ] **43.02.** Inject packet loss, latency, reordering, duplication, and asymmetric partitions rather than only hard shutdowns.
- [ ] **43.03.** Verify challenge single-consumption and revocation/quarantine safety across every partition scenario.

### Implementation & data/state

- [ ] **43.04.** Verify disconnected-mode maximum-age rules and fail-closed transitions.
- [ ] **43.05.** Verify reconnect reconciliation handles duplicated queued events, policy conflicts, revocations, and stale identity epochs.
- [ ] **43.06.** Verify stale leaders/replicas are fenced before accepting security writes after healing.

### Security & failure semantics

- [ ] **43.07.** Measure recovery time, backlog-drain time, expiry misses, and operator intervention required.
- [ ] **43.08.** Run at production-like scale where possible to expose recovery storms.
- [ ] **43.09.** Document each scenario with expected state machine, assertions, and automated pass/fail evidence.

### Component Definition of Done

- [ ] **43.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **43.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **43.D3.** Traceability links `Disaster, partition, reconnect, and degraded-control-plane tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 44. Machine-readable acceptance evidence bundle

**Priority:** P2  
**Source controls:** `C090`  
**Objective:** Generate a cryptographically tied release dossier proving which requirements were actually verified.


### Architecture & contract

- [ ] **44.01.** Define an evidence manifest schema containing release version, source commit, build digest, SBOM digest, test suite IDs/results, performance results, security scans, compatibility matrix, and approval records.
- [ ] **44.02.** Link each SHALL/checklist requirement to one or more evidence artifacts with stable IDs and hashes.
- [ ] **44.03.** Include test environment metadata sufficient to reproduce results: OS, architecture, hardware/TPM, dependencies, configuration, and tool versions.

### Implementation & data/state

- [ ] **44.04.** Sign the evidence manifest with a release/certification key and record signing identity/time.
- [ ] **44.05.** Store immutable evidence in a controlled artifact repository with retention matching release/support life.
- [ ] **44.06.** Fail production release if mandatory evidence is missing, stale, unsigned, or references a different artifact digest.

### Security & failure semantics

- [ ] **44.07.** Provide verification tooling that checks hashes, signatures, schema validity, and requirement coverage offline.
- [ ] **44.08.** Include waivers/exceptions as first-class signed artifacts with owner and expiry rather than silently treating them as passes.

### Component Definition of Done

- [ ] **44.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **44.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **44.D3.** Traceability links `Machine-readable acceptance evidence bundle` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 45. Canary, staged rollout, rollback, and emergency-disable procedures

**Priority:** P2  
**Source controls:** `C092`  
**Objective:** Deploy trust-service changes progressively with objective stop conditions and safe rollback mechanisms.


### Architecture & contract

- [ ] **45.01.** Define rollout rings by environment/site/fleet percentage/risk class and entry/exit criteria for each ring.
- [ ] **45.02.** Deploy schema/config/policy/code changes in an order compatible with mixed versions.
- [ ] **45.03.** Define canary health metrics including attestation failure delta, latency, error-rate, replay anomalies, quarantine spikes, and dependency saturation.

### Implementation & data/state

- [ ] **45.04.** Automate rollout halt/rollback when thresholds are breached while requiring human review for security-significant anomalies.
- [ ] **45.05.** Ensure rollback cannot violate monotonic security state such as consumed challenges, revocations, or minimum policy versions.
- [ ] **45.06.** Provide emergency-disable/kill-switch capabilities scoped narrowly to unsafe optional behavior, not a global trust bypass.

### Security & failure semantics

- [ ] **45.07.** Protect rollback/emergency controls with strong authorization, multi-party approval where appropriate, and tamper-evident audit.
- [ ] **45.08.** Rehearse rollback under load and during partial site failure.
- [ ] **45.09.** Publish post-rollout verification evidence and reconcile version/config drift.

### Component Definition of Done

- [ ] **45.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **45.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **45.D3.** Traceability links `Canary, staged rollout, rollback, and emergency-disable procedures` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 46. Patch, vulnerability, and end-of-life policy

**Priority:** P2  
**Source controls:** `C094`  
**Objective:** Define how security vulnerabilities and dependency/platform lifecycle events are triaged, remediated, and enforced.


### Architecture & contract

- [ ] **46.01.** Inventory first-party components, third-party libraries, OS/base images, cryptographic providers, TPM/TEE SDKs, databases, and infrastructure dependencies.
- [ ] **46.02.** Define severity mapping and remediation SLAs, including emergency timelines for actively exploited vulnerabilities.
- [ ] **46.03.** Continuously ingest vulnerability advisories/CVEs and match them to the SBOM and deployed versions.

### Implementation & data/state

- [ ] **46.04.** Define exception process requiring compensating controls, owner, risk acceptance, and expiry.
- [ ] **46.05.** Define dependency/platform EOL lead time, migration plan, and release blocking dates.
- [ ] **46.06.** Patch in staged rollout rings with regression/security verification and documented rollback.

### Security & failure semantics

- [ ] **46.07.** Maintain supported-release branches and backport policy for security fixes.
- [ ] **46.08.** Publish security advisories and operator upgrade guidance when customer action is required.
- [ ] **46.09.** Track fleet patch compliance and alert on unsupported/EOL versions.

### Component Definition of Done

- [ ] **46.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **46.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **46.D3.** Traceability links `Patch, vulnerability, and end-of-life policy` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 47. Incident severity, paging, containment, and recovery runbook

**Priority:** P2  
**Source controls:** `C097`  
**Objective:** Provide an executable security incident process for trust-subsystem compromise or degradation.


### Architecture & contract

- [ ] **47.01.** Define severity criteria for key compromise, trust-anchor compromise, mass attestation failure, replay acceptance, identity cloning, policy poisoning, audit tampering, and availability incidents.
- [ ] **47.02.** Define 24×7 paging targets, acknowledgement time, incident commander, security lead, communications lead, and escalation tree.
- [ ] **47.03.** Create containment actions for disabling compromised keys, freezing policy publication, quarantining affected nodes, blocking identities, and isolating sites.

### Implementation & data/state

- [ ] **47.04.** Define forensic data preservation for audit ledger, raw evidence digests, configs, builds, logs, traces, and KMS/HSM events.
- [ ] **47.05.** Define safe recovery order and validation gates before trust decisions resume.
- [ ] **47.06.** Provide commands/API steps with prerequisites, expected output, rollback, and authorization level.

### Security & failure semantics

- [ ] **47.07.** Define external/vendor escalation and disclosure decision paths.
- [ ] **47.08.** Run table-top and technical simulations at least periodically and after major architecture changes.
- [ ] **47.09.** Capture post-incident corrective actions into requirements/tests/runbooks with owners and dates.

### Component Definition of Done

- [ ] **47.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **47.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **47.D3.** Traceability links `Incident severity, paging, containment, and recovery runbook` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 48. Recurring access, policy, dependency, and architecture review process

**Priority:** P2  
**Source controls:** `C098`  
**Objective:** Continuously revalidate privileged access, trust policy, dependencies, and architectural assumptions.


### Architecture & contract

- [ ] **48.01.** Perform periodic review of administrative roles, service identities, KMS/HSM permissions, database access, and break-glass grants.
- [ ] **48.02.** Review trust anchors, approved signers, revocation sources, measurement policies, algorithm policy, and offline exceptions.
- [ ] **48.03.** Review dependency versions, EOL dates, vulnerabilities, and supply-chain provenance.

### Implementation & data/state

- [ ] **48.04.** Review architecture assumptions against actual scale, failure incidents, new platform types, and threat intelligence.
- [ ] **48.05.** Reconcile deployed configuration/policy digests against approved source-of-truth.
- [ ] **48.06.** Require evidence and reviewer sign-off; track findings as owned remediation items.

### Security & failure semantics

- [ ] **48.07.** Remove stale access/policies rather than only documenting them.
- [ ] **48.08.** Define review cadence by risk and trigger out-of-cycle review after major incidents/compromises.

### Component Definition of Done

- [ ] **48.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **48.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **48.D3.** Traceability links `Recurring access, policy, dependency, and architecture review process` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 49. Exception, waiver, and technical-debt register

**Priority:** P2  
**Source controls:** `C099`  
**Objective:** Make deviations from security/production requirements explicit, owned, time-bounded, and visible to release gates.


### Architecture & contract

- [ ] **49.01.** Define a structured record with requirement/control ID, scope, rationale, risk, compensating controls, owner, approver, issue date, expiry, and remediation plan.
- [ ] **49.02.** Prohibit indefinite waivers; require explicit expiration and renewal review.
- [ ] **49.03.** Require higher approval for security-critical P0 exceptions and prohibit waiving foundational trust invariants such as replay safety without an approved redesign.

### Implementation & data/state

- [ ] **49.04.** Link each exception to affected releases/environments and machine-readable acceptance evidence.
- [ ] **49.05.** Alert before waiver expiry and fail deployment/release after expiry unless renewed through the approval process.
- [ ] **49.06.** Track aggregate exception count/age/severity as a governance metric.

### Security & failure semantics

- [ ] **49.07.** Close exceptions only with evidence that the underlying requirement is now satisfied.
- [ ] **49.08.** Periodically review recurring exceptions for architectural/root-cause remediation.

### Component Definition of Done

- [ ] **49.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **49.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **49.D3.** Traceability links `Exception, waiver, and technical-debt register` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 50. Formal production exit gate

**Priority:** P2  
**Source controls:** `C100`  
**Objective:** Make production readiness an evidence-driven decision rather than a checklist declaration.


### Architecture & contract

- [ ] **50.01.** Define mandatory gate inputs: implementation status, traceability, tests, threat model, vulnerability status, performance, DR, compatibility, operations, runbooks, SBOM/provenance, and exceptions.
- [ ] **50.02.** Encode objective pass/fail rules where possible and identify which decisions require named human approval.
- [ ] **50.03.** Block release if any P0 component is unsatisfied unless an explicitly authorized policy allows a documented exception; record the exact authority and rationale.

### Implementation & data/state

- [ ] **50.04.** Validate evidence artifact hashes match the candidate build and configuration/policy versions.
- [ ] **50.05.** Require all critical/high vulnerabilities to be remediated or formally accepted under policy.
- [ ] **50.06.** Require successful restore/DR and rollback evidence within the defined freshness window.

### Security & failure semantics

- [ ] **50.07.** Require compatibility/performance results for supported production profiles.
- [ ] **50.08.** Produce a signed gate decision containing approvers, evidence manifest digest, waivers, release digest, and timestamp.
- [ ] **50.09.** Retain past gate decisions immutably and make later revocation possible if evidence is discovered invalid.

### Component Definition of Done

- [ ] **50.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **50.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **50.D3.** Traceability links `Formal production exit gate` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 51. Packaging, build metadata, and dependency pinning

**Priority:** P2  
**Source controls:** `C031`  
**Objective:** Produce deterministic, versioned, verifiable installation artifacts with explicit dependency closure.


### Architecture & contract

- [ ] **51.01.** Define supported packaging formats and platform targets with consistent semantic versioning.
- [ ] **51.02.** Pin direct and transitive dependency versions or hashes using lockfiles/constraints appropriate to each ecosystem.
- [ ] **51.03.** Capture build metadata: source commit, dirty-tree state, toolchain versions, target architecture, build timestamp policy, and feature flags.

### Implementation & data/state

- [ ] **51.04.** Use hermetic/reproducible build inputs where practical and prohibit untracked network dependency resolution during release builds.
- [ ] **51.05.** Generate checksums/signatures for every release artifact and include them in the provenance manifest.
- [ ] **51.06.** Validate archive paths/names for Windows-safe extraction, path-length limits, case collisions, Unicode normalization collisions, and forbidden device names.

### Security & failure semantics

- [ ] **51.07.** Run clean-install/upgrade/uninstall tests on each supported platform and architecture.
- [ ] **51.08.** Ensure default installation does not generate insecure sample keys, trust anchors, or permissive production configuration.
- [ ] **51.09.** Include license/notice/SBOM/security documentation consistently in every release package.

### Verification & interoperability

- [ ] **51.10.** Fail packaging when expected files are missing or untracked extra files appear.

### Component Definition of Done

- [ ] **51.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **51.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **51.D3.** Traceability links `Packaging, build metadata, and dependency pinning` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 52. SBOM, provenance, release signing, and dependency vulnerability scanning

**Priority:** P2  
**Source controls:** `C045, C090`  
**Objective:** Provide verifiable software supply-chain identity and continuous dependency risk assessment.


### Architecture & contract

- [ ] **52.01.** Generate machine-readable SBOM (SPDX or CycloneDX) including direct/transitive dependencies, versions, licenses, hashes, and package identifiers.
- [ ] **52.02.** Generate build provenance attestation linking source revision, builder identity, workflow, materials, artifact digest, and build parameters.
- [ ] **52.03.** Sign release artifacts and provenance with managed release keys; publish verification metadata and rotation policy.

### Implementation & data/state

- [ ] **52.04.** Run dependency vulnerability scanning against current advisory databases and record scan timestamp/tool/database revision.
- [ ] **52.05.** Run license/policy checks and flag prohibited/unknown licenses or packages.
- [ ] **52.06.** Protect CI release workflows from untrusted pull-request secret access and require controlled promotion to signing.

### Security & failure semantics

- [ ] **52.07.** Verify third-party downloaded binaries/packages with signatures/checksums and record provenance.
- [ ] **52.08.** Add provenance verification to deployment/installation so unsigned or mismatched artifacts are rejected where feasible.
- [ ] **52.09.** Archive SBOM/provenance/scan outputs in the acceptance evidence bundle and tie them to exact artifact digests.

### Verification & interoperability

- [ ] **52.10.** Define response workflow when a new post-release vulnerability is discovered in an SBOM component.

### Component Definition of Done

- [ ] **52.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **52.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **52.D3.** Traceability links `SBOM, provenance, release signing, and dependency vulnerability scanning` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 53. License, notice, and security disclosure policy

**Priority:** P2  
**Source controls:** `Governance`  
**Objective:** Make redistribution rights, attribution obligations, and vulnerability reporting channels explicit.


### Architecture & contract

- [ ] **53.01.** Identify and document the project license and ensure repository/package headers and LICENSE file are consistent.
- [ ] **53.02.** Generate NOTICE/third-party attribution from the verified dependency inventory and preserve required copyright/license texts.
- [ ] **53.03.** Review dependencies for copyleft/redistribution/export restrictions inconsistent with distribution goals.

### Implementation & data/state

- [ ] **53.04.** Publish SECURITY.md with supported versions, vulnerability reporting channel, expected acknowledgement, disclosure process, and encryption key if used.
- [ ] **53.05.** Define coordinated vulnerability disclosure timelines and emergency handling for actively exploited issues.
- [ ] **53.06.** Define handling of security researchers, duplicate reports, embargoed advisories, and CVE assignment where applicable.

### Security & failure semantics

- [ ] **53.07.** Add CI checks ensuring LICENSE/NOTICE/SECURITY files are included in release packages and stay synchronized with dependencies.
- [ ] **53.08.** Review cryptography/export/legal obligations appropriate to distribution jurisdictions with qualified counsel when necessary.

### Component Definition of Done

- [ ] **53.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **53.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **53.D3.** Traceability links `License, notice, and security disclosure policy` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# 54. Complete operational day-0/day-1/day-2 runbooks

**Priority:** P2  
**Source controls:** `C096`  
**Objective:** Provide executable procedures for provisioning, deployment, validation, routine operations, upgrades, incidents, and recovery.


### Architecture & contract

- [ ] **54.01.** Create Day-0 prerequisites covering infrastructure, identities, KMS/HSM keys, trust anchors, databases, secure time, network policy, certificates, and capacity.
- [ ] **54.02.** Create Day-1 deployment steps with commands, configuration validation, schema migration, service startup order, readiness checks, canary verification, and rollback points.
- [ ] **54.03.** Create Day-2 procedures for policy publication, trust-anchor rotation, key rotation, certificate renewal, node enrollment/revocation, quarantine review, backup, restore, and capacity scaling.

### Implementation & data/state

- [ ] **54.04.** Include exact preconditions, required permissions, expected outputs, failure branches, and post-action verification for each procedure.
- [ ] **54.05.** Provide troubleshooting decision trees keyed to stable error/reason codes and observability signals.
- [ ] **54.06.** Include controlled procedures for dependency outage, time integrity failure, replay-store saturation, audit-ledger outage, and site disconnection.

### Security & failure semantics

- [ ] **54.07.** Include upgrade/downgrade compatibility checks and prohibit rollback that weakens monotonic security state.
- [ ] **54.08.** Include disaster-recovery and failback steps validated against scheduled game-day evidence.
- [ ] **54.09.** Keep commands/scripts version-controlled and test them in staging; avoid undocumented manual console steps.

### Verification & interoperability

- [ ] **54.10.** Assign runbook owners/review cadence and link alerts directly to the appropriate procedure.

### Component Definition of Done

- [ ] **54.D1.** All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.
- [ ] **54.D2.** No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.
- [ ] **54.D3.** Traceability links `Complete operational day-0/day-1/day-2 runbooks` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.

---

# Program-level production exit gate

- [ ] **G01.** All P0 sections 01–15 meet their component Definition of Done; no P0 waiver weakens a foundational trust invariant without explicit executive/security risk acceptance and compensating architecture.
- [ ] **G02.** All P1 sections 16–34 required by the deployed topology meet Definition of Done and have passed resilience, HA, partition, scale, and operational tests.
- [ ] **G03.** All P2 sections 35–54 required by organizational release policy meet Definition of Done, or have approved, time-bounded waivers.
- [ ] **G04.** The requirements traceability matrix shows no production SHALL requirement with status `unknown`, `unmapped`, or `claimed complete without evidence`.
- [ ] **G05.** Release artifact, source commit, SBOM, provenance, signatures, policy/configuration digests, test evidence, compatibility matrix, and runbook versions are mutually consistent.
- [ ] **G06.** Security review confirms threat-model coverage for replay, relay/cuckoo, identity cloning, policy poisoning, key/trust-anchor compromise, parser attacks, tenant isolation, rollback, and control-plane abuse.
- [ ] **G07.** Restore/DR, failover, rollback, canary, offline/disconnected, and quarantine/recovery exercises have current passing evidence within the organization-defined freshness window.
- [ ] **G08.** Load/soak/burst results demonstrate capacity headroom and no unbounded state/resource growth at target fleet scale and defined adversarial limits.
- [ ] **G09.** Operations/on-call accepts dashboards, alerts, runbooks, paging, incident containment, and recovery procedures; named owners and escalation paths are current.
- [ ] **G10.** A signed production-gate record identifies the exact artifact digest, approved deployment scope, approvers, evidence-manifest digest, active waivers, and decision timestamp.

## Evidence record template

Use the following minimum fields for each completed component or major control:

```yaml
component_id: GAP06-MC-XX
control_id: XX.YY
status: pass | fail | waived
release_version: 
source_commit: 
build_artifact_sha256: 
configuration_digest: 
policy_digest: 
test_or_evidence_id: 
evidence_sha256: 
test_environment: 
verified_by: 
security_reviewer: 
operations_reviewer: 
verified_at_utc: 
waiver_id: null
waiver_expiry_utc: null
notes: 
```

## Completion rule

A component is not production-ready merely because its software exists. It is complete only when its architecture, implementation, security invariants, failure behavior, tests, telemetry, operations, documentation, and immutable acceptance evidence collectively satisfy the component checklist and Universal Gate.
