# INV-36 Control Transport v5.0.0 — Comprehensive Missing-Component Implementation Checklist

**Source audit:** `INV36_AUDIT_REPORT_5.0.0.md` and `INV36_AUDIT_MATRIX_5.0.0.json`  
**Repository:** INV-36 Control transport  
**Audited version:** 5.0.0  
**Audit date:** 2026-09-22  
**Purpose:** Convert every repository-level missing component identified in the v5.0.0 second-pass audit into an implementation-grade, verifiable completion checklist.

## Completion semantics

- `[ ]` means no acceptable repository-local evidence has yet been recorded for the item.
- A checkbox should be marked complete only when implementation **and** verification evidence exist; design text alone does not close an implementation item.
- **P0** — Release-blocking / security- or correctness-critical. Close before production certification.
- **P1** — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.
- Evidence should be reproducible from a clean checkout and, for certification gates, machine-readable and bound to the exact source/artifact digest.
- `SKIP`, missing dependencies, malformed evidence, or unavailable test infrastructure must not be treated as `PASS` for production certification unless a formally approved waiver explicitly covers the condition.

## Global definition of done

- [ ] Every missing component below has a named owner and target release.
- [ ] Every related INV-36 control has a traceability entry pointing to implementation, tests, and evidence.
- [ ] Every security-sensitive interface has a threat-model entry and negative/adversarial tests.
- [ ] Every externally visible contract is versioned and compatibility-tested.
- [ ] Every queue, buffer, concurrency surface, retry loop, and externally supplied length has a documented hard bound.
- [ ] Every production dependency has defined unavailable/degraded behavior.
- [ ] Every operationally significant change emits bounded, redacted telemetry and security-sensitive changes emit tamper-evident audit events.
- [ ] All mandatory CI, platform compatibility, integration, security, performance, and production-exit gates pass from a clean checkout.
- [ ] Release evidence is bound to source and artifact digests and retained according to governance policy.

## Component index

| ID | Priority | Missing component | Related controls |
|---|---:|---|---|
| MC-01 | P0 | External estate core / gate runtime (`pk_core`) | INV-36-C020, INV-36-C090, INV-36-C100 |
| MC-02 | P1 | `MASTER.md` source prompt/workflow corpus | Repository governance/provenance |
| MC-03 | P0 | Real virtio-vsock transport adapter | INV-36-C010, INV-36-C021, INV-36-C030, INV-36-C031 |
| MC-04 | P0 | Authenticated session-establishment adapter | INV-36-C023, INV-36-C044, INV-36-C048 |
| MC-05 | P0 | Key custody and rotation integration | INV-36-C039, INV-36-C047, INV-36-C048 |
| MC-06 | P0 | Typed external protocol schema / IDL | INV-36-C022, INV-36-C082 |
| MC-07 | P0 | Authorization / tenant policy layer | INV-36-C024, INV-36-C042, INV-36-C046 |
| MC-08 | P0 | Runtime configuration subsystem | INV-36-C032, INV-36-C033, INV-36-C034, INV-36-C035, INV-36-C036, INV-36-C037, INV-36-C038 |
| MC-09 | P0 | Health, backpressure and failure-control subsystem | INV-36-C052, INV-36-C053, INV-36-C054, INV-36-C055, INV-36-C056 |
| MC-10 | P1 | Persistent/restart/session recovery design | INV-36-C057 |
| MC-11 | P0 | Quarantine / emergency isolation control | INV-36-C059, INV-36-C092 |
| MC-12 | P1 | Production observability pipeline | INV-36-C071, INV-36-C072, INV-36-C073, INV-36-C074, INV-36-C075, INV-36-C076, INV-36-C077, INV-36-C078, INV-36-C079, INV-36-C080 |
| MC-13 | P1 | Performance certification suite | INV-36-C061, INV-36-C062, INV-36-C063, INV-36-C064, INV-36-C065, INV-36-C066, INV-36-C067, INV-36-C068, INV-36-C069, INV-36-C070 |
| MC-14 | P0 | Protocol fuzzing / property-based robustness suite | INV-36-C085 |
| MC-15 | P1 | Platform/hypervisor compatibility test matrix | INV-36-C084, INV-36-C093 |
| MC-16 | P1 | Integration / disaster / soak / fleet-scale suites | INV-36-C030, INV-36-C083, INV-36-C088, INV-36-C089 |
| MC-17 | P0 | Supply-chain integrity controls | INV-36-C045, INV-36-C090 |
| MC-18 | P0 | Tamper-evident security audit log | INV-36-C049 |
| MC-19 | P1 | Formal architecture decision record (ADR) | INV-36-C010 |
| MC-20 | P0 | Requirements specification + traceability matrix | INV-36-C011, INV-36-C012, INV-36-C013, INV-36-C014, INV-36-C015, INV-36-C016, INV-36-C017, INV-36-C018, INV-36-C019, INV-36-C020 |
| MC-21 | P0 | Operational release / governance pack | INV-36-C009, INV-36-C092, INV-36-C094, INV-36-C097, INV-36-C098, INV-36-C099, INV-36-C100 |
| MC-22 | P0 | Explicit software license | Repository governance/provenance |
| MC-23 | P0 | Continuous integration (CI) workflow | INV-36-C070, INV-36-C090, INV-36-C100 |

## MC-01 — External estate core / gate runtime (`pk_core`)

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C020, INV-36-C090, INV-36-C100  
**Target outcome:** Make the repository independently capable of executing the estate-wide 100-control gate, producing deterministic machine-readable evidence, and failing closed when gate infrastructure is absent or incompatible.

### Related audit requirements

- **INV-36-C020 — MISSING:** Maintain a requirements traceability matrix from each Control transport requirement to implementation and verification evidence.
- **INV-36-C090 — MISSING:** Require machine-readable acceptance evidence before certifying a Control transport release for production.
- **INV-36-C100 — MISSING:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Interface and dependency contract

- [ ] **MC-01.001** — Define the supported `pk_core` package/module name, minimum and maximum compatible versions, Python ABI range, and semantic-versioning policy.
- [ ] **MC-01.002** — Enumerate every imported symbol used by INV-36, including call signatures, return types, exceptions, side effects, and evidence formats.
- [ ] **MC-01.003** — Define whether `pk_core` is a runtime dependency, development/certification dependency, or optional integration and encode that decision in package metadata.
- [ ] **MC-01.004** — Create a compatibility shim or adapter boundary so repository code does not import estate internals directly from multiple modules.
- [ ] **MC-01.005** — Fail with a typed, actionable error when a required gate capability is unavailable; never silently mark a missing gate as passing.
- [ ] **MC-01.006** — Define deterministic behavior for mismatched gate schema versions and unsupported evidence schema revisions.

### Gate execution and evidence

- [ ] **MC-01.007** — Implement a repository-local command such as `python -m inv36_control_transport.audit` that invokes the gate through the adapter.
- [ ] **MC-01.008** — Produce a machine-readable gate result with repository version, commit/source digest, timestamp, environment fingerprint, requirement IDs, status, evidence references, and tool versions.
- [ ] **MC-01.009** — Use an explicit three-state or four-state result model such as PASS/FAIL/SKIP/ERROR; prohibit conversion of SKIP/ERROR into PASS.
- [ ] **MC-01.010** — Emit stable exit codes for pass, requirement failure, infrastructure error, configuration error, and evidence-validation error.
- [ ] **MC-01.011** — Validate the returned evidence document against a checked-in schema before accepting it.
- [ ] **MC-01.012** — Bind every gate run to the exact source/archive digest being certified.
- [ ] **MC-01.013** — Preserve raw gate output as an immutable build artifact for audit review.

### Reproducibility and isolation

- [ ] **MC-01.014** — Pin the gate dependency using hashes or an immutable artifact digest for certification runs.
- [ ] **MC-01.015** — Provide an offline or hermetic path for environments that cannot reach public package registries.
- [ ] **MC-01.016** — Run the gate in a clean environment with only declared dependencies installed.
- [ ] **MC-01.017** — Capture OS, Python, architecture, cryptography backend, compiler/build backend, and relevant hypervisor capabilities in evidence metadata.
- [ ] **MC-01.018** — Ensure gate results are deterministic for an unchanged source tree and normalized environment.
- [ ] **MC-01.019** — Add a negative test proving the build/certification pipeline fails when `pk_core` is absent for a production-certification job.

### Testing and acceptance

- [ ] **MC-01.020** — Unit-test the adapter against a fake gate runtime covering pass, fail, skip, malformed result, timeout, and exception paths.
- [ ] **MC-01.021** — Integration-test against the approved real `pk_core` version in CI.
- [ ] **MC-01.022** — Add schema-compatibility tests across every supported evidence schema version.
- [ ] **MC-01.023** — Test timeout/cancellation behavior so a hung estate gate cannot deadlock the release pipeline.
- [ ] **MC-01.024** — Add a golden evidence fixture and verify stable serialization.
- [ ] **MC-01.025** — Require successful gate execution as a production-release prerequisite.
- [ ] **MC-01.026** — Document the exact owner and escalation path for failures in the external gate runtime.

### Required closure evidence

- [ ] **MC-01.027** — A reviewed design/specification for External estate core / gate runtime (`pk_core`) with explicit owner and version.
- [ ] **MC-01.028** — Repository-local implementation or authoritative external dependency declaration for External estate core / gate runtime (`pk_core`).
- [ ] **MC-01.029** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-01.030** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-01.031** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-01.032** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-01: 32.**

## MC-02 — `MASTER.md` source prompt/workflow corpus

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** No direct Cxxx mapping; repository-level provenance/governance gap  
**Target outcome:** Restore or explicitly retire the authoritative source artifact referenced by prior repository documentation, with provenance, integrity, and reproducibility controls.

### Provenance and source-of-truth

- [ ] **MC-02.001** — Locate the original `MASTER.md` from the authoritative upstream/source package; do not reconstruct it from memory or infer missing content.
- [ ] **MC-02.002** — Record source repository/path, source version or commit, retrieval date, and cryptographic digest.
- [ ] **MC-02.003** — Determine whether `MASTER.md` is normative product input, historical documentation, generated material, or an obsolete reference.
- [ ] **MC-02.004** — If normative, designate a single canonical owner and source location.
- [ ] **MC-02.005** — If obsolete, remove all claims that it is carried verbatim and document the replacement source of truth.
- [ ] **MC-02.006** — Preserve any applicable copyright, attribution, and licensing notices from the original source.

### Integrity and lifecycle

- [ ] **MC-02.007** — Add a checksum verification step for the authoritative corpus.
- [ ] **MC-02.008** — Prevent unreviewed edits by requiring code review/approval for changes to normative workflow text.
- [ ] **MC-02.009** — Version the corpus independently if its lifecycle differs from the transport package.
- [ ] **MC-02.010** — Create a changelog entry whenever normative requirements or workflows change.
- [ ] **MC-02.011** — Define whether generated artifacts must embed the `MASTER.md` digest for traceability.
- [ ] **MC-02.012** — Archive superseded revisions where audit retention requires historical reconstruction.

### Validation and consistency

- [ ] **MC-02.013** — Add a repository test that fails if documentation claims `MASTER.md` exists but the file is absent.
- [ ] **MC-02.014** — Validate internal links, referenced control IDs, version names, and file paths.
- [ ] **MC-02.015** — Check that requirements derived from the corpus are represented in the traceability matrix.
- [ ] **MC-02.016** — Check for contradictory requirements between the corpus, README, SECURITY, compatibility documentation, and code contracts.
- [ ] **MC-02.017** — Generate a machine-readable index of normative sections if automated gate tooling consumes the corpus.
- [ ] **MC-02.018** — Document the exact regeneration/synchronization procedure.

### Acceptance evidence

- [ ] **MC-02.019** — Provide the authoritative file or an explicit deprecation record.
- [ ] **MC-02.020** — Provide source and SHA-256 digest metadata.
- [ ] **MC-02.021** — Provide a consistency-test result proving documentation and repository contents agree.
- [ ] **MC-02.022** — Provide reviewer approval establishing that no source material was fabricated during restoration.

### Required closure evidence

