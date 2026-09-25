# GAP-07 Artifact Provenance & Signing — Production Completion Checklist

**Checklist version:** 1.0.0  
**Target implementation:** GAP-07 v5.0.0  
**Source:** `GAP07_MISSING_COMPONENTS_v5.0.0.md`  
**Scope:** 48 missing/external production components identified after the v5.0.0 audit and hardening pass.  
**Purpose:** Convert the production-gap inventory into executable engineering, security, validation, operations, and release-readiness gates.

## Checklist conventions

- **P0 — Production admission blocker:** must be implemented and end-to-end validated before GAP-07 can be treated as a production signing/verification authority.
- **P1 — High-priority hardening/operations:** required for robust fleet operation, incident response, interoperability, and sustained production reliability.
- **P2 — Certification/resilience/scale:** required for mature assurance, certification evidence, large-fleet operation, and lifecycle governance.
- **External/packaging:** integration and bootstrap dependencies that must be supplied by the parent estate or release system.
- Every item is written as a verifiable gate. Completion should produce code, configuration, tests, telemetry, operational procedure, or machine-verifiable evidence.
- Security-sensitive failures must be **fail closed** unless an explicitly approved, time-bounded, auditable exception policy says otherwise.
- Acceptance evidence should include test IDs, build IDs, artifact digests, schema versions, policy versions, signer/key identifiers, and timestamps from a trusted source where applicable.

## Global completion gates

- [ ] Assign an accountable owner and technical reviewer to every component in this checklist.
- [ ] Map every checklist item to a tracked requirement/work item with immutable identifier and status.
- [ ] Record implementation repository, module, package, API, schema, test, and deployment location for every completed control.
- [ ] Define security invariants for artifact identity, signer identity, environment, artifact kind, provenance lineage, trust version, and policy version.
- [ ] Require structured, stable error codes for all externally observable refusal/failure paths; do not depend on free-form exception text.
- [ ] Require deterministic, canonical machine-readable evidence for every production admission decision.
- [ ] Require negative tests for bypass, downgrade, replay, rollback, cross-tenant confusion, stale trust, malformed input, and dependency failure.
- [ ] Require tests in normal and optimized/interpreter-production modes so security behavior cannot disappear under optimization.
- [ ] Bound all untrusted-input lengths, collection sizes, recursion/depth, decompression ratios, CPU cost, memory cost, and I/O duration.
- [ ] Ensure secret/private-key material never enters logs, traces, metrics labels, crash dumps, exception messages, or mutable application configuration.
- [ ] Use monotonic versions or generations for trust, policy, schema, algorithm, and deployment configuration; reject rollback unless explicitly authorized.
- [ ] Ensure every security-relevant state transition emits an audit event linked to actor, reason, old state, new state, and evidence digest.
- [ ] Define connected and disconnected operating modes and explicitly document which verification guarantees remain valid in each mode.
- [ ] Define recovery behavior for power loss, process crash, disk-full, partial writes, network partition, stale control plane, and dependency outage.
- [ ] Establish CI gates that execute unit, integration, negative, fuzz/property, compatibility, and packaging checks appropriate to the changed surface.
- [ ] Generate and archive SBOM, dependency scan, vulnerability status, test evidence, provenance, and release signatures for every GAP-07 release.
- [ ] Verify all production binaries/packages from a clean environment using only declared dependencies and signed release inputs.
- [ ] Make production admission fail closed when required trust, policy, time, KMS/HSM, transparency, or registry dependencies are unavailable.
- [ ] Prohibit hidden development/test fallbacks in production builds through build-time feature policy plus runtime self-checks.
- [ ] Define measurable service-level indicators for verification latency, trust freshness, revocation propagation, refusal rate, dependency health, and audit export health.
- [ ] Document an emergency-disable/break-glass design with multi-party authorization, narrow scope, expiry, tamper-evident logging, and post-event review.
- [ ] Require independent security review for cryptographic, trust-distribution, canonicalization, and policy-semantic changes.
- [ ] Keep backward-compatibility behavior explicit; never silently accept weaker legacy signature/attestation formats.
- [ ] Maintain a machine-readable compatibility matrix and migration plan for every supported schema, algorithm, registry, runtime, and policy version.
- [ ] Gate production readiness on objective evidence rather than documentation-only completion.

---

# P0 — Required Before Production Admission

## 1. Asymmetric Production Signer/Verifier Backend

**Objective:** Replace reference-only HMAC signing with production-grade asymmetric signatures that provide distributed verification and non-repudiation while preserving GAP-07 domain separation and fail-closed semantics.

### Engineering and security checklist
- [ ] Define the production signature profile, including approved algorithms, key sizes/curves, hash functions, deterministic/non-deterministic requirements, signature encoding, and algorithm identifiers.
- [ ] Implement Ed25519, ECDSA P-256/P-384, RSA-PSS, or the approved estate signing backend behind the existing signer/verifier abstraction without exposing private-key material to GAP-07 callers.
- [ ] Bind artifact digest, artifact kind, environment, schema version, signer identity, key identifier, signing purpose, and any required policy domain into the signed message.
- [ ] Use an unambiguous domain-separation prefix and length-delimited canonical encoding so no two semantic messages can map to the same signed byte sequence through concatenation ambiguity.
- [ ] Define a versioned signature envelope with explicit `alg`, `kid`, signer identity, signing timestamp, artifact digest algorithm, context fields, signature bytes, and optional certificate/attestation references.
- [ ] Reject unknown algorithms, missing fields, duplicate fields, malformed encodings, invalid base encodings, non-canonical representations, and unsupported signature-envelope versions.
- [ ] Reject algorithm substitution/downgrade attempts where the envelope or policy requests a weaker algorithm than the signer identity or key policy permits.
- [ ] Ensure verifier behavior does not infer algorithm solely from key shape or signature length; algorithm selection must be explicit and policy-validated.
- [ ] Add cryptographic verification using constant-time or library-provided hardened primitives; do not implement raw curve/RSA arithmetic in GAP-07.
- [ ] Define key-ID collision behavior and require globally unique or namespace-qualified key identifiers across tenants/sites/environments.
- [ ] Preserve strict separation between verification trust metadata and private signing-key custody.
- [ ] Implement bounded parsing and signature-size limits before invoking cryptographic libraries to prevent parser and big-integer resource abuse.
- [ ] Add deterministic test vectors for every approved algorithm and signature-envelope version, including cross-language verification vectors where production clients are heterogeneous.
- [ ] Add negative vectors for wrong artifact kind, wrong environment, wrong digest, wrong signer, wrong key ID, altered timestamp, altered algorithm, truncated signature, and malformed envelope.
- [ ] Test signature verification with production-equivalent crypto-library versions and platform builds used on Windows, Linux, edge nodes, and any embedded/Wasm boundary.

### Acceptance gates
- [ ] A signature produced by one approved implementation verifies in every supported verifier implementation using the same canonical signed bytes.
- [ ] A valid signature cannot be replayed across artifact kind, environment, signer identity, key ID, or incompatible policy domain.
- [ ] Legacy `PK_SIGNATURE/1` remains rejected unless a separately approved migration verifier is explicitly invoked and auditable.
- [ ] Production builds contain no enabled HMAC signing path except an explicitly isolated test/reference profile that cannot satisfy production admission policy.
- [ ] Independent cryptographic review confirms envelope semantics, domain separation, algorithm usage, failure handling, and library configuration.

## 2. KMS/HSM Integration

**Objective:** Move production private-key operations into managed or hardware-backed custody with explicit provider contracts for AWS KMS, Azure Key Vault/Managed HSM, Google Cloud KMS, PKCS#11, TPM, Vault Transit, or the approved estate equivalent.

### Engineering and security checklist
- [ ] Define a `KeyProvider` production contract that exposes sign/public-key/metadata operations without returning exportable private-key bytes.
- [ ] Model provider-specific key identifiers, versions, aliases, regions, partitions, hardware protection level, and permitted signing algorithms in a normalized internal representation.
- [ ] Implement provider adapters with strict timeout, retry, cancellation, circuit-breaker, and idempotency semantics appropriate to signing requests.
- [ ] Require authenticated workload identity for KMS/HSM access; prohibit static long-lived credentials in repository files, images, local configuration, or environment dumps.
- [ ] Enforce least-privilege provider IAM so signer workloads can invoke only the exact key/version/algorithm operations required.
- [ ] Require non-exportability for production private keys where the selected provider supports it and record protection level as evidence.
- [ ] Validate KMS/HSM responses against the requested algorithm and key version; reject responses that do not match the expected public-key identity.
- [ ] Handle provider key rotation explicitly so aliases cannot silently redirect to an untrusted key without trust-store/policy activation.
- [ ] Distinguish transient provider unavailability from permanent key disable/revocation and map both to stable GAP-07 error codes.
- [ ] Define fail-closed behavior for signing when KMS/HSM attestation, key state, key policy, or provider identity cannot be verified.
- [ ] Add request correlation and audit metadata without logging plaintext secrets, authentication tokens, sensitive provider response bodies, or complete artifact content.
- [ ] Support offline/edge verification using cached public keys/certificates while keeping private signing operations centralized or hardware-bound according to policy.
- [ ] Add provider health probes that test authorization and key metadata without producing unnecessary signatures or consuming rate-limited cryptographic operations.
- [ ] Test provider throttling, timeout, regional outage, permission denial, disabled key, scheduled deletion, version mismatch, HSM session exhaustion, and malformed provider responses.
- [ ] Document key creation ceremony, ownership, recovery constraints, backup policy, destruction policy, separation of duties, and provider-specific emergency controls.

### Acceptance gates
- [ ] No production private key is readable from process memory as raw key bytes by GAP-07 application code.
- [ ] Provider access is demonstrably least-privilege and tied to workload identity with auditable authorization records.
- [ ] Key rotation and version pinning are tested end to end without silent alias-based trust changes.
- [ ] KMS/HSM outage causes deterministic, observable, fail-closed behavior and does not fall back to local software keys.
- [ ] Provider integration passes security review and produces reproducible evidence of key protection level, IAM policy, and tested failure modes.

## 3. Public-Key / Certificate Trust Model

**Objective:** Establish explicit trust anchors, signer identity constraints, certificate/key validation rules, expiry handling, and trust-anchor lifecycle management.

### Engineering and security checklist
- [ ] Define whether trust is raw-public-key, X.509/PKIX, workload identity, Sigstore identity, or a constrained combination, and document the authoritative identity mapping.
- [ ] Define root and intermediate trust-anchor stores with immutable IDs, monotonic versions, activation timestamps, expiry, and retirement state.
- [ ] Implement certificate chain construction and validation using an approved library with deterministic handling of alternate paths and cross-signs.
- [ ] Enforce certificate/key usage constraints, Extended Key Usage where applicable, name/identity constraints, algorithm constraints, and path-length constraints.
- [ ] Define signer identity extraction rules from certificate SAN/subject/OIDC claims or raw-key metadata; do not authorize based on display-name strings alone.
- [ ] Validate certificate validity windows against trusted time and define bounded clock-skew policy.
- [ ] Implement revocation semantics using CRL/OCSP, provider status, transparency state, or estate revocation records as appropriate; specify offline behavior explicitly.
- [ ] Reject expired, not-yet-valid, revoked, weak-algorithm, untrusted-chain, malformed, or identity-mismatched credentials with distinct refusal reasons.
- [ ] Pin trust decisions to a trust-store generation so admission evidence identifies exactly which trust state authorized the artifact.
- [ ] Implement trust-anchor rotation with overlap windows, staged activation, rollback protection, and explicit removal of superseded anchors.
- [ ] Prevent namespace confusion between identical key IDs/certificate subjects in different tenants, sites, environments, or organizational trust domains.
- [ ] Define maximum certificate-chain length and encoded-size bounds to avoid path-building resource exhaustion.
- [ ] Add test chains for root/intermediate rotation, expired intermediates, wrong EKU, name-constraint violations, alternate chains, revoked leaf keys, and untrusted roots.
- [ ] Add cross-platform validation tests to ensure Windows/Linux/OpenSSL/platform stores do not create divergent trust outcomes.
- [ ] Produce human-readable trust reports that explain chain, identity, policy, and refusal reason without exposing sensitive credential material.

### Acceptance gates
- [ ] Every accepted signature maps to one unambiguous authorized signer identity and one recorded trust-store generation.
- [ ] Alternate certificate paths cannot broaden trust beyond explicitly configured anchors and constraints.
- [ ] Expiry and revocation behavior remains fail closed under disconnected operation according to documented staleness limits.
- [ ] Trust-anchor rotation is reversible only through explicitly authorized rollback procedure and cannot be triggered by stale snapshots.
- [ ] Independent PKI/trust review validates chain semantics, identity mapping, revocation, offline behavior, and rotation design.

## 4. DSSE / in-toto / SLSA Attestation Envelopes

**Objective:** Standardize provenance and attestation exchange using DSSE/in-toto/SLSA-compatible structures with strict predicate and builder-identity validation.

### Engineering and security checklist
- [ ] Select supported DSSE envelope and in-toto Statement versions and define exact SLSA provenance predicate version(s) accepted by policy.
- [ ] Implement canonical payload handling consistent with DSSE pre-authentication encoding and prohibit ad-hoc reserialization before signature verification.
- [ ] Validate `subject` entries against the admitted artifact digest and reject attestations that omit the target artifact or contain ambiguous digest sets.
- [ ] Validate predicate type before parsing predicate content; reject unknown or policy-disallowed predicate types.
- [ ] Model builder identity, build platform, invocation ID, build type, source/materials, dependencies, parameters, environment, and timestamps required by policy.
- [ ] Verify every material/source digest using approved algorithms and ensure source URI normalization cannot cause equivalent/non-equivalent confusion.
- [ ] Define policy rules for hermeticity, reproducibility, source completeness, parameter allowlists, external parameters, and build-service identity.
- [ ] Bind attestation signer authorization to the specific predicate/build type; a release signer must not automatically authorize arbitrary provenance predicates.
- [ ] Support multiple attestations while preventing contradictory or superseded provenance from being silently combined.
- [ ] Define attestation freshness and lifecycle semantics independently from immutable artifact-signature validity.
- [ ] Reject duplicate JSON keys, malformed Unicode, oversized arrays/maps, excessive nesting, and invalid numeric representations before semantic evaluation.
- [ ] Preserve original signed payload bytes for evidentiary reproduction while separately exposing parsed normalized fields to policy.
- [ ] Add conformance fixtures from multiple in-toto/SLSA producers and verify identical admission outcomes.
- [ ] Add negative fixtures for subject mismatch, builder mismatch, untrusted signer, missing materials, altered parameters, wrong predicate type, duplicate subjects, and malformed DSSE PAE inputs.
- [ ] Define migration behavior for future predicate/schema versions and require explicit policy enablement rather than permissive forward acceptance.

### Acceptance gates
- [ ] Admission can require a specific attestation predicate and builder identity in addition to an artifact signature.
- [ ] The verified attestation subject digest must exactly match the artifact being admitted.
- [ ] Unsupported or malformed DSSE/in-toto/SLSA input is refused without parser ambiguity or implicit downgrade.
- [ ] Cross-language producer/consumer fixtures pass using byte-identical DSSE verification semantics.
- [ ] Release evidence records the exact attestation schema/predicate versions, signer, digest, and policy decision.

