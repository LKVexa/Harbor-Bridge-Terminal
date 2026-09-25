# GAP-06 SHALL specification (mechanical conversion, v5.0.0)

Each checklist item restated as a normative requirement with a stable id. Not yet atomic or reviewed (38.02/38.03 open).

- **GAP06-REQ-U01** — The subsystem SHALL satisfy: Assign a unique implementation work-item ID and named engineering owner; record security and operations reviewers.  
  status [!]
- **GAP06-REQ-U02** — The subsystem SHALL satisfy: Define explicit in-scope and out-of-scope behavior, trust assumptions, supported deployment modes, and dependency boundaries.  
  status [~]
- **GAP06-REQ-U03** — The subsystem SHALL satisfy: Convert the component objective into SHALL-level requirements with measurable acceptance criteria and stable traceability IDs.  
  status [~]
- **GAP06-REQ-U04** — The subsystem SHALL satisfy: Produce or update architecture/data-flow/state diagrams showing trust boundaries, authoritative state, failure domains, and external dependencies.  
  status [~]
- **GAP06-REQ-U05** — The subsystem SHALL satisfy: Document all externally observable API/schema/state changes and backward/forward compatibility impact.  
  status [~]
- **GAP06-REQ-U06** — The subsystem SHALL satisfy: Define configuration parameters with types, defaults, safe bounds, provenance, mutability, and restart requirements.  
  status [~]
- **GAP06-REQ-U07** — The subsystem SHALL satisfy: Perform threat analysis for spoofing, tampering, replay/rollback, privilege escalation, information leakage, resource exhaustion, and dependency compromise relevant to the component.  
  status [~]
- **GAP06-REQ-U08** — The subsystem SHALL satisfy: Implement deny-by-default behavior for ambiguous, malformed, unauthorized, stale, or unverifiable inputs whenever the component affects a trust decision.  
  status [~]
- **GAP06-REQ-U09** — The subsystem SHALL satisfy: Use bounded parsing/queues/caches/retries and explicit input/resource limits; demonstrate that hostile inputs cannot cause unbounded memory, CPU, storage, thread, or connection growth.  
  status [~]
- **GAP06-REQ-U10** — The subsystem SHALL satisfy: Protect sensitive data in transit and at rest as appropriate; redact logs and prohibit secret/private-key material in diagnostics.  
  status [~]
- **GAP06-REQ-U11** — The subsystem SHALL satisfy: Add deterministic unit tests for normal, boundary, invalid, stale, duplicate, and failure cases.  
  status [~]
- **GAP06-REQ-U12** — The subsystem SHALL satisfy: Add integration tests against production-equivalent dependencies and schemas rather than relying only on mocks.  
  status [!]
- **GAP06-REQ-U13** — The subsystem SHALL satisfy: Add concurrency/fault-injection/negative security tests for race conditions, partial failure, retry duplication, restart, and dependency outage.  
  status [~]
- **GAP06-REQ-U14** — The subsystem SHALL satisfy: Define required metrics, structured logs, traces, security events, health signals, dashboards, alerts, and cardinality/redaction controls.  
  status [~]
- **GAP06-REQ-U15** — The subsystem SHALL satisfy: Define operational limits/SLOs, saturation thresholds, load-shedding or fail-closed behavior, and capacity assumptions.  
  status [~]
- **GAP06-REQ-U16** — The subsystem SHALL satisfy: Document deployment, upgrade, rollback, backup/restore (if stateful), incident response, and recovery procedures.  
  status [~]
- **GAP06-REQ-U17** — The subsystem SHALL satisfy: Generate machine-verifiable acceptance evidence tied to source commit, build artifact digest, configuration/policy version, test result, and tool/environment versions.  
  status [~]
- **GAP06-REQ-U18** — The subsystem SHALL satisfy: Update the requirements traceability matrix so every claimed satisfied requirement links to implementation and passing evidence.  
  status [~]
- **GAP06-REQ-U19** — The subsystem SHALL satisfy: Review open vulnerabilities, waivers, and technical debt; ensure every exception has owner, approver, compensating controls, and expiry.  
  status [~]
- **GAP06-REQ-U20** — The subsystem SHALL satisfy: Require independent code/security/operations review and satisfy the formal production exit gate before marking the component complete.  
  status [!]
- **GAP06-REQ-01.01** — The subsystem SHALL satisfy: Define a supported-attester matrix covering discrete TPM 2.0, firmware TPM, vTPM, and each TEE/platform adapter, including minimum firmware/API versions and explicitly unsupported modes.  
  status [~]
- **GAP06-REQ-01.02** — The subsystem SHALL satisfy: Define a canonical quote/evidence envelope that binds verifier challenge nonce, attesting key identity, PCR selection, PCR digest, clock/reset/restart counters, firmware/security-version metadata, and device identity.  
  status [~]
- **GAP06-REQ-01.03** — The subsystem SHALL satisfy: Parse TPM2B_ATTEST/TPMS_ATTEST structures with a bounds-checked parser; reject trailing bytes, duplicate fields, illegal lengths, unsupported magic/type values, and ambiguous encodings.  
  status [~]
- **GAP06-REQ-01.04** — The subsystem SHALL satisfy: Verify quote signatures using the enrolled attestation key and an allow-listed algorithm/profile; reject SHA-1 and other deprecated algorithms unless an explicitly approved migration policy permits them.  
  status [~]
- **GAP06-REQ-01.05** — The subsystem SHALL satisfy: Recompute PCR digests from the exact quoted PCR selection and compare them byte-for-byte to the quote; support required PCR banks and reject unexpected bank/selection combinations.  
  status [~]
- **GAP06-REQ-01.06** — The subsystem SHALL satisfy: Parse and replay platform event logs against quoted PCRs; surface the first divergent event and retain the validated event-log digest as evidence.  
  status [~]
- **GAP06-REQ-01.07** — The subsystem SHALL satisfy: Add IMA/runtime-measurement verification where supported, including template parsing, file-digest algorithm validation, and policy-controlled treatment of unknown templates.  
  status [~]
- **GAP06-REQ-01.08** — The subsystem SHALL satisfy: Bind quote freshness to a server-issued challenge with explicit issuance time, expiry, intended node, intended service/tenant, and one-time consumption semantics.  
  status [~]
- **GAP06-REQ-01.09** — The subsystem SHALL satisfy: Validate TPM clockInfo resetCount/restartCount/safe semantics and define fail-closed behavior for counter rollback or unsafe clock state.  
  status [~]
- **GAP06-REQ-01.10** — The subsystem SHALL satisfy: For TEE adapters, verify vendor-specific attestation signatures/certificates, security version numbers, debug state, TCB status, and report-data/channel-binding fields.  
  status [~]
- **GAP06-REQ-01.11** — The subsystem SHALL satisfy: Implement anti-cuckoo/relay controls such as channel binding, AK-to-device enrollment binding, locality checks where available, and duplicate-active-attester detection.  
  status [~]
- **GAP06-REQ-01.12** — The subsystem SHALL satisfy: Use hardened cryptographic libraries rather than custom signature primitives; enforce strict public-key sizes, curves, encodings, and signature format validation.  
  status [~]
- **GAP06-REQ-01.13** — The subsystem SHALL satisfy: Create positive test vectors from at least two hardware/vendor families plus vTPM, and negative vectors for tampered nonce, PCR digest, signature, event log, clock counters, and unsupported algorithms.  
  status [!]
- **GAP06-REQ-01.14** — The subsystem SHALL satisfy: Expose verifier result codes that distinguish malformed evidence, authentication failure, freshness failure, PCR/event-log mismatch, unsupported platform, TCB failure, and internal verifier error without leaking secrets.  
  status [~]
- **GAP06-REQ-01.15** — The subsystem SHALL satisfy: Record machine-verifiable evidence containing verifier version, trust-anchor set, policy version, raw-evidence digest, parsed claims digest, decision, reason code, and decision timestamp.  
  status [~]
- **GAP06-REQ-01.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-01.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-01.D3** — The subsystem SHALL satisfy: Traceability links `Real hardware attestation verifier` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-02.01** — The subsystem SHALL satisfy: Define authoritative manufacturer/vendor trust stores and a governed process for importing, reviewing, versioning, activating, and retiring roots/intermediates.  
  status [!]
- **GAP06-REQ-02.02** — The subsystem SHALL satisfy: Parse EK/AK certificates using a strict X.509 implementation; reject malformed DER, duplicate critical extensions, unknown critical extensions, illegal key sizes, and policy-incompatible algorithms.  
  status [~]
- **GAP06-REQ-02.03** — The subsystem SHALL satisfy: Validate full path construction to an approved trust anchor, including Basic Constraints, path length, name constraints where applicable, validity periods, and signature algorithms.  
  status [~]
- **GAP06-REQ-02.04** — The subsystem SHALL satisfy: Validate EK certificate EKU/key-usage/SAN fields and vendor-specific TPM identity attributes according to TCG/vendor profiles.  
  status [~]
- **GAP06-REQ-02.05** — The subsystem SHALL satisfy: Validate AK certification/proof linking the attestation key to the enrolled hardware root; do not treat an arbitrary self-signed AK as equivalent to hardware-backed identity.  
  status [~]
- **GAP06-REQ-02.06** — The subsystem SHALL satisfy: Implement OCSP and/or CRL checking policy with responder authentication, freshness limits, stapling/cache behavior, and explicit soft-fail versus hard-fail rules.  
  status [~]
- **GAP06-REQ-02.07** — The subsystem SHALL satisfy: Maintain revocation cache persistence across restart and ensure stale revocation data cannot silently become trusted.  
  status [ ]
- **GAP06-REQ-02.08** — The subsystem SHALL satisfy: Enforce certificate time validation against the authoritative time policy and define behavior when trusted time is degraded/unavailable.  
  status [~]
- **GAP06-REQ-02.09** — The subsystem SHALL satisfy: Capture certificate serials, subject key identifiers, issuer identifiers, trust-anchor IDs, and revocation evidence in the decision record without logging private key material.  
  status [~]
- **GAP06-REQ-02.10** — The subsystem SHALL satisfy: Add trust-anchor rollover support with overlap windows, staged activation, rollback, and tests preventing accidental trust-store widening.  
  status [ ]
- **GAP06-REQ-02.11** — The subsystem SHALL satisfy: Add negative tests for expired/not-yet-valid certificates, revoked EK/AK, wrong EKU, invalid chain, untrusted manufacturer root, weak signature algorithm, and malformed extensions.  
  status [~]
- **GAP06-REQ-02.12** — The subsystem SHALL satisfy: Add manufacturer-root supply-chain validation: provenance metadata, checksum/signature verification, change approval, and periodic root-store reconciliation.  
  status [!]
- **GAP06-REQ-02.13** — The subsystem SHALL satisfy: Publish a machine-readable certificate-validation policy and compatibility matrix that can be pinned by release and audited independently.  
  status [~]
- **GAP06-REQ-02.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-02.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-02.D3** — The subsystem SHALL satisfy: Traceability links `Endorsement/attestation certificate-chain validation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-03.01** — The subsystem SHALL satisfy: Define enrollment states (unseen, pending, enrolled, suspended, revoked, replaced, recovery-pending) and legal state transitions with explicit authorization requirements.  
  status [~]
- **GAP06-REQ-03.02** — The subsystem SHALL satisfy: Require proof-of-possession for every enrolled identity key and attestation key; bind enrollment to the presented hardware attestation rather than accepting public-key registration alone.  
  status [~]
- **GAP06-REQ-03.03** — The subsystem SHALL satisfy: Authenticate the enrolling principal/service using mTLS or equivalent workload identity and authorize enrollment by site/tenant/environment policy.  
  status [~]
- **GAP06-REQ-03.04** — The subsystem SHALL satisfy: Generate a unique enrollment transaction ID and bind all enrollment messages to node ID, hardware identity, nonce, policy version, and requestor identity.  
  status [~]
- **GAP06-REQ-03.05** — The subsystem SHALL satisfy: Prevent cloning by detecting duplicate active use of the same hardware root/AK identity from conflicting node identities, sites, or channels.  
  status [~]
- **GAP06-REQ-03.06** — The subsystem SHALL satisfy: Define key-rotation protocol with overlap, old/new key proof, atomic activation, rollback rules, and revocation of superseded keys.  
  status [~]
- **GAP06-REQ-03.07** — The subsystem SHALL satisfy: Define hardware replacement/reimage workflows that preserve auditability without silently transferring trust from old hardware to new hardware.  
  status [~]
- **GAP06-REQ-03.08** — The subsystem SHALL satisfy: Implement emergency revocation and suspension, including propagating status to verifiers, scheduler/quarantine systems, caches, and disconnected sites.  
  status [~]
- **GAP06-REQ-03.09** — The subsystem SHALL satisfy: Implement controlled recovery that requires stronger authorization than routine enrollment and cannot bypass proof-of-possession or hardware-root verification.  
  status [ ]
- **GAP06-REQ-03.10** — The subsystem SHALL satisfy: Protect enrollment against replay using expiring nonces, idempotency keys, transaction-state persistence, and one-time finalization.  
  status [~]
- **GAP06-REQ-03.11** — The subsystem SHALL satisfy: Encrypt sensitive enrollment traffic in transit; never transmit private keys; zeroize temporary secrets and redact security logs.  
  status [~]
- **GAP06-REQ-03.12** — The subsystem SHALL satisfy: Create negative tests for duplicate identity, wrong proof key, stale enrollment nonce, revoked hardware, unauthorized operator, cross-tenant enrollment, and partial-transaction replay.  
  status [~]
- **GAP06-REQ-03.13** — The subsystem SHALL satisfy: Persist a complete lifecycle audit trail linking every key/identity version to its predecessor, approver, evidence, timestamps, and reason code.  
  status [~]
- **GAP06-REQ-03.14** — The subsystem SHALL satisfy: Define enrollment SLOs, retry semantics, disaster recovery, and fail-closed behavior when the authoritative enrollment store is unavailable.  
  status [ ]
- **GAP06-REQ-03.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-03.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-03.D3** — The subsystem SHALL satisfy: Traceability links `Cryptographic node identity enrollment protocol` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-04.01** — The subsystem SHALL satisfy: Define workload identity types to support (process, service, container, pod, VM, confidential VM/enclave) and the claim set required for each.  
  status [~]
- **GAP06-REQ-04.02** — The subsystem SHALL satisfy: Define the chain of trust from hardware/node attestation to workload launch evidence, including orchestrator identity and image/artifact provenance.  
  status [~]
- **GAP06-REQ-04.03** — The subsystem SHALL satisfy: Bind workload identity to immutable image digest, signer/provenance identity, runtime configuration digest, namespace/tenant, and node attestation verdict.  
  status [~]
- **GAP06-REQ-04.04** — The subsystem SHALL satisfy: Integrate workload identity issuance with a short-lived credential mechanism (for example SPIFFE-compatible SVID semantics or an equivalent internal contract).  
  status [~]
- **GAP06-REQ-04.05** — The subsystem SHALL satisfy: Prevent credential transfer by binding issued workload credentials to workload key proof-of-possession and, where possible, the attested execution environment.  
  status [ ]
- **GAP06-REQ-04.06** — The subsystem SHALL satisfy: Validate container/VM launch measurements and reject mutable tag-only references when an immutable digest is required.  
  status [~]
- **GAP06-REQ-04.07** — The subsystem SHALL satisfy: Propagate node re-attestation failure/revocation to dependent workload identities according to explicit grace and termination policy.  
  status [~]
- **GAP06-REQ-04.08** — The subsystem SHALL satisfy: Define workload migration semantics so credentials cannot outlive or detach from the newly attested destination environment.  
  status [ ]
- **GAP06-REQ-04.09** — The subsystem SHALL satisfy: Enforce tenant/site/environment isolation in workload identity namespaces and authorization policy.  
  status [~]
- **GAP06-REQ-04.10** — The subsystem SHALL satisfy: Add revocation and forced credential expiry for compromised workloads, nodes, signers, or artifact digests.  
  status [ ]
- **GAP06-REQ-04.11** — The subsystem SHALL satisfy: Create positive/negative integration tests covering node trust loss, workload image substitution, namespace spoofing, replayed launch evidence, and credential theft attempts.  
  status [~]
- **GAP06-REQ-04.12** — The subsystem SHALL satisfy: Expose explainable workload verdicts linking the workload claim to node evidence, artifact provenance, policy versions, and credential issuance event.  
  status [ ]
- **GAP06-REQ-04.13** — The subsystem SHALL satisfy: Define scale targets for credential issuance/rotation across fleet-wide workload churn and burst scenarios.  
  status [ ]
- **GAP06-REQ-04.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-04.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-04.D3** — The subsystem SHALL satisfy: Traceability links `Workload identity attestation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-05.01** — The subsystem SHALL satisfy: Create normative schemas for PK_NODE_IDENTITY/1, PK_ATTESTATION/1, and PK_ACCEPTED_MEASUREMENTS/1 using protobuf, WIT, OpenAPI/JSON Schema, or another approved IDL.  
  status [~]