- [ ] **MC-02.023** — A reviewed design/specification for `MASTER.md` source prompt/workflow corpus with explicit owner and version.
- [ ] **MC-02.024** — Repository-local implementation or authoritative external dependency declaration for `MASTER.md` source prompt/workflow corpus.
- [ ] **MC-02.025** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-02.026** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-02.027** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-02.028** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-02: 28.**

## MC-03 — Real virtio-vsock transport adapter

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C010, INV-36-C021, INV-36-C030, INV-36-C031  
**Target outcome:** Implement the actual host/guest virtio-vsock data path beneath the hardened PK_CTRL_FRAME/2 session layer, with bounded resource use, reconnect behavior, and interoperable endpoint semantics.

### Related audit requirements

- **INV-36-C010 — MISSING:** Approve an architecture decision record for Control transport, its technologies (virtio-vsock), and its function (Lightweight host/guest control traffic).
- **INV-36-C021 — PARTIAL:** Enumerate every API, WIT contract, RPC, event, file, device, hypervisor, or control-plane boundary exposed by Control transport.
- **INV-36-C030 — MISSING:** Create automated integration tests proving Control transport interoperates with adjacent architectural layers.
- **INV-36-C031 — MISSING:** Select and pin approved implementations, versions, or specifications for Control transport: virtio-vsock.

### Platform and socket design

- [ ] **MC-03.001** — Select the approved virtio-vsock specification/runtime targets and document Linux/Windows/macOS applicability; mark unsupported platforms explicitly.
- [ ] **MC-03.002** — Implement an adapter around `AF_VSOCK`/equivalent rather than embedding socket operations in cryptographic/session code.
- [ ] **MC-03.003** — Define host CID, guest CID, port allocation, wildcard/listener behavior, privilege requirements, and collision handling.
- [ ] **MC-03.004** — Define client/server roles and which side initiates control sessions for every deployment mode.
- [ ] **MC-03.005** — Use nonblocking or bounded-blocking I/O with explicit connect/read/write deadlines.
- [ ] **MC-03.006** — Handle partial reads/writes, `EINTR`, `EAGAIN`, reset, peer shutdown, and short-write semantics correctly.
- [ ] **MC-03.007** — Never assume message boundaries from stream reads; implement length-delimited frame extraction over the byte stream.
- [ ] **MC-03.008** — Enforce maximum encoded-frame size before allocating payload buffers.
- [ ] **MC-03.009** — Define socket buffer limits and backlog bounds.
- [ ] **MC-03.010** — Close descriptors deterministically on every failure path and during cancellation.

### Framing and session integration

- [ ] **MC-03.011** — Preserve PK_CTRL_FRAME/2 authentication boundaries exactly; do not decrypt before a complete bounded frame has been received.
- [ ] **MC-03.012** — Associate one established cryptographic session with a clearly defined socket lifetime.
- [ ] **MC-03.013** — Define whether reconnect creates a new session ID and new traffic keys; default to re-establishment rather than sequence reuse.
- [ ] **MC-03.014** — Prevent concurrent readers from consuming bytes from the same stream unless a single demultiplexer owns framing.
- [ ] **MC-03.015** — Serialize outbound frames or otherwise preserve strict monotonically increasing sequence order.
- [ ] **MC-03.016** — Reject legacy PK_CTRL_FRAME/1 peers before application payload processing.
- [ ] **MC-03.017** — Provide clean EOF semantics distinguishing graceful peer shutdown from truncation or transport failure.
- [ ] **MC-03.018** — Expose structured transport error categories without leaking secrets.

### Reliability and backpressure

- [ ] **MC-03.019** — Bound connection attempts and retry only transport-safe operations.
- [ ] **MC-03.020** — Use exponential backoff with jitter for reconnect storms.
- [ ] **MC-03.021** — Propagate send-queue saturation to callers rather than growing unbounded memory.
- [ ] **MC-03.022** — Define high-water/low-water marks for send and receive queues.
- [ ] **MC-03.023** — Implement a maximum concurrent-connection/session limit per process/node/tenant as applicable.
- [ ] **MC-03.024** — Detect stalled peers using deadline/heartbeat policy without weakening security invariants.
- [ ] **MC-03.025** — Ensure shutdown/drain stops new work, flushes only bounded eligible work, and then closes.
- [ ] **MC-03.026** — Protect against accept-loop exhaustion and malicious connection churn.

### Security

- [ ] **MC-03.027** — Apply least privilege to device/socket access and document required capabilities.
- [ ] **MC-03.028** — Do not trust CID/port identity as cryptographic identity; require authenticated session establishment above vsock.
- [ ] **MC-03.029** — Validate every length, version, type, and reserved field before use.
- [ ] **MC-03.030** — Test malformed length prefixes, huge advertised frames, truncated frames, duplicate frames, reordered frames, and random ciphertext.
- [ ] **MC-03.031** — Rate-limit or isolate repeated authentication failures.
- [ ] **MC-03.032** — Prevent plaintext or key material from appearing in socket debug logs.
- [ ] **MC-03.033** — Document the trust boundary between hypervisor-provided transport identity and application identity.

### Testing and certification

- [ ] **MC-03.034** — Create loopback/unit tests using a deterministic fake byte-stream transport.
- [ ] **MC-03.035** — Create Linux AF_VSOCK integration tests using a supported VM/microVM environment.
- [ ] **MC-03.036** — Exercise host-to-guest, guest-to-host, abrupt reset, reboot, suspend/resume where supported, and port-unavailable paths.
- [ ] **MC-03.037** — Run concurrent connection tests and verify sequence isolation between sessions.
- [ ] **MC-03.038** — Add throughput and p50/p95/p99 latency benchmarks for representative control message sizes.
- [ ] **MC-03.039** — Add fault injection for partial read/write, delayed peer, dropped connection, and mid-frame reset.
- [ ] **MC-03.040** — Add interoperability fixtures proving compatible peers can exchange frames across supported protocol versions.
- [ ] **MC-03.041** — Require a real-vsock smoke test in platform certification before production release.

### Required closure evidence

- [ ] **MC-03.042** — A reviewed design/specification for Real virtio-vsock transport adapter with explicit owner and version.
- [ ] **MC-03.043** — Repository-local implementation or authoritative external dependency declaration for Real virtio-vsock transport adapter.
- [ ] **MC-03.044** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-03.045** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-03.046** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-03.047** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-03: 47.**

## MC-04 — Authenticated session-establishment adapter

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C023, INV-36-C044, INV-36-C048  
**Target outcome:** Replace the current assumption of an already-authenticated shared secret with a concrete mutual-authentication and key-establishment protocol bound to peer identity, session context, and policy.

### Related audit requirements

- **INV-36-C023 — PARTIAL:** Define authentication requirements at each Control transport boundary.
- **INV-36-C044 — PARTIAL:** Authenticate nodes, peers, artifacts, providers, and control-plane actors before trust is granted.
- **INV-36-C048 — MISSING:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

### Protocol selection and threat model

- [ ] **MC-04.001** — Define the authenticated key-establishment protocol and security goals: mutual authentication, forward secrecy if required, replay resistance, channel binding, downgrade resistance, and identity binding.
- [ ] **MC-04.002** — Select approved primitives/protocols (for example TLS 1.3 over vsock, Noise pattern, or an attestation-bound ECDH design) and record them in the ADR.
- [ ] **MC-04.003** — Define attacker capabilities including hostile guest, hostile host process, replaying relay, stale credential, compromised tenant workload, and time-service failure.
- [ ] **MC-04.004** — Define peer identity namespaces and canonical encoding.
- [ ] **MC-04.005** — Define trust roots, certificate/attestation authority ownership, and rotation policy.
- [ ] **MC-04.006** — Explicitly define what information is authenticated by the hypervisor versus cryptographically proven end-to-end.

### Handshake implementation

- [ ] **MC-04.007** — Generate ephemeral key material using an approved CSPRNG.
- [ ] **MC-04.008** — Bind transcript hash to protocol version, role, peer identities, session ID, deployment/tenant context where appropriate, and negotiated capabilities.
- [ ] **MC-04.009** — Validate certificates/attestation claims against approved trust anchors and policy before accepting the session.
- [ ] **MC-04.010** — Perform strict algorithm negotiation; reject unsupported, deprecated, unknown, or weaker-than-policy suites.
- [ ] **MC-04.011** — Use unique fresh session IDs and reject reuse where protocol policy requires uniqueness.
- [ ] **MC-04.012** — Derive the existing directional transport keys from the authenticated exporter/handshake secret rather than from unmanaged caller input.
- [ ] **MC-04.013** — Erase or release ephemeral/private secret references as soon as practical.
- [ ] **MC-04.014** — Enforce handshake size and time limits.
- [ ] **MC-04.015** — Use typed failure codes for identity failure, trust-chain failure, attestation failure, expiry, revocation, negotiation failure, timeout, and policy denial.

### Availability and dependency failure

- [ ] **MC-04.016** — Define behavior when CA, attestation verifier, KMS, clock, revocation service, or policy service is unavailable.
- [ ] **MC-04.017** — Fail closed for identity-integrity failures; separately define safe cached/offline behavior if explicitly approved.
- [ ] **MC-04.018** — Define maximum acceptable clock skew and how time uncertainty affects certificate/claim validation.
- [ ] **MC-04.019** — Prevent retry storms against unavailable identity infrastructure.
- [ ] **MC-04.020** — Define reauthentication triggers after credential/key rotation or long-lived sessions.
- [ ] **MC-04.021** — Define handshake cancellation and cleanup on peer disconnect.

### Testing and evidence

- [ ] **MC-04.022** — Create positive mutual-authentication test vectors.
- [ ] **MC-04.023** — Test wrong identity, wrong trust root, expired credential, revoked credential, malformed certificate/claim, replayed transcript, duplicate session ID, downgrade attempt, and MITM transcript modification.
- [ ] **MC-04.024** — Test simultaneous handshakes and resource exhaustion.
- [ ] **MC-04.025** — Add property tests for transcript binding and role separation.
- [ ] **MC-04.026** — Capture machine-readable evidence of negotiated algorithm, peer identity class, trust-root version, and handshake result without exposing secrets.
- [ ] **MC-04.027** — Require security review of the protocol and implementation before production certification.

### Required closure evidence

- [ ] **MC-04.028** — A reviewed design/specification for Authenticated session-establishment adapter with explicit owner and version.
- [ ] **MC-04.029** — Repository-local implementation or authoritative external dependency declaration for Authenticated session-establishment adapter.
- [ ] **MC-04.030** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-04.031** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-04.032** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-04.033** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-04: 33.**

## MC-05 — Key custody and rotation integration

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C039, INV-36-C047, INV-36-C048  
**Target outcome:** Move long-lived key material into managed custody, define key epochs and rotation/revocation semantics, and ensure transport sessions respond safely to key-service failures.

### Related audit requirements

- **INV-36-C039 — PARTIAL:** Keep credentials and secret material out of ordinary Control transport configuration and diagnostics.
- **INV-36-C047 — PARTIAL:** Encrypt sensitive Control transport data in transit and at rest with managed key rotation.
- **INV-36-C048 — MISSING:** Define safe behavior when identity, attestation, policy, key, or time services are unavailable.

### Key inventory and ownership

- [ ] **MC-05.001** — Inventory every key/secret: trust roots, identity keys, handshake credentials, traffic secrets, signing keys, audit-log keys, and test keys.
- [ ] **MC-05.002** — Designate owner, purpose, storage class, rotation interval, destruction policy, and allowed consumers for each key class.
- [ ] **MC-05.003** — Prohibit production private keys from source control, ordinary config files, logs, crash dumps, and command-line arguments.
- [ ] **MC-05.004** — Define environment-specific key namespaces so test/dev credentials cannot authenticate to production.
- [ ] **MC-05.005** — Define key identifiers/epochs that can be logged safely without exposing secret material.

### Custody integration

- [ ] **MC-05.006** — Integrate an approved KMS/HSM/secret-store interface behind a provider abstraction.
- [ ] **MC-05.007** — Use workload identity/least-privilege access to request keys; avoid static bootstrap secrets where possible.
- [ ] **MC-05.008** — Validate returned key metadata, algorithm, state, and version before use.
- [ ] **MC-05.009** — Cache only what is necessary, for a bounded duration, with explicit invalidation.
- [ ] **MC-05.010** — Prevent secret values from being serialized in repr, exception strings, telemetry, evidence, or diagnostics.
- [ ] **MC-05.011** — Use memory-hardening/zeroization facilities where realistically supported, while documenting language-runtime limits.