## 5. Transparency-Log Client and Inclusion Verification

**Objective:** Verify that relevant signatures/attestations are anchored in an append-only transparency system using inclusion proofs and trusted checkpoints.

### Engineering and security checklist
- [ ] Define the supported transparency service(s), log identity, public verification keys, API version, entry types, and checkpoint format.
- [ ] Implement submission/query clients with authenticated TLS, bounded timeouts, retry policy, response-size limits, and explicit server identity validation.
- [ ] Verify Merkle inclusion proofs locally against a signed tree head/checkpoint rather than trusting a server-provided boolean result.
- [ ] Verify checkpoint signatures against pinned log keys and support controlled log-key rotation.
- [ ] Validate entry canonicalization and ensure the transparency entry cryptographically corresponds to the exact artifact signature/attestation under evaluation.
- [ ] Implement consistency-proof verification between previously trusted and newly observed tree heads to detect equivocation/rollback where supported.
- [ ] Cache trusted checkpoints for offline sites with monotonic tree-size enforcement and signed cache metadata.
- [ ] Define maximum checkpoint age/staleness acceptable for each environment and artifact risk class.
- [ ] Detect and refuse smaller/older tree heads unless an explicitly authorized recovery process establishes a new trust anchor.
- [ ] Define behavior for transparency outage separately for signing, publication, verification, and disconnected admission.
- [ ] Record log entry index/UUID, tree size, checkpoint digest, inclusion-proof digest, and verification timestamp in admission evidence.
- [ ] Rate-limit and batch transparency queries to prevent an attacker from amplifying admission traffic into dependency exhaustion.
- [ ] Test malformed proofs, wrong leaf hash, wrong log key, stale checkpoints, inconsistent checkpoints, duplicate entries, unavailable log, and corrupted cache.
- [ ] Implement monitor/auditor hooks for detecting split-view indicators or checkpoint divergence across sites.
- [ ] Document emergency operation when the log is unavailable, including whether admission halts or uses bounded cached evidence under policy.

### Acceptance gates
- [ ] A required transparency-backed artifact is accepted only after local cryptographic verification of its inclusion proof against a trusted checkpoint.
- [ ] Checkpoint rollback and invalid consistency proofs are detected and surfaced as security events.
- [ ] Offline verification uses only signed, age-bounded, rollback-protected cached checkpoints.
- [ ] Transparency dependency outages cannot silently degrade into “verification skipped.”
- [ ] Inclusion/checkpoint evidence is persisted with the admission decision and can be re-verified independently.

## 6. Durable Trust-Store Persistence

**Objective:** Persist trust state transactionally with integrity, rollback protection, backup/restore, corruption detection, and deterministic recovery.

### Engineering and security checklist
- [ ] Define a versioned persistent trust-store schema covering signers, key IDs, trust anchors, revocations, activation windows, policy references, and metadata provenance.
- [ ] Use transactional storage semantics so partially written trust updates never become visible to verifiers.
- [ ] Persist a monotonic generation/version and reject activation of lower generations except through an audited emergency recovery workflow.
- [ ] Sign or MAC trust-store snapshots with a separately managed configuration-authority key and verify before load/activation.
- [ ] Add cryptographic content digests for persisted records and detect corruption before exposing state to the verification path.
- [ ] Separate active, staged, historical, and quarantined trust configurations so rollback/reference data cannot accidentally become authoritative.
- [ ] Implement crash-safe atomic replacement using fsync/transaction commit semantics appropriate to the selected database/filesystem.
- [ ] Define locking/snapshot semantics for concurrent readers and writers; verification must observe one coherent trust generation.
- [ ] Bound database/file sizes and reject pathological or attacker-controlled trust entries that can exhaust memory or CPU at startup.
- [ ] Encrypt sensitive trust metadata at rest if it includes internal identities or operational details requiring confidentiality; integrity is mandatory regardless.
- [ ] Implement backup with snapshot signatures, generation metadata, retention, restore validation, and protection against restoring stale compromised state.
- [ ] Implement startup self-check that validates schema, signature, digest, generation, revocation consistency, and referential integrity before marking ready.
- [ ] Test abrupt power loss/kill during update, disk-full, truncated files, bit corruption, schema mismatch, duplicate IDs, stale restore, and concurrent verification.
- [ ] Provide deterministic export/import tooling that preserves signed representation and does not reserialize away evidentiary fields.
- [ ] Record every trust mutation in the audit ledger with actor, reason, previous generation, new generation, and configuration digest.

### Acceptance gates
- [ ] A crash at any point during trust update leaves either the prior valid generation or the complete new generation active—never a partial mix.
- [ ] Corrupted, unsigned, or rolled-back trust state prevents readiness/admission rather than silently reconstructing defaults.
- [ ] Backup/restore drills prove integrity, monotonicity, and expected recovery-point/recovery-time behavior.
- [ ] Concurrent verification observes atomic snapshots with no mixed-generation authorization decisions.
- [ ] Persistent-state format and recovery behavior are documented and covered by repeatable automated tests.

## 7. Trust-Store Distribution Protocol

**Objective:** Distribute signed trust snapshots/deltas safely to connected and disconnected sites with anti-rollback, staleness limits, and reconnect reconciliation.

### Engineering and security checklist
- [ ] Define signed snapshot and delta formats with schema version, trust generation, parent generation, issue time, expiry/max-staleness, tenant/site scope, and content digest.
- [ ] Sign distribution objects with a dedicated configuration-authority identity distinct from artifact release signers.
- [ ] Require monotonic generation acceptance and exact parent matching for deltas; reject gaps unless a full signed snapshot is fetched.
- [ ] Define deterministic ordering for multiple concurrent updates and prohibit ambiguous branch activation.
- [ ] Implement authenticated transport with certificate/workload identity validation and bounded payload sizes.
- [ ] Support disconnected-site caches with explicit expiry/staleness budgets by environment/risk class.
- [ ] Define fail-closed behavior once offline trust exceeds its maximum age and distinguish “temporarily stale” from “security-invalid.”
- [ ] Reconcile reconnecting sites by comparing active generation/checkpoint and fetching the minimum safe snapshot/delta chain.
- [ ] Prevent a compromised relay/cache from rolling a site backward by validating signatures, generation, parentage, and trusted-time constraints locally.
- [ ] Support urgent revocation distribution that can preempt ordinary update cadence and measure end-to-end propagation time.
- [ ] Add authenticated acknowledgements/telemetry so the control plane can identify which sites have activated each generation.
- [ ] Make activation atomic and preserve prior generation for forensic comparison without allowing automatic rollback.
- [ ] Test duplicate delivery, reordered deltas, missing deltas, stale snapshots, malicious relay, partition, long offline interval, reconnect storm, and control-plane failover.
- [ ] Define bootstrap trust for a new/rebuilt site and require out-of-band or otherwise strongly authenticated initial trust anchor installation.
- [ ] Generate distribution evidence recording publisher, generation, scope, issuance/expiry, recipient site, activation result, and local verification digest.

### Acceptance gates
- [ ] No unsigned, stale, out-of-order, wrong-scope, or rolled-back trust configuration can become active at a site.
- [ ] Disconnected sites enforce documented staleness limits and transition predictably when those limits expire.
- [ ] Emergency revocation reaches connected sites within the declared SLO and produces measurable acknowledgements.
- [ ] Reconnect reconciliation cannot skip required generations or accept divergent trust branches silently.
- [ ] Bootstrap and recovery procedures establish trust without depending on the untrusted distribution channel itself.

## 8. Policy-Engine Adapter (GAP-13)

**Objective:** Resolve all authorization requirements from GAP-13 policy rather than hard-coded verifier assumptions, while keeping policy evaluation deterministic and fail closed.

### Engineering and security checklist
- [ ] Define a versioned policy query contract containing artifact digest, kind, environment, tenant/site, signer identity, key ID, algorithm, provenance facts, SBOM/vulnerability facts, transparency state, and trust generation.
- [ ] Define a versioned decision contract containing allow/deny, stable reason codes, required signer roles, allowed keys/algorithms, threshold rules, freshness, predicate requirements, and exception metadata.
- [ ] Pin each admission decision to an immutable policy bundle digest/version and record it in audit evidence.
- [ ] Validate policy bundle signatures and scope before activation; reject unsigned or stale policy state.
- [ ] Ensure policy evaluation has deterministic semantics for missing attributes, unknown enum values, multiple matching rules, and conflict resolution.
- [ ] Default missing/unknown security-critical policy fields to deny rather than permissive behavior.
- [ ] Separate policy authoring from policy enforcement and enforce least-privilege identities for publishing/activating policy.
- [ ] Implement bounded evaluation time, recursion/depth, rule count, and external-data access so policy cannot become a verification DoS primitive.
- [ ] Prohibit network-dependent policy lookups in the final admission path unless explicitly designed with deterministic failure and caching semantics.
- [ ] Model exceptions/waivers as signed, scoped, time-bounded policy objects with owner, justification, issue/expiry time, and compensating controls.
- [ ] Add differential tests for code/bundle/Wasm/microVM/provider artifact kinds and for development/staging/production environment distinctions.
- [ ] Add negative tests for unauthorized signer role, wrong key, deprecated algorithm, stale signature, missing provenance, failed vulnerability gate, and expired exception.
- [ ] Version the adapter independently so incompatible GAP-13 schema changes fail explicitly rather than misinterpreting fields.
- [ ] Emit structured policy trace/evidence sufficient to explain which rule authorized/refused the artifact without leaking restricted policy internals.
- [ ] Test policy-engine outage, stale cache, corrupt bundle, version skew, conflicting rules, and disconnected operation.

### Acceptance gates
- [ ] No production admission requirement remains hard-coded when it is intended to be centrally governed by GAP-13.
- [ ] Every allow/deny result is reproducible from recorded artifact facts, trust generation, and policy bundle digest.
- [ ] Policy unavailability or incompatibility cannot silently fall back to permissive local defaults.
- [ ] Exceptions are narrow, signed, expiring, auditable, and cannot override controls outside their declared scope.
- [ ] End-to-end GAP-07/GAP-13 conformance tests cover both allowed and adversarial policy scenarios.

## 9. Artifact Registry / OCI Integration

**Objective:** Verify container/OCI indexes and manifests, Wasm modules/components, microVM images, provider bundles, and detached signatures at registry pull/admission boundaries.

### Engineering and security checklist
- [ ] Define supported registry protocols, OCI Distribution/Artifacts versions, media types, manifest/index types, and artifact-specific verification profiles.
- [ ] Resolve tags to immutable digests before policy evaluation; never authorize a mutable tag without binding the resulting digest.
- [ ] Verify manifest/index digests and recursively validate referenced manifests/layers/config blobs according to artifact policy.
- [ ] Detect and reject digest-algorithm mismatch, malformed descriptors, duplicate/ambiguous descriptors, oversized manifests, and unsupported media types.
- [ ] Define signature/attestation discovery using OCI referrers or approved detached-signature conventions without trusting tag naming alone.
- [ ] Bind signatures and attestations to the exact manifest/index/artifact digest under admission.
- [ ] Handle multi-platform indexes by validating the selected child manifest and preserving parent-index association in evidence.
- [ ] Define Wasm component/module and microVM image digest boundaries precisely so runtime-transformed bytes cannot bypass verification.
- [ ] Authenticate registry transport and credentials using least-privilege pull identities; do not expose registry secrets to verifier logs.
- [ ] Implement streamed hashing of large blobs and short-circuit on size/policy violations before full materialization.
- [ ] Prevent TOCTOU by using digest-addressed pulls/content stores after verification and by rechecking digest at runtime handoff.
- [ ] Integrate SBOM/provenance/transparency discovery with the same immutable artifact digest and registry namespace.
- [ ] Test registry partial reads, manifest substitution, tag mutation, wrong referrer, foreign layer, nested index, digest collision simulation, and authentication failure.
- [ ] Add local content-cache rules so cached artifacts retain verification evidence and are re-evaluated when trust/policy changes require it.
- [ ] Record registry, repository, immutable digest, selected platform, manifest media type, verification results, and evidence references in admission audit.

### Acceptance gates
- [ ] Production admission operates on immutable digests, not mutable tags or human-readable names.
- [ ] Artifact bytes handed to the runtime have the same digest that was verified and policy-authorized.
- [ ] Required signatures/attestations are discovered and verified using standards-based or explicitly versioned registry metadata.
- [ ] Registry/cache failures and malformed artifacts are fail closed with bounded resource use.
- [ ] End-to-end tests cover OCI image/index, Wasm, microVM, and provider-bundle artifact classes used by the estate.

## 10. Production Admission Hook

**Objective:** Enforce GAP-07 verification in the deployment/runtime admission path so alternate artifact routes cannot bypass signature, provenance, trust, or policy checks.

### Engineering and security checklist
- [ ] Enumerate every artifact execution/install/deploy path in scope, including orchestrator admission, direct runtime API, local cache, side-loading, rollback, recovery, and operator tooling.
- [ ] Insert verification before any artifact can become executable, loadable, mountable, installable, or eligible for scheduling.
- [ ] Use immutable digest identity through the entire admission handoff and prohibit post-verification tag/path substitution.
- [ ] Require the admission hook to consume signed trust/policy generations and record them in the decision artifact.
- [ ] Define stable allow/deny/defer/error outcomes and ensure infrastructure treats deny/error as non-runnable.
- [ ] Prevent privileged operators or alternate APIs from bypassing admission unless an explicit break-glass workflow is used and audited.
- [ ] Revalidate cached artifacts when relevant trust, revocation, policy, vulnerability, or required-attestation state changes.
- [ ] Define rollback semantics: prior artifacts must still satisfy current or explicitly versioned rollback policy rather than being assumed safe because they once ran.
- [ ] Protect admission-decision cache entries with artifact digest, policy digest, trust generation, timestamp, environment, and scope; reject stale/mismatched cache hits.
- [ ] Bound verification concurrency and queue depth so overload cannot cause the orchestrator to skip checks.
- [ ] Expose readiness separately from liveness; a verifier without current trust/policy/time dependencies must not advertise admission readiness.
- [ ] Add audit correlation from deployment request through verification result to runtime instance/workload identity.
- [ ] Test side-load attempts, cache poisoning, race between verify and execute, mutable tag changes, emergency rollback, privileged API path, and verifier restart.
- [ ] Validate admission behavior under dependency outage, network partition, stale trust, stale policy, KMS/log outage, and disk pressure.
- [ ] Document the only authorized execution paths and continuously test for configuration drift that reopens bypass routes.

### Acceptance gates
- [ ] No supported production execution path can run an artifact without a GAP-07 admission decision or explicitly audited break-glass decision.
- [ ] TOCTOU tests prove the executed artifact digest equals the verified digest.
- [ ] Admission errors never become implicit allows.
- [ ] Cached decisions are invalidated correctly on security-state changes.
- [ ] Penetration/adversarial tests confirm alternate deployment paths cannot bypass enforcement.