- **GAP06-REQ-05.02** — The subsystem SHALL satisfy: Define field types, required/optional semantics, canonical byte encodings, maximum sizes, default handling, and unknown-field behavior.  
  status [~]
- **GAP06-REQ-05.03** — The subsystem SHALL satisfy: Define stable enum/error namespaces and prohibit reuse of numeric IDs or semantic meaning across versions.  
  status [~]
- **GAP06-REQ-05.04** — The subsystem SHALL satisfy: Include explicit schema_version, policy_version, evidence_format, algorithm identifiers, tenant/site context, timestamps, and correlation IDs where applicable.  
  status [~]
- **GAP06-REQ-05.05** — The subsystem SHALL satisfy: Define compatibility rules for additive fields, reserved/deprecated fields, breaking changes, minimum/maximum peer versions, and downgrade prevention.  
  status [~]
- **GAP06-REQ-05.06** — The subsystem SHALL satisfy: Generate client/server bindings from the authoritative schemas and prohibit hand-maintained divergent DTOs.  
  status [ ]
- **GAP06-REQ-05.07** — The subsystem SHALL satisfy: Apply strict input size/depth/repetition limits to prevent parser amplification and resource exhaustion.  
  status [~]
- **GAP06-REQ-05.08** — The subsystem SHALL satisfy: Define canonical serialization for all data that is hashed, signed, or placed in tamper-evident logs.  
  status [~]
- **GAP06-REQ-05.09** — The subsystem SHALL satisfy: Create conformance fixtures with golden binary/JSON encodings and negative malformed examples.  
  status [~]
- **GAP06-REQ-05.10** — The subsystem SHALL satisfy: Add cross-language round-trip tests for every supported implementation language and architecture.  
  status [!]
- **GAP06-REQ-05.11** — The subsystem SHALL satisfy: Add fuzzing for decoders and semantic validators, including unknown fields, duplicate map keys, oversized lengths, invalid UTF encodings, and numeric overflow.  
  status [~]
- **GAP06-REQ-05.12** — The subsystem SHALL satisfy: Publish transport mappings for gRPC/HTTP/IPC/offline bundles, including content types, timeouts, retries, idempotency keys, and authentication context.  
  status [~]
- **GAP06-REQ-05.13** — The subsystem SHALL satisfy: Version the schema package independently and record the exact schema artifact digest in release evidence.  
  status [~]
- **GAP06-REQ-05.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-05.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-05.D3** — The subsystem SHALL satisfy: Traceability links `Typed external schemas and transports` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-06.01** — The subsystem SHALL satisfy: Require mutually authenticated transport for service-to-service calls using mTLS, platform workload identity, or an equivalently strong mechanism.  
  status [~]
- **GAP06-REQ-06.02** — The subsystem SHALL satisfy: Define distinct identities and roles for nodes, verifier services, policy publishers, operators, auditors, automation, and break-glass administrators.  
  status [~]
- **GAP06-REQ-06.03** — The subsystem SHALL satisfy: Implement deny-by-default authorization at each RPC/operation, not only at the listener or ingress layer.  
  status [~]
- **GAP06-REQ-06.04** — The subsystem SHALL satisfy: Bind authorization decisions to tenant/site/environment and resource identifiers to prevent confused-deputy and cross-tenant access.  
  status [~]
- **GAP06-REQ-06.05** — The subsystem SHALL satisfy: Validate peer certificate/SVID/token audience, issuer, expiry, revocation status, and proof-of-possession/channel binding where available.  
  status [~]
- **GAP06-REQ-06.06** — The subsystem SHALL satisfy: Define short-lived credential rotation and ensure servers hot-reload credentials without dropping trust validation.  
  status [ ]
- **GAP06-REQ-06.07** — The subsystem SHALL satisfy: Enforce TLS protocol/cipher/curve policy and disable legacy renegotiation, weak algorithms, plaintext fallback, and unauthenticated local TCP modes.  
  status [~]
- **GAP06-REQ-06.08** — The subsystem SHALL satisfy: Protect privileged policy/enrollment/revocation endpoints with stronger authorization and, where required, multi-party approval.  
  status [ ]
- **GAP06-REQ-06.09** — The subsystem SHALL satisfy: Implement request-level security context propagation without trusting caller-supplied identity headers.  
  status [~]
- **GAP06-REQ-06.10** — The subsystem SHALL satisfy: Add per-principal rate limits and authorization-failure throttling to reduce credential-stuffing/resource-exhaustion attacks.  
  status [~]
- **GAP06-REQ-06.11** — The subsystem SHALL satisfy: Redact secrets, credentials, certificate private material, and raw sensitive evidence from logs/traces.  
  status [~]
- **GAP06-REQ-06.12** — The subsystem SHALL satisfy: Create authorization matrix tests for every endpoint × role × tenant/site combination, including explicit negative tests.  
  status [~]
- **GAP06-REQ-06.13** — The subsystem SHALL satisfy: Emit auditable authentication/authorization decisions with principal ID, operation, target, policy revision, outcome, and reason code.  
  status [~]
- **GAP06-REQ-06.14** — The subsystem SHALL satisfy: Define break-glass access with time-bound grants, immutable audit, post-event review, and no permanent bypass path.  
  status [ ]
- **GAP06-REQ-06.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-06.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-06.D3** — The subsystem SHALL satisfy: Traceability links `Authenticated and authorized service boundary` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-07.01** — The subsystem SHALL satisfy: Define authoritative persistent records for enrollment, identity versions, revocations, outstanding challenges, spent challenges, verdicts, quarantine state, trust anchors, and measurement-policy revisions.  
  status [~]
- **GAP06-REQ-07.02** — The subsystem SHALL satisfy: Choose a transactional persistence engine with documented durability guarantees, fsync/commit semantics, consistency model, backup strategy, and HA behavior.  
  status [~]
- **GAP06-REQ-07.03** — The subsystem SHALL satisfy: Make challenge issuance and consumption atomic with respect to persistence; a crash after acceptance must not make a consumed challenge reusable.  
  status [~]
- **GAP06-REQ-07.04** — The subsystem SHALL satisfy: Persist revocation and quarantine changes before acknowledging success to callers.  
  status [~]
- **GAP06-REQ-07.05** — The subsystem SHALL satisfy: Define schema migration strategy with forward/backward compatibility, transactional migration, backup, dry-run validation, and rollback rules.  
  status [ ]
- **GAP06-REQ-07.06** — The subsystem SHALL satisfy: Encrypt sensitive state at rest and separate encryption keys from the database/storage system using managed KMS/HSM controls.  
  status [ ]
- **GAP06-REQ-07.07** — The subsystem SHALL satisfy: Implement database integrity constraints for uniqueness, foreign keys/references, version monotonicity, and legal state transitions.  
  status [~]
- **GAP06-REQ-07.08** — The subsystem SHALL satisfy: Protect against rollback to stale snapshots by recording monotonic generation/epoch metadata and validating it during restore/startup.  
  status [~]
- **GAP06-REQ-07.09** — The subsystem SHALL satisfy: Define retention and compaction policies that preserve replay safety and required forensic history.  
  status [~]
- **GAP06-REQ-07.10** — The subsystem SHALL satisfy: Create crash-injection tests at each write boundary for challenge issuance/consume, enrollment, revocation, policy activation, and quarantine.  
  status [~]
- **GAP06-REQ-07.11** — The subsystem SHALL satisfy: Create backup/restore tests proving restored state rejects previously consumed challenges and retains revocations/quarantine.  
  status [~]
- **GAP06-REQ-07.12** — The subsystem SHALL satisfy: Expose persistence health, replication lag, transaction latency, storage capacity, corruption/integrity errors, and backup age.  
  status [ ]
- **GAP06-REQ-07.13** — The subsystem SHALL satisfy: Document RPO/RTO targets and validate them with scheduled restore exercises.  
  status [!]
- **GAP06-REQ-07.14** — The subsystem SHALL satisfy: Fail closed or enter an explicitly defined degraded read-only mode when authoritative security state cannot be durably written.  
  status [~]
- **GAP06-REQ-07.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-07.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-07.D3** — The subsystem SHALL satisfy: Traceability links `Durable security state` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-08.01** — The subsystem SHALL satisfy: Define a globally unique challenge identifier and authoritative ownership record including intended node, issuing epoch, expiry, site/tenant, and status.  
  status [~]
- **GAP06-REQ-08.02** — The subsystem SHALL satisfy: Use linearizable compare-and-set/transactional consume semantics or an equivalent design that prevents two replicas from accepting the same challenge.  
  status [~]
- **GAP06-REQ-08.03** — The subsystem SHALL satisfy: Define leader/lease/fencing behavior and reject writes from stale leaders after failover.  
  status [~]
- **GAP06-REQ-08.04** — The subsystem SHALL satisfy: Persist replica epoch/generation numbers and include them in replay-sensitive operations to detect stale state after restart or failback.  
  status [~]
- **GAP06-REQ-08.05** — The subsystem SHALL satisfy: Define consistency behavior under network partition: which side can issue/consume challenges, how minority replicas fail, and when fail-closed is mandatory.  
  status [!]
- **GAP06-REQ-08.06** — The subsystem SHALL satisfy: Prevent nonce issuance collisions across replicas using CSPRNG plus uniqueness enforcement and collision handling.  
  status [~]
- **GAP06-REQ-08.07** — The subsystem SHALL satisfy: Define bounded challenge/spent-record retention consistent with maximum evidence replay window, audit requirements, and restore scenarios.  
  status [~]
- **GAP06-REQ-08.08** — The subsystem SHALL satisfy: Define site failover semantics so challenges issued in one site cannot be erroneously reaccepted after traffic shifts.  
  status [!]
- **GAP06-REQ-08.09** — The subsystem SHALL satisfy: Implement clock-independent or secure-time-assisted expiry semantics that remain safe under wall-clock skew.  
  status [~]
- **GAP06-REQ-08.10** — The subsystem SHALL satisfy: Create concurrency tests with simultaneous consume attempts from multiple replicas and verify exactly one successful commit.  
  status [~]
- **GAP06-REQ-08.11** — The subsystem SHALL satisfy: Create chaos tests for leader loss, split brain, replication lag, delayed messages, retry storms, and failback.  
  status [!]
- **GAP06-REQ-08.12** — The subsystem SHALL satisfy: Expose metrics for duplicate consume attempts, fencing failures, stale leader writes, replication lag, conflict retries, and partition mode.  
  status [ ]
- **GAP06-REQ-08.13** — The subsystem SHALL satisfy: Produce formal invariants for challenge lifecycle and verify them with property/state-machine tests.  
  status [~]
- **GAP06-REQ-08.14** — The subsystem SHALL satisfy: Document operator procedures for partition recovery that do not clear replay state or reset epochs unsafely.  
  status [~]
- **GAP06-REQ-08.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-08.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-08.D3** — The subsystem SHALL satisfy: Traceability links `Distributed replay protection and HA consistency` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-09.01** — The subsystem SHALL satisfy: Define a canonical signed policy bundle containing policy ID/version, target scope, accepted measurements, algorithms, signer identity, activation window, and rollback metadata.  
  status [~]
- **GAP06-REQ-09.02** — The subsystem SHALL satisfy: Sign policy bundles with managed offline/online publication keys whose usage is restricted separately from ordinary service credentials.  
  status [!]
- **GAP06-REQ-09.03** — The subsystem SHALL satisfy: Verify signature, signer authorization, policy schema, semantic invariants, and monotonic version rules before staging.  
  status [~]
- **GAP06-REQ-09.04** — The subsystem SHALL satisfy: Require multi-party approval or change-control evidence for high-impact policy changes according to governance requirements.  
  status [~]
- **GAP06-REQ-09.05** — The subsystem SHALL satisfy: Prevent policy rollback below a minimum trusted version unless an explicitly authorized emergency rollback procedure is invoked.  
  status [~]
- **GAP06-REQ-09.06** — The subsystem SHALL satisfy: Implement staged rollout by environment/site/ring with canary validation and automatic halt on defined error/attestation-failure thresholds.  
  status [~]
- **GAP06-REQ-09.07** — The subsystem SHALL satisfy: Make activation atomic: verifiers must never observe a partially written policy or mixed component set.  
  status [~]
- **GAP06-REQ-09.08** — The subsystem SHALL satisfy: Cache prior policy versions for deterministic verdict explanation and controlled rollback.  
  status [~]
- **GAP06-REQ-09.09** — The subsystem SHALL satisfy: Define conflict and precedence rules for overlapping policy scopes and reject ambiguous policy combinations.  
  status [~]
- **GAP06-REQ-09.10** — The subsystem SHALL satisfy: Protect against poisoning by validating artifact provenance, signer chain, content digest, expected target scope, and approval metadata.  
  status [~]
- **GAP06-REQ-09.11** — The subsystem SHALL satisfy: Add offline/disconnected distribution format with signature validation and maximum-staleness rules.  
  status [ ]
- **GAP06-REQ-09.12** — The subsystem SHALL satisfy: Create tests for tampered policy, unauthorized signer, stale version, wrong target scope, partial bundle, rollback attempt, and conflicting policy.  
  status [~]
- **GAP06-REQ-09.13** — The subsystem SHALL satisfy: Emit publication/activation/rollback events into the tamper-evident audit ledger with signer, approver, digest, and affected scope.  
  status [ ]
- **GAP06-REQ-09.14** — The subsystem SHALL satisfy: Publish machine-readable rollout status and exact active policy digest per verifier/site.  
  status [ ]
- **GAP06-REQ-09.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-09.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-09.D3** — The subsystem SHALL satisfy: Traceability links `Signed measurement-policy publication` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-10.01** — The subsystem SHALL satisfy: Define which decisions require monotonic elapsed time versus trusted wall-clock time and prohibit implicit mixing of the two.  
  status [~]
- **GAP06-REQ-10.02** — The subsystem SHALL satisfy: Integrate an OS monotonic clock for process-local intervals and an authenticated time source for wall-clock validation where required.  
  status [~]
- **GAP06-REQ-10.03** — The subsystem SHALL satisfy: Define maximum tolerated skew, drift, leap behavior, NTP/PTP source requirements, and alert thresholds.  
  status [~]
- **GAP06-REQ-10.04** — The subsystem SHALL satisfy: Persist boot/session epoch metadata so restart cannot cause old challenges/verdicts to regain validity.  
  status [~]