### Rotation and revocation

- [ ] **MC-05.012** — Define key-epoch negotiation and how active sessions transition to new epochs.
- [ ] **MC-05.013** — Implement rotation without accepting mixed or ambiguous epochs.
- [ ] **MC-05.014** — Define maximum session age and mandatory rekey/rehandshake triggers.
- [ ] **MC-05.015** — Implement emergency revocation that prevents new sessions immediately and terminates/renews existing sessions according to policy.
- [ ] **MC-05.016** — Define overlap/grace windows and ensure expired epochs are rejected after the window.
- [ ] **MC-05.017** — Test rollback to an older key epoch and ensure it is denied unless an explicit recovery procedure authorizes it.
- [ ] **MC-05.018** — Record rotation/revocation events in tamper-evident audit logs.

### Failure handling and tests

- [ ] **MC-05.019** — Define behavior for KMS unavailable, permission denied, throttled, stale replica, corrupted response, and clock failure.
- [ ] **MC-05.020** — Use bounded retries with jitter for transient key-service failures.
- [ ] **MC-05.021** — Fail closed when key identity or integrity cannot be verified.
- [ ] **MC-05.022** — Test scheduled rotation under active traffic.
- [ ] **MC-05.023** — Test emergency revocation during active traffic.
- [ ] **MC-05.024** — Test restart with key epoch changes.
- [ ] **MC-05.025** — Test that historical ciphertext cannot be decrypted with unauthorized new or unrelated tenant keys.
- [ ] **MC-05.026** — Produce evidence showing key identifiers/epochs used for certification without disclosing key bytes.

### Required closure evidence

- [ ] **MC-05.027** — A reviewed design/specification for Key custody and rotation integration with explicit owner and version.
- [ ] **MC-05.028** — Repository-local implementation or authoritative external dependency declaration for Key custody and rotation integration.
- [ ] **MC-05.029** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-05.030** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-05.031** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-05.032** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-05: 32.**

## MC-06 — Typed external protocol schema / IDL

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C022, INV-36-C082  
**Target outcome:** Move externally visible wire contracts from implicit Python structure into a versioned, language-neutral schema with generated validation and compatibility tests.

### Related audit requirements

- **INV-36-C022 — PARTIAL:** Use versioned typed schemas for all externally visible Control transport contracts.
- **INV-36-C082 — PARTIAL:** Create contract tests for every public Control transport interface.

### Schema definition

- [ ] **MC-06.001** — Select an IDL/serialization format appropriate for the binary control plane and document the choice (e.g., protobuf, FlatBuffers, Cap’n Proto, CDDL/CBOR, WIT plus explicit framing).
- [ ] **MC-06.002** — Define PK_CTRL_FRAME/2 fields, numeric widths, endianness, length bounds, required/optional semantics, reserved fields, and canonical encoding.
- [ ] **MC-06.003** — Define message-type identifiers and a registry process preventing collisions.
- [ ] **MC-06.004** — Define structured error schema with stable machine-readable codes and bounded diagnostic fields.
- [ ] **MC-06.005** — Define capability/feature negotiation fields if protocol evolution requires them.
- [ ] **MC-06.006** — Reserve extension ranges and specify unknown-field handling.
- [ ] **MC-06.007** — Prohibit ambiguous encodings and duplicate semantic representations where signatures/MACs depend on canonical bytes.

### Generation and implementation

- [ ] **MC-06.008** — Generate codec/binding code from the schema where tooling allows; minimize handwritten duplicate models.
- [ ] **MC-06.009** — Check generated-code/tool versions into reproducible build metadata.
- [ ] **MC-06.010** — Validate decoded lengths and allocation limits before materializing large objects.
- [ ] **MC-06.011** — Keep cryptographic associated-data construction tied to a canonical schema representation.
- [ ] **MC-06.012** — Add schema-version constants generated from or cross-checked against the IDL.
- [ ] **MC-06.013** — Create migration adapters only for explicitly supported prior versions; reject unsupported versions deterministically.

### Compatibility policy

- [ ] **MC-06.014** — Define backward/forward compatibility rules per field change type.
- [ ] **MC-06.015** — Define whether adding optional fields is allowed within a major protocol version.
- [ ] **MC-06.016** — Define deprecation windows and removal criteria.
- [ ] **MC-06.017** — Publish golden binary fixtures for every supported protocol version.
- [ ] **MC-06.018** — Add cross-language fixture tests if non-Python peers are expected.
- [ ] **MC-06.019** — Verify unknown-field behavior, default handling, canonical ordering, and reserved-value rejection.

### Testing and acceptance

- [ ] **MC-06.020** — Add contract tests generated from the schema.
- [ ] **MC-06.021** — Fuzz the decoder and schema boundary.
- [ ] **MC-06.022** — Test min/max sizes, zero-length legal/illegal fields, truncated encoding, duplicate fields, unknown types, and malicious length claims.
- [ ] **MC-06.023** — Add a compatibility test that compares current generated fixtures against previous released fixtures.
- [ ] **MC-06.024** — Fail CI if generated code is stale relative to the schema.
- [ ] **MC-06.025** — Publish the schema and generated documentation as release artifacts.

### Required closure evidence

- [ ] **MC-06.026** — A reviewed design/specification for Typed external protocol schema / IDL with explicit owner and version.
- [ ] **MC-06.027** — Repository-local implementation or authoritative external dependency declaration for Typed external protocol schema / IDL.
- [ ] **MC-06.028** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-06.029** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-06.030** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-06.031** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-06: 31.**

## MC-07 — Authorization / tenant policy layer

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C024, INV-36-C042, INV-36-C046  
**Target outcome:** Enforce explicit least-privilege authorization for every control operation and tenant/workload boundary after peer authentication.

### Related audit requirements

- **INV-36-C024 — MISSING:** Define authorization and explicit capability requirements at each Control transport boundary.
- **INV-36-C042 — MISSING:** Apply least privilege to every identity and capability used by Control transport.
- **INV-36-C046 — MISSING:** Enforce tenant/workload isolation across Control transport execution, memory, state, network, and device boundaries as applicable.

### Policy model

- [ ] **MC-07.001** — Enumerate every control operation, resource type, target scope, and side effect exposed by the transport.
- [ ] **MC-07.002** — Define principals (node, host agent, guest agent, tenant, workload, operator, service) and canonical identity claims.
- [ ] **MC-07.003** — Define capabilities/permissions at operation granularity rather than relying on broad authenticated-peer trust.
- [ ] **MC-07.004** — Define tenant/workload scoping rules and deny cross-tenant access by default.
- [ ] **MC-07.005** — Define policy precedence and explicit deny semantics.
- [ ] **MC-07.006** — Define policy versioning, rollout, expiry, and rollback semantics.
- [ ] **MC-07.007** — Define authorization behavior when policy state is unavailable or stale; security-sensitive operations should fail closed.

### Enforcement architecture

- [ ] **MC-07.008** — Place a single mandatory authorization decision point before application side effects.
- [ ] **MC-07.009** — Pass authenticated identity and immutable request context into authorization; never trust caller-supplied tenant IDs without binding them to identity.
- [ ] **MC-07.010** — Use typed decision outputs: allow/deny plus reason code and policy version.
- [ ] **MC-07.011** — Prevent TOCTOU gaps between authorization and resource mutation where relevant.
- [ ] **MC-07.012** — Constrain administrative bypass paths and require explicit break-glass authorization.
- [ ] **MC-07.013** — Rate-limit repeated denied operations to reduce abuse without hiding legitimate denials.
- [ ] **MC-07.014** — Ensure the relay cannot elevate privilege by rewriting routing metadata.

### Isolation and security tests

- [ ] **MC-07.015** — Test same-tenant allowed cases and cross-tenant denial cases.
- [ ] **MC-07.016** — Test confused-deputy scenarios in which an authorized intermediary is asked to act on another tenant’s resource.
- [ ] **MC-07.017** — Test privilege escalation through message-type substitution, malformed identifiers, wildcard scopes, and stale policy caches.
- [ ] **MC-07.018** — Test revoked permissions during active sessions.
- [ ] **MC-07.019** — Test policy downgrade/rollback attempts.
- [ ] **MC-07.020** — Test default-deny behavior for unknown operations or identities.
- [ ] **MC-07.021** — Fuzz authorization inputs and resource identifiers.

### Audit and evidence

- [ ] **MC-07.022** — Emit tamper-evident audit events for security-sensitive allow/deny decisions.
- [ ] **MC-07.023** — Include policy version and stable reason code in diagnostics without exposing sensitive policy internals.
- [ ] **MC-07.024** — Provide a policy-conformance test suite and machine-readable coverage report.
- [ ] **MC-07.025** — Map each public operation to its required capability in the traceability matrix.
- [ ] **MC-07.026** — Require security-owner approval for any wildcard/admin capability.

### Required closure evidence

- [ ] **MC-07.027** — A reviewed design/specification for Authorization / tenant policy layer with explicit owner and version.
- [ ] **MC-07.028** — Repository-local implementation or authoritative external dependency declaration for Authorization / tenant policy layer.
- [ ] **MC-07.029** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-07.030** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-07.031** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-07.032** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-07: 32.**

## MC-08 — Runtime configuration subsystem

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C032, INV-36-C033, INV-36-C034, INV-36-C035, INV-36-C036, INV-36-C037, INV-36-C038  
**Target outcome:** Provide declarative, validated, provenance-aware, atomically activatable configuration with secure defaults and deterministic rollback.

### Related audit requirements

- **INV-36-C032 — MISSING:** Separate immutable artifacts from mutable configuration and state for Control transport.
- **INV-36-C033 — MISSING:** Define declarative configuration and secure defaults for Control transport.
- **INV-36-C034 — MISSING:** Validate configuration before activation and fail closed on security-critical errors.
- **INV-36-C035 — MISSING:** Support site- and environment-specific configuration without rebuilding immutable artifacts.
- **INV-36-C036 — MISSING:** Record configuration provenance, version, author, and activation time.
- **INV-36-C037 — MISSING:** Apply atomic or transactional configuration updates where partial application is unsafe.
- **INV-36-C038 — MISSING:** Define automatic and operator-driven rollback for failed Control transport changes.

### Configuration model

- [ ] **MC-08.001** — Define a versioned configuration schema covering endpoints, limits, timeouts, retry policy, observability, policy references, feature flags, and approved crypto/session settings.
- [ ] **MC-08.002** — Separate immutable application artifacts from mutable configuration and runtime state.
- [ ] **MC-08.003** — Define secure production defaults and explicitly label unsafe/development-only settings.
- [ ] **MC-08.004** — Define environment/site overlays with deterministic precedence rules.
- [ ] **MC-08.005** — Prohibit secrets in ordinary configuration; use secret references/handles instead.
- [ ] **MC-08.006** — Define strict units and ranges for durations, byte sizes, counts, rates, and percentages.
- [ ] **MC-08.007** — Reject unknown fields in security-sensitive configuration unless forward-compatibility policy explicitly allows them.

### Validation and activation

- [ ] **MC-08.008** — Validate syntax, schema, cross-field constraints, referenced resources, and security policy before activation.
- [ ] **MC-08.009** — Perform semantic validation such as high-water mark > low-water mark and frame limit <= absolute implementation limit.
- [ ] **MC-08.010** — Fail closed on invalid security-critical configuration.
- [ ] **MC-08.011** — Build an immutable in-memory snapshot and swap it atomically.
- [ ] **MC-08.012** — Ensure readers observe either old or new configuration, never partially applied state.
- [ ] **MC-08.013** — Define which fields are hot-reloadable and which require restart/rehandshake.
- [ ] **MC-08.014** — Provide dry-run/validate-only mode.
- [ ] **MC-08.015** — Protect configuration activation with authorization and concurrency control.

### Provenance and rollback

- [ ] **MC-08.016** — Record config version, content digest, source, author/actor, approval, activation time, and target scope.
- [ ] **MC-08.017** — Keep previous known-good snapshots for bounded rollback history.
- [ ] **MC-08.018** — Implement automatic rollback when activation health checks fail within a defined window.
- [ ] **MC-08.019** — Implement operator-driven rollback to a specific approved version.
- [ ] **MC-08.020** — Prevent rollback to revoked/known-vulnerable configuration.
- [ ] **MC-08.021** — Emit audit events for validation failure, activation, rollback, and rejected rollback.
- [ ] **MC-08.022** — Expose active configuration version and digest via health/diagnostic interfaces.