## 11. Persistent Tamper-Evident Audit Export / Anchoring

**Objective:** Export the local `AuditLedger` to durable append-only storage or an external transparency anchor so security events survive host compromise and can be independently verified.

### Engineering and security checklist
- [ ] Define an append-only audit event schema with event ID, sequence, previous hash, timestamp, actor/workload identity, action, object IDs, reason codes, and evidence digests.
- [ ] Preserve the existing local hash-chain semantics when exporting; verify chain continuity before accepting batches into durable storage.
- [ ] Select WORM/object-lock/database-ledger/transparency storage with retention controls appropriate to security and compliance requirements.
- [ ] Authenticate exporters and collectors with mutually authenticated workload identity and least-privilege append-only permissions.
- [ ] Prevent an application identity from deleting or rewriting previously committed audit records.
- [ ] Anchor periodic chain heads into an independent trust domain so later local-history rewrite can be detected.
- [ ] Define sequence/gap handling and refuse to mark export healthy when expected events are missing or reordered.
- [ ] Spool locally during collector outage using bounded, integrity-protected storage with backpressure and disk-full behavior.
- [ ] Encrypt audit transport and sensitive fields at rest while retaining verifiability of chain digests and event identity.
- [ ] Define redaction/tokenization rules so logs contain necessary security evidence without secret key material, credentials, or prohibited artifact content.
- [ ] Implement retention, legal hold, archive, and destruction procedures while preserving chain-verification metadata.
- [ ] Provide an independent verifier that can recompute event-chain hashes and validate external anchors/checkpoints.
- [ ] Add scheduled integrity jobs that verify chain continuity, anchor freshness, expected ingestion rate, and WORM retention state.
- [ ] Test collector outage, duplicate batch, reordered batch, missing event, tampered event, disk-full, exporter restart, clock skew, and credential rotation.
- [ ] Correlate audit records with policy/trust/signature/provenance evidence using immutable IDs rather than fragile text matching.

### Acceptance gates
- [ ] Compromise of a GAP-07 node cannot silently erase or rewrite already anchored audit history.
- [ ] Independent tooling can verify the complete exported chain and detect gaps/tampering.
- [ ] Export outage is observable, bounded by local spool capacity, and never silently drops security events.
- [ ] Retention and access controls are tested against the stated compliance/incident-response requirements.
- [ ] Release/admission investigations can reconstruct who authorized what, under which trust/policy state, with cryptographically linked evidence.

## 12. Trusted-Time Integration

**Objective:** Supply a trustworthy time basis for certificate validity, signature freshness, revocation age, transparency checkpoint staleness, policy expiry, and disconnected-site anti-rollback logic.

### Engineering and security checklist
- [ ] Define authoritative time sources for connected and disconnected deployments, such as authenticated NTP/NTS, secure platform clock, TPM time, PTP with authentication, or signed time attestations.
- [ ] Distinguish wall-clock time from monotonic process time and use each only for semantics it can safely support.
- [ ] Track source quality, synchronization state, estimated error/uncertainty, last successful sync, and trust status.
- [ ] Define maximum tolerated clock offset/uncertainty for certificate validity, signature freshness, policy expiry, and transparency staleness independently.
- [ ] Refuse freshness-sensitive admission when time trust/uncertainty exceeds policy limits rather than assuming local wall clock is correct.
- [ ] Detect backwards wall-clock jumps and prevent them from extending certificate, trust snapshot, policy, or exception validity.
- [ ] Detect implausible forward jumps and avoid prematurely expiring the fleet without operator-visible diagnostics and recovery procedure.
- [ ] Persist sufficient monotonic/last-trusted-time state across restart to detect rollback where hardware/platform support permits.
- [ ] Namespace time attestations by site/device and validate their signer, sequence, issue time, expiry, and anti-replay fields.
- [ ] Define disconnected-site maximum offline duration and how local secure-clock drift affects admissibility.
- [ ] Integrate trusted-time state into readiness and expose stable refusal reasons such as `TIME_UNTRUSTED`, `TIME_STALE`, or `CLOCK_ROLLBACK`.
- [ ] Record time source, uncertainty, and trusted timestamp used for every freshness/expiry-sensitive admission decision.
- [ ] Test NTP spoofing simulation, time source loss, backward/forward jumps, reboot, RTC reset, long offline period, leap-second handling, and source failover.
- [ ] Ensure tests can inject deterministic time through an explicit clock abstraction without exposing a production runtime override.
- [ ] Document operator recovery for lost/invalid secure time without weakening anti-rollback or expiry controls.

### Acceptance gates
- [ ] Freshness and expiry decisions are based only on a time source whose trust/uncertainty satisfies policy.
- [ ] Clock rollback cannot extend expired trust, certificates, exceptions, or signatures.
- [ ] Loss of trusted time produces deterministic fail-closed behavior for controls that depend on it.
- [ ] Disconnected operation has explicit, tested time-staleness limits.
- [ ] Admission evidence records enough time-source metadata to reproduce why a freshness decision was accepted or refused.

---

# P1 — High-Priority Hardening and Operations

## 13. Multi-Signature / Threshold Authorization

**Objective:** Require M-of-N approvals or independent counter-signatures for high-risk artifact classes and release operations without collapsing multiple approvals into one trust identity.

### Engineering and security checklist
- [ ] Define threshold policy semantics by artifact kind, environment, risk class, tenant, release channel, and emergency mode.
- [ ] Model each signer as an independent identity/key with role, organizational boundary, authorization scope, and validity interval.
- [ ] Define whether threshold evaluation counts unique signer identities, unique keys, unique organizations, or a combination; prohibit one principal from satisfying multiple slots unintentionally.
- [ ] Bind all signatures in a threshold set to the same immutable artifact digest, kind, environment, provenance statement, and release context.
- [ ] Define a canonical multi-signature bundle format with deterministic ordering or order-independent evaluation semantics.
- [ ] Reject duplicate signatures, duplicate signer identities, superseded signatures, incompatible envelope versions, and signatures over non-identical contexts.
- [ ] Support required-role compositions such as `build + security + release` in addition to numeric M-of-N thresholds.
- [ ] Enforce independence constraints so delegated/derived credentials cannot satisfy nominally separate reviewer roles when policy forbids it.
- [ ] Define threshold behavior when one signer/key is revoked after release and whether re-authorization is required for continued admission.
- [ ] Support staged/counter-signature workflows without allowing an earlier partial bundle to be mistaken for final authorization.
- [ ] Record each signer decision, timestamp, key, policy role, and verification result in admission evidence.
- [ ] Add negative tests for one signer signing twice, same key under aliases, mixed artifact digests, wrong role combinations, revoked signer, stale signature, and threshold downgrade.
- [ ] Add policy tests proving low-risk artifacts can use narrower thresholds only where explicitly authorized.
- [ ] Add concurrency tests for simultaneous approvals and deterministic bundle finalization.
- [ ] Document approval ceremony, signer separation of duties, substitution rules, and emergency quorum handling.

### Acceptance gates
- [ ] High-risk artifacts cannot satisfy production policy with fewer than the configured independent approvals.
- [ ] Duplicate/aliased signer identities cannot inflate quorum counts.
- [ ] Every counted signature is bound to the identical artifact and authorization context.
- [ ] Threshold policy changes are signed, versioned, audited, and cannot retroactively weaken historical evidence.
- [ ] End-to-end release tests cover normal quorum, missing approver, revoked approver, and emergency-policy paths.

## 14. Key-Compromise Workflow

**Objective:** Provide a tested incident workflow for emergency revocation, impact discovery, quarantine, re-sign/rebuild, and preservation of forensic evidence after signer/key compromise.

### Engineering and security checklist
- [ ] Define compromise severity classes and triggers for suspected, confirmed, scoped, and systemic key compromise.
- [ ] Maintain reverse indexes from signer/key IDs to signed artifacts, attestations, releases, environments, sites, and admission decisions.
- [ ] Implement emergency key/signer revocation with signed authority, monotonic generation, reason code, incident ID, and effective time.
- [ ] Propagate revocation through the trust distribution path with priority over routine updates.
- [ ] Define whether revocation invalidates historical artifacts immediately, at next deployment, on restart, or according to risk-specific policy.
- [ ] Automatically identify potentially affected artifacts using signature and provenance evidence rather than repository names or tags.
- [ ] Integrate quarantine so artifacts signed by compromised identities can be prevented from new execution while evidence is preserved.
- [ ] Define re-sign versus rebuild criteria; do not re-sign artifacts whose build/provenance integrity cannot be independently re-established.
- [ ] Require new keys to use distinct IDs/versions and prohibit restoring a compromised key ID to active state without explicit exceptional procedure.
- [ ] Preserve original compromised signatures, attestations, trust state, and audit records for investigation while clearly marking them revoked.
- [ ] Define KMS/HSM provider actions such as disable, revoke grant, rotate alias, destroy schedule, and evidence capture.
- [ ] Add automated blast-radius reports with confidence/status and explicit unknown/unindexed artifacts.
- [ ] Test compromise of active key, retired key, intermediate CA, trust-distribution authority, multi-sig participant, and transparency identity.
- [ ] Conduct incident simulations measuring detection-to-revocation, revocation-to-fleet-activation, quarantine completion, and recovery time.
- [ ] Define incident closure criteria including key destruction/retirement evidence, affected-artifact disposition, postmortem, and control improvements.

### Acceptance gates
- [ ] A compromised signer/key can be revoked globally without shipping a new application build.
- [ ] The system can enumerate known affected artifacts and admission events from cryptographic evidence.
- [ ] Revocation propagation meets the defined fleet SLO and produces gap/escalation alarms where it does not.
- [ ] Recovery does not reuse compromised key material or silently trust previously affected artifacts.
- [ ] Incident exercises produce complete, immutable evidence suitable for independent review.

## 15. Artifact Quarantine Service

**Objective:** Isolate failed, unknown, revoked, or suspicious artifacts from execution while retaining evidence needed for triage and forensic analysis.

### Engineering and security checklist
- [ ] Define quarantine states such as `pending`, `verification_failed`, `revoked`, `policy_denied`, `malformed`, `under_investigation`, `released`, and `destroyed`.
- [ ] Use artifact digest as the primary identity and retain original registry/source metadata as non-authoritative context.
- [ ] Prevent quarantined artifacts from being mounted, loaded, executed, deployed, promoted, or reintroduced through cache aliases.
- [ ] Store quarantine reason codes, failed checks, trust/policy generations, signer/provenance details, source location, and first/last-seen timestamps.
- [ ] Preserve artifact bytes or references according to forensic retention policy while preventing unauthorized retrieval/execution.
- [ ] Enforce least-privilege access and separation between quarantine reviewers and release authorities.
- [ ] Define cryptographically authorized release-from-quarantine workflow with reason, approvers, scope, and expiry where temporary.
- [ ] Re-run current verification/policy before release; prior manual review must not bypass newly applicable revocation/policy state.
- [ ] Deduplicate repeated observations of the same digest while preserving occurrence metadata and attempted deployment targets.
- [ ] Bound quarantine storage and define pressure behavior that never frees suspicious evidence silently.
- [ ] Integrate malware/vulnerability/forensic tooling through read-only or sandboxed interfaces without granting execution privileges on production nodes.
- [ ] Emit high-severity alerts for repeated blocked executions, cross-site spread, or reappearance after revocation.
- [ ] Test cache alias bypass, rename/tag changes, digest reappearance, quarantine-service outage, storage full, concurrent release/delete, and operator misuse.
- [ ] Define chain-of-custody evidence for artifact acquisition, access, analysis, transfer, and disposition.
- [ ] Document legal/compliance retention constraints and secure destruction requirements where applicable.

### Acceptance gates
- [ ] A quarantined digest cannot execute through any supported artifact path.
- [ ] Quarantine retains enough immutable verification/context evidence to reproduce the original refusal.
- [ ] Release requires authenticated authorization plus revalidation under current trust/policy state.
- [ ] Storage pressure and service outage fail safely without losing or executing quarantined artifacts.
- [ ] Audit records provide end-to-end chain of custody for every quarantined artifact.

## 16. SBOM Verification and Policy Binding

**Objective:** Cryptographically associate SPDX/CycloneDX SBOMs with artifacts, validate their authenticity/completeness, and expose package/vulnerability facts to admission policy.

### Engineering and security checklist
- [ ] Define accepted SBOM standards/versions, encodings, digest algorithms, and profile requirements for each artifact class.
- [ ] Require SBOM subject identity to resolve to the exact artifact digest rather than a mutable package name/version alone.
- [ ] Verify SBOM signature/attestation using an authorized SBOM producer identity distinct from arbitrary release signers if policy requires separation.
- [ ] Validate SPDX/CycloneDX schema and semantic constraints with strict parser bounds and duplicate-key handling.
- [ ] Require component package URLs/CPEs/hashes where available and define policy for unidentified/unversioned dependencies.
- [ ] Validate file/package digests or build-derived completeness attestations where the SBOM generation method supports them.
- [ ] Correlate vulnerability results to immutable SBOM/component versions and record vulnerability database snapshot/version/time.
- [ ] Define admission policy for severity, exploitability, known-exploited status, fix availability, waivers, and age of vulnerability data.
- [ ] Model SBOM exceptions as signed, scoped, expiring policy objects rather than annotations embedded in the SBOM itself.
- [ ] Detect conflicting SBOMs for the same artifact and define authoritative-selection or deny semantics.
- [ ] Preserve original signed SBOM plus normalized package graph separately so parser upgrades do not mutate evidence.
- [ ] Add negative tests for artifact mismatch, unsigned SBOM, untrusted generator, altered component, malformed package IDs, stale vulnerability data, and expired waiver.
- [ ] Test very large SBOMs with bounded memory/CPU and streaming or incremental parsing where required.
- [ ] Record SBOM digest, generator identity, schema version, vulnerability snapshot, policy result, and waiver IDs in admission evidence.
- [ ] Define regeneration/reverification rules when vulnerability intelligence changes without artifact bytes changing.

### Acceptance gates
- [ ] Required SBOMs are cryptographically bound to the exact admitted artifact.
- [ ] Policy can deterministically deny/allow based on verified dependency and vulnerability facts.
- [ ] Stale/missing vulnerability state is handled explicitly and cannot silently become “clean.”
- [ ] Waivers are signed, scoped, expiring, and auditable.
- [ ] The release evidence bundle can reproduce the SBOM/vulnerability decision made at admission time.

## 17. Provenance-to-Artifact Association Format

**Objective:** Define a canonical bundle/index that binds artifact digest, signatures, provenance, SBOM, vulnerability attestations, transparency evidence, and policy result into one unambiguous evidence graph.