- **GAP06-REQ-10.05** — The subsystem SHALL satisfy: Use TPM/TEE monotonic counters or trusted clock claims where available and define validation against server time.  
  status [~]
- **GAP06-REQ-10.06** — The subsystem SHALL satisfy: Detect backward wall-clock jumps and enter a defined degraded/fail-closed state for operations that depend on trusted time.  
  status [~]
- **GAP06-REQ-10.07** — The subsystem SHALL satisfy: Detect excessive forward jumps that could prematurely expire policy/certificates and require controlled recovery.  
  status [~]
- **GAP06-REQ-10.08** — The subsystem SHALL satisfy: Ensure certificate/OCSP/CRL validation uses the same authoritative time policy as attestation freshness.  
  status [~]
- **GAP06-REQ-10.09** — The subsystem SHALL satisfy: Define disconnected-site time behavior, including holdover duration, maximum offline age, and conditions requiring local rejection.  
  status [~]
- **GAP06-REQ-10.10** — The subsystem SHALL satisfy: Add deterministic clock abstraction for tests while preventing test clocks from being enabled in production builds/configuration.  
  status [~]
- **GAP06-REQ-10.11** — The subsystem SHALL satisfy: Create tests for backward/forward jumps, restart, daylight-saving changes, leap seconds, drift, unavailable time sources, and multi-replica skew.  
  status [~]
- **GAP06-REQ-10.12** — The subsystem SHALL satisfy: Expose time-source health, offset, uncertainty, sync age, rollback detections, and degraded-mode metrics.  
  status [ ]
- **GAP06-REQ-10.13** — The subsystem SHALL satisfy: Document recovery procedure after time integrity failure without manually bypassing freshness checks.  
  status [~]
- **GAP06-REQ-10.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-10.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-10.D3** — The subsystem SHALL satisfy: Traceability links `Authoritative time source` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-11.01** — The subsystem SHALL satisfy: Define a typed quarantine command/event containing node identity, reason, attestation verdict ID, severity, policy version, creation time, expiry/review state, and correlation ID.  
  status [~]
- **GAP06-REQ-11.02** — The subsystem SHALL satisfy: Integrate with GAP-01 node supervisor and scheduling control planes so quarantined nodes cannot receive new workloads.  
  status [~]
- **GAP06-REQ-11.03** — The subsystem SHALL satisfy: Define treatment of already-running workloads: drain, migrate, terminate, isolate network, or preserve for forensics based on reason/severity.  
  status [ ]
- **GAP06-REQ-11.04** — The subsystem SHALL satisfy: Make quarantine enforcement idempotent and durable across verifier, scheduler, and supervisor restarts.  
  status [~]
- **GAP06-REQ-11.05** — The subsystem SHALL satisfy: Require explicit trusted re-attestation and/or authorized operator action before clearing quarantine; never clear solely on timeout unless policy explicitly allows it.  
  status [~]
- **GAP06-REQ-11.06** — The subsystem SHALL satisfy: Propagate revocation and severe policy failures to quarantine immediately with bounded control-plane latency.  
  status [~]
- **GAP06-REQ-11.07** — The subsystem SHALL satisfy: Define behavior when enforcement dependencies are unavailable: fail closed for new placement and queue reconciliation work.  
  status [~]
- **GAP06-REQ-11.08** — The subsystem SHALL satisfy: Prevent a node from self-clearing or spoofing quarantine state through untrusted telemetry.  
  status [~]
- **GAP06-REQ-11.09** — The subsystem SHALL satisfy: Add signed/correlated audit events for request, enforcement acknowledgement, workload action, operator override, and release.  
  status [~]
- **GAP06-REQ-11.10** — The subsystem SHALL satisfy: Create integration tests for scheduler race conditions where placement is attempted concurrently with quarantine.  
  status [ ]
- **GAP06-REQ-11.11** — The subsystem SHALL satisfy: Create recovery tests for supervisor disconnect, scheduler restart, duplicate quarantine events, partial drains, and stale release messages.  
  status [~]
- **GAP06-REQ-11.12** — The subsystem SHALL satisfy: Expose fleet metrics for quarantined nodes, enforcement latency, pending drains, failed cordons, overrides, and mean time to trusted recovery.  
  status [ ]
- **GAP06-REQ-11.13** — The subsystem SHALL satisfy: Define operator runbooks for forensic hold, false-positive review, emergency capacity pressure, and safe reintegration.  
  status [~]
- **GAP06-REQ-11.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-11.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-11.D3** — The subsystem SHALL satisfy: Traceability links `Quarantine and cordon enforcement integration` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-12.01** — The subsystem SHALL satisfy: Define attestation validity period by risk class/platform and compute renewal deadline with a safety margin before hard expiry.  
  status [~]
- **GAP06-REQ-12.02** — The subsystem SHALL satisfy: Use randomized jitter to avoid synchronized fleet-wide re-attestation storms while preserving maximum-expiry guarantees.  
  status [~]
- **GAP06-REQ-12.03** — The subsystem SHALL satisfy: Persist next-due/retry state or reconstruct it deterministically after restart without extending trust lifetime.  
  status [ ]
- **GAP06-REQ-12.04** — The subsystem SHALL satisfy: Define retry schedule with exponential/backoff limits, maximum attempts, transient/permanent error classification, and deadline-aware escalation.  
  status [~]
- **GAP06-REQ-12.05** — The subsystem SHALL satisfy: Prioritize nodes nearing hard expiry over routine refresh work and apply per-site/global concurrency caps.  
  status [ ]
- **GAP06-REQ-12.06** — The subsystem SHALL satisfy: Define disconnected-site mode with cached policy/trust anchors, maximum offline trust age, and explicit transition to quarantine/limited mode after expiry.  
  status [~]
- **GAP06-REQ-12.07** — The subsystem SHALL satisfy: Trigger immediate re-attestation on policy change, trust-anchor change, key rotation, suspicious telemetry, firmware update, migration, or administrative request.  
  status [ ]
- **GAP06-REQ-12.08** — The subsystem SHALL satisfy: Invalidate or shorten dependent workload credentials when node verdict approaches/enters expiry according to policy.  
  status [~]
- **GAP06-REQ-12.09** — The subsystem SHALL satisfy: Prevent stale scheduler jobs from renewing superseded/revoked identities or old node epochs.  
  status [ ]
- **GAP06-REQ-12.10** — The subsystem SHALL satisfy: Create simulated-fleet tests for millions of nodes to validate jitter distribution, queue depth, capacity, and expiry miss rate.  
  status [!]
- **GAP06-REQ-12.11** — The subsystem SHALL satisfy: Create failure tests for verifier outage, storage outage, network partition, time skew, repeated bad evidence, and restart.  
  status [ ]
- **GAP06-REQ-12.12** — The subsystem SHALL satisfy: Expose due/overdue counts, renewal latency, retry depth, hard-expiry events, queue saturation, per-site throughput, and failure reasons.  
  status [ ]
- **GAP06-REQ-12.13** — The subsystem SHALL satisfy: Define an SLO such as maximum percentage of healthy nodes that may reach hard expiry due to control-plane failure and verify it in load tests.  
  status [ ]
- **GAP06-REQ-12.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-12.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-12.D3** — The subsystem SHALL satisfy: Traceability links `Re-attestation scheduler` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-13.01** — The subsystem SHALL satisfy: Define a versioned security-event schema for enrollment, challenge issuance/consume, attestation verdict, policy change, trust-anchor change, revocation, quarantine, override, and administrative access.  
  status [~]
- **GAP06-REQ-13.02** — The subsystem SHALL satisfy: Include stable event ID, sequence/epoch, timestamp/time-quality, actor, target, tenant/site, request correlation ID, policy/evidence digests, outcome, and reason code.  
  status [~]
- **GAP06-REQ-13.03** — The subsystem SHALL satisfy: Chain event records cryptographically (hash chain/Merkle structure or equivalent) and periodically sign checkpoints with an HSM/KMS-protected key.  
  status [~]
- **GAP06-REQ-13.04** — The subsystem SHALL satisfy: Store ledger data in append-only/WORM-capable storage with retention and legal/compliance controls appropriate to the deployment.  
  status [!]
- **GAP06-REQ-13.05** — The subsystem SHALL satisfy: Ensure service operators cannot silently edit or delete past records; separate write, read, export, and administrative privileges.  
  status [~]
- **GAP06-REQ-13.06** — The subsystem SHALL satisfy: Protect sensitive evidence using redaction/tokenization/encryption while retaining enough hashes/metadata for forensic correlation.  
  status [~]
- **GAP06-REQ-13.07** — The subsystem SHALL satisfy: Define ordering semantics across replicas/sites and include replica/site sequence metadata to detect omission/reordering.  
  status [ ]
- **GAP06-REQ-13.08** — The subsystem SHALL satisfy: Implement integrity verification tooling that validates chain continuity, signatures, checkpoint coverage, and record schema.  
  status [~]
- **GAP06-REQ-13.09** — The subsystem SHALL satisfy: Export signed evidence bundles for incident response and certification without requiring direct production-database access.  
  status [ ]
- **GAP06-REQ-13.10** — The subsystem SHALL satisfy: Create tamper tests covering record mutation, deletion, insertion, reordering, checkpoint substitution, and stale-ledger replay.  
  status [~]
- **GAP06-REQ-13.11** — The subsystem SHALL satisfy: Create durability tests for crash during append, storage outage, partial replication, and restore.  
  status [ ]
- **GAP06-REQ-13.12** — The subsystem SHALL satisfy: Expose ledger append failures, signing/checkpoint failures, lag, storage utilization, verification errors, and export failures.  
  status [ ]
- **GAP06-REQ-13.13** — The subsystem SHALL satisfy: Define fail behavior for security operations when the audit ledger cannot accept required events; document which operations must halt versus buffer.  
  status [ ]
- **GAP06-REQ-13.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-13.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-13.D3** — The subsystem SHALL satisfy: Traceability links `Tamper-evident security audit ledger` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-14.01** — The subsystem SHALL satisfy: Inventory every secret/key class: service TLS keys, policy-signing keys, audit-checkpoint keys, database encryption keys, API credentials, trust-anchor administration keys, and recovery keys.  
  status [~]
- **GAP06-REQ-14.02** — The subsystem SHALL satisfy: Assign each key a purpose, owner, algorithm, protection class, rotation period, backup/escrow policy, and authorized workload/principal set.  
  status [~]
- **GAP06-REQ-14.03** — The subsystem SHALL satisfy: Use HSM-backed or managed KMS non-exportable keys for high-value signing operations; prohibit private-key material in source code, images, logs, or ordinary config files.  
  status [!]
- **GAP06-REQ-14.04** — The subsystem SHALL satisfy: Implement workload identity based authentication to KMS/HSM and avoid static long-lived cloud/API credentials.  
  status [!]
- **GAP06-REQ-14.05** — The subsystem SHALL satisfy: Enforce separate keys and IAM policies by environment/tenant/risk domain to limit blast radius.  
  status [~]
- **GAP06-REQ-14.06** — The subsystem SHALL satisfy: Implement key rotation with overlapping validation windows, atomic signer activation, verifier trust update, and rollback procedure.  
  status [~]
- **GAP06-REQ-14.07** — The subsystem SHALL satisfy: Implement key revocation/disable and emergency compromise workflow with propagation to all dependent services and policies.  
  status [~]
- **GAP06-REQ-14.08** — The subsystem SHALL satisfy: Zeroize in-process sensitive buffers where feasible and bound secret lifetime/caching; never write secret material to crash dumps.  
  status [~]
- **GAP06-REQ-14.09** — The subsystem SHALL satisfy: Encrypt persisted sensitive state with envelope encryption and record key version/KEK metadata required for recovery.  
  status [ ]
- **GAP06-REQ-14.10** — The subsystem SHALL satisfy: Create backup/restore tests for keys according to policy without violating non-exportability requirements.  
  status [!]
- **GAP06-REQ-14.11** — The subsystem SHALL satisfy: Create negative IAM tests proving unauthorized services/operators cannot sign, decrypt, rotate, or modify trust anchors.  
  status [~]
- **GAP06-REQ-14.12** — The subsystem SHALL satisfy: Enable KMS/HSM audit logging and correlate key-use events with attestation/policy publication actions.  
  status [!]
- **GAP06-REQ-14.13** — The subsystem SHALL satisfy: Define behavior for KMS/HSM outage, throttling, partial region outage, and key disablement; avoid unsafe local fallback keys.  
  status [ ]
- **GAP06-REQ-14.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-14.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-14.D3** — The subsystem SHALL satisfy: Traceability links `Secrets, KMS, and HSM integration` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-15.01** — The subsystem SHALL satisfy: Define assets, trust boundaries, security objectives, assumptions, external dependencies, privileged actors, and deployment variants.  
  status [~]
- **GAP06-REQ-15.02** — The subsystem SHALL satisfy: Enumerate attacker classes including remote unauthenticated, authenticated malicious node, compromised workload, malicious operator, supply-chain attacker, network MITM, and compromised site control plane.  
  status [~]
- **GAP06-REQ-15.03** — The subsystem SHALL satisfy: Model spoofing/tampering/repudiation/information-disclosure/DoS/elevation threats for each data flow and state transition.  
  status [~]
- **GAP06-REQ-15.04** — The subsystem SHALL satisfy: Explicitly analyze replay, quote substitution, nonce theft, relay/cuckoo attacks, cloned AK/device identity, stale policy, and rollback attacks.  
  status [~]
- **GAP06-REQ-15.05** — The subsystem SHALL satisfy: Analyze malicious/compromised firmware and cases where PCRs measure an approved-but-vulnerable image; distinguish integrity from security posture.  
  status [~]
- **GAP06-REQ-15.06** — The subsystem SHALL satisfy: Analyze parser/certificate/event-log attack surface for memory/CPU exhaustion, malformed inputs, algorithm confusion, and differential interpretation.  
  status [~]
- **GAP06-REQ-15.07** — The subsystem SHALL satisfy: Analyze tenant boundary failure, confused-deputy behavior, privilege escalation, break-glass misuse, and policy-signing compromise.  
  status [~]
- **GAP06-REQ-15.08** — The subsystem SHALL satisfy: Analyze side channels and metadata leakage appropriate to the service and deployed TEE/TPM adapters.  
  status [!]
- **GAP06-REQ-15.09** — The subsystem SHALL satisfy: Map every threat to preventive/detective/recovery controls and to an executable verification artifact where feasible.  
  status [~]
- **GAP06-REQ-15.10** — The subsystem SHALL satisfy: Assign residual-risk severity/likelihood, owner, acceptance authority, and expiration/review date.  
  status [!]
- **GAP06-REQ-15.11** — The subsystem SHALL satisfy: Run adversarial test campaigns/penetration testing against the actual production architecture, not only the reference state machine.  
  status [!]
- **GAP06-REQ-15.12** — The subsystem SHALL satisfy: Add fuzzing/property tests and chaos cases directly derived from the threat model.  
  status [~]
- **GAP06-REQ-15.13** — The subsystem SHALL satisfy: Require threat-model review on protocol/schema/crypto/trust-boundary changes and before major releases.  
  status [~]
- **GAP06-REQ-15.14** — The subsystem SHALL satisfy: Produce a signed security assessment/certification package recording scope, versions tested, findings, remediations, waivers, and evidence.  
  status [!]
- **GAP06-REQ-15.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-15.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-15.D3** — The subsystem SHALL satisfy: Traceability links `Threat model and adversarial certification` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-16.01** — The subsystem SHALL satisfy: Define resource models, primary keys, immutable identifiers, revision numbers, lifecycle states, and authorization scope for enrollment and policy records.  
  status [~]