### Testing

- [ ] **MC-08.023** — Unit-test every validation rule and boundary value.
- [ ] **MC-08.024** — Property-test serialization/deserialization and overlay merge determinism.
- [ ] **MC-08.025** — Test concurrent readers during activation.
- [ ] **MC-08.026** — Test crash during activation and verify recovery to old or new complete snapshot.
- [ ] **MC-08.027** — Test automatic rollback triggers and rollback failure handling.
- [ ] **MC-08.028** — Test malicious/oversized configuration and path/reference traversal where applicable.
- [ ] **MC-08.029** — Add golden configuration fixtures for minimum, typical, maximum, and invalid profiles.

### Required closure evidence

- [ ] **MC-08.030** — A reviewed design/specification for Runtime configuration subsystem with explicit owner and version.
- [ ] **MC-08.031** — Repository-local implementation or authoritative external dependency declaration for Runtime configuration subsystem.
- [ ] **MC-08.032** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-08.033** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-08.034** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-08.035** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-08: 35.**

## MC-09 — Health, backpressure and failure-control subsystem

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C052, INV-36-C053, INV-36-C054, INV-36-C055, INV-36-C056  
**Target outcome:** Detect unhealthy/stalled transport behavior, bound retries and queues, prevent cascades, and define safe failover/degraded operation.

### Related audit requirements

- **INV-36-C052 — MISSING:** Define automated health and stall detection thresholds for Control transport.
- **INV-36-C053 — MISSING:** Implement bounded retry with backoff and jitter only where operations are safe to retry.
- **INV-36-C054 — MISSING:** Implement admission control, load shedding, or circuit breaking to prevent Control transport failure cascades.
- **INV-36-C055 — MISSING:** Define failover behavior without violating isolation, residency, or consistency requirements.
- **INV-36-C056 — MISSING:** Provide degraded operation when noncritical dependencies are unavailable.

### Health model

- [ ] **MC-09.001** — Define liveness, readiness, and degradation as separate states with explicit transition criteria.
- [ ] **MC-09.002** — Measure socket/connect health, handshake health, send/receive progress, queue saturation, error rate, dependency state, and last successful peer exchange.
- [ ] **MC-09.003** — Define stall thresholds based on monotonic clocks.
- [ ] **MC-09.004** — Prevent a healthy process from reporting ready when its required transport dependencies are unusable.
- [ ] **MC-09.005** — Define hysteresis to avoid flapping.
- [ ] **MC-09.006** — Expose state transitions and reasons as metrics/logs/audit events.

### Retry and timeout control

- [ ] **MC-09.007** — Classify operations as non-retryable, retryable/idempotent, or retryable with deduplication token.
- [ ] **MC-09.008** — Assign connect, handshake, read, write, drain, and dependency timeouts.
- [ ] **MC-09.009** — Implement exponential backoff with decorrelated/full jitter as appropriate.
- [ ] **MC-09.010** — Set maximum attempts or maximum elapsed retry budget.
- [ ] **MC-09.011** — Honor caller cancellation/deadlines.
- [ ] **MC-09.012** — Prevent retry after terminal authentication, authorization, protocol, or integrity errors.
- [ ] **MC-09.013** — Add retry-storm protection across many sessions.

### Backpressure and overload

- [ ] **MC-09.014** — Define queue and concurrency limits per connection, tenant/workload, and process/node where applicable.
- [ ] **MC-09.015** — Use admission control before accepting work that cannot be serviced within bounded resources.
- [ ] **MC-09.016** — Implement high-water/low-water queue control.
- [ ] **MC-09.017** — Define load-shedding priority classes for critical versus optional control traffic.
- [ ] **MC-09.018** — Implement circuit breaking for failing downstream dependencies with bounded probe behavior.
- [ ] **MC-09.019** — Reject overload with stable machine-readable errors and retry hints where safe.
- [ ] **MC-09.020** — Ensure overload cannot bypass authorization or cryptographic verification.

### Failover and degraded mode

- [ ] **MC-09.021** — Define which dependencies may fail over and which identities/regions/sites are valid alternates.
- [ ] **MC-09.022** — Preserve tenant isolation/residency constraints during failover.
- [ ] **MC-09.023** — Define degraded operations that remain safe when optional telemetry/config services fail.
- [ ] **MC-09.024** — Define operations that must stop when identity, policy, key, or integrity dependencies fail.
- [ ] **MC-09.025** — Prevent split-brain or dual-active ownership during failover.
- [ ] **MC-09.026** — Define recovery and re-entry criteria from degraded state.

### Testing

- [ ] **MC-09.027** — Inject latency, packet/stream stalls, connection resets, dependency errors, and resource exhaustion.
- [ ] **MC-09.028** — Test retry limits and jitter distribution.
- [ ] **MC-09.029** — Test queue saturation and verify bounded memory.
- [ ] **MC-09.030** — Test circuit breaker open/half-open/closed behavior.
- [ ] **MC-09.031** — Test failover under active sessions and verify policy/isolation invariants.
- [ ] **MC-09.032** — Test prolonged dependency failure and recovery without thundering-herd reconnects.

### Required closure evidence

- [ ] **MC-09.033** — A reviewed design/specification for Health, backpressure and failure-control subsystem with explicit owner and version.
- [ ] **MC-09.034** — Repository-local implementation or authoritative external dependency declaration for Health, backpressure and failure-control subsystem.
- [ ] **MC-09.035** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-09.036** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-09.037** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-09.038** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-09: 38.**

## MC-10 — Persistent/restart/session recovery design

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** INV-36-C057  
**Target outcome:** Define and implement safe crash/restart semantics so sequence numbers, session identities, replay protection, and mutable transport state cannot regress or become ambiguous.

### Related audit requirements

- **INV-36-C057 — PARTIAL:** Define crash-consistency, restart, resume, or replay semantics for mutable Control transport state.

### State classification

- [ ] **MC-10.001** — Classify all state as ephemeral, reconstructable, or persistence-required.
- [ ] **MC-10.002** — Document session ID, traffic keys, sequence counters, peer identity, pending outbound work, deduplication state, configuration version, and audit cursor behavior on restart.
- [ ] **MC-10.003** — Default cryptographic session/sequence state to non-resumable unless a formally analyzed resume protocol exists.
- [ ] **MC-10.004** — Define which queued operations may be replayed after process or VM restart.
- [ ] **MC-10.005** — Assign idempotency/deduplication keys to any operation eligible for replay.

### Restart and crash consistency

- [ ] **MC-10.006** — On restart, force a new authenticated session and fresh keys if sequence uniqueness cannot be proven.
- [ ] **MC-10.007** — Never reset a nonce/sequence counter under the same key/session identifier.
- [ ] **MC-10.008** — Discard partial inbound frames and unauthenticated buffered bytes after crash.
- [ ] **MC-10.009** — Define atomic persistence format for any required mutable state.
- [ ] **MC-10.010** — Use checksums/versioning for persisted state and reject corrupt or incompatible state.
- [ ] **MC-10.011** — Define process restart, guest reboot, host reboot, migration, and snapshot/restore semantics separately.
- [ ] **MC-10.012** — Address VM snapshot cloning so two restored copies cannot reuse the same cryptographic session state.

### Operational recovery

- [ ] **MC-10.013** — Define reconstruction steps when state is intentionally ephemeral.
- [ ] **MC-10.014** — Define maximum recovery time objective and what readiness means after restart.
- [ ] **MC-10.015** — Expose recovery status and last clean/unclean shutdown metadata.
- [ ] **MC-10.016** — Define operator action for corrupted persisted state.
- [ ] **MC-10.017** — Ensure recovery respects current authorization/config/key policy rather than blindly restoring stale decisions.

### Testing

- [ ] **MC-10.018** — Crash at each state-transition point and verify invariant preservation.
- [ ] **MC-10.019** — Kill process mid-send and mid-receive.
- [ ] **MC-10.020** — Reboot host/guest during active session.
- [ ] **MC-10.021** — Restore a VM snapshot and verify old session material is rejected or re-established safely.
- [ ] **MC-10.022** — Test duplicate/replayed application operations across restart.
- [ ] **MC-10.023** — Test corrupted/stale persisted state and incompatible schema versions.

### Required closure evidence

- [ ] **MC-10.024** — A reviewed design/specification for Persistent/restart/session recovery design with explicit owner and version.
- [ ] **MC-10.025** — Repository-local implementation or authoritative external dependency declaration for Persistent/restart/session recovery design.
- [ ] **MC-10.026** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-10.027** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-10.028** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-10.029** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-10: 29.**

## MC-11 — Quarantine / emergency isolation control

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C059, INV-36-C092  
**Target outcome:** Provide a rapid, authenticated, auditable mechanism to freeze unsafe transport behavior without requiring a full software redeploy.

### Related audit requirements

- **INV-36-C059 — MISSING:** Provide quarantine, freeze, disable, or isolation controls for unsafe Control transport behavior.
- **INV-36-C092 — MISSING:** Define canary, staged rollout, rollback, and emergency-disable procedures for Control transport.

### Control semantics

- [ ] **MC-11.001** — Define quarantine scopes: process, endpoint, peer identity, tenant, workload, CID/port, node, site, protocol version, or operation class.
- [ ] **MC-11.002** — Define actions: deny new sessions, terminate existing sessions, allow receive-only/drain-only, block selected operations, or disable component entirely.
- [ ] **MC-11.003** — Define precedence of quarantine over ordinary allow policy and configuration.
- [ ] **MC-11.004** — Define default state after restart and whether quarantines persist.
- [ ] **MC-11.005** — Define expiry/TTL and explicit unquarantine workflow.
- [ ] **MC-11.006** — Define emergency-disable path independent of potentially broken normal control-plane paths where feasible.

### Security and authorization

- [ ] **MC-11.007** — Restrict quarantine changes to a dedicated break-glass capability.
- [ ] **MC-11.008** — Require strong operator/service authentication and two-person approval for broad production scopes where policy requires.
- [ ] **MC-11.009** — Prevent quarantined subjects from self-unquarantining.
- [ ] **MC-11.010** — Validate scope selectors to prevent accidental global shutdown.
- [ ] **MC-11.011** — Use signed/versioned directives if quarantine state is distributed.
- [ ] **MC-11.012** — Fail safely if directive authenticity cannot be verified.

### Implementation

- [ ] **MC-11.013** — Check quarantine state before session establishment and before privileged application operations.
- [ ] **MC-11.014** — Ensure termination closes sockets and discards session keys/state.
- [ ] **MC-11.015** — Make quarantine propagation bounded and observable.
- [ ] **MC-11.016** — Prevent races in which a new operation begins after quarantine acceptance.
- [ ] **MC-11.017** — Add a local administrative kill switch guarded by OS permissions for extreme recovery cases.
- [ ] **MC-11.018** — Expose current quarantine state without exposing secrets.

### Testing and operations

- [ ] **MC-11.019** — Test targeted and global quarantine during idle and active traffic.
- [ ] **MC-11.020** — Test persistence/expiry semantics across restart.
- [ ] **MC-11.021** — Test authorization failures and forged directives.
- [ ] **MC-11.022** — Measure time from directive issuance to enforced isolation.
- [ ] **MC-11.023** — Create incident runbook steps for quarantine, validation, containment, and safe restoration.
- [ ] **MC-11.024** — Emit tamper-evident audit events for request, approval, activation, expiry, and removal.

### Required closure evidence

- [ ] **MC-11.025** — A reviewed design/specification for Quarantine / emergency isolation control with explicit owner and version.
- [ ] **MC-11.026** — Repository-local implementation or authoritative external dependency declaration for Quarantine / emergency isolation control.
- [ ] **MC-11.027** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-11.028** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-11.029** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-11.030** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-11: 30.**

## MC-12 — Production observability pipeline

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** INV-36-C071, INV-36-C072, INV-36-C073, INV-36-C074, INV-36-C075, INV-36-C076, INV-36-C077, INV-36-C078, INV-36-C079, INV-36-C080  
**Target outcome:** Provide production-grade health, metrics, logs, traces, explainability, safe diagnostics, retention policy, dashboards, and alerts tied to stable identities and release lineage.