### Engineering and security checklist
- [ ] Define a versioned association schema with one immutable artifact digest as the root subject.
- [ ] Represent each evidence object by content digest, media/type identifier, schema version, producer/signer identity, and retrieval location if external.
- [ ] Distinguish required, optional, superseded, and informational evidence references.
- [ ] Prevent cycles or ambiguous parentage in the evidence graph unless explicitly modeled and safely bounded.
- [ ] Define canonical ordering/serialization or content-address each object so association integrity does not depend on map/list ordering.
- [ ] Sign the association index or embed it in a signed/attested envelope with explicit domain separation.
- [ ] Validate that every signature, provenance statement, SBOM, vulnerability attestation, and transparency entry resolves back to the same root artifact subject.
- [ ] Define multi-platform/multi-artifact release bundles without allowing one valid child artifact to authorize unrelated siblings.
- [ ] Support multiple signatures/attestations of the same type with deterministic policy selection and conflict detection.
- [ ] Model evidence freshness independently so mutable security intelligence can be refreshed while immutable build evidence remains stable.
- [ ] Add size/count/depth limits and reject dangling references, duplicate object IDs, unknown critical types, and hash mismatches.
- [ ] Support offline packaging of all required verification evidence with integrity-protected manifests.
- [ ] Add round-trip interoperability tests across supported languages/tools and registries.
- [ ] Record which association schema and object digests were evaluated in every admission decision.
- [ ] Define migration rules that preserve historical verification of older bundle versions without implicitly accepting weaker semantics for new releases.

### Acceptance gates
- [ ] One association bundle deterministically identifies all security evidence required to evaluate a specific artifact digest.
- [ ] Evidence for one artifact cannot be substituted into another artifact’s bundle without detection.
- [ ] Conflicting or missing required evidence yields explicit denial/refusal.
- [ ] Offline verification can reproduce the same association graph without registry-specific naming conventions.
- [ ] Schema migration and backward verification are covered by conformance vectors.

## 18. Canonical Serialization Interoperability Tests

**Objective:** Prove that JSON/CBOR/Protobuf/DSSE or other selected encodings produce identical security semantics across languages, parsers, runtimes, and platforms.

### Engineering and security checklist
- [ ] Inventory every serialized security object and identify which bytes are signed versus which are parsed then canonicalized.
- [ ] Document canonicalization rules for object-key ordering, Unicode normalization, numbers, booleans/null, binary encoding, timestamps, and duplicate keys.
- [ ] Prefer standardized canonical encodings where available; do not rely on runtime-specific dictionary ordering or floating-point formatting.
- [ ] Build golden byte vectors for valid signatures, provenance links, policy facts, trust snapshots, DSSE envelopes, and evidence bundles.
- [ ] Generate golden parse trees/semantic objects alongside bytes so tests detect both byte and interpretation divergence.
- [ ] Test multiple independent implementations/languages used by the estate against the same vector corpus.
- [ ] Include adversarial Unicode such as combining characters, noncharacters, homoglyphs, invalid sequences, and normalization edge cases.
- [ ] Include numeric edge cases such as leading zero, exponent notation, negative zero, overflow-sized integers, NaN/Infinity rejection, and precision boundaries.
- [ ] Include duplicate JSON object keys and require deterministic rejection rather than “first wins/last wins” divergence.
- [ ] Include map/list reordering, whitespace, escaped characters, alternate binary/base encodings, and non-canonical CBOR encodings.
- [ ] Test schema-version mismatch and unknown critical fields across old/new readers.
- [ ] Require parsers to preserve signed raw payload bytes where the signature scheme authenticates the transport representation.
- [ ] Add differential fuzzing comparing parse/verify outcomes across implementations.
- [ ] Run interoperability vectors in CI for every supported runtime/library upgrade.
- [ ] Version the corpus and archive exact toolchain/library versions used to produce each golden vector.

### Acceptance gates
- [ ] All supported implementations agree on accept/refuse outcome for every conformance vector.
- [ ] No duplicate-key, Unicode, numeric, or encoding ambiguity produces divergent security decisions.
- [ ] Signed-byte semantics are never altered by parse-and-reserialize behavior unless the specification explicitly requires canonicalization.
- [ ] Runtime/library upgrades cannot merge without passing the full interoperability corpus.
- [ ] Corpus results are archived as release evidence with implementation and dependency versions.

## 19. Algorithm-Agility Policy

**Objective:** Govern cryptographic algorithm approval, deprecation, transition, compliance constraints, and downgrade resistance without hard-coding one permanent algorithm set.

### Engineering and security checklist
- [ ] Maintain a signed algorithm registry with stable IDs, approved usage, minimum key parameters, hash requirements, compliance tags, and lifecycle status.
- [ ] Model states such as `preferred`, `approved`, `legacy-verify-only`, `deprecated`, and `prohibited` with activation/deadline timestamps.
- [ ] Allow policy to vary by artifact class, environment, tenant, jurisdiction/compliance boundary, and signer role.
- [ ] Require signature envelopes to identify the algorithm explicitly and cross-check it against actual key type/parameters.
- [ ] Reject algorithm/key mismatches and unknown algorithm IDs before expensive verification.
- [ ] Prevent downgrade by binding algorithm identifiers into signed context and policy decision evidence.
- [ ] Define dual-signing transition windows for algorithm migration and exact rules for when both/one signature is required.
- [ ] Define FIPS or other compliance-mode requirements by deployment and ensure crypto providers are validated/configured accordingly where mandated.
- [ ] Track crypto-library/provider versions and security advisories that can force an algorithm/provider status change.
- [ ] Model post-quantum/hybrid migration capability without pre-authorizing unspecified future algorithms.
- [ ] Define emergency algorithm disable that can propagate through signed policy/trust state without application redeployment.
- [ ] Test deprecated/prohibited algorithm refusal, legacy verification boundaries, dual-signing transition, wrong key size, and provider mismatch.
- [ ] Ensure cached admission decisions are invalidated when algorithm policy changes materially.
- [ ] Emit telemetry for algorithm usage so remaining legacy signatures can be measured before cutoff.
- [ ] Document migration playbooks with signer/key rollout, trust update, dual-sign phase, cutoff, and cleanup.

### Acceptance gates
- [ ] Algorithm acceptance is policy-controlled and auditable rather than inferred from library support.
- [ ] A prohibited algorithm is rejected even if the crypto library can technically verify it.
- [ ] Transition periods can require dual signatures without ambiguity over which policy generation applied.
- [ ] Emergency deprecation can be propagated safely and observed fleet-wide.
- [ ] Release evidence records algorithm IDs, key parameters, provider/compliance mode, and governing policy version.

## 20. Replay Cache / Nonce Support for Online Protocols

**Objective:** Prevent replay of one-time or session-bound authorization/signing requests where immutable artifact verification alone does not provide sufficient anti-replay semantics.

### Engineering and security checklist
- [ ] Identify protocol surfaces that are replay-sensitive, separating immutable artifact signatures from online authorization/signing transactions.
- [ ] Define nonce/challenge entropy, length, namespace, encoding, issuance authority, scope, and expiration semantics.
- [ ] Bind nonce, requester identity, operation type, artifact digest, environment, policy context, and expiry into the signed/authorized request.
- [ ] Use cryptographically secure random generation for unpredictable challenges and prohibit timestamp-only nonce construction.
- [ ] Store consumed nonces/replay tokens transactionally with atomic check-and-set semantics.
- [ ] Namespace replay state by tenant/site/protocol so identical values in independent domains cannot collide.
- [ ] Define cache TTL and capacity from maximum allowed replay window plus clock uncertainty.
- [ ] Bound replay-cache memory/storage and fail closed or shed safely rather than evicting still-valid entries silently.
- [ ] Protect distributed replay caches against stale replicas; choose strong consistency or scope challenges to a single authoritative verifier.
- [ ] Define behavior across process restart and failover so a restart cannot reset one-time authorization state prematurely.
- [ ] Reject reused, expired, malformed, wrong-scope, wrong-requester, and future-issued challenges with stable error codes.
- [ ] Avoid logging full bearer-like tokens/nonces where log exposure could enable replay before consumption.
- [ ] Test concurrent duplicate requests, race conditions, cache failover, clock skew, cache saturation, restart, and network partition.
- [ ] Add metrics for replay refusals, cache utilization, expired challenges, and synchronization failures without high-cardinality raw nonce labels.
- [ ] Document which protocols intentionally do not use replay state and why immutable signed-object semantics are sufficient there.

### Acceptance gates
- [ ] The same one-time authorization cannot succeed twice, including under concurrency and failover.
- [ ] Replay protection survives restart/failover for the full configured replay window.
- [ ] Cache pressure does not silently weaken anti-replay guarantees.
- [ ] Nonces are cryptographically bound to requester, operation, artifact, and scope where applicable.
- [ ] Replay-cache behavior is covered by race, failure, and adversarial tests.

## 21. Tenant Namespace Isolation

**Objective:** Prevent signer, key, trust-root, policy, artifact, and evidence collisions across tenants, sites, environments, and administrative domains.

### Engineering and security checklist
- [ ] Define a canonical namespace model covering tenant, organization, site, environment, trust domain, and artifact scope.
- [ ] Require every signer identity, key ID, trust anchor, policy bundle, artifact reference, and admission decision to carry explicit namespace context.
- [ ] Prevent global lookup by short/unqualified signer or key IDs in production paths.
- [ ] Define canonical namespace encoding and comparison semantics, including case sensitivity, Unicode normalization, reserved characters, and maximum lengths.
- [ ] Bind namespace identifiers into signed/attested messages whenever cross-namespace replay would otherwise be possible.
- [ ] Partition trust stores and policy caches logically or physically so one tenant cannot activate another tenant's trust material accidentally.
- [ ] Enforce authorization checks on all administrative APIs using namespace-scoped roles and resources.
- [ ] Prevent registry/repository names from implicitly defining trust domain without validated tenant mapping.
- [ ] Ensure metrics/logs/traces include bounded namespace labels while protecting sensitive tenant identifiers according to telemetry policy.
- [ ] Define cross-tenant sharing explicitly through signed delegation/allowlist objects rather than implicit global trust.
- [ ] Add collision tests using identical key IDs, certificate subjects, artifact names, and policy IDs under different namespaces.
- [ ] Add confused-deputy tests where a valid tenant-A signature is presented to a tenant-B admission endpoint.
- [ ] Test namespace canonicalization edge cases including case folding, whitespace, Unicode confusables, path separators, and percent/URL encodings.
- [ ] Verify cache keys include all namespace dimensions that affect trust/policy/admission results.
- [ ] Document namespace migration/rename semantics without allowing identity aliasing to bypass historical trust records.

### Acceptance gates
- [ ] A valid artifact/signature from one tenant/site/environment is refused in another unless explicit cross-domain delegation exists.
- [ ] Namespace collisions cannot cause trust-store, policy-cache, or admission-cache confusion.
- [ ] Administrative APIs enforce resource-scoped authorization for all tenant-affecting operations.
- [ ] Signed evidence records namespace context sufficient to reproduce the authorization domain.
- [ ] Adversarial cross-tenant conformance tests pass for identity, key, artifact, registry, and cache boundaries.

## 22. Rate Limiting / Admission Control

**Objective:** Bound verification workload and protect GAP-07 dependencies from CPU, memory, I/O, cryptographic, and external-service exhaustion.

### Engineering and security checklist
- [ ] Define separate resource budgets for hashing, signature verification, certificate/path validation, policy evaluation, transparency queries, registry I/O, and evidence parsing.
- [ ] Implement bounded request queues with explicit maximum depth and deterministic overload refusal rather than unbounded memory growth.
- [ ] Enforce concurrency limits globally and by tenant/site/request class where noisy-neighbor isolation is required.
- [ ] Add token-bucket/leaky-bucket or equivalent admission controls for expensive external operations such as KMS/transparency/registry calls.
- [ ] Bound artifact size, manifest size, evidence-object count, certificate-chain depth, SBOM size, and parser nesting before expensive downstream processing.
- [ ] Prioritize emergency revocation/control-plane traffic over ordinary admission work so overload cannot block security updates.
- [ ] Define per-request deadlines and propagate cancellation to registry, policy, transparency, and crypto provider calls.
- [ ] Implement load shedding that returns stable retryable/non-retryable reason codes and never converts overload into implicit allow.
- [ ] Prevent attacker-controlled high-cardinality keys from creating unbounded limiter state.
- [ ] Use backpressure for streaming uploads/pulls and avoid buffering complete large artifacts in memory.
- [ ] Expose queue depth, saturation, rejected requests, deadline expirations, CPU, memory, and dependency utilization as metrics.
- [ ] Test malicious bursts of valid-but-expensive signatures, huge malformed evidence bundles, slow streams, repeated cache misses, and registry amplification.
- [ ] Verify limiter fairness so one tenant cannot starve others while preserving policy-defined priority classes.
- [ ] Benchmark limiter overhead under normal load and verify no unsafe race permits limit bypass.
- [ ] Document capacity assumptions and derive default limits from benchmark evidence rather than arbitrary constants.

### Acceptance gates
- [ ] Verification resource use remains bounded under adversarial input and burst load.
- [ ] Overload results in explicit refusal/backpressure, never skipped verification or uncontrolled memory growth.
- [ ] Emergency security-control traffic remains serviceable within defined limits during admission saturation.
- [ ] Metrics provide enough signal to distinguish demand, attack, dependency slowdown, and local resource exhaustion.
- [ ] Load tests demonstrate stable recovery after saturation without restart or data corruption.

## 23. Streaming File / Registry Verification API

**Objective:** Verify large artifacts incrementally from files, sockets, registry streams, or content stores without materializing complete payloads in memory.

### Engineering and security checklist
- [ ] Define a streaming verification interface accepting bounded readers/file descriptors/content streams plus expected digest/size metadata.
- [ ] Support approved digest algorithms through incremental hash contexts and prevent algorithm changes mid-stream.
- [ ] Track exact byte count and reject truncated or overlong streams relative to trusted descriptor metadata where size is known.
- [ ] Bind final digest result to the verified artifact context only after EOF/finalization succeeds.
- [ ] Ensure caller cannot use partial-hash state as an admission success signal.
- [ ] Support cancellation/deadlines and close/release underlying resources on all failure paths.
- [ ] Prevent TOCTOU for file-backed verification by using stable handles, file identity/inode metadata where applicable, or immutable content-addressed stores.
- [ ] Define sparse-file, symlink, reparse-point, hard-link, and device-file policy for local filesystem inputs.
- [ ] Bound chunk sizes and internal buffering to prevent memory spikes and pathological small-read overhead.
- [ ] Integrate streamed registry verification with digest-addressed pulls and authenticated manifest descriptors.
- [ ] Surface progress/bytes hashed for observability without exposing artifact contents.
- [ ] Test short read, zero-length read loops, connection reset, partial content, late corruption, changing file, disk I/O error, cancellation, and oversized content.
- [ ] Compare streamed digest results against one-shot reference hashing across large randomized corpora.
- [ ] Add performance benchmarks for multi-GB artifacts, concurrent streams, slow storage, and edge-node constrained hardware.
- [ ] Document API ownership/lifetime rules so callers cannot reuse closed/verified streams incorrectly.

### Acceptance gates
- [ ] Multi-GB artifacts can be verified with bounded memory independent of artifact size.
- [ ] The admitted digest always corresponds to the exact complete byte stream handed to downstream execution/storage.
- [ ] Truncation, extension, mid-stream mutation, and I/O failure are reliably detected and fail closed.
- [ ] Streaming performance meets defined throughput/CPU targets on supported hardware.
- [ ] API semantics are covered by fuzz, race, cancellation, and lifecycle tests.