- **GAP06-REQ-16.02** — The subsystem SHALL satisfy: Expose create/read/update/revoke/publish operations with optimistic concurrency or transactional compare-and-swap guards.  
  status [~]
- **GAP06-REQ-16.03** — The subsystem SHALL satisfy: Require idempotency keys for mutating operations and persist their results for a bounded retry window.  
  status [~]
- **GAP06-REQ-16.04** — The subsystem SHALL satisfy: Validate all updates against schema, security invariants, scope/tenant rules, policy precedence, and signer/approver requirements before commit.  
  status [~]
- **GAP06-REQ-16.05** — The subsystem SHALL satisfy: Use atomic transactions so related records (policy + activation pointer + audit event, identity + key version + revocation state) cannot partially apply.  
  status [~]
- **GAP06-REQ-16.06** — The subsystem SHALL satisfy: Implement pagination/filtering with bounded limits and stable cursors; prevent unbounded scans from administrative APIs.  
  status [ ]
- **GAP06-REQ-16.07** — The subsystem SHALL satisfy: Define retention, tombstone, and deletion restrictions for security/audit-relevant records.  
  status [ ]
- **GAP06-REQ-16.08** — The subsystem SHALL satisfy: Emit change notifications/events only after durable commit and include revision identifiers for downstream idempotency.  
  status [ ]
- **GAP06-REQ-16.09** — The subsystem SHALL satisfy: Create race tests for simultaneous updates, stale revision writes, revoke-vs-rotate, and publish-vs-rollback.  
  status [~]
- **GAP06-REQ-16.10** — The subsystem SHALL satisfy: Create failure tests for database timeout, partial transaction failure, event-publish failure, and client retry.  
  status [ ]
- **GAP06-REQ-16.11** — The subsystem SHALL satisfy: Expose transaction latency, conflict rate, failed validations, idempotent replays, and database dependency health.  
  status [ ]
- **GAP06-REQ-16.12** — The subsystem SHALL satisfy: Provide export/backup tooling and migration procedures that preserve revision history and provenance.  
  status [~]
- **GAP06-REQ-16.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-16.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-16.D3** — The subsystem SHALL satisfy: Traceability links `Persistent enrollment and measurement-policy API with transactional updates` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-17.01** — The subsystem SHALL satisfy: Define limits by principal, node, tenant, site, source network, endpoint, and operation cost rather than a single global request rate.  
  status [~]
- **GAP06-REQ-17.02** — The subsystem SHALL satisfy: Use token-bucket/leaky-bucket/concurrency controls with bounded queues and deterministic rejection behavior.  
  status [~]
- **GAP06-REQ-17.03** — The subsystem SHALL satisfy: Classify operations by cost, including certificate/event-log parsing, cryptographic verification, policy publication, enrollment, and decision explanation.  
  status [ ]
- **GAP06-REQ-17.04** — The subsystem SHALL satisfy: Reserve capacity for re-attestation nearing hard expiry, revocation/quarantine actions, and control-plane recovery.  
  status [ ]
- **GAP06-REQ-17.05** — The subsystem SHALL satisfy: Prevent one tenant/site from exhausting global verifier CPU, memory, storage, HSM throughput, or database transactions.  
  status [~]
- **GAP06-REQ-17.06** — The subsystem SHALL satisfy: Apply payload-size and evidence-complexity limits before expensive parsing/crypto work where safe.  
  status [~]
- **GAP06-REQ-17.07** — The subsystem SHALL satisfy: Define retry-after/backoff responses and avoid client retry synchronization storms.  
  status [~]
- **GAP06-REQ-17.08** — The subsystem SHALL satisfy: Rate-limit authentication failures and malformed evidence while preserving forensic visibility.  
  status [ ]
- **GAP06-REQ-17.09** — The subsystem SHALL satisfy: Load-test normal, burst, abusive, and adversarial traffic to establish safe thresholds with headroom.  
  status [~]
- **GAP06-REQ-17.10** — The subsystem SHALL satisfy: Create fairness tests demonstrating sustained heavy load from one principal does not starve others.  
  status [~]
- **GAP06-REQ-17.11** — The subsystem SHALL satisfy: Expose accepted/rejected/queued requests, limiter saturation, per-class latency, cost-unit usage, and top offenders without high-cardinality explosions.  
  status [ ]
- **GAP06-REQ-17.12** — The subsystem SHALL satisfy: Document emergency tuning and safe dynamic configuration with bounds/approval/audit.  
  status [~]
- **GAP06-REQ-17.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-17.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-17.D3** — The subsystem SHALL satisfy: Traceability links `Rate limiting, quotas, fairness, and per-principal admission control` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-18.01** — The subsystem SHALL satisfy: Define replay record key, scope, issue/consume timestamps, expiry, identity epoch, and maximum evidence lifetime that determines safe retention.  
  status [~]
- **GAP06-REQ-18.02** — The subsystem SHALL satisfy: Derive minimum retention from maximum challenge TTL, offline/retry windows, backup/restore age, clock uncertainty, and incident-forensics requirements.  
  status [~]
- **GAP06-REQ-18.03** — The subsystem SHALL satisfy: Use partitioning/TTL compaction only when deletion cannot reopen a valid replay window.  
  status [~]
- **GAP06-REQ-18.04** — The subsystem SHALL satisfy: Persist replay state across restart and include it in backup/restore/failover design.  
  status [~]
- **GAP06-REQ-18.05** — The subsystem SHALL satisfy: Prevent generation rollback after restore by using monotonic epochs/fencing markers that invalidate stale challenges.  
  status [~]
- **GAP06-REQ-18.06** — The subsystem SHALL satisfy: Bound outstanding unused challenges separately from spent-challenge history and garbage-collect them after safe expiry.  
  status [~]
- **GAP06-REQ-18.07** — The subsystem SHALL satisfy: Protect cache operations with atomic uniqueness/consume constraints at the authoritative store.  
  status [~]
- **GAP06-REQ-18.08** — The subsystem SHALL satisfy: Capacity-model worst-case adversarial issuance/consume rates and storage amplification.  
  status [ ]
- **GAP06-REQ-18.09** — The subsystem SHALL satisfy: Create long-duration soak tests proving storage remains bounded under expected and attack traffic.  
  status [~]
- **GAP06-REQ-18.10** — The subsystem SHALL satisfy: Create replay tests across compaction boundaries, restart, restore from backup, site failover, and clock anomalies.  
  status [~]
- **GAP06-REQ-18.11** — The subsystem SHALL satisfy: Expose replay-state size, insertion/lookup latency, compaction lag, TTL deletions, duplicate hits, and storage pressure.  
  status [ ]
- **GAP06-REQ-18.12** — The subsystem SHALL satisfy: Document emergency storage-pressure handling that never clears replay state indiscriminately.  
  status [~]
- **GAP06-REQ-18.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-18.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-18.D3** — The subsystem SHALL satisfy: Traceability links `Bounded replay-cache lifecycle design` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-19.01** — The subsystem SHALL satisfy: Define an error envelope with stable code, category, retryability, safe message, correlation ID, optional field violations, and server version.  
  status [~]
- **GAP06-REQ-19.02** — The subsystem SHALL satisfy: Separate authentication/authorization, malformed request, unsupported capability, freshness failure, attestation failure, policy failure, dependency failure, conflict, throttling, and internal error namespaces.  
  status [~]
- **GAP06-REQ-19.03** — The subsystem SHALL satisfy: Ensure external messages do not reveal trust-store internals, private certificate material, secret policy details, stack traces, filesystem paths, or database structure.  
  status [~]
- **GAP06-REQ-19.04** — The subsystem SHALL satisfy: Define mapping to transport status codes without making clients depend solely on HTTP/gRPC codes.  
  status [~]
- **GAP06-REQ-19.05** — The subsystem SHALL satisfy: Version error codes additively and never silently reuse a code for a different semantic condition.  
  status [~]
- **GAP06-REQ-19.06** — The subsystem SHALL satisfy: Include retry-after/deadline hints only when retry is safe and meaningful.  
  status [~]
- **GAP06-REQ-19.07** — The subsystem SHALL satisfy: Provide operator-only diagnostics in protected logs/traces correlated by ID, separate from client-facing details.  
  status [ ]
- **GAP06-REQ-19.08** — The subsystem SHALL satisfy: Create conformance tests for every documented error path and check safe redaction.  
  status [~]
- **GAP06-REQ-19.09** — The subsystem SHALL satisfy: Add fuzz/negative tests to ensure unexpected parser exceptions map to bounded generic errors rather than process crashes or data leakage.  
  status [~]
- **GAP06-REQ-19.10** — The subsystem SHALL satisfy: Publish an error catalog with remediation guidance and client retry behavior.  
  status [~]
- **GAP06-REQ-19.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-19.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-19.D3** — The subsystem SHALL satisfy: Traceability links `Structured machine-readable errors` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-20.01** — The subsystem SHALL satisfy: Classify every API operation as read-only, idempotent, conditionally idempotent, or non-idempotent and document retry rules.  
  status [ ]
- **GAP06-REQ-20.02** — The subsystem SHALL satisfy: Require client-generated idempotency keys for enrollment, revocation, policy publication, and other mutating operations that may be retried.  
  status [~]
- **GAP06-REQ-20.03** — The subsystem SHALL satisfy: Persist idempotency outcome keyed by principal/scope/operation and reject key reuse with different request digests.  
  status [~]
- **GAP06-REQ-20.04** — The subsystem SHALL satisfy: Define server deadlines and propagate remaining deadline to downstream dependencies.  
  status [ ]
- **GAP06-REQ-20.05** — The subsystem SHALL satisfy: Implement exponential backoff with jitter and upper bounds; avoid automatic retries on permanent validation/security failures.  
  status [~]
- **GAP06-REQ-20.06** — The subsystem SHALL satisfy: Apply bounded queues/concurrency limits and return explicit overload signals before resource exhaustion.  
  status [~]
- **GAP06-REQ-20.07** — The subsystem SHALL satisfy: Prevent duplicate challenge issuance/consumption and duplicate policy activation under client/network retries.  
  status [~]
- **GAP06-REQ-20.08** — The subsystem SHALL satisfy: Handle ambiguous commit outcomes by allowing safe status lookup/reconciliation via transaction ID.  
  status [ ]
- **GAP06-REQ-20.09** — The subsystem SHALL satisfy: Create fault-injection tests for response loss after commit, connection reset mid-request, duplicate delivery, delayed response, and downstream timeout.  
  status [ ]
- **GAP06-REQ-20.10** — The subsystem SHALL satisfy: Expose retry counts, idempotency hits/conflicts, queue depth, shed load, deadline exceeded, and ambiguous-outcome reconciliations.  
  status [ ]
- **GAP06-REQ-20.11** — The subsystem SHALL satisfy: Document client SDK retry defaults and prohibit hidden infinite retries.  
  status [ ]
- **GAP06-REQ-20.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-20.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-20.D3** — The subsystem SHALL satisfy: Traceability links `Retry, idempotency, and backpressure contract` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-21.01** — The subsystem SHALL satisfy: Define authoritative tenant/site/environment identifiers and prohibit caller-controlled free-form trust domains.  
  status [~]
- **GAP06-REQ-21.02** — The subsystem SHALL satisfy: Bind authenticated principal identities to allowed tenant/site/environment scopes through authorization policy.  
  status [~]
- **GAP06-REQ-21.03** — The subsystem SHALL satisfy: Partition or strongly namespace enrollment records, policies, replay state, verdicts, caches, metrics, and audit views by scope.  
  status [ ]
- **GAP06-REQ-21.04** — The subsystem SHALL satisfy: Ensure challenge issuance and evidence verification require exact scope binding and reject cross-scope reuse.  
  status [~]
- **GAP06-REQ-21.05** — The subsystem SHALL satisfy: Use separate trust anchors/signing keys/configuration where risk policy requires stronger cryptographic isolation.  
  status [ ]
- **GAP06-REQ-21.06** — The subsystem SHALL satisfy: Prevent cross-tenant policy references, node-ID collisions, data export, and decision-explain access.  
  status [~]
- **GAP06-REQ-21.07** — The subsystem SHALL satisfy: Define global-admin actions explicitly and require stronger authentication/approval/audit.  
  status [ ]
- **GAP06-REQ-21.08** — The subsystem SHALL satisfy: Add tests for horizontal privilege escalation using valid credentials from another tenant/site/environment.  
  status [~]
- **GAP06-REQ-21.09** — The subsystem SHALL satisfy: Add data-layer tests for missing scope predicates and cache-key collisions.  
  status [ ]
- **GAP06-REQ-21.10** — The subsystem SHALL satisfy: Create backup/restore/export procedures that preserve isolation and access controls.  
  status [ ]
- **GAP06-REQ-21.11** — The subsystem SHALL satisfy: Expose isolation-policy violations as security metrics/events without leaking other tenant identifiers.  
  status [ ]
- **GAP06-REQ-21.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-21.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-21.D3** — The subsystem SHALL satisfy: Traceability links `Environment, site, and tenant isolation enforcement` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-22.01** — The subsystem SHALL satisfy: Define which verifier functions may run locally/offline and which require central authority.  
  status [~]
- **GAP06-REQ-22.02** — The subsystem SHALL satisfy: Provision signed cached trust anchors, measurement policies, revocation snapshots, schema versions, and local verifier keys before disconnection.  
  status [ ]
- **GAP06-REQ-22.03** — The subsystem SHALL satisfy: Define maximum offline age separately for policy, revocation data, certificate status, node verdicts, and workload credentials.  
  status [~]
- **GAP06-REQ-22.04** — The subsystem SHALL satisfy: Use local secure/monotonic time and detect rollback across reboot where platform capabilities allow.  
  status [ ]
- **GAP06-REQ-22.05** — The subsystem SHALL satisfy: Issue offline verdicts with explicit degraded/offline provenance and shorter validity when central freshness cannot be established.  
  status [~]
- **GAP06-REQ-22.06** — The subsystem SHALL satisfy: Prevent disconnected sites from enrolling new trust roots or performing unrestricted recovery unless a separately governed offline process exists.  
  status [ ]
- **GAP06-REQ-22.07** — The subsystem SHALL satisfy: Queue signed local audit events and reconcile them centrally with duplicate/conflict detection after reconnect.  
  status [ ]
- **GAP06-REQ-22.08** — The subsystem SHALL satisfy: Define conflict resolution when central policy/revocation changed during outage; central revocation must take precedence.  
  status [~]
- **GAP06-REQ-22.09** — The subsystem SHALL satisfy: Force re-attestation/reconciliation after reconnect before extending long-lived trust.  
  status [ ]
- **GAP06-REQ-22.10** — The subsystem SHALL satisfy: Create tests for outages longer than each configured offline limit and verify deterministic transition to limited/fail-closed mode.  
  status [~]
- **GAP06-REQ-22.11** — The subsystem SHALL satisfy: Create partition/reconnect tests with conflicting policy versions, revoked identities, and clock drift.  
  status [ ]
- **GAP06-REQ-22.12** — The subsystem SHALL satisfy: Expose offline duration, cached-policy age, revocation-snapshot age, local queue depth, and trust-expiry risk.  
  status [ ]
- **GAP06-REQ-22.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-22.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-22.D3** — The subsystem SHALL satisfy: Traceability links `Disconnected and offline attestation mode` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-23.01** — The subsystem SHALL satisfy: Define separate liveness (process can run), readiness (safe to serve trust decisions), and detailed dependency health models.  
  status [~]
- **GAP06-REQ-23.02** — The subsystem SHALL satisfy: Mark service unready when authoritative state, required trust stores, KMS/HSM, or secure time makes decisions unsafe, even if the process is alive.  
  status [~]