### Related audit requirements

- **INV-36-C071 — MISSING:** Expose Control transport health, readiness, version, configuration, dependency status, and active capability set.
- **INV-36-C072 — PARTIAL:** Emit structured metrics for rate, errors, latency, saturation, backlog, and resource use.
- **INV-36-C073 — MISSING:** Emit structured logs with stable node, tenant, workload, component, and operation identifiers.
- **INV-36-C074 — MISSING:** Propagate trace context across all relevant Control transport boundaries.
- **INV-36-C075 — MISSING:** Expose high-cardinality diagnostic detail safely without leaking tenant or secret data.
- **INV-36-C076 — MISSING:** Record the reason for every automated decision made by Control transport.
- **INV-36-C077 — MISSING:** Provide an operator-readable explain view linking decisions to input state, policies, topology, and constraints.
- **INV-36-C078 — MISSING:** Correlate Control transport events with application release lineage and the live infrastructure graph.
- **INV-36-C079 — MISSING:** Define telemetry retention, sampling, privacy, and export policy.
- **INV-36-C080 — MISSING:** Create dashboards and alerts distinguishing ordinary load, degradation, policy rejection, dependency failure, attack, and software defect.

### Health and inventory

- [ ] **MC-12.001** — Expose liveness/readiness/degraded state, software version, protocol version, active config digest, dependency status, enabled capabilities, and quarantine state.
- [ ] **MC-12.002** — Use a stable machine-readable health schema with reason codes.
- [ ] **MC-12.003** — Distinguish local process health from peer/session health.
- [ ] **MC-12.004** — Avoid reporting readiness before required identity/key/policy dependencies are usable.
- [ ] **MC-12.005** — Expose build/source digest for incident correlation.

### Metrics

- [ ] **MC-12.006** — Export request/frame rates, bytes, successful/failed handshakes, auth failures, authorization denials, integrity failures, reconnects, queue depth, dropped work, and active sessions.
- [ ] **MC-12.007** — Export latency histograms for connect, handshake, send, receive, end-to-end control operation, and dependency calls.
- [ ] **MC-12.008** — Export CPU, memory, file descriptor/socket count, buffer usage, and thread/task counts.
- [ ] **MC-12.009** — Export saturation/high-water indicators and circuit-breaker state.
- [ ] **MC-12.010** — Use bounded-cardinality labels; never label metrics with raw unbounded tenant/workload IDs unless an approved aggregation strategy exists.
- [ ] **MC-12.011** — Document units and histogram buckets.

### Structured logging

- [ ] **MC-12.012** — Use a stable JSON/event schema with timestamp, severity, component, version, node, tenant/workload pseudonymous IDs as policy permits, session correlation ID, operation ID, and reason code.
- [ ] **MC-12.013** — Redact plaintext payloads, secrets, key material, credentials, authorization tokens, and sensitive policy content.
- [ ] **MC-12.014** — Rate-limit repeated identical errors while preserving counters.
- [ ] **MC-12.015** — Use monotonic duration measurements in addition to wall-clock timestamps.
- [ ] **MC-12.016** — Define log levels and prohibit security-critical failures from debug-only visibility.

### Tracing and explainability

- [ ] **MC-12.017** — Accept/propagate standard trace context across allowed boundaries and define when a new trust boundary requires trace-context sanitization.
- [ ] **MC-12.018** — Create spans for connect, handshake, policy, key service, encode/seal, socket write/read, open/verify, and application dispatch.
- [ ] **MC-12.019** — Record stable decision reason codes for retries, rejects, load shedding, failover, quarantine, and policy decisions.
- [ ] **MC-12.020** — Provide an operator explain endpoint/command that summarizes current state, dependencies, config, policy version, queue pressure, recent failures, and decision reasons.
- [ ] **MC-12.021** — Correlate events with release/build digest and infrastructure/node identity.

### Retention/privacy/export

- [ ] **MC-12.022** — Define metric/log/trace/audit retention periods by environment and data class.
- [ ] **MC-12.023** — Define sampling rules and always-on retention for specified security events.
- [ ] **MC-12.024** — Define tenant privacy/pseudonymization requirements.
- [ ] **MC-12.025** — Define export endpoints, TLS/auth requirements, buffering limits, and behavior when telemetry backends are unavailable.
- [ ] **MC-12.026** — Ensure telemetry outage cannot block core control traffic indefinitely.

### Dashboards/alerts/tests

- [ ] **MC-12.027** — Create dashboards for traffic, latency, failures, saturation, auth/security events, dependency health, and version rollout.
- [ ] **MC-12.028** — Define alerts that distinguish ordinary load, overload, dependency failure, policy rejection, attack indicators, and software defects.
- [ ] **MC-12.029** — Attach runbook links and severity to alerts.
- [ ] **MC-12.030** — Test telemetry schemas and redaction.
- [ ] **MC-12.031** — Load-test observability overhead and verify bounded memory when exporters are unavailable.
- [ ] **MC-12.032** — Create synthetic alert tests for every critical alert path.

### Required closure evidence

- [ ] **MC-12.033** — A reviewed design/specification for Production observability pipeline with explicit owner and version.
- [ ] **MC-12.034** — Repository-local implementation or authoritative external dependency declaration for Production observability pipeline.
- [ ] **MC-12.035** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-12.036** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-12.037** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-12.038** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-12: 38.**

## MC-13 — Performance certification suite

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** INV-36-C061, INV-36-C062, INV-36-C063, INV-36-C064, INV-36-C065, INV-36-C066, INV-36-C067, INV-36-C068, INV-36-C069, INV-36-C070  
**Target outcome:** Create reproducible performance and resource baselines, capacity models, optimization evidence, and release-blocking regression thresholds.

### Related audit requirements

- **INV-36-C061 — MISSING:** Establish reproducible baselines for Control transport latency, throughput, startup, CPU, memory, storage, network, and power overhead.
- **INV-36-C062 — PARTIAL:** Define p50, p95, p99, and worst-case performance thresholds for Control transport.
- **INV-36-C063 — MISSING:** Measure Control transport under steady load, burst load, overload, scale-out, scale-in, and recovery.
- **INV-36-C064 — MISSING:** Measure per-workload and per-tenant overhead introduced by Control transport.
- **INV-36-C065 — MISSING:** Identify avoidable serialization, copies, context switches, network hops, duplicated images, or duplicated state in Control transport.
- **INV-36-C066 — MISSING:** Apply locality, caching, direct composition, batching, zero-copy, or kernel-bypass optimizations where semantics permit.
- **INV-36-C067 — PARTIAL:** Bound memory growth, queue depth, buffer size, concurrency, and resource fan-out.
- **INV-36-C068 — MISSING:** Measure power and thermal impact on constrained edge nodes where relevant.
- **INV-36-C069 — MISSING:** Define capacity models and saturation signals that predict when Control transport needs more resources.
- **INV-36-C070 — MISSING:** Block releases that regress approved Control transport startup, density, throughput, or tail-latency thresholds.

### Benchmark methodology

- [ ] **MC-13.001** — Define supported hardware/VM profiles, CPU governor/power mode, OS/kernel/hypervisor versions, Python/runtime versions, and cryptography backend.
- [ ] **MC-13.002** — Pin benchmark datasets/message-size distributions and session counts.
- [ ] **MC-13.003** — Warm up runtimes and report number of iterations, confidence intervals/dispersion, and outlier policy.
- [ ] **MC-13.004** — Use monotonic high-resolution timing.
- [ ] **MC-13.005** — Separate cryptographic/session processing from real-vsock end-to-end benchmarks.
- [ ] **MC-13.006** — Record raw result files and environment fingerprints.

### Metrics and scenarios

- [ ] **MC-13.007** — Measure p50/p95/p99/max connect and handshake latency.
- [ ] **MC-13.008** — Measure p50/p95/p99/max send/receive/control-operation latency across small, typical, and maximum message sizes.
- [ ] **MC-13.009** — Measure messages/s and bytes/s under steady-state load.
- [ ] **MC-13.010** — Measure CPU time, wall time, memory RSS/heap, allocations, socket/buffer usage, and context switches.
- [ ] **MC-13.011** — Measure startup/readiness time and session-establishment rate.
- [ ] **MC-13.012** — Measure per-session, per-workload, and per-tenant overhead.
- [ ] **MC-13.013** — Measure burst, overload, scale-out, scale-in, reconnect storm, and recovery behavior.
- [ ] **MC-13.014** — Measure power/energy and thermal behavior on constrained edge profiles when in scope.

### Profiling and optimization

- [ ] **MC-13.015** — Profile serialization/encoding, cryptographic operations, copies, allocations, locking, context switches, and syscalls.
- [ ] **MC-13.016** — Identify avoidable buffer copies and evaluate `memoryview`/buffer reuse where safe.
- [ ] **MC-13.017** — Evaluate batching only if it does not violate latency or ordering semantics.
- [ ] **MC-13.018** — Evaluate socket buffer sizing and queue limits empirically.
- [ ] **MC-13.019** — Document any zero-copy/kernel-bypass optimization with security and compatibility tradeoffs.
- [ ] **MC-13.020** — Re-run correctness/security tests after performance optimizations.

### Capacity model

- [ ] **MC-13.021** — Derive saturation signals from CPU, queue depth, latency growth, error rate, and connection/session count.
- [ ] **MC-13.022** — Publish safe operating envelope per certified node/VM profile.
- [ ] **MC-13.023** — Define headroom target and overload threshold.
- [ ] **MC-13.024** — Define resource quotas and fairness model where multi-tenant.
- [ ] **MC-13.025** — Validate capacity model against independent load runs.

### Regression gate

- [ ] **MC-13.026** — Set approved thresholds for p50/p95/p99/max latency, throughput, startup, CPU, memory, and density.
- [ ] **MC-13.027** — Define statistically meaningful regression tolerance and noise handling.
- [ ] **MC-13.028** — Fail release CI/certification when thresholds regress beyond policy.
- [ ] **MC-13.029** — Archive baseline and candidate result artifacts for comparison.
- [ ] **MC-13.030** — Require documented waiver with owner/expiry for any accepted regression.

### Required closure evidence

- [ ] **MC-13.031** — A reviewed design/specification for Performance certification suite with explicit owner and version.
- [ ] **MC-13.032** — Repository-local implementation or authoritative external dependency declaration for Performance certification suite.
- [ ] **MC-13.033** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-13.034** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-13.035** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-13.036** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-13: 36.**

## MC-14 — Protocol fuzzing / property-based robustness suite

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C085  
**Target outcome:** Continuously exercise all untrusted protocol/configuration boundaries against malformed, adversarial, stateful, and resource-exhaustion inputs.

### Related audit requirements

- **INV-36-C085 — MISSING:** Fuzz parsers, schemas, protocol handlers, WIT/RPC boundaries, or untrusted inputs handled by Control transport.

### Fuzz targets

- [ ] **MC-14.001** — Create fuzz targets for frame header parsing, length decoding, AEAD open/verification wrapper, typed schema decoder, message dispatcher, configuration parser, policy input parser, and handshake parser.
- [ ] **MC-14.002** — Create stateful fuzzing around session sequence transitions and reconnect/rekey state machines.
- [ ] **MC-14.003** — Create differential tests against independent codecs/implementations where possible.
- [ ] **MC-14.004** — Include a fake transport that can fragment bytes at every position.

### Corpus and generators

- [ ] **MC-14.005** — Seed corpus with valid min/typical/max frames for every supported message type/version.
- [ ] **MC-14.006** — Include truncated, overlong, zero-length, duplicate, reordered, unknown-version, unknown-type, reserved-field, and noncanonical encodings.
- [ ] **MC-14.007** — Include ciphertext/tag corruption at every region.
- [ ] **MC-14.008** — Include max-boundary and one-over-max lengths.
- [ ] **MC-14.009** — Include repeated/replayed sequence numbers and near-`2^64` sequence values.
- [ ] **MC-14.010** — Include malicious Unicode/text only where text fields exist.
- [ ] **MC-14.011** — Persist minimized regressions as permanent corpus cases.

### Properties/invariants