## 24. Atomic Trust Configuration Activation

**Objective:** Stage, validate, commit, and if necessary recover trust configuration without exposing partially validated or mixed generations to verification traffic.

### Engineering and security checklist
- [ ] Define lifecycle states such as `downloaded`, `signature_verified`, `schema_validated`, `semantically_validated`, `staged`, `active`, `superseded`, and `rejected`.
- [ ] Verify snapshot/delta signature, scope, generation, parent, schema, expiry, and content digest before staging.
- [ ] Run semantic validation for duplicate IDs, broken references, invalid algorithms, contradictory revocation state, expired anchors, and unauthorized policy references.
- [ ] Precompute immutable runtime indexes from staged configuration before commit to avoid lazy activation-time failures.
- [ ] Commit activation through one atomic pointer/generation swap visible consistently to all verifier threads/processes.
- [ ] Preserve the previous valid generation for forensic comparison and controlled emergency recovery without automatic rollback.
- [ ] Require operator/service identity and signed update provenance for manual activation paths.
- [ ] Make activation idempotent for repeated delivery of the same generation/digest.
- [ ] Reject activation if trusted time, storage durability, audit export, or required distribution preconditions are not satisfied.
- [ ] Emit pre-activation validation results and post-activation audit events with old/new generation and configuration digest.
- [ ] Invalidate dependent admission caches deterministically when the active trust generation changes.
- [ ] Test verifier traffic during activation to prove every request sees exactly old or new state, never a mixed view.
- [ ] Test process crash before/during/after commit, disk-full, corrupted staged config, stale generation, duplicate activation, and concurrent update attempts.
- [ ] Define rollback as a new signed recovery action/generation rather than pointer movement to older unsigned state.
- [ ] Expose active/staged generation and last activation status through health/diagnostic endpoints.

### Acceptance gates
- [ ] No partially validated trust data is visible to admission.
- [ ] Concurrent verification observes one coherent trust generation per decision.
- [ ] Crash recovery deterministically identifies the last durably committed valid generation.
- [ ] Rollback requires explicit signed authorization and remains auditable/monotonic at the control-plane level.
- [ ] Activation tests cover corruption, concurrency, dependency failure, and cache invalidation.

## 25. Metrics / Log / Trace Exporter

**Objective:** Provide production-grade observability for verification behavior, security refusals, dependency health, latency, and lifecycle events without leaking secrets or creating unsafe cardinality.

### Engineering and security checklist
- [ ] Define a telemetry schema with stable metric names, units, log event IDs, trace span names, and semantic attributes.
- [ ] Export counters for verification attempts, accepts, denials, malformed inputs, signature failures, provenance failures, policy denials, revocations, and dependency errors.
- [ ] Export histograms for total verification latency plus hashing, crypto, policy, registry, transparency, and trust-load suboperations.
- [ ] Export gauges for queue depth, active trust/policy generation age, checkpoint staleness, audit spool usage, replay-cache utilization, and dependency readiness.
- [ ] Use stable refusal/error codes as labels/fields and prohibit raw exception text as a high-cardinality metric dimension.
- [ ] Bound tenant/artifact/signer labeling; use sampled logs or trace attributes rather than unbounded digest/key IDs in metrics.
- [ ] Redact/private-classify credentials, tokens, private keys, artifact content, certificate secrets, and sensitive policy payloads from all telemetry.
- [ ] Propagate OpenTelemetry trace context across admission, registry, policy, transparency, and KMS calls while respecting trust-boundary constraints.
- [ ] Correlate logs/traces with audit event IDs without treating mutable logging systems as the authoritative security ledger.
- [ ] Define sampling that never drops required audit events and preserves sufficient traces for rare security failures.
- [ ] Provide liveness, readiness, dependency, and degraded-state endpoints with clear semantics.
- [ ] Test telemetry exporter outage/backpressure so verification does not deadlock or block indefinitely.
- [ ] Add schema/version compatibility tests for collectors and dashboards.
- [ ] Verify telemetry cardinality and volume under fleet-scale load and attack simulations.
- [ ] Maintain a data-classification and retention policy for observability data distinct from tamper-evident audit retention.

### Acceptance gates
- [ ] Operators can distinguish invalid artifacts, stale trust, dependency outages, policy denials, overload, and software defects from telemetry alone.
- [ ] Telemetry failure cannot weaken verification or block admission indefinitely.
- [ ] No secret/private-key material appears in automated telemetry leak tests.
- [ ] Metrics remain cardinality-bounded at expected fleet scale.
- [ ] Trace/log correlation can reconstruct performance flow while authoritative security evidence remains in the audit system.

## 26. Alerting / Dashboard Package

**Objective:** Convert GAP-07 telemetry into actionable operational and security views with severity, ownership, runbook linkage, and noise-resistant alert logic.

### Engineering and security checklist
- [ ] Define dashboards for admission volume/outcomes, verification latency, trust/policy freshness, key/KMS health, transparency health, audit export, registry errors, and resource saturation.
- [ ] Create distinct alert classes for invalid signatures, replay attempts, signer revocation hits, stale trust, stale policy, untrusted time, KMS outage, transparency inconsistency, and software exceptions.
- [ ] Define thresholds from SLOs/baselines using sustained windows or rates rather than single-event noise where appropriate.
- [ ] Treat cryptographic integrity violations and checkpoint inconsistency as security alerts even at low event counts.
- [ ] Route alerts to accountable on-call/security owners with severity and escalation policy.
- [ ] Include stable diagnostic dimensions such as site, environment, component, reason code, trust generation, and dependency class while avoiding sensitive identifiers.
- [ ] Link every alert to a version-controlled runbook and expected first-response actions.
- [ ] Add alert suppression/deduplication for known maintenance while preventing broad mute rules from hiding unrelated security events.
- [ ] Monitor absence-of-signal conditions such as stopped audit export, no trust-update acknowledgements, or missing admission metrics from active sites.
- [ ] Create fleet views for revocation propagation and stale/disconnected nodes.
- [ ] Add release annotations so regressions can be correlated with deployed GAP-07 versions/config generations.
- [ ] Test alert firing through synthetic fault injection rather than assuming dashboard queries are correct.
- [ ] Define paging versus ticketing thresholds and maximum tolerated acknowledgement/resolution times.
- [ ] Review alert precision/recall after incidents and tune without weakening critical integrity alarms.
- [ ] Version dashboards/alerts as code and validate queries against telemetry schema changes in CI.

### Acceptance gates
- [ ] Every declared critical failure mode has a tested alert with owner and runbook.
- [ ] Security-integrity failures cannot be hidden by normal operational-noise suppression rules.
- [ ] Fleet dashboards expose stale/revoked/out-of-date sites and propagation status.
- [ ] Synthetic failure exercises demonstrate alerts arrive within defined detection latency.
- [ ] Dashboard/alert definitions are version controlled, peer reviewed, and released with compatibility tests.

## 27. Fleet Revocation Propagation SLO

**Objective:** Define and verify worst-case time for signer/key/trust revocations to reach and become active across connected and intermittently connected sites.

### Engineering and security checklist
- [ ] Define separate SLOs for connected, degraded, and disconnected site classes and by severity of revocation.
- [ ] Measure `revocation_created -> published -> received -> validated -> activated -> acknowledged` timestamps for every site.
- [ ] Use trusted time or bounded uncertainty when calculating propagation latency.
- [ ] Maintain fleet inventory mapping expected sites/nodes to current trust generation and last acknowledgement.
- [ ] Escalate sites that miss acknowledgement or remain on a generation containing revoked trust beyond their allowed window.
- [ ] Define emergency push/poll cadence that is faster than routine trust updates for high-severity compromise.
- [ ] Ensure distribution backoff/retry cannot stretch propagation beyond the SLO without alerting.
- [ ] Define disconnected-site behavior once cached trust exceeds revocation freshness limits, including fail-closed admission where required.
- [ ] Simulate control-plane outage and prove alternate/recovery distribution behavior or explicit inability to meet SLO.
- [ ] Test large-fleet fanout and reconnect storms after prolonged partitions.
- [ ] Track percentile and worst-case propagation latency, not only fleet-average performance.
- [ ] Exclude decommissioned nodes only through authoritative inventory state to avoid hiding unpatched stragglers.
- [ ] Record per-generation rollout evidence for incident/release review.
- [ ] Integrate propagation health into production-readiness and incident-response dashboards.
- [ ] Review SLO values against realistic threat windows and network/site operating constraints at least on a defined cadence.

### Acceptance gates
- [ ] Connected sites activate emergency revocations within the declared worst-case SLO under normal production load.
- [ ] Missed/stale sites are automatically identified and escalated rather than disappearing from fleet statistics.
- [ ] Disconnected sites enforce predeclared stale-trust behavior after freshness limits expire.
- [ ] Large-scale revocation tests validate fanout capacity and recovery from partial failure.
- [ ] Incident evidence can prove when each site received and activated the revocation.

## 28. Compatibility Matrix

**Objective:** Maintain an authoritative, test-backed matrix of supported signature/provenance schemas, algorithms, runtimes, registries, architectures, dependencies, and migration windows.

### Engineering and security checklist
- [ ] Define machine-readable compatibility dimensions for GAP-07 version, signature envelope, provenance schema, DSSE/in-toto/SLSA versions, trust schema, and policy adapter version.
- [ ] Include approved algorithms/key parameters and crypto-provider/library versions with lifecycle status.
- [ ] Include supported Python/runtime/OS/architecture combinations and edge/desktop/server deployment profiles.
- [ ] Include supported OCI registry versions/features, referrer behavior, content-store semantics, Wasm runtimes, and microVM formats.
- [ ] Include KMS/HSM providers and validated API/provider versions.
- [ ] Define `supported`, `transitional`, `verify-only`, `deprecated`, and `unsupported` states with start/end dates.
- [ ] Attach a conformance-test suite identifier to every supported matrix row.
- [ ] Reject runtime startup or production readiness when the deployed combination is outside approved support unless an explicit signed exception exists.
- [ ] Prevent automatic “best effort” compatibility fallbacks that bypass required fields or security semantics.
- [ ] Define forward/backward compatibility rules for unknown critical fields and newer schema versions.
- [ ] Test upgrade/downgrade paths between every adjacent supported release where state/schema persists.
- [ ] Validate mixed-fleet operation during rolling upgrades and define maximum supported version skew.
- [ ] Track end-of-life dates and generate alerts before production deployments reach unsupported combinations.
- [ ] Publish migration guidance and required re-sign/re-attest/rebuild actions when security formats change incompatibly.
- [ ] Generate the compatibility matrix from version-controlled data and validate it in CI against actual test results.

### Acceptance gates
- [ ] Every production deployment maps to an explicitly supported, tested compatibility row.
- [ ] Unsupported combinations fail readiness or require a visible, signed, expiring exception.
- [ ] Rolling upgrade/version-skew behavior is tested for all supported transition paths.
- [ ] Documentation and machine-readable compatibility data cannot drift from CI evidence unnoticed.
- [ ] Deprecation deadlines have tested migration paths and measurable fleet adoption status.

---

# P2 — Certification, Resilience, and Scale

## 29. Fuzzing Harnesses

**Objective:** Continuously exercise signature, provenance, evidence, registry, trust, and policy parsers against malformed/adversarial input and state transitions.

### Engineering and security checklist
- [ ] Inventory every untrusted parser/decoder boundary, including signature envelopes, provenance records, DSSE, certificates, trust snapshots, OCI manifests, SBOMs, policy responses, and evidence bundles.
- [ ] Build in-process fuzz entry points that avoid network/process startup overhead and expose the smallest security-relevant parse/validate/verify function.
- [ ] Seed corpora with valid minimal, valid maximal, legacy, malformed, and cross-version examples for every supported schema.
- [ ] Add structure-aware mutators for JSON/CBOR/Protobuf/DER/PEM/OCI descriptors where generic byte mutation gives poor semantic coverage.
- [ ] Include Unicode malformed sequences, normalization edge cases, duplicate JSON keys, deeply nested structures, oversized lengths, empty values, and unexpected critical fields.
- [ ] Fuzz base64/base64url/hex/PEM decoders for padding ambiguity, non-canonical encodings, whitespace, truncation, and overlong inputs.
- [ ] Fuzz certificate/path-validation inputs with unusual extensions, path lengths, name constraints, key parameters, and malformed ASN.1.
- [ ] Fuzz provenance-chain state machines for invalid previous-link references, index discontinuity, duplicated steps, cycles, and inconsistent artifact digests.
- [ ] Fuzz trust-update state transitions for rollback, duplicate generation, malformed deltas, conflicting revocations, and activation races.
- [ ] Define resource guards and treat hangs, excessive allocation, stack exhaustion, and pathological CPU behavior as failures even without crashes.
- [ ] Run fuzz targets under sanitizers/instrumented runtimes where available, including memory/undefined-behavior checks for native dependencies.
- [ ] Deduplicate/minimize crashing inputs and automatically promote fixed regressions into deterministic unit-test fixtures.
- [ ] Track coverage over security-critical branches and reject superficial line coverage as the only success criterion.
- [ ] Execute short fuzz smoke runs in normal CI and longer campaigns in scheduled/security pipelines with retained corpus evolution.
- [ ] Record fuzzer engine/version, corpus digest, runtime, coverage metrics, crashes, hangs, and triage disposition in release evidence.

### Acceptance gates
- [ ] Every externally reachable parser has at least one maintained fuzz target.
- [ ] Fuzzing detects crashes, hangs, resource explosions, assertion failures, and security-semantic inconsistencies.
- [ ] Historical fuzz findings remain permanently covered by regression tests.
- [ ] Fuzz corpus and findings are versioned and reproducible for each release candidate.
- [ ] Release policy defines minimum fuzz runtime/coverage and contains no unresolved critical/high-severity fuzz findings.

## 30. Property-Based Tests

**Objective:** Validate broad security invariants over automatically generated inputs instead of relying only on example-based test vectors.

### Engineering and security checklist
- [ ] Formalize core invariants for domain separation, artifact-kind/environment binding, trust lookup, revocation, threshold counting, and provenance-chain continuity.
- [ ] Generate arbitrary valid/invalid signature envelopes under bounded schemas and assert mutation of any security-bound field invalidates verification.
- [ ] Generate provenance chains of varying length and assert deterministic head calculation, order sensitivity, previous-link continuity, and tamper detection.
- [ ] Generate trust-store rotations/revocations and assert monotonic state, no silent signer replacement, and deterministic active-key resolution.
- [ ] Generate tenant/site/environment namespaces and assert no cross-domain authorization without explicit delegation.
- [ ] Generate policy requirements and artifact facts and assert deny-by-default behavior for missing/unknown critical attributes.
- [ ] Generate canonicalization-equivalent inputs and assert identical semantics only where the format specification says they are equivalent.
- [ ] Generate non-equivalent encodings that look visually similar and assert they cannot collapse to the same security identity unexpectedly.
- [ ] Generate threshold signer sets and assert duplicates/aliases never count as independent approvals where independence is required.
- [ ] Generate trust-distribution generations/deltas and assert rollback, parent mismatch, or branch divergence cannot activate.
- [ ] Generate time sequences including rollback/forward jumps and assert expiry/freshness invariants remain safe.
- [ ] Add shrinking/minimization support so failures reduce to small reproducible counterexamples.
- [ ] Fix random seeds in stored regressions while keeping randomized exploration in scheduled runs.
- [ ] Run properties under normal and optimized runtime modes and across supported implementation languages where practical.
- [ ] Map each security property to a documented invariant and requirements-traceability entry.