- **GAP06-REQ-23.03** — The subsystem SHALL satisfy: Define degraded modes explicitly for noncritical dependencies such as analytics exporters and distinguish them from trust-critical failures.  
  status [~]
- **GAP06-REQ-23.04** — The subsystem SHALL satisfy: Include version/build ID, schema compatibility, active policy generation, trust-anchor generation, and replica role in protected diagnostics.  
  status [ ]
- **GAP06-REQ-23.05** — The subsystem SHALL satisfy: Avoid exposing secrets, certificate bodies, node identifiers, internal topology, or dependency credentials on unauthenticated health endpoints.  
  status [~]
- **GAP06-REQ-23.06** — The subsystem SHALL satisfy: Use bounded dependency probes with short deadlines and avoid cascading overload caused by health checks.  
  status [ ]
- **GAP06-REQ-23.07** — The subsystem SHALL satisfy: Add startup readiness gates so the service does not accept traffic before migrations, trust stores, policy, replay state, and time checks complete.  
  status [ ]
- **GAP06-REQ-23.08** — The subsystem SHALL satisfy: Add shutdown/drain readiness behavior that removes the instance before terminating in-flight work.  
  status [ ]
- **GAP06-REQ-23.09** — The subsystem SHALL satisfy: Create tests for every dependency failure and verify the correct liveness/readiness/degraded classification.  
  status [~]
- **GAP06-REQ-23.10** — The subsystem SHALL satisfy: Integrate readiness with orchestration/load balancing and validate failover behavior.  
  status [!]
- **GAP06-REQ-23.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-23.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-23.D3** — The subsystem SHALL satisfy: Traceability links `Health, readiness, and dependency endpoints` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-24.01** — The subsystem SHALL satisfy: Define RED/USE metrics for API latency/rate/errors, crypto verifier latency, queue utilization, replay state, persistence, KMS/HSM, time sync, policy generation, and scheduler renewal.  
  status [~]
- **GAP06-REQ-24.02** — The subsystem SHALL satisfy: Define security counters for replay rejection, invalid signatures, certificate failures, PCR mismatches, revocations, quarantine actions, authz denials, and policy rollback attempts.  
  status [~]
- **GAP06-REQ-24.03** — The subsystem SHALL satisfy: Use structured logs with event name, severity, correlation/trace ID, component version, site/tenant-safe identifiers, reason code, and sanitized context.  
  status [~]
- **GAP06-REQ-24.04** — The subsystem SHALL satisfy: Adopt distributed tracing across ingress, verifier, policy store, replay store, KMS/HSM, scheduler, and quarantine integrations.  
  status [~]
- **GAP06-REQ-24.05** — The subsystem SHALL satisfy: Propagate trace context only through trusted headers/metadata and sanitize untrusted client-provided trace identifiers.  
  status [ ]
- **GAP06-REQ-24.06** — The subsystem SHALL satisfy: Define redaction rules for raw evidence, public-key material where sensitive, certificate serials, node identifiers, secrets, and personal data.  
  status [~]
- **GAP06-REQ-24.07** — The subsystem SHALL satisfy: Control metric label cardinality; never place unbounded node IDs/challenge IDs into metric labels.  
  status [~]
- **GAP06-REQ-24.08** — The subsystem SHALL satisfy: Define telemetry retention, access control, encryption, export destinations, and incident preservation procedures.  
  status [ ]
- **GAP06-REQ-24.09** — The subsystem SHALL satisfy: Create dashboards for availability, latency, fleet trust posture, policy rollout, replay anomalies, expiry risk, storage, and dependency health.  
  status [!]
- **GAP06-REQ-24.10** — The subsystem SHALL satisfy: Define actionable alerts with severity, thresholds, burn-rate logic, runbook links, and anti-flap behavior.  
  status [~]
- **GAP06-REQ-24.11** — The subsystem SHALL satisfy: Create telemetry tests asserting required events/metrics on success and key failure paths and verifying secret redaction.  
  status [~]
- **GAP06-REQ-24.12** — The subsystem SHALL satisfy: Capacity-test observability pipelines so telemetry cannot backpressure or crash the trust service.  
  status [ ]