- [ ] **MC-14.012** — Parser must never crash the process on arbitrary bytes.
- [ ] **MC-14.013** — Parser must not allocate above configured hard bounds based solely on attacker-controlled length.
- [ ] **MC-14.014** — Unauthenticated input must never reach application dispatch.
- [ ] **MC-14.015** — Accepted sequence state must never move backwards or skip unexpectedly.
- [ ] **MC-14.016** — Encode/decode round-trip must preserve canonical values for valid messages.
- [ ] **MC-14.017** — Invalid frames must not mutate session state except documented failure counters.
- [ ] **MC-14.018** — Failure paths must close/reject cleanly without secret leakage.

### Execution and CI

- [ ] **MC-14.019** — Run fast property-based tests on every PR.
- [ ] **MC-14.020** — Run bounded fuzz campaigns on PR/merge and longer campaigns nightly/weekly.
- [ ] **MC-14.021** — Use sanitizer/instrumented native dependencies where applicable.
- [ ] **MC-14.022** — Capture seed, minimized input, stack trace, source digest, and environment for failures.
- [ ] **MC-14.023** — Fail CI on newly reproducible crashes, hangs, excessive memory, assertion/invariant failures, or parser acceptance violations.
- [ ] **MC-14.024** — Track fuzz coverage and stale targets.

### Required closure evidence

- [ ] **MC-14.025** — A reviewed design/specification for Protocol fuzzing / property-based robustness suite with explicit owner and version.
- [ ] **MC-14.026** — Repository-local implementation or authoritative external dependency declaration for Protocol fuzzing / property-based robustness suite.
- [ ] **MC-14.027** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-14.028** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-14.029** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-14.030** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-14: 30.**

## MC-15 — Platform/hypervisor compatibility test matrix

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** INV-36-C084, INV-36-C093  
**Target outcome:** Certify the component across explicitly supported CPU architectures, OS/runtime versions, hypervisors/microVMs, virtio-vsock implementations, and protocol combinations.

### Related audit requirements

- **INV-36-C084 — MISSING:** Create compatibility tests across supported CPU architectures, runtimes, hypervisors, providers, and protocol versions relevant to Control transport.
- **INV-36-C093 — PARTIAL:** Maintain a supported-version compatibility matrix for Control transport and adjacent dependencies.

### Support matrix definition

- [ ] **MC-15.001** — List supported CPU architectures (e.g., x86_64, arm64) and explicitly unsupported architectures.
- [ ] **MC-15.002** — List guest and host OS/kernel versions.
- [ ] **MC-15.003** — List Python/runtime and cryptography-library versions.
- [ ] **MC-15.004** — List hypervisors/microVMs/providers and their vsock implementation/version.
- [ ] **MC-15.005** — List protocol frame/session versions and peer-version combinations.
- [ ] **MC-15.006** — List required kernel modules/device nodes/capabilities and environment prerequisites.
- [ ] **MC-15.007** — Define support tier: certified, best-effort, experimental, unsupported.

### Compatibility harness

- [ ] **MC-15.008** — Automate VM/microVM creation for each certified matrix row.
- [ ] **MC-15.009** — Run real vsock connect, handshake, bidirectional frame exchange, close, reconnect, and failure tests.
- [ ] **MC-15.010** — Capture hypervisor/device/driver versions automatically.
- [ ] **MC-15.011** — Validate CID discovery/allocation semantics per platform.
- [ ] **MC-15.012** — Test MTU/stream fragmentation assumptions without relying on message boundaries.
- [ ] **MC-15.013** — Test host/guest reboot and upgrade sequences.

### Cross-version behavior

- [ ] **MC-15.014** — Test same-version peers.
- [ ] **MC-15.015** — Test every explicitly supported mixed-version pair.
- [ ] **MC-15.016** — Verify deterministic rejection of unsupported legacy/newer versions.
- [ ] **MC-15.017** — Test capability negotiation and unknown extensions.
- [ ] **MC-15.018** — Test rolling upgrade where one side updates before the other.
- [ ] **MC-15.019** — Publish maximum supported skew and deprecation dates.

### Certification evidence

- [ ] **MC-15.020** — Produce machine-readable matrix results keyed by environment fingerprint.
- [ ] **MC-15.021** — Retain logs, protocol fixtures, and build/source digests for failed/certified rows.
- [ ] **MC-15.022** — Require all mandatory rows to pass before release.
- [ ] **MC-15.023** — Allow exceptions only through a documented waiver with owner, scope, risk, and expiry.
- [ ] **MC-15.024** — Update COMPATIBILITY.md from or alongside the machine-readable matrix.

### Required closure evidence

- [ ] **MC-15.025** — A reviewed design/specification for Platform/hypervisor compatibility test matrix with explicit owner and version.
- [ ] **MC-15.026** — Repository-local implementation or authoritative external dependency declaration for Platform/hypervisor compatibility test matrix.
- [ ] **MC-15.027** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-15.028** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-15.029** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-15.030** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-15: 30.**

## MC-16 — Integration / disaster / soak / fleet-scale suites

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** INV-36-C030, INV-36-C083, INV-36-C088, INV-36-C089  
**Target outcome:** Validate the control transport as part of its surrounding architecture under realistic duration, scale, partitions, failures, and recovery—not only as a unit-tested library.

### Related audit requirements

- **INV-36-C030 — MISSING:** Create automated integration tests proving Control transport interoperates with adjacent architectural layers.
- **INV-36-C083 — MISSING:** Create integration tests with every supported adjacent layer and execution tier.
- **INV-36-C088 — MISSING:** Create benchmark, soak, burst, and fleet-scale tests appropriate to Control transport.
- **INV-36-C089 — MISSING:** Create disaster, partition, reconnect, and degraded-control-plane tests.

### Adjacent-layer integration

- [ ] **MC-16.001** — Enumerate every producer/consumer, host agent, guest agent, policy service, identity service, key service, config service, telemetry backend, and lifecycle controller that integrates with INV-36.
- [ ] **MC-16.002** — Create versioned test doubles only where real adjacent components are impractical; maintain at least one full-stack path using real implementations.
- [ ] **MC-16.003** — Validate startup ordering and dependency unavailability.
- [ ] **MC-16.004** — Test malformed/unsupported messages from adjacent layers.
- [ ] **MC-16.005** — Test rolling upgrades across adjacent component versions.
- [ ] **MC-16.006** — Test authorization/tenant identity propagation end-to-end.

### Disaster and partition

- [ ] **MC-16.007** — Inject host/guest process crash, VM reboot, node reboot, network/vsock reset, control-plane partition, KMS/policy/identity outage, telemetry outage, and storage/config outage as applicable.
- [ ] **MC-16.008** — Inject asymmetric failure where one side believes the session is live and the other has restarted.
- [ ] **MC-16.009** — Test prolonged partition followed by reconnection and confirm fresh session establishment/replay protection.
- [ ] **MC-16.010** — Test stale controller/duplicate owner scenarios.
- [ ] **MC-16.011** — Test quarantine/emergency-disable during failure recovery.
- [ ] **MC-16.012** — Verify recovery objectives and no cross-tenant leakage or privilege relaxation.

### Soak and burst

- [ ] **MC-16.013** — Run multi-hour/day soak tests with representative traffic and periodic reconnect/rotation.
- [ ] **MC-16.014** — Track memory/file descriptor/thread/task growth for leaks.
- [ ] **MC-16.015** — Inject burst traffic and reconnect storms.
- [ ] **MC-16.016** — Exercise maximum frame sizes and mixed size distributions.
- [ ] **MC-16.017** — Rotate keys/config/policies during soak.
- [ ] **MC-16.018** — Collect p50/p95/p99 latency and error/saturation trends over time.

### Fleet scale

- [ ] **MC-16.019** — Simulate or deploy representative node/session counts.
- [ ] **MC-16.020** — Test fan-out/fan-in control operations and synchronized reconnects.
- [ ] **MC-16.021** — Validate global dependency load and rate limiting.
- [ ] **MC-16.022** — Check fairness across tenants/workloads.
- [ ] **MC-16.023** — Test staged rollout across a heterogeneous fleet.
- [ ] **MC-16.024** — Validate observability cardinality and backend load at fleet scale.

### Acceptance

- [ ] **MC-16.025** — Define pass/fail recovery objectives per failure scenario.
- [ ] **MC-16.026** — Archive machine-readable results and raw telemetry.
- [ ] **MC-16.027** — Gate production release on mandatory scenarios.
- [ ] **MC-16.028** — Create regression cases for every discovered production-like failure.

### Required closure evidence

- [ ] **MC-16.029** — A reviewed design/specification for Integration / disaster / soak / fleet-scale suites with explicit owner and version.
- [ ] **MC-16.030** — Repository-local implementation or authoritative external dependency declaration for Integration / disaster / soak / fleet-scale suites.
- [ ] **MC-16.031** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-16.032** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-16.033** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-16.034** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-16: 34.**

## MC-17 — Supply-chain integrity controls

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C045, INV-36-C090  
**Target outcome:** Provide verifiable dependency, build, artifact, and release provenance with vulnerability scanning and signed attestations.

### Related audit requirements

- **INV-36-C045 — MISSING:** Verify signatures, digests, provenance, and approved versions for executable or policy artifacts consumed by Control transport.
- **INV-36-C090 — MISSING:** Require machine-readable acceptance evidence before certifying a Control transport release for production.

### Dependency control

- [ ] **MC-17.001** — Inventory direct and transitive runtime/build/test dependencies.
- [ ] **MC-17.002** — Pin production dependencies to approved versions and hashes where tooling supports it.
- [ ] **MC-17.003** — Separate runtime from development/test dependencies.
- [ ] **MC-17.004** — Define dependency-source policy and approved registries/mirrors.
- [ ] **MC-17.005** — Automate known-vulnerability and malicious-package scanning.
- [ ] **MC-17.006** — Define severity/SLA policy for dependency findings.
- [ ] **MC-17.007** — Prevent unreviewed dependency drift in release builds.

### SBOM and provenance

- [ ] **MC-17.008** — Generate an SBOM in an industry-standard machine-readable format for every release artifact.
- [ ] **MC-17.009** — Include package name/version, dependency versions, hashes, licenses, and build metadata.
- [ ] **MC-17.010** — Generate build provenance/attestation binding source revision, builder identity, workflow, inputs, and artifact digest.
- [ ] **MC-17.011** — Use reproducible/hermetic build techniques where practical.
- [ ] **MC-17.012** — Compare built wheel/archive contents against an allowlist/manifest.
- [ ] **MC-17.013** — Archive SBOM and provenance with the release.

### Signing and verification

- [ ] **MC-17.014** — Sign release artifacts using a managed signing identity/key.
- [ ] **MC-17.015** — Verify signatures/digests before installation or certification.
- [ ] **MC-17.016** — Define key rotation/revocation for signing identities.
- [ ] **MC-17.017** — Publish verification instructions and expected trust roots.
- [ ] **MC-17.018** — Fail release if signing/provenance generation or verification fails.
- [ ] **MC-17.019** — Emit tamper-evident audit evidence for signing events.

### CI/security hardening

- [ ] **MC-17.020** — Pin third-party CI actions/plugins by immutable revision.
- [ ] **MC-17.021** — Use least-privilege CI tokens and short-lived credentials.
- [ ] **MC-17.022** — Protect release workflows with approval/environment controls.
- [ ] **MC-17.023** — Prevent pull-request code from exfiltrating release credentials.
- [ ] **MC-17.024** — Run secret scanning and repository hygiene checks.
- [ ] **MC-17.025** — Retain machine-readable scan reports and exception waivers.

### Required closure evidence

- [ ] **MC-17.026** — A reviewed design/specification for Supply-chain integrity controls with explicit owner and version.
- [ ] **MC-17.027** — Repository-local implementation or authoritative external dependency declaration for Supply-chain integrity controls.
- [ ] **MC-17.028** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-17.029** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-17.030** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-17.031** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-17: 31.**

## MC-18 — Tamper-evident security audit log

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C049  
**Target outcome:** Record security-sensitive actions and decisions in an append-only, integrity-verifiable event stream suitable for incident reconstruction and compliance evidence.

### Related audit requirements

- **INV-36-C049 — MISSING:** Emit tamper-evident audit events for security-sensitive Control transport operations.

### Event model