### Acceptance gates
- [ ] Core cryptographic/trust/provenance invariants have executable property tests.
- [ ] Property-generated counterexamples are reproducible and promoted to permanent regression fixtures after fixes.
- [ ] Tests cover both valid-state closure properties and invalid-state rejection properties.
- [ ] Property test runs are integrated into release qualification with recorded seeds/configuration.
- [ ] No critical security invariant exists only as prose without corresponding executable validation or formal review rationale.

## 31. Concurrency / Race Tests

**Objective:** Prove verification, rotation, revocation, policy/trust activation, replay handling, and cache behavior remain correct under simultaneous operations.

### Engineering and security checklist
- [ ] Enumerate shared mutable state including active trust snapshot, key metadata, policy snapshot, admission cache, replay cache, audit sequence, and configuration generation.
- [ ] Define atomicity/consistency guarantees for each shared state and document allowed visibility across threads/processes.
- [ ] Stress simultaneous verification while rotating active signer keys and assert each decision observes one coherent generation.
- [ ] Stress simultaneous verification and signer/key revocation and define the exact linearization point for authorization.
- [ ] Race trust configuration staging/activation with large concurrent verification load and detect mixed-generation reads.
- [ ] Race policy activation with admission-cache lookup/invalidation and assert stale permits cannot survive security-relevant updates.
- [ ] Race duplicate nonce/replay-token consumption from multiple workers and assert only one succeeds.
- [ ] Race multi-signature bundle finalization and duplicate signer submission.
- [ ] Race audit-event append/export so sequence and previous-hash continuity remain deterministic.
- [ ] Race registry/cache population for the same artifact digest and verify no partially downloaded content becomes trusted.
- [ ] Add forced scheduling/yield points or deterministic concurrency-test hooks around critical compare-and-swap/commit boundaries.
- [ ] Run high-iteration stress under thread/process sanitizers or race detectors where the language/runtime supports them.
- [ ] Test multi-process/file-lock/database transaction behavior in addition to in-process thread safety.
- [ ] Test cancellation/shutdown while operations hold locks or transactions to detect deadlock/resource leaks.
- [ ] Record concurrency model and lock/order rules in architecture documentation and enforce with code review/static tooling where possible.

### Acceptance gates
- [ ] No test can produce a mixed trust/policy generation within one admission decision.
- [ ] Revocation/rotation has a defined and tested linearization point relative to concurrent verification.
- [ ] Replay and threshold counters remain race-safe under simultaneous requests.
- [ ] Audit and persistent state remain consistent after forced concurrent failure/shutdown.
- [ ] Long-running concurrency stress completes without deadlock, livelock, race findings, or invariant violations.

## 32. Fault-Injection Tests

**Objective:** Validate deterministic fail-closed behavior and recovery under dependency, storage, network, clock, and control-plane faults.

### Engineering and security checklist
- [ ] Build injectable interfaces for KMS/HSM, registry, transparency log, trusted time, trust storage/distribution, policy engine, and audit exporter.
- [ ] Inject KMS timeout, throttling, permission denial, disabled key, malformed response, and regional outage.
- [ ] Inject registry partial reads, connection resets, corrupted layers/manifests, auth expiry, stale cache, and slow streams.
- [ ] Inject transparency timeout, invalid inclusion proof, stale checkpoint, inconsistent checkpoint, and unreachable service.
- [ ] Inject trust snapshot corruption, invalid signature, rollback generation, missing delta, disk-full, fsync failure, and database unavailability.
- [ ] Inject policy-engine timeout, corrupt signed bundle, unsupported schema, stale cache, conflicting rule result, and unavailability.
- [ ] Inject trusted-time loss, backward/forward jumps, high uncertainty, RTC reset, and source failover.
- [ ] Inject audit-export outage, local spool full, duplicate acknowledgement, reordered export batch, and WORM backend failure.
- [ ] Inject process termination/power-loss equivalents at persistent-state commit points and validate crash recovery.
- [ ] Inject network partitions between site and control plane with prolonged disconnected operation followed by reconnect storm.
- [ ] Inject CPU/memory/disk pressure and verify rate limiting/backpressure preserves security semantics.
- [ ] Verify every injected fault maps to stable observable error/state rather than generic success or uncaught exception.
- [ ] Measure recovery time and whether manual intervention is required for each fault class.
- [ ] Automate fault scenarios in pre-release/staging environments and isolate destructive tests from production data.
- [ ] Preserve fault-injection scenario definitions and results as release evidence.

### Acceptance gates
- [ ] No critical dependency fault causes an implicit allow or insecure fallback.
- [ ] Crash/restart tests preserve the last valid durable trust/audit state and detect partial state.
- [ ] Recovery behavior matches documented RTO/RPO/SLO expectations.
- [ ] Operators receive actionable telemetry/alerts for every high-severity injected fault.
- [ ] Fault-injection suites run automatically for release candidates and after changes to dependency/state-management code.

## 33. Performance Benchmark Suite

**Objective:** Quantify verification latency, hashing throughput, resource consumption, concurrency behavior, cold start, and edge-node impact using reproducible workloads.

### Engineering and security checklist
- [ ] Define representative artifact classes/sizes for OCI manifests/images, Wasm components, microVM images, provider bundles, and metadata-only verification.
- [ ] Define benchmark hardware profiles for server, workstation, edge, constrained edge, and any accelerator-assisted environment in scope.
- [ ] Measure end-to-end p50/p95/p99/max admission latency under warm and cold caches.
- [ ] Measure isolated hashing throughput per digest algorithm across artifact size and storage medium.
- [ ] Measure signature verification throughput/latency per algorithm/key size/provider.
- [ ] Measure certificate/path-validation, DSSE/provenance parsing, policy evaluation, and transparency proof verification separately.
- [ ] Measure CPU utilization, peak/resident memory, allocations, file descriptors, network bytes, and storage I/O per request.
- [ ] Measure scaling as concurrency increases and identify saturation knee, queueing onset, and recovery behavior.
- [ ] Measure cold startup including trust/policy load, schema initialization, provider setup, and readiness time.
- [ ] Measure performance with telemetry/audit enabled at production settings rather than benchmarking a stripped configuration.
- [ ] Measure disconnected/offline verification versus online dependency-backed verification.
- [ ] For edge nodes, capture power draw/energy per verification and thermal throttling effects where measurable.
- [ ] Use fixed datasets with recorded digests plus statistically sound iteration counts/warmup methodology.
- [ ] Define regression budgets and fail CI/release qualification on material unexplained regressions.
- [ ] Archive benchmark tool version, machine profile, OS/runtime, dependency versions, configuration, raw results, and summary statistics.

### Acceptance gates
- [ ] Performance targets exist for every production hardware profile and key artifact class.
- [ ] p95/p99 and saturation behavior meet admission SLOs with security/telemetry features enabled.
- [ ] Benchmark methodology/results are reproducible on controlled hardware.
- [ ] Resource ceilings inform rate-limit and capacity defaults.
- [ ] Release evidence highlights regressions and records approved exceptions with owners/expiry.

## 34. Soak / Burst / Fleet-Scale Tests

**Objective:** Validate long-duration stability, burst recovery, trust-update fanout, revocation propagation, and admission behavior at realistic fleet scale.

### Engineering and security checklist
- [ ] Define fleet models for node/site count, tenant count, artifact admission rate, trust update rate, offline ratio, and geographic/network latency.
- [ ] Run multi-hour/day soak tests with continuous verification, trust refresh, telemetry export, and periodic key/policy rotations.
- [ ] Detect memory/handle/thread/socket growth, queue drift, cache leaks, audit-spool accumulation, and latency degradation over time.
- [ ] Run burst tests significantly above expected peak admission rate to validate bounded queueing/load shedding and recovery.
- [ ] Simulate mass rollout where many nodes pull/verify the same new artifact concurrently.
- [ ] Simulate emergency revocation fanout to the full fleet and measure worst-case activation latency.
- [ ] Simulate large reconnect waves after disconnected sites regain control-plane access.
- [ ] Mix valid, invalid, stale, malformed, and expensive adversarial artifacts into sustained load.
- [ ] Exercise trust/policy generation churn while admission continues and verify snapshot consistency.
- [ ] Include dependency degradation (slow registry/KMS/transparency) during high load to test cascading-failure resistance.
- [ ] Measure control-plane, storage, audit, and telemetry backend capacity in addition to verifier-node capacity.
- [ ] Define steady-state baselines and automated leak/regression thresholds.
- [ ] Test autoscaling or static-capacity failover behavior without weakening rate/security limits.
- [ ] Preserve representative synthetic data and load profiles as versioned test fixtures.
- [ ] Produce fleet-scale test reports with percentile latency, failures, dropped/retried work, propagation timing, resource saturation, and recovery time.

### Acceptance gates
- [ ] Sustained production-equivalent load completes without progressive resource leakage or security-state drift.
- [ ] Burst overload remains bounded and returns to normal without restart/manual cleanup.
- [ ] Fleet revocation/trust update propagation meets declared worst-case objectives under scale.
- [ ] Reconnect storms do not create rollback, duplicate activation, or control-plane collapse.
- [ ] Capacity planning is based on measured fleet-scale behavior with documented headroom.

## 35. Disaster Recovery Tooling

**Objective:** Reconstruct trust/audit state from signed backups and anchors, verify continuity, and restore service within declared RPO/RTO without reintroducing stale or compromised trust.

### Engineering and security checklist
- [ ] Define recoverable state inventory: trust snapshots, revocations, policy references, algorithm registry, audit chain/anchors, transparency checkpoints, configuration, and release evidence.
- [ ] Classify which state is authoritative, reconstructable, cache-only, or intentionally non-restorable.
- [ ] Produce signed/versioned backups with generation, content digest, creation time, scope, and source identity.
- [ ] Store backups in an administrative/failure domain separate from the primary verifier/control-plane storage.
- [ ] Enforce immutable retention and access controls on critical trust/audit backups.
- [ ] Build restore tooling that validates signature, digest, schema, generation, expiry, and rollback policy before writing state.
- [ ] Verify restored audit-chain continuity against external anchors/checkpoints and detect missing segments.
- [ ] Prevent restoring a snapshot predating emergency revocations unless an explicitly authorized incident procedure reconciles them first.
- [ ] Define new-site bootstrap after total loss, including root-of-trust installation and independent validation.
- [ ] Reconcile restored site state with the live control plane before resuming admission when connectivity exists.
- [ ] Test region/site loss, corrupted primary database, lost node filesystem, lost audit spool, and total control-plane rebuild.
- [ ] Automate integrity checks after restore before marking service ready.
- [ ] Measure RPO/RTO during scheduled drills and record deviations/action items.
- [ ] Maintain offline/printed or otherwise independent recovery procedures for scenarios where normal documentation systems are unavailable.
- [ ] Require two-person or equivalent strong authorization for restoration of root trust/critical configuration.

### Acceptance gates
- [ ] A clean environment can restore the latest safe trust state and independently verify its authenticity/monotonicity.
- [ ] Recovery cannot silently resurrect revoked keys or stale policy.
- [ ] Audit continuity can be proven against external anchors after restore.
- [ ] Scheduled DR drills meet declared RPO/RTO or create tracked remediation.
- [ ] Restored service remains fail closed until all critical integrity checks succeed.

## 36. Formal Threat Model

**Objective:** Maintain a versioned, evidence-linked threat model covering artifact supply chain, signer/trust compromise, parsers, rollback/replay, offline operation, side channels, and insider abuse.

### Engineering and security checklist
- [ ] Define system context, assets, trust boundaries, actors, data flows, deployment modes, and external dependencies using an architecture/data-flow model.
- [ ] Enumerate protected assets including signing keys, trust roots, policy state, artifact identity, provenance, audit evidence, availability, and tenant isolation.
- [ ] Model attackers such as malicious publisher, compromised builder, compromised signer, rogue operator, compromised control plane, registry attacker, network attacker, and malicious tenant.
- [ ] Apply STRIDE or equivalent across every data flow/component and LINDDUN/privacy analysis where sensitive identity/telemetry data warrants it.
- [ ] Model signature replay across kind/environment/tenant, algorithm downgrade, key-ID confusion, canonicalization ambiguity, and certificate-chain manipulation.
- [ ] Model trust snapshot rollback, stale disconnected sites, compromised distribution relays, emergency-revocation suppression, and malicious bootstrap.
- [ ] Model provenance/SBOM substitution, contradictory attestations, registry tag mutation, TOCTOU, cache poisoning, and alternate execution paths.
- [ ] Model parser/resource attacks including oversized input, decompression bombs, deep nesting, Unicode ambiguity, malformed ASN.1, and expensive cryptographic inputs.
- [ ] Model KMS/HSM/control-plane compromise and separation-of-duties failures, not just external attackers.
- [ ] Model transparency split-view/equivocation, stale checkpoints, and dependency outage downgrade attempts.
- [ ] Model trusted-time manipulation and its effects on expiry/freshness/revocation.
- [ ] Map every threat to preventative/detective/recovery controls and identify residual risk plus owner.
- [ ] Tie threat IDs to tests, alerts, runbooks, and requirements traceability entries.
- [ ] Re-review the model for every material architecture/trust/algorithm/deployment change and on a fixed cadence.
- [ ] Conduct independent adversarial review/tabletop using the model and capture newly discovered abuse cases.

### Acceptance gates
- [ ] Every critical trust boundary and security asset has explicit threats and mapped mitigations.
- [ ] Residual risks are named, owned, and approved rather than implicitly accepted.
- [ ] High-severity threats have executable negative/fault/penetration tests where feasible.
- [ ] Threat-model version is referenced from release/security-review evidence.
- [ ] Architecture changes cannot be production-approved without updating affected threat-model elements.

## 37. Independent Security / Cryptographic Review

**Objective:** Obtain independent assurance that production cryptography, key custody, canonicalization, trust semantics, and failure behavior match the intended security model.