- **GAP06-REQ-24.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-24.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-24.D3** — The subsystem SHALL satisfy: Traceability links `Metrics, logging, and tracing implementation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-25.01** — The subsystem SHALL satisfy: Define a stable verdict ID and store the immutable decision context needed for later explanation.  
  status [~]
- **GAP06-REQ-25.02** — The subsystem SHALL satisfy: Include decision result, reason code tree, evidence digest, quote/report digest, measurement-policy ID/version/digest, trust-anchor generation, identity version, verifier version, issuance, and expiry.  
  status [~]
- **GAP06-REQ-25.03** — The subsystem SHALL satisfy: Provide claim-level explanation for which measurement/PCR/runtime rule passed or failed without exposing secrets or unrelated tenant data.  
  status [ ]
- **GAP06-REQ-25.04** — The subsystem SHALL satisfy: Protect the API with authorization distinct from ordinary attestation submission; restrict forensic detail to approved operator/auditor roles.  
  status [~]
- **GAP06-REQ-25.05** — The subsystem SHALL satisfy: Support deterministic reconstruction so the same stored inputs/policy/verifier version can reproduce the decision or clearly report nondeterministic external dependencies.  
  status [ ]
- **GAP06-REQ-25.06** — The subsystem SHALL satisfy: Link certificate/revocation evidence, policy publication event, challenge issuance/consume record, and quarantine action via correlation IDs.  
  status [ ]
- **GAP06-REQ-25.07** — The subsystem SHALL satisfy: Define retention aligned with incident, compliance, and audit requirements.  
  status [ ]
- **GAP06-REQ-25.08** — The subsystem SHALL satisfy: Provide machine-readable output suitable for SIEM/certification tooling and a human-readable operator rendering.  
  status [~]
- **GAP06-REQ-25.09** — The subsystem SHALL satisfy: Create tests for redaction, cross-tenant access, missing/expired evidence, old verifier versions, and policy rollback history.  
  status [ ]
- **GAP06-REQ-25.10** — The subsystem SHALL satisfy: Ensure explanation generation cannot mutate verdict state or trigger re-evaluation silently.  
  status [~]
- **GAP06-REQ-25.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-25.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-25.D3** — The subsystem SHALL satisfy: Traceability links `Decision explain API` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-26.01** — The subsystem SHALL satisfy: Estimate node/workload counts, attestation frequency, policy versions, audit-event rate, replay-state rate, retention, and worst-case burst factors.  
  status [~]
- **GAP06-REQ-26.02** — The subsystem SHALL satisfy: Define partition/shard keys that distribute load while preserving atomicity requirements for identity/challenge/policy operations.  
  status [~]
- **GAP06-REQ-26.03** — The subsystem SHALL satisfy: Avoid hotspots from global counters, active-policy pointers, tenant supernodes, or time-based keys.  
  status [ ]
- **GAP06-REQ-26.04** — The subsystem SHALL satisfy: Define cross-shard transaction requirements and redesign operations to minimize them where safe.  
  status [ ]
- **GAP06-REQ-26.05** — The subsystem SHALL satisfy: Plan index strategy and bounded query patterns for enrollment lookup, revocation lookup, challenge consume, verdict explanation, and audits.  
  status [ ]
- **GAP06-REQ-26.06** — The subsystem SHALL satisfy: Define replication factor, consistency level, failover, rebalancing, backup, and restore per data class.  
  status [!]
- **GAP06-REQ-26.07** — The subsystem SHALL satisfy: Capacity-model storage growth including indexes, audit ledger, event logs/evidence retention, tombstones, and replication overhead.  
  status [~]
- **GAP06-REQ-26.08** — The subsystem SHALL satisfy: Define high-water marks and load-shedding behavior before disk, IOPS, connection, or transaction limits are exhausted.  
  status [ ]
- **GAP06-REQ-26.09** — The subsystem SHALL satisfy: Benchmark representative read/write mixes at target and 2× burst load with realistic record sizes.  
  status [!]
- **GAP06-REQ-26.10** — The subsystem SHALL satisfy: Test online shard split/rebalance/failover while attestation traffic continues.  
  status [!]
- **GAP06-REQ-26.11** — The subsystem SHALL satisfy: Expose per-shard latency, size, hot-key indicators, replication lag, connection saturation, compaction, and error rates.  
  status [ ]
- **GAP06-REQ-26.12** — The subsystem SHALL satisfy: Document scaling playbook and maximum supported fleet envelope per release.  
  status [ ]
- **GAP06-REQ-26.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-26.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-26.D3** — The subsystem SHALL satisfy: Traceability links `Fleet-scale persistence and sharding model` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-27.01** — The subsystem SHALL satisfy: Define failure domains and RTO/RPO for verifier compute, state stores, audit ledger, KMS/HSM, policy distribution, time services, and site control planes.  
  status [!]
- **GAP06-REQ-27.02** — The subsystem SHALL satisfy: Implement automated instance/replica failover with fencing so stale instances cannot continue accepting security writes.  
  status [~]
- **GAP06-REQ-27.03** — The subsystem SHALL satisfy: Replicate critical state according to defined consistency and durability requirements; distinguish synchronous from asynchronous data classes.  
  status [!]
- **GAP06-REQ-27.04** — The subsystem SHALL satisfy: Create signed, encrypted backups with independent retention and access controls; regularly verify restoreability.  
  status [~]
- **GAP06-REQ-27.05** — The subsystem SHALL satisfy: Protect against backup rollback reopening replay/revocation windows using epochs/generations and post-restore reconciliation.  
  status [~]
- **GAP06-REQ-27.06** — The subsystem SHALL satisfy: Define region/site failover traffic routing and trust-anchor/policy synchronization prerequisites.  
  status [!]
- **GAP06-REQ-27.07** — The subsystem SHALL satisfy: Define behavior when KMS/HSM is region-scoped and ensure failover has authorized key access without copying private keys unsafely.  
  status [!]
- **GAP06-REQ-27.08** — The subsystem SHALL satisfy: Create DR tests for total database loss, corrupted snapshot, site loss, region loss, split brain, and prolonged WAN partition.  
  status [~]
- **GAP06-REQ-27.09** — The subsystem SHALL satisfy: Validate that revocations/quarantines and consumed challenges remain effective after restore/failover.  
  status [~]
- **GAP06-REQ-27.10** — The subsystem SHALL satisfy: Run scheduled game days and capture objective RTO/RPO measurements and remediation actions.  
  status [!]
- **GAP06-REQ-27.11** — The subsystem SHALL satisfy: Expose DR replication lag, backup age, restore-test status, fencing events, and failover state.  
  status [ ]
- **GAP06-REQ-27.12** — The subsystem SHALL satisfy: Maintain step-by-step recovery and failback runbooks with command validation and rollback points.  
  status [~]
- **GAP06-REQ-27.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-27.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-27.D3** — The subsystem SHALL satisfy: Traceability links `Failover and disaster recovery implementation` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-28.01** — The subsystem SHALL satisfy: List supported TPM versions/vendors/firmware lines, TEE technologies, vTPM implementations, hypervisors, CPU architectures, OS families, boot modes, and attestation protocols.  
  status [~]
- **GAP06-REQ-28.02** — The subsystem SHALL satisfy: Define minimum firmware/microcode/OS/runtime versions and explicitly unsupported/deprecated combinations.  
  status [~]
- **GAP06-REQ-28.03** — The subsystem SHALL satisfy: Map supported PCR banks/algorithms/event-log formats and platform-specific evidence fields.  
  status [~]
- **GAP06-REQ-28.04** — The subsystem SHALL satisfy: Define server/client/schema version compatibility ranges and downgrade behavior.  
  status [~]
- **GAP06-REQ-28.05** — The subsystem SHALL satisfy: Include edge/disconnected-site tiers and resource-constrained variants with their reduced capabilities.  
  status [ ]
- **GAP06-REQ-28.06** — The subsystem SHALL satisfy: Build CI/hardware-lab jobs covering representative matrix cells and prioritize high-risk/vendor-specific paths.  
  status [!]
- **GAP06-REQ-28.07** — The subsystem SHALL satisfy: Use golden evidence fixtures for matrix cells that cannot run in every CI cycle and periodically refresh them from real hardware.  
  status [!]
- **GAP06-REQ-28.08** — The subsystem SHALL satisfy: Create regression tests for known vendor quirks without silently widening validation rules.  
  status [ ]
- **GAP06-REQ-28.09** — The subsystem SHALL satisfy: Version and publish the compatibility matrix with each release and link it to test evidence.  
  status [~]
- **GAP06-REQ-28.10** — The subsystem SHALL satisfy: Define deprecation notice period, migration guidance, and hard removal gates for old algorithms/platforms.  
  status [~]
- **GAP06-REQ-28.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-28.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-28.D3** — The subsystem SHALL satisfy: Traceability links `Compatibility matrix` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-29.01** — The subsystem SHALL satisfy: Define an explicit contract for each dependency, including API/schema version, authentication, authorization, retries, idempotency, and failure semantics.  
  status [~]
- **GAP06-REQ-29.02** — The subsystem SHALL satisfy: Integrate GAP-01 node supervisor for identity lifecycle, health state, and quarantine/cordon enforcement.  
  status [~]
- **GAP06-REQ-29.03** — The subsystem SHALL satisfy: Integrate GAP-02 hardware capability discovery to correlate attested hardware claims with discovered platform capabilities without trusting discovery alone.  
  status [!]
- **GAP06-REQ-29.04** — The subsystem SHALL satisfy: Integrate GAP-07 artifact provenance/signing so workload/boot artifact digests can be validated against authorized provenance.  
  status [!]
- **GAP06-REQ-29.05** — The subsystem SHALL satisfy: Integrate PLN-07/SCH-01 planning/scheduling so trust verdicts are mandatory placement inputs and stale/expired verdicts cannot be used.  
  status [~]
- **GAP06-REQ-29.06** — The subsystem SHALL satisfy: Define correlation IDs and stable node/workload identifiers across all systems to avoid identity ambiguity.  
  status [ ]
- **GAP06-REQ-29.07** — The subsystem SHALL satisfy: Add circuit-breaker/degraded behavior for each dependency and document which failures require fail-closed placement.  
  status [ ]
- **GAP06-REQ-29.08** — The subsystem SHALL satisfy: Create contract tests using versioned fixtures for each adapter and prevent deployment with incompatible peer versions.  
  status [~]
- **GAP06-REQ-29.09** — The subsystem SHALL satisfy: Create end-to-end tests: enroll → attest → schedule → policy change → re-attest → quarantine → recover.  
  status [~]
- **GAP06-REQ-29.10** — The subsystem SHALL satisfy: Create race/failure tests for concurrent scheduling and trust revocation, stale cache, delayed events, duplicate events, and partial dependency outage.  
  status [ ]
- **GAP06-REQ-29.11** — The subsystem SHALL satisfy: Expose adapter latency/errors/version mismatch and reconciliation backlog metrics.  
  status [ ]
- **GAP06-REQ-29.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-29.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-29.D3** — The subsystem SHALL satisfy: Traceability links `Integration adapters and tests for GAP-01/GAP-02/GAP-07/PLN-07/SCH-01` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-30.01** — The subsystem SHALL satisfy: Classify every setting as build-time immutable, startup immutable, dynamic safe, security-sensitive dynamic, or secret.  
  status [~]
- **GAP06-REQ-30.02** — The subsystem SHALL satisfy: Define a typed schema with defaults, ranges, enums, cross-field constraints, and unknown-key rejection.  
  status [~]
- **GAP06-REQ-30.03** — The subsystem SHALL satisfy: Assign each setting an owner, rationale, environment scope, security impact, restart requirement, and change mechanism.  
  status [ ]
- **GAP06-REQ-30.04** — The subsystem SHALL satisfy: Keep secrets out of ordinary configuration and reference them through KMS/secret-manager handles.  
  status [~]
- **GAP06-REQ-30.05** — The subsystem SHALL satisfy: Cryptographically sign or integrity-protect security-sensitive configuration bundles and validate signer/scope/version before activation.  
  status [~]
- **GAP06-REQ-30.06** — The subsystem SHALL satisfy: Use monotonic configuration revisions and atomic activation; never combine partial files from different generations.  
  status [ ]
- **GAP06-REQ-30.07** — The subsystem SHALL satisfy: Implement staged rollout/canary and automated rollback for dynamic configuration changes.  
  status [ ]
- **GAP06-REQ-30.08** — The subsystem SHALL satisfy: Record provenance: source commit/artifact, author/automation identity, approver, timestamp, digest, and deployment scope.  
  status [ ]
- **GAP06-REQ-30.09** — The subsystem SHALL satisfy: Validate startup configuration before serving traffic and fail with actionable errors on unsafe values.  
  status [~]
- **GAP06-REQ-30.10** — The subsystem SHALL satisfy: Create tests for missing/unknown keys, boundary values, conflicting settings, stale revision, unauthorized signer, and rollback.  
  status [~]
- **GAP06-REQ-30.11** — The subsystem SHALL satisfy: Expose active configuration generation/digest and drift detection without exposing secret values.  
  status [~]
- **GAP06-REQ-30.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-30.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-30.D3** — The subsystem SHALL satisfy: Traceability links `Production configuration model` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-31.01** — The subsystem SHALL satisfy: Define an algorithm registry with unambiguous identifiers for hashes, signature schemes, key types, curves, certificate signatures, and evidence formats.  
  status [~]
- **GAP06-REQ-31.02** — The subsystem SHALL satisfy: Define approved/preferred/deprecated/prohibited states by environment/compliance profile and effective dates.  
  status [~]
- **GAP06-REQ-31.03** — The subsystem SHALL satisfy: Negotiate or select algorithms by policy rather than client preference; reject downgrade to weaker-but-supported options.  
  status [~]
- **GAP06-REQ-31.04** — The subsystem SHALL satisfy: Bind algorithm identifiers into signed/hashed structures to prevent algorithm-substitution attacks.  
  status [~]
- **GAP06-REQ-31.05** — The subsystem SHALL satisfy: Support multiple PCR banks/signature schemes during controlled migration and define precedence/dual-validation rules.  
  status [~]
- **GAP06-REQ-31.06** — The subsystem SHALL satisfy: Define minimum key sizes/curves and strict encoding rules for each supported algorithm.  
  status [~]
- **GAP06-REQ-31.07** — The subsystem SHALL satisfy: Add organization/FIPS policy hooks where required without assuming FIPS mode equals complete security.  
  status [~]
- **GAP06-REQ-31.08** — The subsystem SHALL satisfy: Create migration tooling to inventory fleet algorithm use and identify blockers before deprecation deadlines.  
  status [ ]
- **GAP06-REQ-31.09** — The subsystem SHALL satisfy: Create negative tests for unknown algorithm IDs, mismatched identifiers, weak keys, downgrade attempts, and signature-format ambiguity.  
  status [~]
- **GAP06-REQ-31.10** — The subsystem SHALL satisfy: Publish cryptographic-policy changes with release notes, compatibility impact, and rollback strategy.  
  status [ ]
- **GAP06-REQ-31.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-31.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-31.D3** — The subsystem SHALL satisfy: Traceability links `Algorithm agility` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-32.01** — The subsystem SHALL satisfy: Define supported PCR banks and exact PCR roles per boot mode/platform, avoiding a universal hard-coded PCR set.  
  status [~]
- **GAP06-REQ-32.02** — The subsystem SHALL satisfy: Implement event-log parser for required TCG formats with strict bounds checking, event-type handling, digest-algorithm validation, and unknown-event policy.  
  status [~]
- **GAP06-REQ-32.03** — The subsystem SHALL satisfy: Replay event log into software PCR state and compare against quoted PCR digest/values.  
  status [~]
- **GAP06-REQ-32.04** — The subsystem SHALL satisfy: Normalize measurements into typed semantic components such as firmware, bootloader, Secure Boot variables, kernel, initrd, command line, drivers, IMA, container image, and workload.  
  status [ ]
- **GAP06-REQ-32.05** — The subsystem SHALL satisfy: Define policy rules over component digests/version/signers rather than only opaque aggregate PCR values where explainability is required.  
  status [ ]
- **GAP06-REQ-32.06** — The subsystem SHALL satisfy: Validate Secure Boot state, key databases, revocation databases, and relevant measured-boot variables where platform supports them.  
  status [ ]
- **GAP06-REQ-32.07** — The subsystem SHALL satisfy: Parse IMA templates safely and define approved measurement/appraisal policies and handling of mutable files.  
  status [~]
- **GAP06-REQ-32.08** — The subsystem SHALL satisfy: Bind container/workload image measurements to signed artifact provenance and immutable digests.  
  status [ ]
- **GAP06-REQ-32.09** — The subsystem SHALL satisfy: Define composite-policy semantics for optional components, version ranges, signer allow-lists, deny-lists, and emergency revocations.  
  status [ ]
- **GAP06-REQ-32.10** — The subsystem SHALL satisfy: Create a corpus of real event logs across supported vendors/OS versions plus malformed/adversarial fixtures.  
  status [!]
- **GAP06-REQ-32.11** — The subsystem SHALL satisfy: Fuzz parsers and enforce CPU/memory/depth limits to prevent crafted-log denial of service.  
  status [~]
- **GAP06-REQ-32.12** — The subsystem SHALL satisfy: Provide explanation output showing which semantic component caused a policy mismatch.  
  status [~]
- **GAP06-REQ-32.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-32.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-32.D3** — The subsystem SHALL satisfy: Traceability links `Measurement semantics and event-log parser` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-33.01** — The subsystem SHALL satisfy: Bind enrolled AK/EK identities to a unique node record, expected platform attributes, site, and lifecycle epoch.  
  status [~]
- **GAP06-REQ-33.02** — The subsystem SHALL satisfy: Use verifier challenge binding that includes node/service/session context and cannot be transparently replayed across sessions.  
  status [~]
- **GAP06-REQ-33.03** — The subsystem SHALL satisfy: Where supported, bind attestation to the authenticated transport/channel or workload key using report-data/channel-binding fields.  
  status [~]
- **GAP06-REQ-33.04** — The subsystem SHALL satisfy: Detect simultaneous active attestations or sessions using the same hardware identity from mutually exclusive locations/nodes.  
  status [~]
- **GAP06-REQ-33.05** — The subsystem SHALL satisfy: Incorporate TPM locality/credential activation/platform certificates where useful to strengthen proof that the attester is the enrolled device.  
  status [!]
- **GAP06-REQ-33.06** — The subsystem SHALL satisfy: Define network/time plausibility heuristics only as supplementary signals, not sole cryptographic proof.  
  status [ ]
- **GAP06-REQ-33.07** — The subsystem SHALL satisfy: Flag identity moves/replacements that exceed allowed topology/location policy and require re-enrollment where appropriate.  
  status [ ]
- **GAP06-REQ-33.08** — The subsystem SHALL satisfy: Correlate hardware capability discovery and attested platform attributes to detect impossible/abrupt identity changes.  
  status [!]
- **GAP06-REQ-33.09** — The subsystem SHALL satisfy: Create lab relay/cuckoo tests with a proxy forwarding quote challenges to another machine and verify detection/prevention mechanisms.  
  status [!]
- **GAP06-REQ-33.10** — The subsystem SHALL satisfy: Create clone tests using copied VM/vTPM state and define expected behavior after snapshot/restore/migration.  
  status [!]
- **GAP06-REQ-33.11** — The subsystem SHALL satisfy: Emit high-severity audit/security events for duplicate-active identity and relay indicators with protected forensic context.  
  status [ ]
- **GAP06-REQ-33.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-33.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-33.D3** — The subsystem SHALL satisfy: Traceability links `Identity cloning and relay detection` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-34.01** — The subsystem SHALL satisfy: Define policy domains and an explicit precedence model; security/trust constraints must not be silently weakened by cost/SLO preferences.  
  status [~]
- **GAP06-REQ-34.02** — The subsystem SHALL satisfy: Represent rules in a typed intermediate model with scope, priority, mandatory/preferential semantics, version, owner, and provenance.  
  status [~]
- **GAP06-REQ-34.03** — The subsystem SHALL satisfy: Detect contradictory mandatory constraints before activation and reject unsatisfiable policy sets.  
  status [ ]
- **GAP06-REQ-34.04** — The subsystem SHALL satisfy: Define deterministic tie-breaking independent of input ordering or hash-map iteration.  
  status [~]
- **GAP06-REQ-34.05** — The subsystem SHALL satisfy: Expose an explain function showing which rules applied, which were overridden, and why.  
  status [~]
- **GAP06-REQ-34.06** — The subsystem SHALL satisfy: Prevent lower-authority scopes from overriding higher-authority security baselines unless delegation explicitly permits it.  
  status [ ]
- **GAP06-REQ-34.07** — The subsystem SHALL satisfy: Integrate trust verdict expiry/quarantine as hard constraints in planning/scheduling decisions.  
  status [~]
- **GAP06-REQ-34.08** — The subsystem SHALL satisfy: Define residency/site constraints and ensure cross-tenant policies cannot reference unauthorized resources.  
  status [ ]
- **GAP06-REQ-34.09** — The subsystem SHALL satisfy: Create property tests for determinism, monotonicity of security restrictions, and order independence.  
  status [ ]
- **GAP06-REQ-34.10** — The subsystem SHALL satisfy: Create scenario tests combining security, residency, performance, and cost constraints including unsatisfiable cases.  
  status [ ]
- **GAP06-REQ-34.11** — The subsystem SHALL satisfy: Version the precedence engine and record its version in placement/verdict explanations.  
  status [ ]
- **GAP06-REQ-34.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-34.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-34.D3** — The subsystem SHALL satisfy: Traceability links `Policy conflict and precedence engine` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-35.01** — The subsystem SHALL satisfy: Reconstruct MASTER.md from the current implemented architecture and explicitly mark aspirational versus implemented behavior.  
  status [~]
- **GAP06-REQ-35.02** — The subsystem SHALL satisfy: Include subsystem purpose, scope, trust boundaries, architecture, APIs/schemas, state model, lifecycle, failure modes, security assumptions, dependencies, and release gates.  
  status [~]
- **GAP06-REQ-35.03** — The subsystem SHALL satisfy: Cross-reference the 100-entry checklist and the missing-components checklist with stable IDs.  
  status [~]
- **GAP06-REQ-35.04** — The subsystem SHALL satisfy: Include version history and compatibility notes matching the package version.  
  status [~]
- **GAP06-REQ-35.05** — The subsystem SHALL satisfy: Add documentation validation in CI to fail if README claims bundled artifacts that are absent.  
  status [~]
- **GAP06-REQ-35.06** — The subsystem SHALL satisfy: Generate/check a file manifest and documentation link checker during packaging.  
  status [~]
- **GAP06-REQ-35.07** — The subsystem SHALL satisfy: Require architecture/security owner review for material master-document changes.  
  status [!]
- **GAP06-REQ-35.08** — The subsystem SHALL satisfy: Record the MASTER.md digest in release evidence so certification references an immutable document.  
  status [~]
- **GAP06-REQ-35.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-35.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-35.D3** — The subsystem SHALL satisfy: Traceability links `MASTER.md source artifact` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-36.01** — The subsystem SHALL satisfy: Create ADRs for hardware roots, attestation protocol, persistence engine, HA consistency model, replay strategy, policy distribution, audit ledger, KMS/HSM, secure time, and offline mode.  
  status [~]
- **GAP06-REQ-36.02** — The subsystem SHALL satisfy: Use a standard ADR template with context, decision, options considered, tradeoffs, security implications, operational implications, migration path, and status.  
  status [~]
- **GAP06-REQ-36.03** — The subsystem SHALL satisfy: Record quantitative decision drivers such as latency, fleet scale, RPO/RTO, evidence size, and vendor compatibility.  
  status [~]
- **GAP06-REQ-36.04** — The subsystem SHALL satisfy: Link each ADR to threat-model items, requirements, implementation components, and test evidence.  
  status [~]
- **GAP06-REQ-36.05** — The subsystem SHALL satisfy: Define supersession rules so later ADRs do not silently rewrite history.  
  status [ ]
- **GAP06-REQ-36.06** — The subsystem SHALL satisfy: Review ADRs when assumptions change, dependencies reach EOL, cryptographic policy changes, or scale exceeds design bounds.  
  status [ ]
- **GAP06-REQ-36.07** — The subsystem SHALL satisfy: Include rejected alternatives and reasons sufficient for future engineers to avoid repeating analysis.  
  status [~]
- **GAP06-REQ-36.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-36.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-36.D3** — The subsystem SHALL satisfy: Traceability links `Architecture Decision Record` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-37.01** — The subsystem SHALL satisfy: Assign a primary engineering owner/team and backup owner for the subsystem.  
  status [!]
- **GAP06-REQ-37.02** — The subsystem SHALL satisfy: Assign security owner for trust model, crypto policy, threat model, and exception approval.  
  status [!]
- **GAP06-REQ-37.03** — The subsystem SHALL satisfy: Assign operational/on-call owner for production incidents and dependency health.  
  status [!]
- **GAP06-REQ-37.04** — The subsystem SHALL satisfy: Define escalation matrix by severity with paging targets, management/security escalation, and vendor escalation where needed.  
  status [!]
- **GAP06-REQ-37.05** — The subsystem SHALL satisfy: Publish ownership in repository metadata, runbooks, service catalog, and alert routing.  
  status [!]
- **GAP06-REQ-37.06** — The subsystem SHALL satisfy: Define handoff requirements during organizational change so no critical component becomes ownerless.  
  status [ ]
- **GAP06-REQ-37.07** — The subsystem SHALL satisfy: Review ownership at least quarterly and after major incidents/reorganizations.  
  status [ ]
- **GAP06-REQ-37.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-37.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-37.D3** — The subsystem SHALL satisfy: Traceability links `Named owner and escalation path` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [ ]
- **GAP06-REQ-38.01** — The subsystem SHALL satisfy: Convert ambiguous goals into atomic SHALL/SHALL NOT requirements with unique stable IDs.  
  status [~]
- **GAP06-REQ-38.02** — The subsystem SHALL satisfy: Ensure every requirement states preconditions, actors, inputs, behavior, outputs, failure behavior, and measurable acceptance criteria where applicable.  
  status [ ]
- **GAP06-REQ-38.03** — The subsystem SHALL satisfy: Distinguish normative requirements from rationale, examples, and implementation guidance.  
  status [ ]
- **GAP06-REQ-38.04** — The subsystem SHALL satisfy: Create a traceability matrix mapping requirement → threat/control → design component → code/module → test(s) → release evidence.  
  status [~]
- **GAP06-REQ-38.05** — The subsystem SHALL satisfy: Mark requirement status as implemented/partial/not implemented/deferred/waived with owner and rationale.  
  status [~]
- **GAP06-REQ-38.06** — The subsystem SHALL satisfy: Prevent release gate from counting a requirement as satisfied without linked machine-verifiable evidence.  
  status [~]
- **GAP06-REQ-38.07** — The subsystem SHALL satisfy: Add CI validation for duplicate IDs, orphan tests, orphan implementation claims, and stale version references.  
  status [~]
- **GAP06-REQ-38.08** — The subsystem SHALL satisfy: Baseline/spec version must be immutable once used for certification; changes create a new revision.  
  status [ ]
- **GAP06-REQ-38.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-38.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-38.D3** — The subsystem SHALL satisfy: Traceability links `SHALL-level specification and requirements traceability matrix` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-39.01** — The subsystem SHALL satisfy: Define latency percentiles for challenge issuance, attestation verification, enrollment, policy fetch/publish, replay consume, explanation, and quarantine propagation.  
  status [~]
- **GAP06-REQ-39.02** — The subsystem SHALL satisfy: Define sustained and burst throughput targets at service, site, and tenant level.  
  status [ ]
- **GAP06-REQ-39.03** — The subsystem SHALL satisfy: Define CPU, memory, storage/IOPS, network, KMS/HSM, and database connection/transaction budgets.  
  status [ ]
- **GAP06-REQ-39.04** — The subsystem SHALL satisfy: Define evidence-size distributions and worst-case event-log/certificate-chain sizes.  
  status [ ]
- **GAP06-REQ-39.05** — The subsystem SHALL satisfy: Define cold-start, failover recovery, backlog-drain, and re-attestation-storm targets.  
  status [ ]
- **GAP06-REQ-39.06** — The subsystem SHALL satisfy: Benchmark on representative hardware/VM profiles and record exact environment/tool versions.  
  status [~]
- **GAP06-REQ-39.07** — The subsystem SHALL satisfy: Include tail-latency and saturation curves rather than averages alone.  
  status [ ]
- **GAP06-REQ-39.08** — The subsystem SHALL satisfy: Create automated regression thresholds in CI/performance pipelines with approved variance margins.  
  status [ ]
- **GAP06-REQ-39.09** — The subsystem SHALL satisfy: Run burst and soak tests long enough to expose leaks, compaction effects, cache churn, and thermal/power limits where relevant.  
  status [~]
- **GAP06-REQ-39.10** — The subsystem SHALL satisfy: Publish baseline artifacts per release and document expected capacity envelope/headroom.  
  status [~]
- **GAP06-REQ-39.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-39.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-39.D3** — The subsystem SHALL satisfy: Traceability links `Performance baselines and release thresholds` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-40.01** — The subsystem SHALL satisfy: Fuzz all external schema decoders, certificate parsers, TPM/TEE evidence parsers, event-log/IMA parsers, policy bundle parsers, and audit import/export formats.  
  status [~]
- **GAP06-REQ-40.02** — The subsystem SHALL satisfy: Seed fuzzers with real valid corpora plus known malformed/corner-case fixtures.  
  status [~]
- **GAP06-REQ-40.03** — The subsystem SHALL satisfy: Use structure-aware generation where possible so tests reach semantic validation rather than only syntax rejection.  
  status [ ]
- **GAP06-REQ-40.04** — The subsystem SHALL satisfy: Define properties for challenge uniqueness/single-consumption, revocation monotonicity, policy version monotonicity, tenant isolation, deterministic decision, and no trust increase on malformed input.  
  status [~]
- **GAP06-REQ-40.05** — The subsystem SHALL satisfy: Add state-machine/model-based tests that generate legal/illegal lifecycle transition sequences.  
  status [ ]
- **GAP06-REQ-40.06** — The subsystem SHALL satisfy: Run fuzzing with sanitizers/instrumentation appropriate to implementation language and capture crashes, hangs, OOM, excessive CPU, and assertion failures.  
  status [ ]
- **GAP06-REQ-40.07** — The subsystem SHALL satisfy: Convert every discovered bug into a minimized regression corpus entry.  
  status [~]
- **GAP06-REQ-40.08** — The subsystem SHALL satisfy: Run bounded fuzz smoke tests in normal CI and longer campaigns on scheduled/security pipelines.  
  status [~]
- **GAP06-REQ-40.09** — The subsystem SHALL satisfy: Track coverage and time-to-bug metrics without treating coverage percentage as sufficient proof.  
  status [ ]
- **GAP06-REQ-40.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-40.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-40.D3** — The subsystem SHALL satisfy: Traceability links `Fuzz and property tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-41.01** — The subsystem SHALL satisfy: Identify shared-state race points: challenge issue/consume, enrollment rotation/revocation, policy activation, verdict cache, quarantine, scheduler renewal, and audit sequencing.  
  status [~]