- [ ] **MC-18.001** — Define security-audit event schema with event ID, timestamp, monotonic sequence/counter where applicable, actor identity, target, tenant/workload scope, operation, decision, reason, policy/config/key versions, component version, and correlation ID.
- [ ] **MC-18.002** — Enumerate mandatory events: handshake success/failure, authorization decision, key rotation/revocation, config activation/rollback, quarantine changes, admin actions, security policy changes, integrity failures, repeated replay/spoof attempts, and release/certification actions.
- [ ] **MC-18.003** — Define redaction/data-class rules; never record secret/key/plaintext payload values.
- [ ] **MC-18.004** — Define clock uncertainty/time-source metadata if legal/audit ordering depends on wall time.

### Integrity mechanism

- [ ] **MC-18.005** — Use append-only storage semantics and restrict mutation/deletion.
- [ ] **MC-18.006** — Hash-chain or Merkle-chain records/batches so deletion/reordering/tampering is detectable.
- [ ] **MC-18.007** — Periodically sign checkpoints with a managed audit-signing key or external trusted service.
- [ ] **MC-18.008** — Bind log segment metadata to source/component version and node identity.
- [ ] **MC-18.009** — Define segment rotation and checkpoint frequency.
- [ ] **MC-18.010** — Store verification metadata separately enough to detect local compromise where feasible.

### Reliability and privacy

- [ ] **MC-18.011** — Bound in-memory audit buffering.
- [ ] **MC-18.012** — Define behavior when remote audit sink is unavailable; security-critical actions may require fail-closed or durable local buffering according to policy.
- [ ] **MC-18.013** — Protect transport and storage encryption independently from ordinary operational logs.
- [ ] **MC-18.014** — Define retention and legal hold policy.
- [ ] **MC-18.015** — Define tenant access boundaries for audit data.
- [ ] **MC-18.016** — Protect against log injection and oversized attacker-controlled fields.

### Verification and tooling

- [ ] **MC-18.017** — Provide an offline verifier that validates chain/signatures and reports first corruption/gap.
- [ ] **MC-18.018** — Test deletion, insertion, reordering, bit flip, duplicate record, forged checkpoint, and wrong signing key.
- [ ] **MC-18.019** — Test crash during log append/segment rotation.
- [ ] **MC-18.020** — Export machine-readable verification result for release/incident evidence.
- [ ] **MC-18.021** — Integrate audit-log integrity checks into periodic operations.

### Required closure evidence

- [ ] **MC-18.022** — A reviewed design/specification for Tamper-evident security audit log with explicit owner and version.
- [ ] **MC-18.023** — Repository-local implementation or authoritative external dependency declaration for Tamper-evident security audit log.
- [ ] **MC-18.024** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-18.025** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-18.026** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-18.027** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-18: 27.**

## MC-19 — Formal architecture decision record (ADR)

**Priority:** P1 — Production-readiness critical. Close before broad production rollout; may be staged only with an approved, time-bounded waiver.  
**Traceability:** INV-36-C010  
**Target outcome:** Capture and approve the architecture rationale for virtio-vsock, session security, trust boundaries, and major implementation choices, including rejected alternatives and consequences.

### Related audit requirements

- **INV-36-C010 — MISSING:** Approve an architecture decision record for Control transport, its technologies (virtio-vsock), and its function (Lightweight host/guest control traffic).

### Decision content

- [ ] **MC-19.001** — Create a versioned ADR with status, date, owners, approvers, context, decision, alternatives, consequences, and supersession rules.
- [ ] **MC-19.002** — Define the exact problem: lightweight host/guest control traffic and why a dedicated transport is required.
- [ ] **MC-19.003** — Document why virtio-vsock is selected over TCP/IP, Unix sockets, shared memory, virtio-serial, gRPC over IP, or other plausible options.
- [ ] **MC-19.004** — Document security/trust assumptions of the hypervisor-provided vsock boundary.
- [ ] **MC-19.005** — Document why PK_CTRL_FRAME/2 uses the selected AEAD/KDF design and how authenticated session establishment supplies secrets.
- [ ] **MC-19.006** — Document ordering, replay, sequence exhaustion, reconnect, and session-lifetime choices.
- [ ] **MC-19.007** — Document platform limitations and portability consequences.
- [ ] **MC-19.008** — Document operational/observability/testing consequences.

### Quantified criteria

- [ ] **MC-19.009** — Include latency/throughput/resource targets used in the decision.
- [ ] **MC-19.010** — Include isolation and attack-surface criteria.
- [ ] **MC-19.011** — Include deployment and compatibility constraints.
- [ ] **MC-19.012** — Include recovery/failure-mode analysis.
- [ ] **MC-19.013** — Include maintenance/tooling maturity considerations.

### Governance

- [ ] **MC-19.014** — Assign technical and security approvers.
- [ ] **MC-19.015** — Link the ADR to requirements and threat model.
- [ ] **MC-19.016** — Define triggers requiring ADR re-review: protocol major version, crypto primitive change, new hypervisor, changed trust boundary, new transport, or material performance regression.
- [ ] **MC-19.017** — Mark superseded ADRs but retain historical versions.
- [ ] **MC-19.018** — Require release evidence to reference the active ADR revision.

### Required closure evidence

- [ ] **MC-19.019** — A reviewed design/specification for Formal architecture decision record (ADR) with explicit owner and version.
- [ ] **MC-19.020** — Repository-local implementation or authoritative external dependency declaration for Formal architecture decision record (ADR).
- [ ] **MC-19.021** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-19.022** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-19.023** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-19.024** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-19: 24.**

## MC-20 — Requirements specification + traceability matrix

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C011, INV-36-C012, INV-36-C013, INV-36-C014, INV-36-C015, INV-36-C016, INV-36-C017, INV-36-C018, INV-36-C019, INV-36-C020  
**Target outcome:** Convert the transport mission into testable SHALL-level requirements and maintain bidirectional traceability to design, code, tests, evidence, risks, and releases.

### Related audit requirements

- **INV-36-C011 — MISSING:** Translate the source function of Control transport — Lightweight host/guest control traffic — into testable SHALL-level requirements.
- **INV-36-C012 — MISSING:** Define functional requirements for Control transport across cloud, datacenter, near-edge, and far-edge contexts where applicable.
- **INV-36-C013 — PARTIAL:** Define non-functional requirements for latency, availability, durability, consistency, isolation, or determinism as applicable.
- **INV-36-C014 — MISSING:** Define success, partial success, degraded operation, retryable failure, and terminal failure semantics for Control transport.
- **INV-36-C015 — PARTIAL:** Define lifecycle states and legal state transitions managed or exposed by Control transport.
- **INV-36-C016 — PARTIAL:** Define versioning and backward-compatibility requirements for Control transport.
- **INV-36-C017 — MISSING:** Define capacity ceilings, quotas, and fairness semantics relevant to Control transport.
- **INV-36-C018 — MISSING:** Define behavior when network connectivity is intermittent or absent.
- **INV-36-C019 — MISSING:** Define precedence rules when Control transport requirements conflict with security, residency, SLO, or cost constraints.
- **INV-36-C020 — MISSING:** Maintain a requirements traceability matrix from each Control transport requirement to implementation and verification evidence.

### Requirements specification

- [ ] **MC-20.001** — Create uniquely identified SHALL requirements for host/guest connectivity, authentication, confidentiality/integrity, authorization, framing, ordering, replay protection, size limits, lifecycle, configuration, observability, failure handling, and operations.
- [ ] **MC-20.002** — Separate functional from non-functional requirements.
- [ ] **MC-20.003** — Define deployment-context requirements for cloud, datacenter, near-edge, and far-edge only where actually supported.
- [ ] **MC-20.004** — Define measurable latency, availability, startup, throughput, recovery, memory, CPU, and durability targets.
- [ ] **MC-20.005** — Define success, partial success, degraded, retryable, denied, protocol error, integrity failure, and terminal failure semantics.
- [ ] **MC-20.006** — Define lifecycle states and legal transitions including uninitialized, configured, connecting, authenticating, ready, degraded, draining, quarantined, closed, and failed as applicable.
- [ ] **MC-20.007** — Define protocol compatibility and deprecation requirements.
- [ ] **MC-20.008** — Define quotas/fairness and resource ceilings.
- [ ] **MC-20.009** — Define disconnected/intermittent-connectivity behavior.
- [ ] **MC-20.010** — Define precedence when security/residency constraints conflict with availability, SLO, cost, or operator preference.

### Requirement quality

- [ ] **MC-20.011** — Ensure every SHALL statement is atomic, unambiguous, testable, and has a defined verification method.
- [ ] **MC-20.012** — Avoid implementation details in requirements unless the technology itself is mandated.
- [ ] **MC-20.013** — Define units, thresholds, tolerances, and observation windows.
- [ ] **MC-20.014** — Identify requirement rationale and source.
- [ ] **MC-20.015** — Classify safety/security-critical requirements.
- [ ] **MC-20.016** — Assign owner and approval state.

### Traceability matrix

- [ ] **MC-20.017** — Create columns for requirement ID, design/ADR, implementation modules/symbols, config fields, unit tests, integration tests, security tests, performance tests, operational runbook, evidence artifact, status, owner, and release version.
- [ ] **MC-20.018** — Ensure every requirement has at least one verification reference before certification.
- [ ] **MC-20.019** — Ensure every test/evidence artifact traces back to at least one requirement or risk.
- [ ] **MC-20.020** — Automate detection of orphan requirements and orphan tests where practical.
- [ ] **MC-20.021** — Include partial/waived status with explicit rationale, risk owner, and expiry.
- [ ] **MC-20.022** — Generate a machine-readable representation alongside human-readable Markdown.

### Change control and acceptance

- [ ] **MC-20.023** — Require impact analysis when a requirement changes.
- [ ] **MC-20.024** — Update traceability in the same change as code/test modifications.
- [ ] **MC-20.025** — Version the requirements baseline and freeze the baseline used for each release.
- [ ] **MC-20.026** — Fail production exit gate when mandatory requirements lack passing evidence.
- [ ] **MC-20.027** — Archive signed/approved baseline and trace matrix per release.

### Required closure evidence

- [ ] **MC-20.028** — A reviewed design/specification for Requirements specification + traceability matrix with explicit owner and version.
- [ ] **MC-20.029** — Repository-local implementation or authoritative external dependency declaration for Requirements specification + traceability matrix.
- [ ] **MC-20.030** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-20.031** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-20.032** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-20.033** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-20: 33.**

## MC-21 — Operational release / governance pack

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C009, INV-36-C092, INV-36-C094, INV-36-C097, INV-36-C098, INV-36-C099, INV-36-C100  
**Target outcome:** Establish ownership, release/rollback discipline, incident response, vulnerability/EOL SLAs, recurring reviews, exception governance, and a formal production exit gate.

### Related audit requirements

- **INV-36-C009 — MISSING:** Assign an accountable owner and escalation path for Control transport.
- **INV-36-C092 — MISSING:** Define canary, staged rollout, rollback, and emergency-disable procedures for Control transport.
- **INV-36-C094 — MISSING:** Define patching, vulnerability response, and end-of-life SLAs for Control transport.
- **INV-36-C097 — MISSING:** Define incident severity, paging, escalation, containment, and recovery procedures.
- **INV-36-C098 — MISSING:** Perform recurring access, policy, dependency, configuration, and architecture reviews.
- **INV-36-C099 — MISSING:** Track exceptions, waivers, technical debt, and deprecated behaviors with owners and expiry dates.
- **INV-36-C100 — MISSING:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Ownership and service model

- [ ] **MC-21.001** — Name accountable service owner, technical owner, security owner, release owner, and on-call/escalation contacts.
- [ ] **MC-21.002** — Define RACI for development, approval, deployment, incident response, key/policy/config changes, and deprecation.
- [ ] **MC-21.003** — Define support hours and severity response expectations.
- [ ] **MC-21.004** — Publish production SLO measurement windows, error budgets, and escalation when budgets are exhausted.
- [ ] **MC-21.005** — Keep ownership metadata versioned and discoverable from repository/service catalog.

### Release and rollback