### Engineering and security checklist
- [ ] Define review scope covering signature envelope, asymmetric algorithms, KMS/HSM boundary, PKI/trust model, DSSE/SLSA handling, transparency verification, trusted time, and trust distribution.
- [ ] Provide reviewers with architecture diagrams, threat model, cryptographic message formats, canonicalization rules, key lifecycle, policy semantics, and deployment assumptions.
- [ ] Include source code and production configuration for security-critical paths rather than reviewing design documents only.
- [ ] Review cryptographic library/provider selection, versions, configuration flags, FIPS/compliance mode where applicable, and unsafe/default APIs.
- [ ] Verify domain separation and signed-field coverage for artifact digest, kind, environment, namespace, signer identity, algorithm, and relevant policy context.
- [ ] Review certificate chain/path validation, revocation, name/identity mapping, key usage, and trust-anchor rotation semantics.
- [ ] Review KMS/HSM IAM, alias/version behavior, non-exportability assumptions, emergency disable, and auditability.
- [ ] Review canonicalization and parser behavior for duplicate keys, Unicode, numeric forms, DSSE PAE, ASN.1, CBOR, and any custom binary formats.
- [ ] Review offline/disconnected verification rules, staleness limits, trusted-time assumptions, and anti-rollback behavior.
- [ ] Review error handling for oracle leakage, permissive fallback, caught/uncaught exception behavior, and optimization/runtime mode differences.
- [ ] Review threshold/multi-signature logic for signer independence and quorum-counting attacks.
- [ ] Review audit/tamper-evidence design and whether the logging authority is sufficiently independent of the system being audited.
- [ ] Track every review finding with severity, owner, remediation, test evidence, and closure status.
- [ ] Require re-review of material changes to message format, crypto algorithms, trust anchors, key custody, canonicalization, or policy semantics.
- [ ] Preserve the review report/attestation and exact reviewed commit/build/configuration identifiers as controlled release evidence.

### Acceptance gates
- [ ] All critical/high review findings are remediated or formally risk-accepted by authorized governance before production admission.
- [ ] Review scope includes deployed configuration and provider boundaries, not only library-level cryptography.
- [ ] Remediations include regression tests proving the identified weakness remains closed.
- [ ] The reviewed source/configuration can be mapped to released artifact digests.
- [ ] Security review cadence and change-trigger criteria are documented and enforced by release governance.

## 38. Release Acceptance Evidence Bundle

**Objective:** Produce one machine-readable, independently verifiable evidence package for every release candidate containing security, quality, provenance, and operational-readiness results.

### Engineering and security checklist
- [ ] Define a versioned release-evidence manifest rooted in the immutable GAP-07 release artifact digest.
- [ ] Include source revision, build invocation, builder identity, build provenance, source/material digests, and reproducibility information where applicable.
- [ ] Include unit/integration/security/conformance/property/fuzz/fault/concurrency/performance/soak test result artifacts with stable suite IDs and pass/fail summaries.
- [ ] Include exact runtime, OS, architecture, dependency, crypto-library/provider, and test-tool versions used for qualification.
- [ ] Include generated SBOM, dependency inventory, vulnerability scan results, vulnerability database timestamp/version, and approved waivers.
- [ ] Include cryptographic review/security review report references and unresolved/accepted risk records.
- [ ] Include compatibility-matrix row(s), migration notes, schema changes, algorithm changes, and deployment constraints.
- [ ] Include signed trust/policy/schema definitions used in release qualification where they materially affect results.
- [ ] Include benchmark raw data/summary and evidence that required performance/SLO thresholds were met.
- [ ] Include fuzz corpus version/digest, execution duration/coverage, crash count, and triage status.
- [ ] Include DR/fault/soak/concurrency results where required by release policy and indicate any test waived with signed justification.
- [ ] Content-address every evidence object and sign/attest the top-level evidence manifest.
- [ ] Store the bundle in durable, access-controlled retention and optionally publish required portions alongside the release artifact.
- [ ] Build independent verification tooling that validates manifest signatures, object hashes, completeness rules, and release-artifact binding.
- [ ] Define release gate policy that fails automatically when required evidence is missing, failed, stale, unsigned, or incompatible.

### Acceptance gates
- [ ] Every production release has a signed evidence bundle bound to its exact artifact digest.
- [ ] An independent verifier can determine whether all mandatory release gates passed without querying ephemeral CI state.
- [ ] Missing or failed required evidence prevents promotion.
- [ ] Waived gates are explicit, signed, scoped, owned, and time-bounded.
- [ ] Historical evidence remains re-verifiable after CI systems, branches, or build workers are gone.

## 39. Vulnerability / Dependency Management

**Objective:** Maintain authoritative dependency inventory, continuous security monitoring, patch SLAs, cryptographic-library response, and emergency update capability.

### Engineering and security checklist
- [ ] Generate a complete direct/transitive dependency inventory for runtime, build, test, packaging, native libraries, crypto providers, base images, and deployment tooling.
- [ ] Record exact resolved versions and integrity hashes/lockfiles; prohibit floating/unpinned production dependencies where reproducibility is required.
- [ ] Produce SPDX/CycloneDX SBOM for GAP-07 itself and bind it to the release artifact digest.
- [ ] Scan dependencies and container/base images against one or more maintained vulnerability intelligence sources.
- [ ] Track vulnerability database/feed freshness and treat unavailable/stale scanning state explicitly.
- [ ] Define remediation SLAs by severity, exploitability, exposure, known-exploited status, and compensating controls.
- [ ] Monitor cryptographic library/provider advisories separately because algorithm/provider flaws can invalidate trust assumptions fleet-wide.
- [ ] Define end-of-life policy for runtimes, libraries, OS/base images, registry APIs, and KMS/HSM provider versions.
- [ ] Require dependency updates to run security/conformance/interoperability/performance regression suites before release.
- [ ] Implement exception/waiver records with affected component/version, rationale, risk owner, expiry, and compensating controls.
- [ ] Maintain an emergency patch path that can rebuild, re-attest, re-sign, and distribute GAP-07 rapidly without bypassing release evidence.
- [ ] Detect dependency confusion/typosquatting using private registry/allowlist, package integrity, and namespace controls.
- [ ] Verify downloaded build dependencies and tools by digest/signature/provenance where supported.
- [ ] Remove unused dependencies and optional crypto algorithms/providers to reduce attack surface.
- [ ] Measure mean time to triage/remediate and report overdue vulnerabilities/unsupported components to service ownership.

### Acceptance gates
- [ ] Production artifacts have complete, immutable dependency/SBOM evidence.
- [ ] Known vulnerabilities are triaged against defined SLAs with explicit owned disposition.
- [ ] Critical crypto/runtime advisories can trigger an emergency release path without disabling provenance/signing controls.
- [ ] Unsupported/EOL dependencies are blocked by release policy unless explicitly time-bounded and risk accepted.
- [ ] Dependency-integrity and provenance controls prevent unreviewed package substitution in builds.

## 40. Operational Runbooks

**Objective:** Provide executable, tested procedures for normal and emergency GAP-07 operations so responders do not invent security-sensitive steps during incidents.

### Engineering and security checklist
- [ ] Create signer onboarding runbook covering identity proofing, key creation, authorization scope, trust publication, validation, and evidence capture.
- [ ] Create signer offboarding runbook covering revocation/retirement, trust update, affected artifacts, credential removal, and verification.
- [ ] Create routine and emergency key rotation runbooks with KMS/HSM/provider-specific commands/checks and rollback constraints.
- [ ] Create key-compromise response runbook with revocation, blast-radius discovery, quarantine, re-sign/rebuild, notification, and evidence preservation.
- [ ] Create trust-store update/rollback-recovery runbook with generation/signature validation and post-activation verification.
- [ ] Create transparency-log outage/inconsistency runbook distinguishing availability failure from cryptographic inconsistency/split-view indicators.
- [ ] Create trusted-time failure/clock-rollback runbook and clearly state which admissions must halt.
- [ ] Create disconnected-site stale-trust recovery and reconnect reconciliation runbook.
- [ ] Create registry/cache corruption and TOCTOU investigation runbook.
- [ ] Create audit-export/spool-full/tamper-detection runbook.
- [ ] Create policy-engine outage/corrupt bundle/version-skew runbook.
- [ ] Create emergency-disable/break-glass runbook with authorization quorum, narrow scope, expiry, audit, and restoration steps.
- [ ] Include preconditions, commands/API operations, expected outputs, stop conditions, rollback restrictions, escalation contacts, and evidence to retain.
- [ ] Exercise runbooks in tabletop and technical drills; record duration, ambiguity, failed steps, and corrective changes.
- [ ] Version runbooks with the platform and link alert/dashboard entries directly to the applicable procedure.

### Acceptance gates
- [ ] Every critical alert/failure mode maps to a maintained runbook.
- [ ] Runbooks have been technically exercised rather than documentation-reviewed only.
- [ ] Security-sensitive steps specify authorization and evidence requirements explicitly.
- [ ] Outdated runbooks fail documentation/release checks when interfaces or procedures change.
- [ ] Responders can complete representative recovery/incident drills within declared operational objectives.

## 41. Ownership / Escalation Metadata

**Objective:** Make technical, operational, security, risk, and exception accountability explicit and machine-queryable for every GAP-07 component/control.

### Engineering and security checklist
- [ ] Assign one accountable service owner and one maintained operational team to GAP-07.
- [ ] Assign security/cryptographic review ownership separately where independence is required.
- [ ] Record primary/secondary on-call routes, escalation levels, and expected acknowledgement times by incident severity.
- [ ] Define incident severity criteria for key compromise, trust corruption, invalid signature acceptance, transparency inconsistency, stale revocation, audit loss, and availability failure.
- [ ] Assign owners for trust roots, KMS/HSM keys, policy bundles, registry integration, deployment manifests, and CI/release pipelines.
- [ ] Assign waiver/exception approvers and prohibit implementation owners from self-approving high-risk exceptions where separation is required.
- [ ] Maintain contact/ownership metadata in version-controlled machine-readable form with effective dates.
- [ ] Integrate ownership data into alerts, dashboards, runbooks, service catalog, and requirements traceability.
- [ ] Define backup/delegation when owners are unavailable and test escalation outside normal hours.
- [ ] Define review cadence for service ownership and automatically detect orphaned/departed identities where directory integration exists.
- [ ] Define risk-acceptance authority by severity and maximum waiver duration.
- [ ] Define who can authorize emergency break-glass, trust rollback recovery, root-anchor changes, and signing-key destruction.
- [ ] Require transfer checklist when ownership changes, including keys/access, open risks, incidents, roadmap, and runbook review.
- [ ] Audit privileged owner/approver actions through the tamper-evident event system.
- [ ] Include ownership/escalation metadata in release evidence so accountability at release time is reconstructable.

### Acceptance gates
- [ ] No production-critical component/control is orphaned or owned only by an individual without backup/escalation.
- [ ] Critical incidents page the correct accountable team within the declared acknowledgement window.
- [ ] High-risk exceptions and root/key changes have documented independent authorization.
- [ ] Ownership metadata is synchronized with runbooks/alerts/service catalog and checked for staleness.
- [ ] Historical release/incident evidence can identify the accountable authority at the time of the event.

## 42. Architecture Decision Records (ADRs)

**Objective:** Preserve the rationale, alternatives, assumptions, consequences, and migration constraints behind security-critical production design choices.

### Engineering and security checklist
- [ ] Create an ADR template containing context, decision, status, date, owners/reviewers, considered alternatives, security consequences, operational consequences, and rollback/migration implications.
- [ ] Record the production asymmetric signing algorithm/profile decision and rejected alternatives.
- [ ] Record KMS/HSM provider/custody model, key exportability policy, and provider identity/IAM assumptions.
- [ ] Record trust-root/PKI model, certificate identity mapping, revocation mechanism, and offline verification policy.
- [ ] Record DSSE/in-toto/SLSA attestation formats/versions and canonicalization strategy.
- [ ] Record transparency-log service and checkpoint/offline-cache trust model.
- [ ] Record trust-store persistence/distribution architecture and anti-rollback semantics.
- [ ] Record GAP-13 policy adapter contract and deny/default semantics.
- [ ] Record OCI/Wasm/microVM artifact identity boundaries and admission-hook architecture.
- [ ] Record trusted-time source/uncertainty policy and disconnected-operation limits.
- [ ] Record audit anchoring/storage technology and independence/retention assumptions.
- [ ] Record algorithm-agility/deprecation process and future migration strategy.
- [ ] Link ADRs to threat-model items, requirements, implementation modules, tests, and successor/superseding ADRs.
- [ ] Require security review for ADRs that alter cryptographic/trust boundaries.
- [ ] Mark obsolete decisions as superseded rather than deleting history; preserve applicability by release/version range.

### Acceptance gates
- [ ] Every listed security-critical architecture choice has an approved ADR before production rollout.
- [ ] ADRs clearly identify assumptions that, if changed, require re-evaluation.
- [ ] Superseded decisions retain traceable history and migration rationale.
- [ ] Implementation/release review can map deployed behavior to the applicable ADR set.
- [ ] Architecture changes cannot merge into production without required ADR/threat-model updates.

## 43. Requirements Traceability Matrix

**Objective:** Map the complete GAP-07 control set—including the original 100 controls and this completion checklist—to code, tests, dependencies, owners, evidence, and status.

### Engineering and security checklist
- [ ] Define a machine-readable traceability schema with requirement/control ID, text, priority, component, owner, status, implementation reference, test references, evidence, and external dependencies.
- [ ] Import/map all existing 100 GAP-07 checklist/control IDs without renumbering historical identifiers.
- [ ] Add unique IDs for every item in this professional completion checklist or link them to tracked engineering requirements.
- [ ] Map each requirement to exact source module/function/configuration or mark it explicitly external/not-applicable with rationale.
- [ ] Map each requirement to positive, negative, failure-mode, and integration tests where applicable.
- [ ] Map each requirement to runtime telemetry/alert/runbook evidence when operational verification is part of the control.
- [ ] Map external requirements to GAP-06/GAP-08/GAP-13/PLN-06/PLN-07/`pk_core` interfaces with owner and version.
- [ ] Record release-evidence object/digest proving each control for a specific production release.
- [ ] Distinguish design-complete, code-complete, test-complete, integrated, production-validated, waived, and blocked states.
- [ ] Require signed/time-bounded waiver metadata for controls not fully satisfied at release.
- [ ] Automate stale-link detection when referenced files/tests/modules are renamed or removed.
- [ ] Compute coverage metrics by P0/P1/P2, component, test type, and release gate, but do not allow aggregate percentages to mask missing P0 controls.
- [ ] Fail production release when mandatory traceability entries lack implementation/test/evidence or contain unresolved critical/high blockers.
- [ ] Version and sign the traceability matrix as part of the release acceptance evidence bundle.
- [ ] Generate human-readable views for engineering, security, operations, and auditors from the same authoritative machine-readable source.

### Acceptance gates
- [ ] Every mandatory GAP-07 control has an authoritative trace from requirement to implementation to verification evidence.
- [ ] P0 gaps cannot be hidden by aggregate completion percentages.
- [ ] External dependencies have explicit interface/version/owner/status rather than vague “handled elsewhere” notes.
- [ ] Traceability is validated automatically in CI/release gating.
- [ ] Historical release matrices remain immutable/re-verifiable and map to exact artifact/evidence digests.

---

# External Packaging and Documentation Dependencies

## 44. Estate `pk_core` Dependency Integration

**Objective:** Restore full estate-level conformance execution by supplying and validating the parent `pk_core` dependency without weakening GAP-07's standalone fail-closed behavior.