- **GAP06-REQ-41.02** — The subsystem SHALL satisfy: Create high-contention tests with synchronized barriers to force concurrent attempts at atomic operations.  
  status [~]
- **GAP06-REQ-41.03** — The subsystem SHALL satisfy: Run multi-process tests against the production persistence backend, not only an in-memory model.  
  status [!]
- **GAP06-REQ-41.04** — The subsystem SHALL satisfy: Run multi-replica tests across the actual HA/consensus configuration.  
  status [!]
- **GAP06-REQ-41.05** — The subsystem SHALL satisfy: Inject delays between read/validate/write phases to expose time-of-check/time-of-use flaws.  
  status [ ]
- **GAP06-REQ-41.06** — The subsystem SHALL satisfy: Test revoke-vs-attest, rotate-vs-attest, quarantine-vs-schedule, policy-activate-vs-verify, and restore-vs-live-traffic races.  
  status [ ]
- **GAP06-REQ-41.07** — The subsystem SHALL satisfy: Use language/runtime race detectors or sanitizers where supported.  
  status [ ]
- **GAP06-REQ-41.08** — The subsystem SHALL satisfy: Assert invariants after each run: no duplicate challenge acceptance, no revoked identity reactivation, no mixed policy generation, no cross-tenant leakage.  
  status [~]
- **GAP06-REQ-41.09** — The subsystem SHALL satisfy: Retain deterministic seeds/traces for failing interleavings as regression artifacts.  
  status [ ]
- **GAP06-REQ-41.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-41.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-41.D3** — The subsystem SHALL satisfy: Traceability links `Concurrency and race tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-42.01** — The subsystem SHALL satisfy: Build a workload generator modeling node populations, platform mix, attestation intervals, evidence sizes, enrollment churn, policy rollouts, and failure rates.  
  status [~]
- **GAP06-REQ-42.02** — The subsystem SHALL satisfy: Run baseline benchmarks for each core operation and full end-to-end flow.  
  status [~]
- **GAP06-REQ-42.03** — The subsystem SHALL satisfy: Run multi-hour/day soak tests to reveal leaks, unbounded caches, fragmentation, compaction stalls, and drift.  
  status [!]
- **GAP06-REQ-42.04** — The subsystem SHALL satisfy: Run synchronized burst scenarios such as site reconnect, verifier restart, policy-triggered re-attestation, and certificate rollover.  
  status [~]
- **GAP06-REQ-42.05** — The subsystem SHALL satisfy: Run failure-amplified load with slow database/KMS/time dependencies to validate backpressure.  
  status [ ]
- **GAP06-REQ-42.06** — The subsystem SHALL satisfy: Validate fairness across tenants/sites under mixed heavy and light workloads.  
  status [~]
- **GAP06-REQ-42.07** — The subsystem SHALL satisfy: Capture latency percentiles, throughput, resource usage, queue depths, error reasons, GC/runtime behavior, and dependency saturation.  
  status [~]
- **GAP06-REQ-42.08** — The subsystem SHALL satisfy: Compare results against release thresholds and prior version baselines.  
  status [ ]
- **GAP06-REQ-42.09** — The subsystem SHALL satisfy: Archive workload profiles, raw results, environment metadata, and pass/fail summary as release evidence.  
  status [~]
- **GAP06-REQ-42.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-42.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-42.D3** — The subsystem SHALL satisfy: Traceability links `Benchmark, soak, burst, and fleet tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-43.01** — The subsystem SHALL satisfy: Define chaos scenarios for database partition, replica split brain, KMS/HSM outage, secure-time loss, policy distributor loss, audit sink outage, scheduler disconnect, and site WAN loss.  
  status [ ]
- **GAP06-REQ-43.02** — The subsystem SHALL satisfy: Inject packet loss, latency, reordering, duplication, and asymmetric partitions rather than only hard shutdowns.  
  status [!]
- **GAP06-REQ-43.03** — The subsystem SHALL satisfy: Verify challenge single-consumption and revocation/quarantine safety across every partition scenario.  
  status [ ]
- **GAP06-REQ-43.04** — The subsystem SHALL satisfy: Verify disconnected-mode maximum-age rules and fail-closed transitions.  
  status [~]
- **GAP06-REQ-43.05** — The subsystem SHALL satisfy: Verify reconnect reconciliation handles duplicated queued events, policy conflicts, revocations, and stale identity epochs.  
  status [~]
- **GAP06-REQ-43.06** — The subsystem SHALL satisfy: Verify stale leaders/replicas are fenced before accepting security writes after healing.  
  status [~]
- **GAP06-REQ-43.07** — The subsystem SHALL satisfy: Measure recovery time, backlog-drain time, expiry misses, and operator intervention required.  
  status [ ]
- **GAP06-REQ-43.08** — The subsystem SHALL satisfy: Run at production-like scale where possible to expose recovery storms.  
  status [!]
- **GAP06-REQ-43.09** — The subsystem SHALL satisfy: Document each scenario with expected state machine, assertions, and automated pass/fail evidence.  
  status [ ]
- **GAP06-REQ-43.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-43.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-43.D3** — The subsystem SHALL satisfy: Traceability links `Disaster, partition, reconnect, and degraded-control-plane tests` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-44.01** — The subsystem SHALL satisfy: Define an evidence manifest schema containing release version, source commit, build digest, SBOM digest, test suite IDs/results, performance results, security scans, compatibility matrix, and approval records.  
  status [~]
- **GAP06-REQ-44.02** — The subsystem SHALL satisfy: Link each SHALL/checklist requirement to one or more evidence artifacts with stable IDs and hashes.  
  status [~]
- **GAP06-REQ-44.03** — The subsystem SHALL satisfy: Include test environment metadata sufficient to reproduce results: OS, architecture, hardware/TPM, dependencies, configuration, and tool versions.  
  status [~]
- **GAP06-REQ-44.04** — The subsystem SHALL satisfy: Sign the evidence manifest with a release/certification key and record signing identity/time.  
  status [!]
- **GAP06-REQ-44.05** — The subsystem SHALL satisfy: Store immutable evidence in a controlled artifact repository with retention matching release/support life.  
  status [!]
- **GAP06-REQ-44.06** — The subsystem SHALL satisfy: Fail production release if mandatory evidence is missing, stale, unsigned, or references a different artifact digest.  
  status [~]
- **GAP06-REQ-44.07** — The subsystem SHALL satisfy: Provide verification tooling that checks hashes, signatures, schema validity, and requirement coverage offline.  
  status [~]
- **GAP06-REQ-44.08** — The subsystem SHALL satisfy: Include waivers/exceptions as first-class signed artifacts with owner and expiry rather than silently treating them as passes.  
  status [~]
- **GAP06-REQ-44.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-44.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-44.D3** — The subsystem SHALL satisfy: Traceability links `Machine-readable acceptance evidence bundle` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-45.01** — The subsystem SHALL satisfy: Define rollout rings by environment/site/fleet percentage/risk class and entry/exit criteria for each ring.  
  status [~]
- **GAP06-REQ-45.02** — The subsystem SHALL satisfy: Deploy schema/config/policy/code changes in an order compatible with mixed versions.  
  status [ ]
- **GAP06-REQ-45.03** — The subsystem SHALL satisfy: Define canary health metrics including attestation failure delta, latency, error-rate, replay anomalies, quarantine spikes, and dependency saturation.  
  status [~]
- **GAP06-REQ-45.04** — The subsystem SHALL satisfy: Automate rollout halt/rollback when thresholds are breached while requiring human review for security-significant anomalies.  
  status [ ]
- **GAP06-REQ-45.05** — The subsystem SHALL satisfy: Ensure rollback cannot violate monotonic security state such as consumed challenges, revocations, or minimum policy versions.  
  status [~]
- **GAP06-REQ-45.06** — The subsystem SHALL satisfy: Provide emergency-disable/kill-switch capabilities scoped narrowly to unsafe optional behavior, not a global trust bypass.  
  status [~]
- **GAP06-REQ-45.07** — The subsystem SHALL satisfy: Protect rollback/emergency controls with strong authorization, multi-party approval where appropriate, and tamper-evident audit.  
  status [~]
- **GAP06-REQ-45.08** — The subsystem SHALL satisfy: Rehearse rollback under load and during partial site failure.  
  status [!]
- **GAP06-REQ-45.09** — The subsystem SHALL satisfy: Publish post-rollout verification evidence and reconcile version/config drift.  
  status [ ]
- **GAP06-REQ-45.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-45.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-45.D3** — The subsystem SHALL satisfy: Traceability links `Canary, staged rollout, rollback, and emergency-disable procedures` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-46.01** — The subsystem SHALL satisfy: Inventory first-party components, third-party libraries, OS/base images, cryptographic providers, TPM/TEE SDKs, databases, and infrastructure dependencies.  
  status [~]
- **GAP06-REQ-46.02** — The subsystem SHALL satisfy: Define severity mapping and remediation SLAs, including emergency timelines for actively exploited vulnerabilities.  
  status [~]
- **GAP06-REQ-46.03** — The subsystem SHALL satisfy: Continuously ingest vulnerability advisories/CVEs and match them to the SBOM and deployed versions.  
  status [!]
- **GAP06-REQ-46.04** — The subsystem SHALL satisfy: Define exception process requiring compensating controls, owner, risk acceptance, and expiry.  
  status [~]
- **GAP06-REQ-46.05** — The subsystem SHALL satisfy: Define dependency/platform EOL lead time, migration plan, and release blocking dates.  
  status [~]
- **GAP06-REQ-46.06** — The subsystem SHALL satisfy: Patch in staged rollout rings with regression/security verification and documented rollback.  
  status [ ]
- **GAP06-REQ-46.07** — The subsystem SHALL satisfy: Maintain supported-release branches and backport policy for security fixes.  
  status [ ]
- **GAP06-REQ-46.08** — The subsystem SHALL satisfy: Publish security advisories and operator upgrade guidance when customer action is required.  
  status [ ]
- **GAP06-REQ-46.09** — The subsystem SHALL satisfy: Track fleet patch compliance and alert on unsupported/EOL versions.  
  status [ ]
- **GAP06-REQ-46.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-46.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-46.D3** — The subsystem SHALL satisfy: Traceability links `Patch, vulnerability, and end-of-life policy` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-47.01** — The subsystem SHALL satisfy: Define severity criteria for key compromise, trust-anchor compromise, mass attestation failure, replay acceptance, identity cloning, policy poisoning, audit tampering, and availability incidents.  
  status [~]
- **GAP06-REQ-47.02** — The subsystem SHALL satisfy: Define 24×7 paging targets, acknowledgement time, incident commander, security lead, communications lead, and escalation tree.  
  status [!]
- **GAP06-REQ-47.03** — The subsystem SHALL satisfy: Create containment actions for disabling compromised keys, freezing policy publication, quarantining affected nodes, blocking identities, and isolating sites.  
  status [~]
- **GAP06-REQ-47.04** — The subsystem SHALL satisfy: Define forensic data preservation for audit ledger, raw evidence digests, configs, builds, logs, traces, and KMS/HSM events.  
  status [~]
- **GAP06-REQ-47.05** — The subsystem SHALL satisfy: Define safe recovery order and validation gates before trust decisions resume.  
  status [ ]
- **GAP06-REQ-47.06** — The subsystem SHALL satisfy: Provide commands/API steps with prerequisites, expected output, rollback, and authorization level.  
  status [~]
- **GAP06-REQ-47.07** — The subsystem SHALL satisfy: Define external/vendor escalation and disclosure decision paths.  
  status [!]