- [ ] **MC-21.006** — Define canary population, staged rollout percentages, soak durations, promotion criteria, and automatic halt criteria.
- [ ] **MC-21.007** — Define protocol-version sequencing for host/guest rolling upgrades.
- [ ] **MC-21.008** — Define rollback prerequisites and cases where rollback is unsafe due to protocol/state/key changes.
- [ ] **MC-21.009** — Define emergency-disable/quarantine procedure.
- [ ] **MC-21.010** — Require artifact signature/provenance and production gate evidence before rollout.
- [ ] **MC-21.011** — Capture release decision, approvers, evidence bundle, artifact digest, config version, and compatibility matrix.

### Incident response

- [ ] **MC-21.012** — Define incident severity levels and examples specific to authentication bypass, cross-tenant exposure, transport outage, replay/integrity failures, widespread latency, and dependency compromise.
- [ ] **MC-21.013** — Define paging, escalation, incident command, communications, containment, evidence preservation, recovery, and post-incident review.
- [ ] **MC-21.014** — Create runbooks for identity/key compromise, policy misconfiguration, reconnect storm, hypervisor/vsock failure, protocol incompatibility, and telemetry outage.
- [ ] **MC-21.015** — Define criteria for quarantine and global emergency disable.
- [ ] **MC-21.016** — Define forensic artifacts to retain.

### Vulnerability and lifecycle

- [ ] **MC-21.017** — Define patch SLAs by severity/exploitability.
- [ ] **MC-21.018** — Define vulnerability intake, triage, embargo, remediation, verification, disclosure, and customer/operator communication.
- [ ] **MC-21.019** — Define supported release branches and EOL dates.
- [ ] **MC-21.020** — Define minimum notice for deprecating protocol versions unless emergency security action is required.
- [ ] **MC-21.021** — Define dependency update cadence.

### Recurring governance

- [ ] **MC-21.022** — Schedule periodic access, key, policy, dependency, configuration, threat-model, compatibility, and architecture reviews.
- [ ] **MC-21.023** — Track waivers/exceptions with scope, justification, compensating controls, owner, approval, and expiry date.
- [ ] **MC-21.024** — Track technical debt and deprecated behaviors with target removal release.
- [ ] **MC-21.025** — Automatically flag expired waivers.
- [ ] **MC-21.026** — Require remediation or explicit reapproval before release if an exception expires.

### Production exit gate

- [ ] **MC-21.027** — Create a machine-readable release checklist covering architecture, requirements, interfaces, implementation, security, resilience, performance, observability, tests, compatibility, rollback, operations, ownership, license, SBOM/provenance, and gate evidence.
- [ ] **MC-21.028** — Require all mandatory controls PASS; treat SKIP/ERROR as non-passing unless a formally approved waiver applies.
- [ ] **MC-21.029** — Bind the gate result to source and artifact digests.
- [ ] **MC-21.030** — Require named approvers for final production certification.
- [ ] **MC-21.031** — Archive the complete evidence bundle immutably.

### Required closure evidence

- [ ] **MC-21.032** — A reviewed design/specification for Operational release / governance pack with explicit owner and version.
- [ ] **MC-21.033** — Repository-local implementation or authoritative external dependency declaration for Operational release / governance pack.
- [ ] **MC-21.034** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-21.035** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-21.036** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-21.037** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-21: 37.**

## MC-22 — Explicit software license

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** No direct Cxxx mapping; repository-level provenance/governance gap  
**Target outcome:** Provide an unambiguous legal grant for use, modification, redistribution, and contribution, with third-party notice handling appropriate to the project.

### License selection and approval

- [ ] **MC-22.001** — Identify the intended license through the repository owner/legal authority; do not assume one from neighboring projects.
- [ ] **MC-22.002** — Confirm that all contributed/source material can legally be distributed under the selected license.
- [ ] **MC-22.003** — Confirm compatibility with third-party dependency licenses and copied/generated code.
- [ ] **MC-22.004** — If Apache-2.0 is selected, include the complete standard license text and apply NOTICE handling where required.
- [ ] **MC-22.005** — If another license is selected, use the canonical unmodified license text unless legal counsel approves changes.

### Repository implementation

- [ ] **MC-22.006** — Add top-level `LICENSE` with the canonical license text.
- [ ] **MC-22.007** — Add `NOTICE` when required by the selected license or upstream notices.
- [ ] **MC-22.008** — Add package metadata classifiers/license expression using SPDX identifier where supported.
- [ ] **MC-22.009** — Add copyright/attribution headers only where project policy requires them.
- [ ] **MC-22.010** — Document contribution licensing expectations.
- [ ] **MC-22.011** — Ensure source distributions and wheels include license/notice files.

### Third-party compliance

- [ ] **MC-22.012** — Generate a third-party dependency/license inventory.
- [ ] **MC-22.013** — Preserve required attribution/notices.
- [ ] **MC-22.014** — Flag strong-copyleft, source-available, noncommercial, or otherwise incompatible licenses for legal review.
- [ ] **MC-22.015** — Verify generated artifacts do not omit required notices.
- [ ] **MC-22.016** — Add CI checks for missing license metadata in new dependencies.

### Acceptance

- [ ] **MC-22.017** — Obtain repository-owner/legal approval.
- [ ] **MC-22.018** — Build wheel/sdist and verify license files are packaged.
- [ ] **MC-22.019** — Publish the SPDX expression and third-party notice artifact with releases.
- [ ] **MC-22.020** — Record license decision in release/governance evidence.

### Required closure evidence

- [ ] **MC-22.021** — A reviewed design/specification for Explicit software license with explicit owner and version.
- [ ] **MC-22.022** — Repository-local implementation or authoritative external dependency declaration for Explicit software license.
- [ ] **MC-22.023** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-22.024** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-22.025** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-22.026** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-22: 26.**

## MC-23 — Continuous integration (CI) workflow

**Priority:** P0 — Release-blocking / security- or correctness-critical. Close before production certification.  
**Traceability:** INV-36-C070, INV-36-C090, INV-36-C100  
**Target outcome:** Automate deterministic build, test, security, compatibility, evidence, and release gates on every change and protected release branch.

### Related audit requirements

- **INV-36-C070 — MISSING:** Block releases that regress approved Control transport startup, density, throughput, or tail-latency thresholds.
- **INV-36-C090 — MISSING:** Require machine-readable acceptance evidence before certifying a Control transport release for production.
- **INV-36-C100 — MISSING:** Require a formal production exit gate confirming architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness.

### Workflow foundation

- [ ] **MC-23.001** — Create CI workflows for pull requests, protected-branch merges, scheduled/nightly tests, and tagged releases.
- [ ] **MC-23.002** — Pin OS images/toolchains/actions/plugins to approved versions or immutable revisions.
- [ ] **MC-23.003** — Use dependency caching only when cache keys include lockfile/hash/toolchain inputs and cannot bypass integrity checks.
- [ ] **MC-23.004** — Set explicit job timeouts and cancellation behavior.
- [ ] **MC-23.005** — Use concurrency controls to cancel obsolete PR runs while preserving release runs.
- [ ] **MC-23.006** — Upload logs/test reports/evidence with defined retention.

### Core quality gates

- [ ] **MC-23.007** — Run compile/import checks.
- [ ] **MC-23.008** — Run unit tests in normal and optimized (`-O`) modes where assertion-elision risk exists.
- [ ] **MC-23.009** — Run type checking and lint/static analysis if adopted by project standards.
- [ ] **MC-23.010** — Build wheel and sdist from a clean checkout.
- [ ] **MC-23.011** — Install built wheel into a clean environment and run smoke/round-trip tests.
- [ ] **MC-23.012** — Check package metadata/version synchronization.
- [ ] **MC-23.013** — Fail on generated schema/code drift.

### Security gates

- [ ] **MC-23.014** — Run dependency vulnerability scanning.
- [ ] **MC-23.015** — Run secret scanning.
- [ ] **MC-23.016** — Run static security analysis appropriate to Python/native dependencies.
- [ ] **MC-23.017** — Run threat-model-derived security tests.
- [ ] **MC-23.018** — Run property tests and bounded fuzzing.
- [ ] **MC-23.019** — Generate/verify SBOM, provenance, and artifact signatures on release workflows.
- [ ] **MC-23.020** — Use least-privilege CI permissions and short-lived release credentials.

### Integration/performance gates

- [ ] **MC-23.021** — Run fake-transport integration tests on every PR.
- [ ] **MC-23.022** — Run real-vsock platform integration on available certified runners/nightly infrastructure.
- [ ] **MC-23.023** — Run compatibility matrix jobs for required Python/OS/architecture combinations.
- [ ] **MC-23.024** — Run short performance smoke benchmarks on PRs and full certification benchmarks on release/nightly pipelines.
- [ ] **MC-23.025** — Compare performance against approved baseline and fail on disallowed regression.
- [ ] **MC-23.026** — Run soak/disaster/fleet-scale suites on scheduled or release pipelines.

### Evidence and release control

- [ ] **MC-23.027** — Invoke the `pk_core`/estate gate for production certification.
- [ ] **MC-23.028** — Aggregate JUnit/test, coverage, fuzz, security scan, compatibility, benchmark, SBOM, provenance, signature, and traceability results into one evidence manifest.
- [ ] **MC-23.029** — Bind evidence to source commit and built artifact digests.
- [ ] **MC-23.030** — Fail release when mandatory evidence is missing, malformed, skipped, expired, or failing.
- [ ] **MC-23.031** — Require protected-environment approval before signing/publishing production artifacts.
- [ ] **MC-23.032** — Publish only artifacts produced by the validated build job; never rebuild after approval.
- [ ] **MC-23.033** — Archive release evidence immutably.

### Required closure evidence

- [ ] **MC-23.034** — A reviewed design/specification for Continuous integration (CI) workflow with explicit owner and version.
- [ ] **MC-23.035** — Repository-local implementation or authoritative external dependency declaration for Continuous integration (CI) workflow.
- [ ] **MC-23.036** — Positive, negative, boundary, and failure-path automated tests with machine-readable results.
- [ ] **MC-23.037** — Traceability entries linking the component to relevant requirements, code, tests, risks, and release evidence.
- [ ] **MC-23.038** — Operational documentation covering deployment/configuration, diagnosis, rollback/recovery, and known limitations where applicable.
- [ ] **MC-23.039** — A production-exit-gate record showing all mandatory items complete or covered by an approved time-bounded waiver.

**Checklist items in MC-23: 39.**

## Recommended dependency-aware execution order

- [ ] 1. **Governance/source baseline:** MC-22 license, MC-19 ADR, MC-20 requirements/traceability, MC-21 ownership/governance, MC-02 source-corpus provenance.
- [ ] 2. **Security and external contracts:** MC-06 typed IDL, MC-04 authenticated establishment, MC-05 key custody/rotation, MC-07 authorization, MC-18 tamper-evident audit log.
- [ ] 3. **Runtime path:** MC-03 real virtio-vsock adapter, MC-08 configuration, MC-09 health/backpressure/failure control, MC-10 restart/recovery, MC-11 quarantine.
- [ ] 4. **Verification/telemetry:** MC-12 observability, MC-14 fuzzing, MC-13 performance certification, MC-15 compatibility matrix, MC-16 integration/disaster/soak/fleet-scale.
- [ ] 5. **Supply chain and automated certification:** MC-17 supply-chain controls, MC-23 CI, MC-01 estate gate runtime.
- [ ] 6. **Final production exit:** run MC-21 production gate only after required P0/P1 evidence is bound to the exact release artifact.

## Final release certification checklist

- [ ] All P0 component checklists are complete with no unresolved mandatory item.
- [ ] All P1 component checklists are complete or each remaining item has an approved owner, compensating control, documented risk, and expiry date.
- [ ] All 100 INV-36 controls have a final status based on current repository-local or authoritative certifying evidence.
- [ ] No `SKIP` or missing-infrastructure result is counted as a production PASS without explicit waiver.
- [ ] Cryptographic/session tests, real-vsock integration, fuzzing, adversarial security, recovery, compatibility, soak, and performance gates pass.
- [ ] SBOM, vulnerability scan, provenance, signatures, license/notice, and artifact digests are present and verified.
- [ ] Rollback, quarantine/emergency-disable, incident response, owner/escalation, and EOL/patch SLAs are approved and tested.
- [ ] The evidence manifest and production-exit decision are archived immutably and identify the exact 5.x release artifact being certified.