### Engineering and security checklist
- [ ] Identify the authoritative `pk_core` repository/package, supported version range, release channel, owner, and cryptographic distribution mechanism.
- [ ] Pin the exact compatible `pk_core` version or digest for every GAP-07 release; prohibit unbounded/latest dependency resolution in production qualification.
- [ ] Document the adapter contract between GAP-07 and `pk_core`, including imported symbols, data structures, error semantics, lifecycle, and security assumptions.
- [ ] Verify `pk_core` release signatures/provenance/SBOM before use in GAP-07 build or test environments.
- [ ] Add startup/import compatibility checks that fail explicitly on missing/incompatible API rather than silently skipping security behavior.
- [ ] Keep dependency-free GAP-07 core security tests runnable even when `pk_core` is absent so local guarantees remain continuously testable.
- [ ] Restore the two estate-adapter tests currently skipped because `pk_core` was not supplied and add them to required CI/release gates.
- [ ] Add interface-contract tests covering valid/invalid artifact decisions, error translation, policy/trust objects, and edge-case serialization.
- [ ] Detect semantic version/API changes in `pk_core` that could alter authorization or validation behavior and require explicit review.
- [ ] Test version skew between GAP-07 and adjacent estate releases during rolling upgrade scenarios.
- [ ] Ensure `pk_core` cannot inject mutable global state or insecure defaults into GAP-07 without being surfaced by configuration/self-checks.
- [ ] Include `pk_core` in dependency inventory, SBOM, vulnerability scanning, compatibility matrix, and release evidence.
- [ ] Define fallback behavior when `pk_core` is unavailable: production estate features requiring it must fail closed; standalone reference tests may remain available.
- [ ] Add owner/escalation/runbook entries for `pk_core` integration failures and incompatible releases.
- [ ] Preserve a minimal interface fixture/mock for deterministic unit tests without misrepresenting the mock as full estate conformance.

### Acceptance gates
- [ ] Full 100-control estate adapter/conformance suite executes with zero dependency-related skips in production qualification.
- [ ] The exact `pk_core` release is authenticated, pinned, inventoried, and traceable to the GAP-07 release artifact.
- [ ] Incompatible/missing `pk_core` cannot produce a false-ready production state.
- [ ] Adapter semantics are covered by versioned contract tests and compatibility-matrix entries.
- [ ] Dependency ownership and upgrade process are documented with release/security review triggers.

## 45. Adjacent-Layer Integration Fixtures — GAP-06 / GAP-08 / PLN-06 / PLN-07 / GAP-13

**Objective:** Supply realistic contract fixtures and end-to-end test environments for the identity/attestation, OTA lifecycle, planning/runtime, and policy layers that interact with GAP-07.

### Engineering and security checklist
- [ ] Define the authoritative interface/version for each adjacent layer and identify which fields/security assertions GAP-07 consumes or produces.
- [ ] Build versioned fixtures for GAP-06 device/signer identity and attestation objects used to authorize signing or admission principals.
- [ ] Build GAP-08 OTA/rollback fixtures covering update artifact signatures, rollback authorization, revoked release, interrupted update, and recovery images.
- [ ] Build PLN-06/PLN-07 runtime/admission fixtures representing every artifact launch/deployment path that must call GAP-07.
- [ ] Build GAP-13 policy fixtures for signer role, algorithm, threshold, freshness, provenance, vulnerability, exception, and environment rules.
- [ ] Include both golden-valid and adversarial-invalid fixture sets with stable expected reason codes.
- [ ] Version fixture schemas independently from implementation source so compatibility regressions are visible.
- [ ] Include cross-component namespace/tenant/environment identifiers to test confusion and replay boundaries.
- [ ] Exercise trust/policy generation changes during OTA/deployment workflows and verify cache invalidation/admission re-evaluation.
- [ ] Exercise device identity/key rotation from GAP-06 and verify GAP-07 trust updates propagate without accepting stale identities.
- [ ] Exercise OTA rollback where an older artifact is still cryptographically valid but disallowed by current policy/revocation state.
- [ ] Exercise policy-engine outage/version skew and verify runtime admission remains fail closed.
- [ ] Add end-to-end correlation IDs so test evidence can trace artifact build/sign/attest/policy/admit/deploy/rollback events across components.
- [ ] Run fixtures in clean isolated test environments and archive exact component versions/config digests.
- [ ] Add compatibility ownership and coordinated release gates so adjacent-layer schema changes cannot land without GAP-07 conformance validation.

### Acceptance gates
- [ ] GAP-07 passes end-to-end tests against production-representative adjacent-layer implementations, not only mocks.
- [ ] Every consumed/produced cross-component field has a versioned contract and negative test coverage.
- [ ] Version skew, rollback, identity rotation, and policy failure scenarios produce deterministic safe outcomes.
- [ ] Cross-component evidence can reconstruct the full authorization/deployment path for one artifact digest.
- [ ] Adjacent-layer changes trigger automated GAP-07 compatibility tests before coordinated production release.

## 46. CI/CD Workflow Definitions

**Objective:** Encode build, test, security, evidence, signing, and release promotion gates in repository-level automation so production quality does not depend on manual execution.

### Engineering and security checklist
- [ ] Add version-controlled CI workflows for supported platforms/runtimes with least-privilege runner permissions.
- [ ] Pin third-party CI actions/tools/images by immutable digest or reviewed version and include them in dependency/provenance controls.
- [ ] Separate untrusted pull-request/test execution from trusted release-signing contexts and prevent secret exposure to untrusted code.
- [ ] Run syntax/static checks plus dependency-free core tests in normal and optimized runtime modes on every change.
- [ ] Run `pk_core` estate conformance tests in an environment where the authenticated dependency is available.
- [ ] Run negative/replay/tamper/revocation/rotation/freshness tests as mandatory security gates.
- [ ] Run schema validation, canonicalization/interoperability vectors, and compatibility-matrix validation.
- [ ] Run property/concurrency/fault tests at appropriate cadence and fuzz smoke tests on every change with longer scheduled fuzz campaigns.
- [ ] Run SBOM generation, dependency/vulnerability scans, secret scanning, license checks, and provenance generation.
- [ ] Run performance regression checks on controlled runners or dedicated benchmark stages where noisy shared runners are unsuitable.
- [ ] Build release artifacts reproducibly where feasible and calculate immutable digests before signing/attestation.
- [ ] Require protected release environment/manual approval or multi-party authorization before production signing/promotion.
- [ ] Generate DSSE/in-toto/SLSA build provenance and sign release/evidence manifests using production-approved key custody.
- [ ] Upload immutable release evidence, test reports, SBOM, provenance, signatures, and checksums to durable storage/registry.
- [ ] Prevent release/promotion when required jobs are skipped, stale, cancelled, failed, or executed against a different commit/artifact digest.

### Acceptance gates
- [ ] A clean clone can execute the declared CI qualification workflow without undocumented manual steps.
- [ ] Production secrets/signing authority are unreachable from untrusted PR/fork execution contexts.
- [ ] Required security tests and evidence generation are enforced as branch/release gates, not optional jobs.
- [ ] Release signatures/provenance are bound to the exact artifacts produced by the gated pipeline.
- [ ] CI definitions themselves are reviewed, versioned, dependency-scanned, and included in the release threat model/evidence.

## 47. Production Deployment Manifests

**Objective:** Define secure, reproducible Kubernetes/Wasm/microVM/service packaging and site bootstrap manifests with least privilege, network isolation, secrets policy, resource limits, and health semantics.

### Engineering and security checklist
- [ ] Define each supported deployment topology and package GAP-07 using immutable image/module/artifact digests rather than mutable tags.
- [ ] Run as non-root/non-administrator where possible with read-only root filesystem and minimal writable state mounts.
- [ ] Drop unnecessary Linux capabilities/privileges and define equivalent hardening for Windows/service or microVM deployments.
- [ ] Define dedicated service/workload identity with least-privilege access to KMS/HSM, trust distribution, policy, transparency, registry, audit, and telemetry endpoints.
- [ ] Store secrets only in approved secret-management mechanisms; prohibit embedded credentials in manifests, images, ConfigMaps, scripts, or environment dumps.
- [ ] Define network policy/firewall rules allowing only required egress/ingress destinations and ports.
- [ ] Configure CPU/memory/storage/file-descriptor/process limits aligned to benchmark/rate-limit evidence.
- [ ] Define liveness, readiness, startup, and dependency/degraded health probes with fail-closed readiness semantics.
- [ ] Mount trust/policy/configuration through signed/validated activation paths rather than directly trusting mutable filesystem content.
- [ ] Protect audit spool/trust state persistent volumes with appropriate durability, integrity, encryption, ownership, and backup policies.
- [ ] Define pod/service/container security context, seccomp/AppArmor/SELinux or platform-equivalent confinement where applicable.
- [ ] Define anti-affinity/redundancy/availability configuration while preserving consistent trust/policy state across replicas.
- [ ] Define site bootstrap that installs initial root trust through an authenticated out-of-band or otherwise strongly validated process.
- [ ] Add configuration-policy tests/linting that reject privileged mode, mutable tags, broad network access, missing limits, unapproved mounts, or insecure secret injection.
- [ ] Generate deployment provenance and bind released manifests/charts/templates to the GAP-07 release evidence bundle.

### Acceptance gates
- [ ] Production manifests deploy only authenticated immutable GAP-07 artifacts/configuration.
- [ ] Runtime identities and network access satisfy documented least-privilege requirements.
- [ ] Readiness does not become healthy without valid current trust/policy/time/dependency state required for admission.
- [ ] Deployment-hardening policy tests block known insecure configuration classes automatically.
- [ ] Site bootstrap/recovery manifests are tested from a clean environment and produce reproducible, auditable trust establishment.

## 48. Signed Release Artifacts for GAP-07 Itself

**Objective:** Close the bootstrap/self-hosting loop so GAP-07 binaries/packages, manifests, provenance, SBOMs, and updates can themselves be authenticated before installation or upgrade.

### Engineering and security checklist
- [ ] Define the root-of-trust/bootstrap mechanism used to verify the first trusted GAP-07 release on a clean site.
- [ ] Separate GAP-07 release-signing keys from ordinary artifact-signing identities and scope them exclusively to GAP-07 release/update authorization.
- [ ] Sign every production GAP-07 archive/image/package/installer by immutable digest using the approved asymmetric/KMS/HSM backend.
- [ ] Generate DSSE/in-toto/SLSA provenance for GAP-07 builds identifying source revision, builder, build type, materials, and parameters.
- [ ] Publish a signed SBOM and vulnerability status bound to each GAP-07 release digest.
- [ ] Publish transparency-log inclusion evidence/checkpoints for release signatures/attestations where transparency is required.
- [ ] Define a signed update manifest with release version, artifact digests, platform/architecture, minimum compatible version, schema migrations, and rollback constraints.
- [ ] Enforce monotonic/anti-rollback version policy for GAP-07 self-updates, with explicitly authorized recovery exceptions only.
- [ ] Verify GAP-07 release signatures/provenance/SBOM before extracting, installing, activating, or running migration code.
- [ ] Preserve the previously verified release for controlled recovery but prevent automatic downgrade to known vulnerable/revoked versions.
- [ ] Define signer/key rotation for GAP-07 release authority and securely distribute new verification trust before old key retirement.
- [ ] Define compromise response for the GAP-07 release-signing key, including revocation, affected-release identification, rebuild/re-sign, and bootstrap-key recovery.
- [ ] Bind deployment manifests and release evidence bundle to the same exact GAP-07 artifact digest.
- [ ] Add clean-room update tests from each supported prior version, including tampered archive, wrong signer, revoked signer, stale update manifest, and interrupted update.
- [ ] Document independent verification commands/tooling that operators can use before trusting a new GAP-07 release.

### Acceptance gates
- [ ] A clean site can establish trust in GAP-07 without trusting unsigned binaries or an unverified network download.
- [ ] Every production GAP-07 release is signed, attested, SBOM-bound, and tied to immutable release evidence.
- [ ] Tampered, unsigned, revoked, wrong-platform, or rollback releases are rejected before code execution.
- [ ] Release-key rotation/compromise recovery can occur without abandoning the established root of trust.
- [ ] Self-update verification is tested end to end and included in every release qualification cycle.

---

# Final Production-Readiness Exit Criteria

- [ ] All 12 P0 components are implemented, integrated, and validated end to end in a production-equivalent environment.
- [ ] No P0 item is satisfied solely by documentation, mock behavior, or an untested external assumption.
- [ ] Production signing uses approved asymmetric keys under KMS/HSM or equivalent protected custody; HMAC reference mode cannot satisfy production policy.
- [ ] Artifact signatures bind all required context and cannot be replayed across kind, environment, namespace, signer, or incompatible policy domain.
- [ ] Trust roots, revocations, policy, transparency checkpoints, and trusted-time state are versioned, authenticated, freshness-bounded, and rollback protected.
- [ ] Production admission is non-bypassable for every supported artifact execution/deployment path.
- [ ] OCI/Wasm/microVM/provider artifact bytes handed to runtime match the immutable digest actually verified.
- [ ] Required provenance, SBOM, vulnerability, transparency, and multi-signature evidence is bound to the same artifact subject and policy decision.
- [ ] Tamper-evident audit data is exported/anchored outside the node and can be independently verified.
- [ ] Key compromise, trust corruption, dependency outage, stale disconnected-site state, and time failure all have tested fail-closed behavior.
- [ ] P1 operational controls have owners, telemetry, alerts, runbooks, SLOs, and negative/failure-mode test evidence.
- [ ] P2 fuzz/property/concurrency/fault/performance/soak/DR programs execute to defined release thresholds with no unresolved critical/high findings.
- [ ] Independent security/cryptographic review has closed or formally dispositioned all critical/high findings.
- [ ] CI/CD enforces required tests, security scans, provenance, SBOM, evidence generation, and release signing from isolated trusted contexts.
- [ ] Production deployment manifests enforce immutable artifacts, least privilege, network constraints, resource bounds, secure configuration, and fail-closed readiness.
- [ ] Full estate conformance tests execute with authenticated `pk_core` and production-representative GAP-06/GAP-08/PLN-06/PLN-07/GAP-13 integrations.
- [ ] Requirements traceability maps mandatory controls to implementation, tests, external dependencies, owners, and immutable release evidence.
- [ ] Compatibility and migration policy covers every supported signature/provenance/trust/policy/runtime/registry version combination.
- [ ] GAP-07 itself is distributed as a signed, attested, SBOM-bound, rollback-protected release that can be verified from an established root of trust.
- [ ] A release acceptance authority can independently reproduce the production-readiness decision from the evidence bundle without relying on transient CI UI state.

## Recommended closure sequence

1. **Close P0 trust/crypto primitives first:** Components 1–7 and 12.
2. **Close P0 policy and enforcement:** Components 8–11.
3. **Integrate adjacent estate dependencies:** Components 44–48, especially `pk_core`, GAP-13, admission hooks, CI/CD, and deployment manifests.
4. **Close P1 operational controls:** Components 13–28.
5. **Execute P2 assurance/certification program:** Components 29–43.
6. **Freeze a release candidate and generate the complete release acceptance evidence bundle.**
7. **Run clean-room deployment, compromise, rollback, disconnected-site, DR, and fleet revocation exercises before declaring production readiness.**