- **GAP06-REQ-47.08** — The subsystem SHALL satisfy: Run table-top and technical simulations at least periodically and after major architecture changes.  
  status [!]
- **GAP06-REQ-47.09** — The subsystem SHALL satisfy: Capture post-incident corrective actions into requirements/tests/runbooks with owners and dates.  
  status [ ]
- **GAP06-REQ-47.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-47.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-47.D3** — The subsystem SHALL satisfy: Traceability links `Incident severity, paging, containment, and recovery runbook` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-48.01** — The subsystem SHALL satisfy: Perform periodic review of administrative roles, service identities, KMS/HSM permissions, database access, and break-glass grants.  
  status [~]
- **GAP06-REQ-48.02** — The subsystem SHALL satisfy: Review trust anchors, approved signers, revocation sources, measurement policies, algorithm policy, and offline exceptions.  
  status [~]
- **GAP06-REQ-48.03** — The subsystem SHALL satisfy: Review dependency versions, EOL dates, vulnerabilities, and supply-chain provenance.  
  status [~]
- **GAP06-REQ-48.04** — The subsystem SHALL satisfy: Review architecture assumptions against actual scale, failure incidents, new platform types, and threat intelligence.  
  status [~]
- **GAP06-REQ-48.05** — The subsystem SHALL satisfy: Reconcile deployed configuration/policy digests against approved source-of-truth.  
  status [ ]
- **GAP06-REQ-48.06** — The subsystem SHALL satisfy: Require evidence and reviewer sign-off; track findings as owned remediation items.  
  status [!]
- **GAP06-REQ-48.07** — The subsystem SHALL satisfy: Remove stale access/policies rather than only documenting them.  
  status [ ]
- **GAP06-REQ-48.08** — The subsystem SHALL satisfy: Define review cadence by risk and trigger out-of-cycle review after major incidents/compromises.  
  status [~]
- **GAP06-REQ-48.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-48.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-48.D3** — The subsystem SHALL satisfy: Traceability links `Recurring access, policy, dependency, and architecture review process` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-49.01** — The subsystem SHALL satisfy: Define a structured record with requirement/control ID, scope, rationale, risk, compensating controls, owner, approver, issue date, expiry, and remediation plan.  
  status [~]
- **GAP06-REQ-49.02** — The subsystem SHALL satisfy: Prohibit indefinite waivers; require explicit expiration and renewal review.  
  status [~]
- **GAP06-REQ-49.03** — The subsystem SHALL satisfy: Require higher approval for security-critical P0 exceptions and prohibit waiving foundational trust invariants such as replay safety without an approved redesign.  
  status [~]
- **GAP06-REQ-49.04** — The subsystem SHALL satisfy: Link each exception to affected releases/environments and machine-readable acceptance evidence.  
  status [ ]
- **GAP06-REQ-49.05** — The subsystem SHALL satisfy: Alert before waiver expiry and fail deployment/release after expiry unless renewed through the approval process.  
  status [~]
- **GAP06-REQ-49.06** — The subsystem SHALL satisfy: Track aggregate exception count/age/severity as a governance metric.  
  status [ ]
- **GAP06-REQ-49.07** — The subsystem SHALL satisfy: Close exceptions only with evidence that the underlying requirement is now satisfied.  
  status [ ]
- **GAP06-REQ-49.08** — The subsystem SHALL satisfy: Periodically review recurring exceptions for architectural/root-cause remediation.  
  status [ ]
- **GAP06-REQ-49.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-49.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-49.D3** — The subsystem SHALL satisfy: Traceability links `Exception, waiver, and technical-debt register` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-50.01** — The subsystem SHALL satisfy: Define mandatory gate inputs: implementation status, traceability, tests, threat model, vulnerability status, performance, DR, compatibility, operations, runbooks, SBOM/provenance, and exceptions.  
  status [~]
- **GAP06-REQ-50.02** — The subsystem SHALL satisfy: Encode objective pass/fail rules where possible and identify which decisions require named human approval.  
  status [~]
- **GAP06-REQ-50.03** — The subsystem SHALL satisfy: Block release if any P0 component is unsatisfied unless an explicitly authorized policy allows a documented exception; record the exact authority and rationale.  
  status [~]
- **GAP06-REQ-50.04** — The subsystem SHALL satisfy: Validate evidence artifact hashes match the candidate build and configuration/policy versions.  
  status [~]
- **GAP06-REQ-50.05** — The subsystem SHALL satisfy: Require all critical/high vulnerabilities to be remediated or formally accepted under policy.  
  status [!]
- **GAP06-REQ-50.06** — The subsystem SHALL satisfy: Require successful restore/DR and rollback evidence within the defined freshness window.  
  status [ ]
- **GAP06-REQ-50.07** — The subsystem SHALL satisfy: Require compatibility/performance results for supported production profiles.  
  status [ ]
- **GAP06-REQ-50.08** — The subsystem SHALL satisfy: Produce a signed gate decision containing approvers, evidence manifest digest, waivers, release digest, and timestamp.  
  status [!]
- **GAP06-REQ-50.09** — The subsystem SHALL satisfy: Retain past gate decisions immutably and make later revocation possible if evidence is discovered invalid.  
  status [ ]
- **GAP06-REQ-50.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-50.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-50.D3** — The subsystem SHALL satisfy: Traceability links `Formal production exit gate` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-51.01** — The subsystem SHALL satisfy: Define supported packaging formats and platform targets with consistent semantic versioning.  
  status [~]
- **GAP06-REQ-51.02** — The subsystem SHALL satisfy: Pin direct and transitive dependency versions or hashes using lockfiles/constraints appropriate to each ecosystem.  
  status [~]
- **GAP06-REQ-51.03** — The subsystem SHALL satisfy: Capture build metadata: source commit, dirty-tree state, toolchain versions, target architecture, build timestamp policy, and feature flags.  
  status [~]
- **GAP06-REQ-51.04** — The subsystem SHALL satisfy: Use hermetic/reproducible build inputs where practical and prohibit untracked network dependency resolution during release builds.  
  status [ ]
- **GAP06-REQ-51.05** — The subsystem SHALL satisfy: Generate checksums/signatures for every release artifact and include them in the provenance manifest.  
  status [~]
- **GAP06-REQ-51.06** — The subsystem SHALL satisfy: Validate archive paths/names for Windows-safe extraction, path-length limits, case collisions, Unicode normalization collisions, and forbidden device names.  
  status [~]
- **GAP06-REQ-51.07** — The subsystem SHALL satisfy: Run clean-install/upgrade/uninstall tests on each supported platform and architecture.  
  status [ ]
- **GAP06-REQ-51.08** — The subsystem SHALL satisfy: Ensure default installation does not generate insecure sample keys, trust anchors, or permissive production configuration.  
  status [~]
- **GAP06-REQ-51.09** — The subsystem SHALL satisfy: Include license/notice/SBOM/security documentation consistently in every release package.  
  status [~]
- **GAP06-REQ-51.10** — The subsystem SHALL satisfy: Fail packaging when expected files are missing or untracked extra files appear.  
  status [~]
- **GAP06-REQ-51.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-51.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-51.D3** — The subsystem SHALL satisfy: Traceability links `Packaging, build metadata, and dependency pinning` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-52.01** — The subsystem SHALL satisfy: Generate machine-readable SBOM (SPDX or CycloneDX) including direct/transitive dependencies, versions, licenses, hashes, and package identifiers.  
  status [~]
- **GAP06-REQ-52.02** — The subsystem SHALL satisfy: Generate build provenance attestation linking source revision, builder identity, workflow, materials, artifact digest, and build parameters.  
  status [~]
- **GAP06-REQ-52.03** — The subsystem SHALL satisfy: Sign release artifacts and provenance with managed release keys; publish verification metadata and rotation policy.  
  status [!]
- **GAP06-REQ-52.04** — The subsystem SHALL satisfy: Run dependency vulnerability scanning against current advisory databases and record scan timestamp/tool/database revision.  
  status [!]
- **GAP06-REQ-52.05** — The subsystem SHALL satisfy: Run license/policy checks and flag prohibited/unknown licenses or packages.  
  status [~]
- **GAP06-REQ-52.06** — The subsystem SHALL satisfy: Protect CI release workflows from untrusted pull-request secret access and require controlled promotion to signing.  
  status [!]
- **GAP06-REQ-52.07** — The subsystem SHALL satisfy: Verify third-party downloaded binaries/packages with signatures/checksums and record provenance.  
  status [ ]
- **GAP06-REQ-52.08** — The subsystem SHALL satisfy: Add provenance verification to deployment/installation so unsigned or mismatched artifacts are rejected where feasible.  
  status [ ]
- **GAP06-REQ-52.09** — The subsystem SHALL satisfy: Archive SBOM/provenance/scan outputs in the acceptance evidence bundle and tie them to exact artifact digests.  
  status [~]
- **GAP06-REQ-52.10** — The subsystem SHALL satisfy: Define response workflow when a new post-release vulnerability is discovered in an SBOM component.  
  status [ ]
- **GAP06-REQ-52.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-52.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-52.D3** — The subsystem SHALL satisfy: Traceability links `SBOM, provenance, release signing, and dependency vulnerability scanning` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-53.01** — The subsystem SHALL satisfy: Identify and document the project license and ensure repository/package headers and LICENSE file are consistent.  
  status [!]
- **GAP06-REQ-53.02** — The subsystem SHALL satisfy: Generate NOTICE/third-party attribution from the verified dependency inventory and preserve required copyright/license texts.  
  status [ ]
- **GAP06-REQ-53.03** — The subsystem SHALL satisfy: Review dependencies for copyleft/redistribution/export restrictions inconsistent with distribution goals.  
  status [~]
- **GAP06-REQ-53.04** — The subsystem SHALL satisfy: Publish SECURITY.md with supported versions, vulnerability reporting channel, expected acknowledgement, disclosure process, and encryption key if used.  
  status [~]
- **GAP06-REQ-53.05** — The subsystem SHALL satisfy: Define coordinated vulnerability disclosure timelines and emergency handling for actively exploited issues.  
  status [~]
- **GAP06-REQ-53.06** — The subsystem SHALL satisfy: Define handling of security researchers, duplicate reports, embargoed advisories, and CVE assignment where applicable.  
  status [~]
- **GAP06-REQ-53.07** — The subsystem SHALL satisfy: Add CI checks ensuring LICENSE/NOTICE/SECURITY files are included in release packages and stay synchronized with dependencies.  
  status [~]
- **GAP06-REQ-53.08** — The subsystem SHALL satisfy: Review cryptography/export/legal obligations appropriate to distribution jurisdictions with qualified counsel when necessary.  
  status [!]
- **GAP06-REQ-53.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-53.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-53.D3** — The subsystem SHALL satisfy: Traceability links `License, notice, and security disclosure policy` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-54.01** — The subsystem SHALL satisfy: Create Day-0 prerequisites covering infrastructure, identities, KMS/HSM keys, trust anchors, databases, secure time, network policy, certificates, and capacity.  
  status [~]
- **GAP06-REQ-54.02** — The subsystem SHALL satisfy: Create Day-1 deployment steps with commands, configuration validation, schema migration, service startup order, readiness checks, canary verification, and rollback points.  
  status [~]
- **GAP06-REQ-54.03** — The subsystem SHALL satisfy: Create Day-2 procedures for policy publication, trust-anchor rotation, key rotation, certificate renewal, node enrollment/revocation, quarantine review, backup, restore, and capacity scaling.  
  status [~]
- **GAP06-REQ-54.04** — The subsystem SHALL satisfy: Include exact preconditions, required permissions, expected outputs, failure branches, and post-action verification for each procedure.  
  status [~]
- **GAP06-REQ-54.05** — The subsystem SHALL satisfy: Provide troubleshooting decision trees keyed to stable error/reason codes and observability signals.  
  status [~]
- **GAP06-REQ-54.06** — The subsystem SHALL satisfy: Include controlled procedures for dependency outage, time integrity failure, replay-store saturation, audit-ledger outage, and site disconnection.  
  status [~]
- **GAP06-REQ-54.07** — The subsystem SHALL satisfy: Include upgrade/downgrade compatibility checks and prohibit rollback that weakens monotonic security state.  
  status [~]
- **GAP06-REQ-54.08** — The subsystem SHALL satisfy: Include disaster-recovery and failback steps validated against scheduled game-day evidence.  
  status [!]
- **GAP06-REQ-54.09** — The subsystem SHALL satisfy: Keep commands/scripts version-controlled and test them in staging; avoid undocumented manual console steps.  
  status [ ]
- **GAP06-REQ-54.10** — The subsystem SHALL satisfy: Assign runbook owners/review cadence and link alerts directly to the appropriate procedure.  
  status [!]
- **GAP06-REQ-54.D1** — The subsystem SHALL satisfy: All component-specific items above and Universal Gate U01–U20 are either `[x]` or covered by an unexpired approved waiver.  
  status [!]
- **GAP06-REQ-54.D2** — The subsystem SHALL satisfy: No open Critical/High defect remains that can cause false trust, bypass isolation, reopen replay, cross tenant/site boundaries, or corrupt authoritative security state.  
  status [!]
- **GAP06-REQ-54.D3** — The subsystem SHALL satisfy: Traceability links `Complete operational day-0/day-1/day-2 runbooks` to requirements, design, code, tests, runbooks, and signed/machine-verifiable acceptance evidence for the exact release artifact.  
  status [~]
- **GAP06-REQ-G01** — The subsystem SHALL satisfy: All P0 sections 01–15 meet their component Definition of Done; no P0 waiver weakens a foundational trust invariant without explicit executive/security risk acceptance and compensating architecture.  
  status [!]
- **GAP06-REQ-G02** — The subsystem SHALL satisfy: All P1 sections 16–34 required by the deployed topology meet Definition of Done and have passed resilience, HA, partition, scale, and operational tests.  
  status [!]
- **GAP06-REQ-G03** — The subsystem SHALL satisfy: All P2 sections 35–54 required by organizational release policy meet Definition of Done, or have approved, time-bounded waivers.  
  status [!]
- **GAP06-REQ-G04** — The subsystem SHALL satisfy: The requirements traceability matrix shows no production SHALL requirement with status `unknown`, `unmapped`, or `claimed complete without evidence`.  
  status [!]
- **GAP06-REQ-G05** — The subsystem SHALL satisfy: Release artifact, source commit, SBOM, provenance, signatures, policy/configuration digests, test evidence, compatibility matrix, and runbook versions are mutually consistent.  
  status [!]
- **GAP06-REQ-G06** — The subsystem SHALL satisfy: Security review confirms threat-model coverage for replay, relay/cuckoo, identity cloning, policy poisoning, key/trust-anchor compromise, parser attacks, tenant isolation, rollback, and control-plane abuse.  
  status [!]
- **GAP06-REQ-G07** — The subsystem SHALL satisfy: Restore/DR, failover, rollback, canary, offline/disconnected, and quarantine/recovery exercises have current passing evidence within the organization-defined freshness window.  
  status [!]
- **GAP06-REQ-G08** — The subsystem SHALL satisfy: Load/soak/burst results demonstrate capacity headroom and no unbounded state/resource growth at target fleet scale and defined adversarial limits.  
  status [!]
- **GAP06-REQ-G09** — The subsystem SHALL satisfy: Operations/on-call accepts dashboards, alerts, runbooks, paging, incident containment, and recovery procedures; named owners and escalation paths are current.  
  status [!]
- **GAP06-REQ-G10** — The subsystem SHALL satisfy: A signed production-gate record identifies the exact artifact digest, approved deployment scope, approvers, evidence-manifest digest, active waivers, and decision timestamp.  
  status [!]
