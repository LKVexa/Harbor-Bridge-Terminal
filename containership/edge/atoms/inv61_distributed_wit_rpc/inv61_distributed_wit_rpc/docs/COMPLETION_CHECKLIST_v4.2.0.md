# INV-61 Distributed WIT RPC v4.2.0
# Missing Components — Professional Engineering Completion Checklist

**Source audit:** `POST_UPDATE_AUDIT.md` from INV-61 v4.2.0  
**Prepared:** 2026-09-22  
**Purpose:** Convert every post-update missing/incomplete component (M01–M32) into an implementation-ready, verification-oriented engineering checklist.

## Usage and completion rules

- A checkbox may be marked complete only when an implementation artifact **and** objective evidence exist.
- Evidence should be addressable by repository path, test identifier, build artifact digest, CI job URL/ID, benchmark report, ADR, runbook, or signed release record.
- “Implemented” without negative-path testing is not sufficient for security, reliability, protocol, or recovery items.
- Any waived item must have an owner, rationale, risk statement, compensating control, approval, review date, and expiry.
- Production exit requires all **Definition of Done / Acceptance Gates** for the applicable component to pass.
- Requirements should use normative language (`MUST`, `SHOULD`, `MAY`) and stable requirement IDs.

---

## M01 — `pk_core` dependency and reproducible dependency manifest
**Related audit controls:** C031, C040, C090, C100  
**Objective:** Make the original inventory/gating path reproducible from a clean machine with an explicit, pinned, integrity-verified `pk_core` dependency.

### Dependency definition and source control
- [ ] Determine whether `pk_core` is an internal package, public package, vendored module, monorepo workspace dependency, or generated artifact.
- [ ] Record the canonical source repository, package name, package index, and responsible owner.
- [ ] Pin an exact compatible `pk_core` version or immutable source revision; do not rely on an unbounded version range.
- [ ] Document the minimum and maximum supported versions if compatibility across multiple versions is intentionally supported.
- [ ] Add a package/build manifest (`pyproject.toml` or equivalent) declaring `pk_core` as an explicit dependency.
- [ ] Add a reproducible lock artifact containing resolved transitive dependency versions and hashes.
- [ ] Ensure dependency resolution is deterministic across supported platforms and Python versions.
- [ ] If vendoring is required, define the vendoring procedure, upstream revision, patch set, and update policy.
- [ ] Prohibit silent fallback to a different locally installed `pk_core` version.
- [ ] Fail startup/build clearly when the required version is absent or incompatible.

### Integrity and supply-chain controls
- [ ] Record SHA-256 or stronger digests for distributable dependency artifacts.
- [ ] Verify hashes during bootstrap/install before use.
- [ ] Require signed artifacts or repository commit verification where supported.
- [ ] Generate dependency provenance showing package source, version, digest, resolver, and build timestamp.
- [ ] Include `pk_core` in SBOM generation and vulnerability/license scanning.
- [ ] Define an allow-list of approved `pk_core` versions/revisions.
- [ ] Define a procedure for urgent revocation of a compromised dependency revision.
- [ ] Prevent dependency confusion by pinning the intended package index/namespace.
- [ ] Verify that local editable installs cannot accidentally shadow the production dependency in CI/release builds.

### Runtime and API compatibility
- [ ] Enumerate every symbol imported from `pk_core` by INV-61.
- [ ] Add explicit compatibility checks for required APIs at startup/test time.
- [ ] Validate the expected `pk_core` schema/inventory contract version.
- [ ] Add negative tests for missing symbols, incompatible return types, malformed inventory data, and version drift.
- [ ] Add a compatibility shim only if necessary; version and test it independently.
- [ ] Ensure errors identify the required package version without exposing sensitive environment data.

### Reproducibility and verification
- [ ] Add a clean-environment CI job that installs from the manifest/lock only.
- [ ] Run the three currently skipped `pk_core` conformance tests in that clean environment.
- [ ] Fail CI if any `pk_core` conformance test is skipped unexpectedly.
- [ ] Add an offline/restricted-network build test if offline deployment is a requirement.
- [ ] Verify bootstrap from an empty virtual environment on every supported Python runtime.
- [ ] Verify dependency resolution on Windows and at least one Linux distribution if both are supported.
- [ ] Capture a machine-readable dependency tree as a release artifact.

### Documentation and operations
- [ ] Document installation, upgrade, rollback, cache/offline-mirror, and troubleshooting procedures.
- [ ] Record the dependency owner and escalation path.
- [ ] Define cadence for dependency review and update qualification.
- [ ] Document compatibility expectations between INV-61 and `pk_core` releases.

### Definition of Done / Acceptance Gates
- [ ] A clean checkout can install all dependencies using only committed manifests/locks and approved package sources.
- [ ] `pk_core` version and artifact integrity are deterministic and verifiable.
- [ ] Original `pk_core` conformance suite executes with **zero unexpected skips** and passes.
- [ ] SBOM/provenance include `pk_core` and its transitive dependencies.
- [ ] Upgrade and rollback procedures have been exercised in CI or a release-candidate environment.

---

## M02 — Missing historical master-source artifact (`MASTER.md`)
**Related audit controls:** C020, C090, C100  
**Objective:** Restore or formally supersede the missing source-of-truth artifact for the 100-item master prompt/workflow set with traceable provenance.

### Source recovery and provenance
- [ ] Search authoritative source control history, release archives, build outputs, and documentation stores for the original `MASTER.md`.
- [ ] Verify recovered content against prior release hashes, tags, or review records where available.
- [ ] Record source revision, author/owner, recovery date, and provenance evidence.
- [ ] If the original cannot be recovered, create a formal loss record describing what is missing and why.
- [ ] Decide whether the authoritative replacement is `MASTER.md`, `CHECKLIST.json`, generated documentation, or another versioned artifact.
- [ ] Document the supersession decision in an ADR.

### Content integrity and traceability
- [ ] Ensure all 100 expected master prompts/workflows are present exactly once.
- [ ] Assign stable IDs that map unambiguously to C001–C100 or the intended control numbering.
- [ ] Cross-reference each source item to its corresponding structured checklist entry.
- [ ] Add a generation/validation script that detects missing, duplicate, reordered, or orphaned entries.
- [ ] Validate Markdown structure, headings, anchors, and machine-readable metadata if retained as Markdown.
- [ ] Preserve historical wording separately if a normalized/generated form is introduced.
- [ ] Add a schema/version marker to the master artifact.
- [ ] Add a checksum/digest for the authoritative source artifact to release metadata.

### Change management
- [ ] Define whether edits occur in `MASTER.md`, `CHECKLIST.json`, or a higher-level source generator.
- [ ] Prevent dual-authoritative sources from drifting silently.
- [ ] Add CI that regenerates derived artifacts and fails on uncommitted differences.
- [ ] Require review for changes affecting requirement intent or control semantics.
- [ ] Maintain changelog entries for material requirement changes.
- [ ] Define backward-compatibility expectations for control IDs and references.

### Verification
- [ ] Add tests confirming the expected count of 100 items.
- [ ] Add tests confirming unique control IDs.
- [ ] Add tests confirming every checklist control has a source entry and vice versa.
- [ ] Add a content digest comparison or signed manifest in release CI.
- [ ] Validate that README claims match actual repository contents.

### Definition of Done / Acceptance Gates
- [ ] A single authoritative master-source artifact is present or a formally documented replacement is established.
- [ ] All 100 controls have bidirectional traceability to the source.
- [ ] CI prevents missing/duplicate/drifted master content.
- [ ] Provenance and change-management rules are documented and reviewed.

---

## M03 — Real cross-host network transport adapter
**Related audit controls:** C011, C012, C021, C030, C083  
**Objective:** Convert in-process dictionary dispatch into a real, bounded, observable, secure remote invocation path between independent hosts.

### Transport architecture
- [ ] Select and document the production transport (for example QUIC, HTTP/2, HTTP/3, TCP+TLS, NATS, or an approved message fabric).
- [ ] Define why the selected transport satisfies latency, reliability, deployment, firewall/NAT, and security requirements.
- [ ] Specify client/server connection lifecycle states and transitions.
- [ ] Define stream/connection multiplexing semantics and maximum concurrent in-flight calls.
- [ ] Define request/response correlation rules.
- [ ] Define connection pooling, idle timeout, keepalive, reconnect, and drain behavior.
- [ ] Define DNS/service-discovery and endpoint-selection behavior.
- [ ] Define behavior for IPv4/IPv6, proxy traversal, NAT, and dual-stack environments as applicable.
- [ ] Specify maximum frame/message sizes before allocating full payload buffers.
- [ ] Define transport-level flow control and interaction with application backpressure.

### Adapter implementation
- [ ] Implement a transport-neutral client interface that accepts typed/canonical RPC frames.
- [ ] Implement a server listener/acceptor that emits validated frame bytes to the decoder.
- [ ] Keep transport bytes separate from decoded application values until validation succeeds.
- [ ] Enforce bounded reads and reject oversized length prefixes before allocation.
- [ ] Enforce read/write/connect/handshake/idle deadlines.
- [ ] Implement graceful connection shutdown/draining.
- [ ] Implement deterministic error mapping from transport failures to RPC status codes.
- [ ] Ensure partial reads/writes and fragmented frames are handled correctly.
- [ ] Protect against request smuggling, truncation, and frame boundary confusion.
- [ ] Ensure network-facing parser code never uses `pickle`, `eval`, arbitrary object deserialization, or unsafe dynamic imports.

### Security integration
- [ ] Require authenticated encrypted channels for production transport.
- [ ] Bind authenticated peer identity into RPC request context.
- [ ] Enforce host/peer verification and certificate validation.
- [ ] Define allowed cipher/protocol versions and disable insecure legacy negotiation.
- [ ] Rate-limit connection establishment and failed handshakes.
- [ ] Prevent unauthenticated peers from reaching dispatcher logic.

### Reliability behavior
- [ ] Define retry-safe versus non-retry-safe transport errors.
- [ ] Define behavior for mid-flight disconnects and ambiguous completion.
- [ ] Ensure duplicate execution cannot be silently caused by reconnect/retry behavior.
- [ ] Propagate cancellation and deadlines through the transport.
- [ ] Implement bounded queues for accepted but undispatched work.
- [ ] Reject new work during graceful drain when required.

### Verification and interoperability
- [ ] Add loopback integration tests over real sockets, not only direct function calls.
- [ ] Add two-process tests proving independent client/server process operation.
- [ ] Add two-host/container/network-namespace tests proving cross-host behavior.
- [ ] Test packet fragmentation, delayed packets, disconnects, resets, half-close, and timeout paths.
- [ ] Test malformed length fields and intentionally truncated frames.
- [ ] Test concurrency at the configured maximum and above it.
- [ ] Add interoperability tests with at least one independently implemented peer if the protocol is intended to be open/interoperable.
- [ ] Benchmark framing and transport overhead separately.

### Observability and operations
- [ ] Emit connection, handshake, stream, byte, retry, timeout, and failure metrics.
- [ ] Emit structured connection lifecycle logs without leaking credentials or payload secrets.
- [ ] Propagate trace context at the transport boundary.
- [ ] Expose active connections, inflight calls, queue depth, and transport saturation in readiness/metrics.
- [ ] Document firewall ports, service discovery, certificates, proxies, and operational limits.

### Definition of Done / Acceptance Gates
- [ ] Cross-host invocation succeeds between isolated processes/machines using the production adapter.
- [ ] Malformed/oversized/unauthenticated network traffic is rejected before dispatch.
- [ ] Deadline, cancellation, reconnect, and graceful-drain semantics have automated coverage.
- [ ] Transport resource limits are measurable and enforced.
- [ ] Interoperability, security, and performance test evidence is attached to the release candidate.

---

## M04 — WIT parser/bindings and canonical wire serialization
**Related audit controls:** C021, C022, C029, C084, C085  
**Objective:** Implement a standards-aligned WIT/component-model contract pipeline and deterministic byte-level wire representation.

### WIT source model
- [ ] Define the authoritative WIT package/world/interface files and repository locations.
- [ ] Pin the WIT/component-model specification version targeted by the implementation.
- [ ] Define naming/versioning conventions for packages, interfaces, worlds, resources, and functions.
- [ ] Validate WIT sources during CI with an approved parser/toolchain.
- [ ] Fail builds on unresolved imports, duplicate definitions, unsupported types, or semantic errors.
- [ ] Record a normalized interface digest used for compatibility checks.

### Binding generation
- [ ] Select or implement a deterministic binding generator.
- [ ] Generate host/client and guest/server bindings as applicable.
- [ ] Ensure generated bindings are reproducible from committed WIT sources.
- [ ] Version generated-code templates/tooling.
- [ ] Add CI that regenerates bindings and fails on drift.
- [ ] Document when generated files are committed versus built on demand.
- [ ] Ensure generated code does not contain unsafe deserialization shortcuts.

### Canonical value mapping
- [ ] Define mapping for all supported WIT scalar types.
- [ ] Define mapping for strings, lists, tuples, records, variants, options, results, enums, flags, and resources as applicable.
- [ ] Define integer width/sign behavior and overflow rejection.
- [ ] Define UTF-8 validation and invalid-sequence behavior.
- [ ] Define floating-point NaN/infinity/canonicalization policy where floats are supported.
- [ ] Define maximum nesting depth, collection length, string length, and total decoded size.
- [ ] Define resource-handle identity/lifetime semantics if resources cross the boundary.
- [ ] Define unknown variant/discriminant handling.

### Wire codec
- [ ] Specify the byte-level frame format, including magic/version/type/length fields if used.
- [ ] Specify endianness and canonical integer encoding.
- [ ] Ensure the same logical value has one canonical serialized form where required.
- [ ] Reject trailing bytes, duplicate fields, impossible lengths, and non-canonical encodings.
- [ ] Parse incrementally with bounded allocations.
- [ ] Enforce maximum frame size prior to full payload allocation.
- [ ] Keep schema/version negotiation separate from payload decode where practical.
- [ ] Produce deterministic error codes for syntax, schema, type, and bounds failures.

### Interoperability fixtures
- [ ] Create golden byte fixtures for representative WIT values and full RPC frames.
- [ ] Include boundary values for every numeric type.
- [ ] Include empty/max-length lists and strings.
- [ ] Include nested record/variant/result combinations.
- [ ] Include malformed/truncated/oversized/non-canonical fixtures.
- [ ] Validate fixtures with an independent implementation/toolchain.
- [ ] Store fixture digests and protocol version metadata.

### Testing and fuzzing
- [ ] Add round-trip encode/decode property tests.
- [ ] Add decode(encode(x)) equality tests for all supported value domains.
- [ ] Add canonical re-encoding tests for accepted input.
- [ ] Add coverage-guided fuzz targets at raw-byte decode boundaries.
- [ ] Add parser differential tests against an independent WIT implementation where feasible.
- [ ] Add memory-allocation and nesting-depth adversarial tests.

### Definition of Done / Acceptance Gates
- [ ] WIT sources are authoritative, validated, versioned, and traceable to generated bindings.
- [ ] Canonical byte serialization is specified and covered by golden fixtures.
- [ ] Independent peer/tooling can exchange representative frames successfully.
- [ ] Malformed byte streams fail closed within explicit CPU/memory bounds.
- [ ] Binding and codec generation are reproducible in CI.

---

## M05 — Protocol negotiation and supported-version compatibility matrix
**Related audit controls:** C016, C027, C093  
**Objective:** Replace exact-version-only rejection with an explicit, safe negotiation and migration policy while preventing unintended downgrade.

### Version model
- [ ] Define separate versions for transport framing, RPC envelope, WIT schema/interface, and implementation if they evolve independently.
- [ ] Define compatibility semantics for major/minor/patch changes.
- [ ] Identify which changes are wire-compatible, source-compatible, behavior-compatible, or breaking.
- [ ] Define minimum supported peer versions per release.
- [ ] Define deprecation windows and end-of-support policy.
- [ ] Publish a machine-readable compatibility matrix.

### Negotiation protocol
- [ ] Define a pre-dispatch negotiation message or handshake capability exchange.
- [ ] Advertise supported protocol versions/ranges and optional capabilities.
- [ ] Select the highest mutually supported non-prohibited version deterministically.
- [ ] Bind the negotiated version to the authenticated session.
- [ ] Prevent mid-session renegotiation unless explicitly supported.
- [ ] Reject peers with no compatible version using a stable error code.
- [ ] Avoid revealing unnecessary implementation details in negotiation failures.

### Downgrade protection
- [ ] Define a policy for versions disabled due to security vulnerabilities.
- [ ] Refuse negotiation to revoked versions even if both peers technically support them.
- [ ] Bind negotiated parameters cryptographically to the secure channel where possible.
- [ ] Log attempted prohibited downgrades as security events.
- [ ] Test active downgrade/man-in-the-middle scenarios.

### Migration/adaptation
- [ ] Define adapters for intentionally supported schema migrations.
- [ ] Document lossy versus lossless conversions.
- [ ] Reject fields/types that cannot be safely represented in the negotiated version.
- [ ] Ensure compatibility adapters have independent unit and integration tests.
- [ ] Define operational sequencing for rolling upgrades across mixed-version fleets.
- [ ] Define rollback expectations after partial rollout.

### Verification
- [ ] Build a full pairwise version interoperability matrix for supported releases.
- [ ] Test current↔current, current↔oldest-supported, and rolling-upgrade combinations.
- [ ] Add negative tests for unknown future versions.
- [ ] Add negative tests for revoked/insecure versions.
- [ ] Add tests for incompatible WIT/interface revisions even when transport versions match.
- [ ] Gate releases on the published compatibility matrix.

### Definition of Done / Acceptance Gates
- [ ] Supported peer/version combinations are machine-readable and release-versioned.
- [ ] Negotiation selects only mutually supported, policy-approved versions.
- [ ] Downgrade attacks and revoked versions are rejected and auditable.
- [ ] Rolling upgrade and rollback procedures are tested across supported combinations.

---

## M06 — Peer/node/workload authentication integration
**Related audit controls:** C023, C044, C048  
**Objective:** Establish cryptographically verifiable identity for every production caller and callee and carry that identity into authorization/audit decisions.

### Identity architecture
- [ ] Define identity principals: node, workload, service, tenant, operator, and/or component instance.
- [ ] Select the identity mechanism (for example mTLS PKI, SPIFFE/SPIRE SVIDs, workload attestation, signed tokens, or approved equivalent).
- [ ] Define trust roots and trust domains.
- [ ] Define issuer/CA ownership and rotation responsibilities.
- [ ] Define identity naming conventions and uniqueness requirements.
- [ ] Define how tenant/workload identity maps to WIT interface authorization subjects.

### Authentication implementation
- [ ] Authenticate peers before accepting RPC application data.
- [ ] Validate certificate/token signatures, issuer, audience, validity window, and revocation status as applicable.
- [ ] Enforce hostname/SPIFFE ID/service identity constraints.
- [ ] Bind authenticated identity to the transport/session to prevent identity swapping.
- [ ] Pass an immutable authenticated-principal object into `Endpoint.handle`/dispatch context.
- [ ] Ensure application-provided identity fields cannot override authenticated transport identity.
- [ ] Reject anonymous identity unless explicitly allowed by policy for a specific endpoint.
- [ ] Define clock-skew tolerance for expiring credentials.

### Credential lifecycle
- [ ] Implement automated credential issuance/bootstrap.
- [ ] Implement rotation without requiring full fleet restart where feasible.
- [ ] Define short-lived credential policy.
- [ ] Implement revocation/emergency disable behavior.
- [ ] Define behavior during identity-provider or CA outage.
- [ ] Prevent expired credentials from being accepted due to stale caches.
- [ ] Protect private keys using OS/TPM/HSM/secret-store controls appropriate to the deployment tier.

### Security controls
- [ ] Rate-limit authentication failures.
- [ ] Avoid credential/token contents in logs.
- [ ] Detect and audit identity mismatch or impersonation attempts.
- [ ] Define protection against token replay if bearer tokens are used.
- [ ] Require mutual authentication for privileged/admin/control-plane RPC.
- [ ] Test unknown CA, expired cert, revoked cert, wrong audience, wrong service identity, and malformed credential cases.

### Observability and operations
- [ ] Emit authentication success/failure counters partitioned by non-sensitive reason codes.
- [ ] Include authenticated principal IDs in authorized audit events subject to privacy rules.
- [ ] Expose credential-expiry horizon metrics without exposing secrets.
- [ ] Alert on elevated authentication failure rates and imminent fleet credential expiry.
- [ ] Provide runbooks for rotation, revocation, trust-root rollover, and identity-provider outage.

### Definition of Done / Acceptance Gates
- [ ] Every production RPC session has a verified principal before dispatch.
- [ ] Principal identity is immutable and available to authorization/audit layers.
- [ ] Credential rotation and revocation are automated and tested.
- [ ] Negative authentication tests and outage scenarios pass.
- [ ] No secrets/private keys/tokens are emitted in logs or error responses.

---

## M07 — Authorization and capability enforcement
**Related audit controls:** C024, C042, C043, C046  
**Objective:** Enforce least-privilege access to interfaces/functions/resources using authenticated identity and explicit capability/policy decisions.

### Policy model
- [ ] Define authorization subjects, resources, actions, conditions, and decision outcomes.
- [ ] Map WIT package/interface/function/resource operations to stable authorization resource IDs.
- [ ] Define tenant boundaries and cross-tenant access rules.
- [ ] Define capability grant format, scope, expiration, delegation, and revocation semantics.
- [ ] Choose RBAC, ABAC, capability tokens, policy engine, or a documented combination.
- [ ] Define default-deny behavior for unknown resources/actions.
- [ ] Define policy precedence and conflict resolution.

### Enforcement points
- [ ] Enforce authorization after authentication but before user function dispatch.
- [ ] Enforce at both interface and function level where required.
- [ ] Enforce per-resource instance ownership/capability for stateful WIT resources.
- [ ] Ensure authorization checks use trusted authenticated context, not caller-controlled identity fields.
- [ ] Prevent registration of exported functions that bypass policy hooks.
- [ ] Ensure internal/admin functions have separate, stricter policy controls.
- [ ] Deny calls if the policy engine is unavailable unless an explicitly approved fail-open exception exists.

### Capability lifecycle
- [ ] Implement issuance/grant workflow with owner approval where required.
- [ ] Implement expiration and revocation.
- [ ] Prevent capability replay outside allowed subject/session/audience.
- [ ] Define delegation and attenuation semantics if delegation is supported.
- [ ] Record provenance for grants and revocations.
- [ ] Prevent capability escalation through wildcard or overly broad pattern matching.

### Decision auditing
- [ ] Emit stable authorization decision IDs/reason codes.
- [ ] Audit denials and privileged grants without logging secret tokens.
- [ ] Correlate authorization decisions with request/trace IDs.
- [ ] Record policy version/hash used for each auditable decision.
- [ ] Expose metrics for allow/deny/error outcomes and policy latency.

### Verification
- [ ] Add positive tests for every intended authorized role/capability.
- [ ] Add negative tests for missing, expired, revoked, wrong-tenant, wrong-interface, and wrong-function permissions.
- [ ] Add privilege-escalation tests for wildcard, inheritance, delegation, and confused-deputy cases.
- [ ] Add policy-engine outage and stale-cache tests.
- [ ] Add cross-tenant isolation tests.
- [ ] Add mutation tests ensuring a removed check causes test failure.

### Definition of Done / Acceptance Gates
- [ ] All dispatchable operations have an explicit authorization policy mapping.
- [ ] Default-deny is enforced for unspecified access.
- [ ] Privilege-escalation and cross-tenant negative tests pass.
- [ ] Policy decisions are auditable and tied to immutable policy versions.
- [ ] Grant/revoke lifecycle is operationally documented and exercised.

---

## M08 — Transport encryption and key lifecycle
**Related audit controls:** C047, C048  
**Objective:** Protect RPC confidentiality and integrity in transit and define complete certificate/key lifecycle controls.

### Cryptographic architecture
- [ ] Require TLS 1.3, QUIC TLS, or an equivalently approved authenticated encryption channel for production.
- [ ] Define approved cipher suites and key exchange algorithms.
- [ ] Disable insecure protocol versions, renegotiation modes, and weak algorithms.
- [ ] Define certificate/key sizes and cryptoperiods.
- [ ] Define trust-root storage and rollover procedures.
- [ ] Document whether payload-level encryption/signatures are needed in addition to transport security.

### Channel establishment
- [ ] Validate peer identity during the secure handshake.
- [ ] Require mutual TLS for service-to-service production traffic where appropriate.
- [ ] Enforce server name/SPIFFE/service identity verification.
- [ ] Bind RPC negotiation and authenticated identity to the established channel.
- [ ] Ensure application data is never dispatched before secure-channel establishment completes.
- [ ] Configure handshake timeouts and resource bounds.

### Key protection and rotation
- [ ] Store private keys in protected OS stores, HSMs, TPMs, or approved secret managers.
- [ ] Restrict key file permissions and process access.
- [ ] Automate certificate issuance and renewal.
- [ ] Support overlap windows for zero-downtime rotation.
- [ ] Define emergency revocation and compromised-key replacement procedure.
- [ ] Test trust-root rollover with mixed old/new certificates.
- [ ] Prevent stale session resumption from bypassing revocation policy where relevant.

### Failure and outage semantics
- [ ] Define fail-closed behavior when certificates are expired, revoked, malformed, or unverifiable.
- [ ] Define behavior when OCSP/CRL/identity service is temporarily unavailable.
- [ ] Prevent fallback to plaintext on secure-channel failure.
- [ ] Emit clear but non-sensitive failure reason codes.
- [ ] Rate-limit repeated failed handshakes.

### Verification
- [ ] Test plaintext connection rejection.
- [ ] Test expired, not-yet-valid, revoked, wrong-host, wrong-trust-domain, and self-signed certificates.
- [ ] Test supported and prohibited protocol/cipher combinations.
- [ ] Test rotation under active load.
- [ ] Test key compromise/revocation and recovery procedure.
- [ ] Add automated configuration scanning for insecure TLS settings.

### Definition of Done / Acceptance Gates
- [ ] All production network paths are authenticated and encrypted with approved algorithms.
- [ ] Plaintext fallback is impossible in production configuration.
- [ ] Key/certificate rotation and revocation have automated tests and runbooks.
- [ ] Trust-root rollover is validated without uncontrolled outage.
- [ ] Crypto configuration is continuously checked in CI/release validation.

---
## M09 — Replay/spoofing defenses and request identity
**Related audit controls:** C041, C049, C050  
**Objective:** Give every call a cryptographically bound identity and prevent replay, spoofing, and ambiguous duplicate execution.

### Request identity model
- [ ] Define a globally unique request ID format with sufficient entropy (for example UUIDv7/128-bit random or equivalent).
- [ ] Separate request ID, attempt ID, trace ID, and idempotency key; document each semantic role.
- [ ] Require request IDs on all production calls before dispatch.
- [ ] Validate request ID syntax/length and reject malformed identifiers before expensive processing.
- [ ] Bind authenticated sender identity, destination, interface, function, negotiated version, and request ID into the authenticated session/envelope.
- [ ] Prevent callers from supplying a sender identity that overrides the transport-authenticated principal.
- [ ] Define request ID retention duration sufficient for deduplication/audit requirements.

### Anti-replay mechanism
- [ ] Select nonce, monotonic sequence, timestamp-window, idempotency-ledger, or signed-envelope replay protection appropriate to the transport.
- [ ] Define replay window size and maximum accepted clock skew if timestamps are used.
- [ ] Persist replay state where restart would otherwise reopen the replay window.
- [ ] Key replay detection by authenticated principal and security context, not by request ID alone.
- [ ] Reject exact duplicate envelopes deterministically.
- [ ] Distinguish legitimate idempotent retries from hostile replay.
- [ ] Bound replay-cache memory and define eviction behavior that does not silently weaken security.
- [ ] Define behavior during cache/state-store outage; default to fail closed for security-sensitive operations.

### Spoofing/tamper resistance
- [ ] Authenticate the sender and receiver endpoints.
- [ ] Integrity-protect request metadata including request ID, method, interface version, deadline, and capability context.
- [ ] Reject messages whose authenticated channel identity conflicts with envelope identity.
- [ ] Detect invalid sequence/nonce reuse and raise a security event.
- [ ] Ensure intermediaries cannot rewrite authorization-relevant fields without detection.
- [ ] Prohibit unsigned/unbound caller-supplied audit identities.

### Duplicate execution handling
- [ ] Define exactly-once, at-most-once, or at-least-once expectations per operation class.
- [ ] Require idempotency keys for retriable mutating operations where applicable.
- [ ] Cache completed idempotent results for a bounded retention period.
- [ ] Return the original result/status for a recognized idempotent retry when safe.
- [ ] Define outcome for duplicate non-idempotent requests (reject, conflict, or manual resolution).
- [ ] Ensure ambiguous network failure does not trigger unconditional re-execution.

### Testing and evidence
- [ ] Test identical request replay on the same connection.
- [ ] Test replay across reconnects/new sessions.
- [ ] Test replay after server restart.
- [ ] Test nonce/sequence wraparound and out-of-order windows if applicable.
- [ ] Test spoofed request IDs and spoofed sender identities.
- [ ] Test replay cache saturation/eviction behavior.
- [ ] Test legitimate retries remain functional without weakening replay controls.
- [ ] Verify audit records correlate replay rejection with request and principal IDs.

### Definition of Done / Acceptance Gates
- [ ] Every call has a stable request identity and authenticated principal binding.
- [ ] Replay attempts are detected across the defined threat window, including restart where required.
- [ ] Duplicate execution semantics are formally documented per operation class.
- [ ] Security/audit events distinguish replay, malformed identity, duplicate retry, and spoofing.

---

## M10 — Cancellation, idempotency, retry, and reconnect semantics
**Related audit controls:** C014, C018, C025, C053, C057, C089  
**Objective:** Define predictable behavior when calls are cancelled, retried, disconnected, timed out, or resumed, without creating duplicate side effects.

### Deadline and cancellation semantics
- [ ] Define absolute deadline representation and clock domain.
- [ ] Specify client-to-server deadline propagation and maximum deadline horizon.
- [ ] Distinguish deadline expiration from explicit caller cancellation.
- [ ] Propagate cancellation to in-flight handlers using a cancellable context/token.
- [ ] Define whether cancellation is cooperative, preemptive, or advisory for each execution tier.
- [ ] Ensure handlers can observe cancellation without polling unsafe global state.
- [ ] Define cleanup guarantees for partially executed calls.
- [ ] Return stable cancellation/deadline status codes.
- [ ] Prevent cancellation after a committed side effect from being reported as if nothing happened.

### Idempotency model
- [ ] Classify operations as safe/read-only, idempotent-mutating, non-idempotent, streaming, or transactional.
- [ ] Encode retry/idempotency policy in interface metadata or generated bindings.
- [ ] Define idempotency-key format, scope, TTL, and collision handling.
- [ ] Persist idempotency results for the required retry horizon.
- [ ] Ensure result caching cannot leak data across tenants/principals.
- [ ] Define conflict semantics when the same key is reused with different arguments.

### Retry policy
- [ ] Define which status/error classes are retriable.
- [ ] Prohibit automatic retry of non-idempotent operations unless an explicit idempotency mechanism exists.
- [ ] Implement bounded exponential backoff with jitter.
- [ ] Define max attempts, max total retry duration, and per-attempt deadline budgeting.
- [ ] Respect `Retry-After`/server retry hints if the protocol supports them.
- [ ] Stop retries when the original call deadline/cancellation fires.
- [ ] Prevent synchronized retry storms through jitter and server overload hints.

### Reconnect/resume state machine
- [ ] Define connection states and transitions: disconnected, connecting, authenticated, ready, draining, failed, closed.
- [ ] Define how in-flight requests are classified after disconnect: definitely not sent, maybe sent, completed-unknown, completed-known.
- [ ] Retry only calls whose semantics permit it.
- [ ] Define session resumption requirements and security binding.
- [ ] Avoid reusing stale authentication/authorization state after reconnect.
- [ ] Re-run version/capability negotiation after reconnect where required.

### Observability
- [ ] Emit attempts-per-call, retry delay, cancellation, deadline, ambiguous completion, and reconnect metrics.
- [ ] Log reason-coded retries/cancellations without payload secrets.
- [ ] Correlate all attempts to one logical request ID.
- [ ] Trace retry attempts as child spans/linked spans with consistent semantics.

### Verification
- [ ] Test cancellation before dispatch, during queue wait, during handler execution, and during response write.
- [ ] Test timeout exactly at deadline boundary.
- [ ] Test retriable and non-retriable error classification.
- [ ] Test duplicate suppression for idempotent retries.
- [ ] Test disconnect before request bytes, mid-request, after request/ before response, and mid-response.
- [ ] Test retry exhaustion and backoff caps.
- [ ] Test server restart during in-flight calls.
- [ ] Test reconnect under rolling deployment and certificate rotation.

### Definition of Done / Acceptance Gates
- [ ] Retry behavior is deterministic and derived from documented operation semantics.
- [ ] Non-idempotent side effects cannot be duplicated by automatic reconnect/retry logic.
- [ ] Cancellation/deadline propagation is end-to-end tested.
- [ ] Reconnect state is observable and produces no hidden infinite retry loops.

---

## M11 — Backpressure, admission control, and circuit breaking
**Related audit controls:** C017, C025, C028, C054, C067  
**Objective:** Bound resource consumption under overload, protect dependencies, and provide fair admission/load shedding.

### Resource limits
- [ ] Define max encoded frame bytes.
- [ ] Define max decoded payload bytes.
- [ ] Define max argument count, collection length, string length, nesting depth, and resource-handle count.
- [ ] Define max concurrent connections per node and per principal/tenant.
- [ ] Define max concurrent requests globally and per interface/function.
- [ ] Define max queued requests and queue memory budget.
- [ ] Define max response size and streaming buffer size.
- [ ] Enforce limits before unbounded allocation whenever possible.

### Admission control
- [ ] Implement bounded admission queues.
- [ ] Define priority classes and starvation/fairness rules if priorities exist.
- [ ] Implement per-tenant/principal quotas.
- [ ] Implement token/leaky bucket or equivalent request-rate limiting.
- [ ] Define overload rejection status and retry hints.
- [ ] Ensure rejected calls do not consume normal execution slots.
- [ ] Reserve capacity for health/control/admin traffic if operationally necessary.
- [ ] Define burst capacity separately from sustained rate.

### Backpressure propagation
- [ ] Propagate receiver saturation to senders rather than buffering indefinitely.
- [ ] Integrate transport flow control with RPC queue limits.
- [ ] Bound producer speed for streaming operations.
- [ ] Expose queue depth/high-water marks to adaptive clients.
- [ ] Define behavior when downstream dependencies apply backpressure.

### Circuit breakers
- [ ] Implement breaker states (closed/open/half-open) with deterministic transitions.
- [ ] Define failure types counted toward breaker trip thresholds.
- [ ] Exclude caller errors that should not penalize dependency health.
- [ ] Define rolling window, failure threshold, open duration, and probe policy.
- [ ] Scope breakers appropriately per dependency/endpoint/tenant.
- [ ] Emit state-transition events and metrics.
- [ ] Prevent breaker oscillation through hysteresis/backoff.

### Overload safety
- [ ] Shed load before memory/FD/thread/task exhaustion.
- [ ] Ensure overload errors are cheap to generate.
- [ ] Prevent unauthenticated clients from consuming protected queue capacity.
- [ ] Define degraded-mode feature shedding order.
- [ ] Validate that administrative/emergency-disable channels remain available under overload.

### Verification
- [ ] Test every configured hard limit at limit-1, limit, and limit+1.
- [ ] Run burst and sustained overload tests.
- [ ] Verify bounded memory under malicious oversized/slow clients.
- [ ] Verify fairness across tenants under contention.
- [ ] Verify circuit breaker opens, probes, recovers, and reopens correctly.
- [ ] Test downstream outage with caller retry pressure.
- [ ] Verify graceful degradation rather than process crash/OOM.

### Definition of Done / Acceptance Gates
- [ ] CPU, memory, connection, queue, and concurrency limits are explicit and enforced.
- [ ] Overload results in bounded rejection/degradation, not unbounded queuing or resource exhaustion.
- [ ] Per-tenant fairness and protected control capacity are validated.
- [ ] Circuit-breaker behavior is observable and tested under real failure scenarios.

---

## M12 — Configuration subsystem and provenance
**Related audit controls:** C032–C040  
**Objective:** Provide validated, versioned, atomic, provenance-rich configuration with safe secrets handling and rollback.

### Configuration model
- [ ] Define all runtime configuration keys in a typed schema.
- [ ] Classify settings as immutable-at-startup, hot-reloadable, secret, policy-controlled, or derived.
- [ ] Define defaults explicitly and prohibit hidden environment-dependent defaults for security-critical settings.
- [ ] Assign units/ranges/enums for numeric and enumerated settings.
- [ ] Define required versus optional values.
- [ ] Define precedence among defaults, file, environment, CLI, orchestrator, and remote config.
- [ ] Reject unknown keys unless forward-compatible behavior is explicitly designed.

### Validation
- [ ] Validate syntax and schema before activation.
- [ ] Validate semantic invariants across related fields.
- [ ] Validate referenced files/certificates/endpoints without exposing secrets.
- [ ] Validate security minima (TLS, auth, size limits, retry ceilings) cannot be disabled accidentally in production profile.
- [ ] Fail startup on invalid required configuration.
- [ ] Return stable validation errors identifying the offending key and constraint.

### Provenance
- [ ] Compute a canonical configuration hash.
- [ ] Record source/provenance for each effective value where practical.
- [ ] Expose non-secret effective configuration metadata through diagnostics.
- [ ] Record config version/hash in logs, traces, audit events, and release evidence.
- [ ] Associate configuration changes with actor, reason, approval, and deployment ID.

### Atomic activation and rollback
- [ ] Parse and validate candidate configuration before replacing active configuration.
- [ ] Activate multi-key changes atomically.
- [ ] Preserve last-known-good configuration.
- [ ] Automatically roll back on activation failure where safe.
- [ ] Define reload concurrency semantics for in-flight calls.
- [ ] Prevent partial security-policy updates.
- [ ] Provide explicit reload success/failure health signal.

### Secret separation
- [ ] Keep credentials/private keys/tokens out of ordinary config files where possible.
- [ ] Reference secret-manager identifiers rather than raw secret values.
- [ ] Redact secret values from diagnostics/errors/logs.
- [ ] Enforce restrictive file/secret permissions.
- [ ] Define secret rotation/reload behavior.
- [ ] Ensure configuration snapshots/backups do not accidentally contain plaintext secrets.

### Environment overlays
- [ ] Define base/site/environment/tenant override model.
- [ ] Validate overlays against the same schema.
- [ ] Detect conflicting or shadowed settings.
- [ ] Make effective configuration deterministic regardless of file enumeration order.
- [ ] Test development, staging, and production profiles separately.

### Verification
- [ ] Add schema unit tests for every key.
- [ ] Add invalid type/range/unknown key tests.
- [ ] Add atomic rollback tests.
- [ ] Add hot-reload race tests if reload is supported.
- [ ] Add secret-redaction tests.
- [ ] Add golden effective-config snapshots for representative deployments.

### Definition of Done / Acceptance Gates
- [ ] Effective configuration is typed, validated, reproducible, and provenance-addressable.
- [ ] Security-critical defaults cannot silently degrade.
- [ ] Updates are atomic and rollback-capable.
- [ ] Secrets are isolated and redaction is verified.
- [ ] Release artifacts identify the configuration schema/version they support.

---

## M13 — Tamper-evident security audit event pipeline
**Related audit controls:** C049  
**Objective:** Produce durable, integrity-protected security events for accountability, forensics, and compliance.

### Audit event schema
- [ ] Define stable event IDs and schema version.
- [ ] Include event time, monotonic sequence if available, node/service identity, authenticated principal, request/trace ID, event type, outcome, and reason code.
- [ ] Include policy/config version hashes relevant to the decision.
- [ ] Include target interface/function/resource identifiers without sensitive payload content.
- [ ] Define mandatory events: auth success/failure, authorization denial, replay rejection, version/signature drift, config change, key rotation, emergency disable, privileged operation, and audit pipeline failure.
- [ ] Define data classification and privacy/redaction rules for every field.

### Tamper evidence
- [ ] Chain records using cryptographic hashes or use an append-only integrity-protected backend.
- [ ] Sign batches/checkpoints with a protected signing key where required.
- [ ] Include sequence numbers to detect deletion/reordering.
- [ ] Store checkpoints outside the service trust boundary where feasible.
- [ ] Define verification tooling to validate chain/signatures.
- [ ] Protect audit signing keys separately from application data-plane keys.

### Durability and delivery
- [ ] Use bounded local buffering with explicit overflow policy.
- [ ] Define whether security-sensitive operations fail closed if audit delivery is unavailable.
- [ ] Retry export with bounded backoff.
- [ ] Persist unshipped critical audit events across restart if required.
- [ ] Prevent unauthenticated callers from flooding audit storage unchecked.
- [ ] Track dropped/deferred audit events as health/metrics.

### Access and retention
- [ ] Define retention duration by event class.
- [ ] Restrict audit read access using least privilege.
- [ ] Separate operational logs from immutable security audit records.
- [ ] Define legal/privacy deletion exceptions and procedures where applicable.
- [ ] Encrypt audit data in transit and at rest.

### Verification
- [ ] Test every required event type.
- [ ] Test redaction of secrets/tokens/payloads.
- [ ] Tamper with stored records and verify detection.
- [ ] Delete/reorder records and verify sequence/chain detection.
- [ ] Simulate sink outage, disk full, backpressure, and restart.
- [ ] Verify time synchronization/clock anomaly handling in event ordering.
- [ ] Exercise forensic reconstruction from a representative incident trace.

### Definition of Done / Acceptance Gates
- [ ] Required security decisions generate durable, schema-valid audit events.
- [ ] Record deletion/modification/reordering is detectable within the defined threat model.
- [ ] Audit sink failure is observable and handled according to documented fail-open/fail-closed policy.
- [ ] Forensic correlation across principal/request/policy/config versions is demonstrable.

---

## M14 — Health/readiness/dependency status endpoint
**Related audit controls:** C052, C071  
**Objective:** Expose actionable liveness, readiness, dependency, and degradation status without leaking sensitive internals.

### Health model
- [ ] Define separate liveness, readiness, startup, and dependency health semantics.
- [ ] Define component states such as starting, ready, degraded, draining, not-ready, failed.
- [ ] Define transition criteria and debounce/hysteresis rules.
- [ ] Ensure liveness does not depend on optional external dependencies.
- [ ] Ensure readiness reflects ability to serve requests safely, including auth/policy/config/transport prerequisites.
- [ ] Define stall detection for event loop/thread pool/queue progress.

### Dependency checks
- [ ] Enumerate critical dependencies: identity provider, policy engine, state store, transport broker, config source, audit sink, etc.
- [ ] Define per-dependency timeout and freshness threshold.
- [ ] Avoid expensive synchronous deep checks on every probe.
- [ ] Cache dependency health with bounded staleness.
- [ ] Expose degraded-but-serving versus hard-not-ready distinctions.

### Endpoint design
- [ ] Provide machine-readable status with schema version.
- [ ] Include service version/build ID/config hash/protocol version where safe.
- [ ] Include reason-coded component states.
- [ ] Do not expose credentials, internal topology, stack traces, or sensitive endpoint details.
- [ ] Separate public/basic health from authenticated detailed diagnostics if necessary.
- [ ] Make health endpoint resource use bounded and independent of normal request backlog where possible.

### Orchestrator integration
- [ ] Document probe intervals, timeouts, failure thresholds, and initial delay.
- [ ] Validate Kubernetes/systemd/orchestrator integration if used.
- [ ] Ensure drain sets readiness false before terminating active work.
- [ ] Ensure transient dependency blips do not cause restart storms.

### Verification
- [ ] Test healthy, degraded, not-ready, draining, and failed states.
- [ ] Test dependency timeout/outage and recovery transitions.
- [ ] Test event-loop/thread stall simulation.
- [ ] Verify probe endpoints remain responsive under overload.
- [ ] Verify sensitive data never appears in health output.

### Definition of Done / Acceptance Gates
- [ ] Operators/orchestrators can distinguish alive, ready, degraded, and draining states.
- [ ] Critical dependency failures drive documented readiness behavior.
- [ ] Health checks are bounded, non-sensitive, and overload-resilient.
- [ ] Probe configuration is included in deployment artifacts and tested.

---

## M15 — Production metrics exporter
**Related audit controls:** C061–C064, C069, C072, C080  
**Objective:** Export low-cardinality, actionable metrics for latency, errors, saturation, capacity, and protocol health.

### Metric taxonomy
- [ ] Define service-level request count, error count, and duration histograms.
- [ ] Define transport connection/stream metrics.
- [ ] Define inflight requests, queue depth, queue wait, and rejection metrics.
- [ ] Define retry/cancellation/deadline metrics.
- [ ] Define authentication/authorization outcome metrics with safe reason labels.
- [ ] Define version/signature/serialization mismatch counters.
- [ ] Define circuit-breaker state and trip counters.
- [ ] Define CPU, memory, FD/socket, thread/task, and network byte metrics.
- [ ] Define audit exporter/config/identity dependency health metrics.
- [ ] Define build/version/config metadata as info metrics with bounded labels.

### Histogram/SLO design
- [ ] Choose histogram buckets appropriate to p50/p95/p99 latency targets.
- [ ] Separate queue time, handler time, serialization time, and transport time where useful.
- [ ] Measure request and response payload size distributions.
- [ ] Define saturation indicators used for capacity planning.
- [ ] Define error-budget/SLO metric formulas.

### Cardinality controls
- [ ] Prohibit raw request IDs, user IDs, unbounded resource IDs, URLs, stack traces, or arbitrary error text as metric labels.
- [ ] Define bounded enumerations for interface/function labels or aggregate where count is high.
- [ ] Implement unknown/other buckets for unexpected reason codes.
- [ ] Add tests/linting for label cardinality policy.
- [ ] Document estimated time-series cardinality at expected deployment scale.

### Exporter implementation
- [ ] Implement Prometheus/OpenMetrics, OpenTelemetry Metrics, or approved exporter.
- [ ] Ensure scraping/export does not block the RPC critical path.
- [ ] Bound exporter queues and retry behavior.
- [ ] Define exporter authentication/TLS if remote push is used.
- [ ] Define behavior when metrics backend is unavailable.
- [ ] Expose process start time and exporter health.

### Dashboards and alerts
- [ ] Provide baseline service health dashboard.
- [ ] Provide latency/error/saturation dashboard by bounded dimensions.
- [ ] Provide transport/retry/circuit-breaker dashboard.
- [ ] Provide auth/security anomaly dashboard.
- [ ] Define alerts for error-rate, p99, saturation, queue growth, readiness, dependency failure, cert expiry, and audit loss.
- [ ] Tie alerts to runbooks and owners.

### Verification
- [ ] Unit-test metric increments and label sets.
- [ ] Verify counters are monotonic and histograms use correct units.
- [ ] Verify no high-cardinality labels under fuzzed method/error inputs.
- [ ] Load-test exporter overhead.
- [ ] Validate dashboards/alerts against injected failures.

### Definition of Done / Acceptance Gates
- [ ] Metrics cover latency, errors, traffic, saturation, security, dependency, and release metadata.
- [ ] Cardinality is bounded and documented.
- [ ] Exporter failure cannot take down request serving.
- [ ] Dashboards and alerts are validated using controlled fault injection.

---

## M16 — Structured operational logging
**Related audit controls:** C073, C075, C076, C077  
**Objective:** Produce machine-parseable, privacy-aware logs with stable correlation and operationally useful reason codes.

### Log schema
- [ ] Choose a structured format such as JSON with explicit schema version.
- [ ] Define required fields: timestamp, severity, service, version/build, node/instance, event name, request/trace ID, interface/function, outcome, and reason code.
- [ ] Include tenant/workload/principal identifiers only where permitted and normalized.
- [ ] Use stable event names and reason-code enums rather than arbitrary prose for automation.
- [ ] Include configuration/protocol version metadata where relevant.
- [ ] Standardize duration/byte units.

### Privacy and redaction
- [ ] Classify fields as public, internal, sensitive, secret, or prohibited.
- [ ] Never log passwords, bearer tokens, private keys, session secrets, or raw capabilities.
- [ ] Define payload logging policy; default to no payloads for RPC data.
- [ ] Redact or hash identifiers according to privacy requirements.
- [ ] Sanitize attacker-controlled strings to prevent log forging/injection.
- [ ] Limit stack traces to controlled debug contexts and scrub secrets.

### Logging behavior
- [ ] Define severity mapping for normal rejection versus operational fault versus security event.
- [ ] Avoid per-request info logs at high volume unless sampling is intentional.
- [ ] Implement bounded asynchronous logging or non-blocking sink integration.
- [ ] Define behavior on sink backpressure/disk full.
- [ ] Implement rate limiting/deduplication for repetitive errors.
- [ ] Ensure logging failures do not recursively generate unbounded logs.

### Correlation
- [ ] Correlate logs with request ID and trace/span ID.
- [ ] Correlate retries/attempts to the same logical request.
- [ ] Correlate configuration/policy/key changes with audit event IDs.
- [ ] Ensure cross-host timestamps have documented synchronization assumptions.

### Verification
- [ ] Add schema validation tests for representative log events.
- [ ] Add redaction tests using known secret canaries.
- [ ] Add log injection tests with newline/control-character/unicode attacker input.
- [ ] Add load tests for logging overhead/backpressure.
- [ ] Verify retention/export pipeline preserves structured fields.

### Definition of Done / Acceptance Gates
- [ ] Production logs are structured, schema-versioned, correlated, and bounded.
- [ ] Secret leakage tests pass.
- [ ] Log sink failure/backpressure cannot cause unbounded request latency or memory growth.
- [ ] Operators can trace a representative request/failure across hosts using stable identifiers.

---
## M17 — Distributed trace propagation
**Related audit controls:** C074, C078  
**Objective:** Propagate end-to-end causal context across RPC boundaries with bounded, standards-aligned tracing.

### Trace context model
- [ ] Select a standard propagation format such as W3C Trace Context plus baggage where appropriate.
- [ ] Define trace ID, span ID, parent relationship, sampling flag, and tracestate handling.
- [ ] Specify which RPC envelope fields carry trace context.
- [ ] Validate trace header lengths/characters before use.
- [ ] Reject or sanitize malformed propagation data without breaking the underlying RPC where policy allows.
- [ ] Define whether untrusted callers may supply trace IDs and how trust boundaries are represented.
- [ ] Prevent caller-provided baggage from becoming an unbounded metadata channel.

### Span lifecycle
- [ ] Create a client span for outbound calls.
- [ ] Create a server span for inbound calls after minimal frame validation.
- [ ] Record interface, function, protocol version, retry attempt, and bounded status metadata.
- [ ] Record queue wait, serialization, transport, and handler phases as child spans/events where justified.
- [ ] Mark deadline, cancellation, auth denial, version drift, and serialization failures with stable semantic status.
- [ ] End spans on all success/error/cancel/timeout paths.
- [ ] Link retry attempts to the same logical operation.

### Security/privacy controls
- [ ] Do not place payloads, credentials, capabilities, or unrestricted user input in span attributes.
- [ ] Define an allow-list of attribute keys and bounded value lengths.
- [ ] Define tenant/principal trace-identification policy.
- [ ] Ensure baggage propagation across tenant/security boundaries is explicitly controlled.
- [ ] Prevent high-cardinality request IDs from being indexed as unbounded metric dimensions even if present in traces.

### Sampling/export
- [ ] Define head/tail/adaptive sampling policy.
- [ ] Preserve or force sampling for critical security/incident traces where approved.
- [ ] Bound trace exporter queue memory and retry behavior.
- [ ] Define behavior when collector is unavailable.
- [ ] Configure authenticated/encrypted trace export.
- [ ] Document expected tracing overhead at nominal and peak traffic.

### Verification
- [ ] Test trace propagation across at least two process/host hops.
- [ ] Test retry/cancellation/deadline trace relationships.
- [ ] Test malformed trace context.
- [ ] Test no-context calls and context regeneration policy.
- [ ] Test sampling on/off paths.
- [ ] Verify attributes comply with cardinality/privacy policy.
- [ ] Validate a representative trace in the chosen backend/collector.

### Definition of Done / Acceptance Gates
- [ ] Cross-host calls can be followed as one causal trace.
- [ ] Retry/error/cancellation semantics are visible and correctly linked.
- [ ] Trace metadata is bounded and privacy-reviewed.
- [ ] Collector failure does not break the RPC data plane.

---

## M18 — Telemetry retention/privacy/export policy
**Related audit controls:** C075, C079  
**Objective:** Govern telemetry collection, export, retention, access, deletion, and privacy across logs, metrics, traces, and audit data.

### Data inventory and classification
- [ ] Enumerate every telemetry stream and exporter.
- [ ] Classify fields as operational, security, tenant metadata, personal data, secret, or prohibited.
- [ ] Document lawful/contractual basis for collecting sensitive fields where applicable.
- [ ] Mark fields that must never leave a tenant/site/region.
- [ ] Define data residency requirements by deployment.
- [ ] Maintain a schema registry or versioned telemetry dictionary.

### Collection minimization
- [ ] Collect only fields required for operational/security objectives.
- [ ] Prohibit raw RPC payload collection by default.
- [ ] Define hashing/pseudonymization rules for identifiers.
- [ ] Bound free-form text fields and sanitize attacker-controlled content.
- [ ] Apply sampling before export where full fidelity is unnecessary.

### Retention and deletion
- [ ] Define retention per logs/metrics/traces/security audit class.
- [ ] Define hot/warm/cold storage if applicable.
- [ ] Define deletion/expiry enforcement and evidence.
- [ ] Define exception handling for legal hold/security investigations.
- [ ] Test retention enforcement in representative backends.
- [ ] Document backup retention interaction.

### Export governance
- [ ] Maintain an exporter destination allow-list.
- [ ] Require authentication and encryption for remote exporters.
- [ ] Prevent dynamic arbitrary exporter destinations in production unless policy-approved.
- [ ] Define proxy/firewall/network egress restrictions.
- [ ] Validate exporter certificates and endpoint identities.
- [ ] Define behavior when export is unavailable or throttled.

### Tenant/privacy isolation
- [ ] Enforce tenant-scoped access to tenant-specific telemetry.
- [ ] Verify dashboards/queries cannot cross tenant boundaries unintentionally.
- [ ] Define operator/admin access logging.
- [ ] Redact shared-platform telemetry where tenant identifiers are unnecessary.
- [ ] Document support/incident access procedures.

### Verification and review
- [ ] Add automated secret-canary tests across all telemetry exporters.
- [ ] Test high-cardinality/large-value inputs.
- [ ] Test export destination allow-list enforcement.
- [ ] Review telemetry schema on every material protocol change.
- [ ] Perform periodic privacy/security review of retention and access.

### Definition of Done / Acceptance Gates
- [ ] Every telemetry field has an owner/classification/retention/export policy.
- [ ] Secrets and prohibited payload data are excluded by testable controls.
- [ ] Export destinations and tenant access are policy-enforced.
- [ ] Retention/deletion requirements are demonstrably operational.

---

## M19 — Failover, partition, split-brain, duplicate-execution controls
**Related audit controls:** C051, C055–C060, C089  
**Objective:** Define safe distributed behavior during node failure, network partition, ownership changes, and concurrent recovery.

### Ownership/leadership model
- [ ] Define whether INV-61 itself owns distributed work/state or delegates ownership to adjacent layers.
- [ ] If ownership exists, define authoritative owner/leader election mechanism.
- [ ] Define fencing tokens/epochs for exclusive writers/executors.
- [ ] Reject work from stale leaders/epochs.
- [ ] Define lease duration, renewal, clock assumptions, and expiration semantics.
- [ ] Define ownership handoff protocol and in-flight request treatment.

### Partition semantics
- [ ] Define behavior for client↔server, server↔dependency, and multi-site partitions.
- [ ] Explicitly choose consistency/availability behavior per operation class.
- [ ] Define whether isolated partitions may accept reads/writes.
- [ ] Prevent dual-primary/split-brain side effects.
- [ ] Define quorum requirements if replicated coordination is used.
- [ ] Define stale-read tolerance where applicable.

### Failover/recovery
- [ ] Define failure detector and false-positive tolerance.
- [ ] Define automatic versus operator-controlled failover triggers.
- [ ] Define maximum failover time and recovery objective.
- [ ] Preserve request/idempotency state across failover where needed.
- [ ] Ensure new owner can distinguish completed, in-flight, and unknown operations.
- [ ] Define response semantics for calls interrupted by ownership transition.
- [ ] Implement graceful return-to-primary or rebalancing rules.

### Duplicate execution prevention
- [ ] Bind mutating operations to request/idempotency IDs and fencing epochs.
- [ ] Reject stale epoch writes/dispatch.
- [ ] Ensure retries after failover do not execute already committed operations twice.
- [ ] Define deduplication ledger durability/retention.
- [ ] Test ambiguous completion at exact failover boundary.

### Quarantine/freeze controls
- [ ] Implement operator-triggered quarantine for unhealthy/compromised nodes.
- [ ] Implement emergency freeze of mutating operations where required.
- [ ] Define controlled recovery/rejoin validation.
- [ ] Audit all quarantine/freeze/rejoin actions.

### Verification
- [ ] Inject hard node crash during request execution.
- [ ] Inject network partition between peers.
- [ ] Inject asymmetric partition where each side sees different connectivity.
- [ ] Inject delayed/duplicated packets/messages.
- [ ] Test stale leader/fencing token rejection.
- [ ] Test failover under peak traffic.
- [ ] Test failback/rebalance.
- [ ] Prove no duplicate side effects for protected operation classes.

### Definition of Done / Acceptance Gates
- [ ] Partition/failover behavior is explicitly specified by operation class.
- [ ] Split-brain cannot produce uncontrolled duplicate mutation.
- [ ] Fencing/deduplication controls survive restart/failover as required.
- [ ] Failure-injection evidence demonstrates bounded recovery and correct outcomes.

---

## M20 — Durable/restart/replay semantics for mutable state
**Related audit controls:** C057, C058, C095  
**Objective:** Formally define what state exists, what must survive restart, and how state is reconstructed or intentionally discarded.

### State inventory
- [ ] Enumerate all mutable state: registrations, stats, sessions, replay cache, idempotency records, negotiated capabilities, queues, breaker state, config, audit buffers, etc.
- [ ] Classify each state item as ephemeral, reconstructable, durable, security-critical, or externally authoritative.
- [ ] Document ownership and lifecycle for each state class.
- [ ] Define confidentiality/integrity requirements for persisted state.

### Stateless-service option
- [ ] If production service is intended to be stateless, document the statelessness invariant explicitly.
- [ ] Move durable responsibilities to named external systems.
- [ ] Prove restart does not weaken replay/idempotency/security guarantees.
- [ ] Prove registrations/config can be deterministically reconstructed.
- [ ] Define whether local stats may reset and how monitoring handles resets.

### Persistence design
- [ ] Select durable storage for required state.
- [ ] Define transactional boundaries and crash-consistency model.
- [ ] Define write-ahead/checkpoint strategy where necessary.
- [ ] Include schema version in persisted records.
- [ ] Define encryption-at-rest and access controls.
- [ ] Define retention/compaction/garbage collection.
- [ ] Define maximum recovery dataset and recovery-time target.

### Restart/recovery semantics
- [ ] Define cold start, graceful restart, crash restart, and version-upgrade recovery paths.
- [ ] Reconstruct registrations/policy/config before readiness.
- [ ] Restore replay/idempotency state before accepting retriable mutations if required.
- [ ] Detect partial/corrupt checkpoints and fail safely.
- [ ] Define migration procedure for persisted schema changes.
- [ ] Prevent downgrade from opening data with unsupported newer schema unless explicitly safe.

### Backup/restore
- [ ] Define whether state requires backup beyond replication.
- [ ] Define backup frequency, retention, encryption, and integrity checks.
- [ ] Perform automated restore tests.
- [ ] Document RPO/RTO.
- [ ] Validate recovery after total local storage loss if applicable.

### Verification
- [ ] Crash process at controlled points during state mutation.
- [ ] Restart and verify invariants.
- [ ] Test corrupted/truncated state records.
- [ ] Test schema migration forward and rollback constraints.
- [ ] Test restored state against replay/idempotency semantics.
- [ ] Test concurrent restart across multiple nodes.

### Definition of Done / Acceptance Gates
- [ ] Every mutable state item has documented durability/reconstruction semantics.
- [ ] Restart cannot silently weaken security or duplicate-execution guarantees.
- [ ] Crash recovery and, where applicable, backup restore are automated and tested.
- [ ] Recovery time/data-loss characteristics meet documented objectives.

---

## M21 — Requirements specification and traceability matrix
**Related audit controls:** C011–C020  
**Objective:** Convert broad prompts/declarations into normative, testable, uniquely identified requirements with bidirectional evidence traceability.

### Normative requirements
- [ ] Create a requirements specification with stable IDs (for example RPC-REQ-0001...).
- [ ] Use `MUST`, `SHOULD`, and `MAY` consistently.
- [ ] Ensure every requirement is atomic and objectively verifiable.
- [ ] Separate functional, security, reliability, performance, compatibility, operations, and governance requirements.
- [ ] Define assumptions and out-of-scope boundaries.
- [ ] Define glossary for terms such as endpoint, peer, principal, request, attempt, interface version, signature fingerprint, deadline, and capability.

### Protocol/lifecycle specification
- [ ] Define client/server state machines.
- [ ] Define request/response lifecycle from creation through completion/cancel/timeout.
- [ ] Define registration lifecycle.
- [ ] Define negotiation lifecycle.
- [ ] Define authentication/authorization sequence.
- [ ] Define retry/reconnect/failover interactions.
- [ ] Define drain/shutdown behavior.

### Failure taxonomy
- [ ] Define stable error/status code namespace.
- [ ] Classify caller, protocol, auth, authorization, overload, timeout, cancellation, dependency, internal, and transport failures.
- [ ] Define retryability for each code.
- [ ] Define what details may be exposed to remote callers.
- [ ] Define operator diagnostic mapping separate from client-visible errors.

### Conflict/precedence model
- [ ] Define precedence among security, safety, residency, correctness, availability, latency/SLO, and cost requirements.
- [ ] Document fail-open/fail-closed decisions for each critical dependency.
- [ ] Define behavior when policy conflicts with requested compatibility/performance modes.
- [ ] Capture unresolved tradeoffs as ADRs/risk records.

### Traceability matrix
- [ ] Map each C001–C100 checklist control to one or more normative requirements.
- [ ] Map each requirement to implementation module/path.
- [ ] Map each requirement to one or more tests/evidence artifacts.
- [ ] Map security requirements to threat/abuse cases.
- [ ] Map SLO requirements to benchmarks/metrics/alerts.
- [ ] Detect requirements with no implementation or no test automatically.
- [ ] Detect tests with no linked requirement where traceability is expected.

### Review/change control
- [ ] Require review/approval for normative requirement changes.
- [ ] Version the requirements schema/document.
- [ ] Maintain change history and compatibility impact.
- [ ] Re-run impacted verification automatically based on requirement tags where practical.

### Definition of Done / Acceptance Gates
- [ ] All production behavior is covered by uniquely identified normative requirements.
- [ ] Every requirement has implementation and verification evidence or an approved waiver.
- [ ] Failure semantics and requirement-precedence rules are explicit.
- [ ] CI can report orphaned/unverified requirements.

---

## M22 — Owner, escalation path, and approved architecture decision record
**Related audit controls:** C009, C010  
**Objective:** Establish accountable ownership, operational escalation, and formally approved architectural rationale for wRPC design choices.

### Ownership
- [ ] Name the service/component owner role/team.
- [ ] Name security, operations/SRE, and protocol/schema owners.
- [ ] Define code ownership/reviewer requirements for critical paths.
- [ ] Define on-call or incident ownership for production deployments.
- [ ] Define dependency ownership for `pk_core`, identity, policy, transport, and observability integrations.
- [ ] Record ownership in repository metadata (`CODEOWNERS`, service catalog, or equivalent).

### Escalation
- [ ] Define severity levels and response expectations.
- [ ] Define primary and secondary escalation paths.
- [ ] Define security-incident escalation separately if required.
- [ ] Define after-hours/on-call contact mechanism without embedding personal secrets in source.
- [ ] Define escalation for dependency/vendor failures.
- [ ] Link alerts/runbooks to owning team.

### Architecture Decision Record
- [ ] Create ADR describing the problem/context solved by distributed WIT RPC.
- [ ] Document considered alternatives and why they were accepted/rejected.
- [ ] Document transport, WIT/component-model, versioning, auth, authorization, retry, state, and observability choices.
- [ ] Document assumptions and constraints.
- [ ] Document security/privacy implications.
- [ ] Document performance/capacity expectations.
- [ ] Document dependencies on INV-11/36/60/65 and ownership boundaries.
- [ ] Document consequences, unresolved risks, and future migration triggers.
- [ ] Obtain named role-based approval/review.

### Governance
- [ ] Define ADR supersession/change process.
- [ ] Review ownership and escalation data periodically.
- [ ] Ensure release/incident processes reference the current ADR and owners.
- [ ] Define succession/handover procedure when teams change.

### Definition of Done / Acceptance Gates
- [ ] Production responsibility is unambiguous across engineering, security, and operations.
- [ ] An approved ADR captures architectural rationale and tradeoffs.
- [ ] Alerts/incidents have a documented escalation destination.
- [ ] Ownership metadata is versioned and periodically reviewed.

---

## M23 — Security architecture and adversarial test suite
**Related audit controls:** C041–C050, C087  
**Objective:** Build a complete threat model and executable adversarial validation suite across protocol, transport, identity, authorization, and resource controls.

### Threat model
- [ ] Define assets: code execution, tenant data, credentials, capabilities, protocol integrity, availability, audit trail, configuration, and control plane.
- [ ] Draw trust boundaries for client, transport, endpoint, policy engine, identity provider, state store, telemetry, and operators.
- [ ] Enumerate attacker classes: unauthenticated remote, authenticated low-privilege, compromised workload, malicious tenant, insider/operator, network attacker, compromised dependency.
- [ ] Use STRIDE, attack trees, or equivalent systematic methodology.
- [ ] Include spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege, replay, downgrade, confused deputy, and supply-chain threats.
- [ ] Map each threat to mitigations and verification evidence.
- [ ] Record residual risk and owner.
- [ ] Review threat model on protocol/architecture changes.

### Protocol abuse cases
- [ ] Malformed frame field sets.
- [ ] Unknown/duplicate fields where schema disallows them.
- [ ] Oversized lengths and integer overflows.
- [ ] Deep nesting and decompression/expansion bombs if compression exists.
- [ ] Signature/version/interface spoofing.
- [ ] Deadline extremes, NaN/infinity, negative or far-future values.
- [ ] Duplicate request/replay sequences.
- [ ] Truncation, concatenation, smuggling, and partial-frame delivery.
- [ ] Invalid UTF-8/type discriminants/resource handles.

### Identity/authorization abuse cases
- [ ] Anonymous access to protected methods.
- [ ] Wrong tenant/principal/capability.
- [ ] Expired/revoked/forged credentials.
- [ ] Capability replay/delegation escalation.
- [ ] Confused-deputy attempts through indirect calls.
- [ ] Policy-engine outage/stale cache manipulation.
- [ ] Cross-tenant resource reference attacks.

### Resource-exhaustion abuse cases
- [ ] Slowloris/slow reader/writer behavior.
- [ ] Connection floods and handshake floods.
- [ ] Request floods per tenant/principal.
- [ ] Queue saturation.
- [ ] Large payload/string/list/nesting attacks.
- [ ] Trace/log cardinality and telemetry amplification attacks.
- [ ] Retry storm and circuit-breaker thrash attacks.

### Secure implementation review
- [ ] Run SAST/linting suitable for Python and native/Wasm adjuncts.
- [ ] Scan for unsafe deserialization, command execution, path injection, temp-file misuse, secret handling, and insecure randomness.
- [ ] Review exception handling for information disclosure.
- [ ] Review cryptographic API use.
- [ ] Review concurrency/state synchronization for security invariant races.
- [ ] Review dependency provenance/vulnerabilities.

### Adversarial test automation
- [ ] Encode abuse cases as repeatable tests, not only manual review notes.
- [ ] Run security suite in CI for changes to protocol/auth/policy/transport.
- [ ] Add periodic deeper fuzz/chaos/security campaigns.
- [ ] Preserve regression inputs for discovered vulnerabilities.
- [ ] Tag security tests to threat IDs and requirements.

### Definition of Done / Acceptance Gates
- [ ] Threat model covers all production trust boundaries and attacker classes.
- [ ] Every high/critical threat has a tested mitigation or approved risk acceptance.
- [ ] Adversarial protocol/identity/authorization/resource tests run automatically.
- [ ] No known critical/high unresolved security findings remain at production exit.

---

## M24 — Parser/protocol fuzzing and property tests
**Related audit controls:** C085  
**Objective:** Continuously discover malformed-input, state-machine, allocation, and serialization defects beyond hand-authored tests.

### Fuzz target design
- [ ] Create raw-byte decoder fuzz target at the earliest network parser boundary.
- [ ] Create RPC envelope/state-machine fuzz target.
- [ ] Create WIT value decoder fuzz target.
- [ ] Create negotiation/version parser fuzz target.
- [ ] Create authentication metadata parser fuzz target if custom parsing exists.
- [ ] Avoid mocks that bypass the real parser logic under test.
- [ ] Make fuzz targets deterministic and side-effect isolated.

### Invariants/properties
- [ ] Parser never crashes the process on arbitrary bytes.
- [ ] Parser never allocates beyond configured hard limits for bounded input.
- [ ] Invalid input never reaches user dispatch.
- [ ] `decode(encode(x)) == x` for supported canonical values.
- [ ] Accepted non-canonical encodings either normalize deterministically or are rejected according to spec.
- [ ] Re-encoding a decoded canonical value produces identical bytes.
- [ ] Error classification is stable for equivalent malformed cases.
- [ ] Deadline/version/signature validation invariants hold across generated cases.
- [ ] Unauthorized/unverified input cannot change authorization-relevant context.

### Corpus and dictionaries
- [ ] Seed corpus with all golden valid frames.
- [ ] Seed corpus with known malformed/truncated/oversized cases.
- [ ] Add protocol tokens/field names/type tags to fuzzer dictionary where helpful.
- [ ] Preserve minimized reproducer inputs for every discovered defect.
- [ ] Version corpus alongside protocol changes.

### Resource controls
- [ ] Configure timeout/CPU budget per fuzz case.
- [ ] Configure memory/allocator limits.
- [ ] Detect pathological super-linear parser behavior.
- [ ] Track coverage of parsing/state-machine branches.
- [ ] Prevent fuzz harness from making real network/external-service calls.

### CI and campaign policy
- [ ] Run a short deterministic fuzz smoke gate in normal CI.
- [ ] Run longer scheduled fuzz campaigns.
- [ ] Run sanitizer/instrumented builds for native components if any exist.
- [ ] Define crash triage owner and SLA.
- [ ] Fail release on unresolved reproducible parser crash/security invariant violation.
- [ ] Track coverage and unique crash history over time.

### Property-based tests
- [ ] Generate structured valid/invalid frames across boundary values.
- [ ] Generate nested WIT values up to configured depth limits.
- [ ] Generate version negotiation combinations.
- [ ] Generate request/retry/replay sequences against a state model.
- [ ] Shrink failing cases automatically and add regressions.

### Definition of Done / Acceptance Gates
- [ ] Network/WIT/protocol parsers have active fuzz targets and maintained corpora.
- [ ] Critical parser invariants are encoded as machine-checked properties.
- [ ] CI/scheduled campaigns run within defined resource budgets.
- [ ] All discovered crashes/invariant violations are reproducible, minimized, and regression-tested.

---
## M25 — Concurrency and race-condition tests
**Related audit controls:** C086  
**Objective:** Define thread/async safety guarantees and prove that concurrent registration, dispatch, metrics, shutdown, and configuration changes preserve invariants.

### Concurrency model
- [ ] Declare whether the endpoint is single-threaded, multi-threaded, async-task based, multi-process, or supports multiple execution modes.
- [ ] Define which objects are immutable and which are shared mutable state.
- [ ] Define ownership for export registry, endpoint statistics, replay/idempotency caches, breaker state, config references, and connection/session state.
- [ ] Identify every lock, atomic primitive, queue, event, and synchronization boundary.
- [ ] Document lock ordering to prevent deadlock.
- [ ] Define whether handler functions may re-enter the endpoint or register/unregister functions during execution.
- [ ] Define safe shutdown/drain interaction with active requests.
- [ ] Define safe config reload interaction with active requests.

### Implementation hardening
- [ ] Protect `EndpointStats` mutation with a concurrency-safe strategy or redesign it for per-thread/per-task aggregation.
- [ ] Ensure export registration/lookup cannot observe partially constructed entries.
- [ ] Ensure duplicate-export detection is atomic under concurrent registration.
- [ ] Ensure unregister/replace operations, if introduced, are linearizable or explicitly versioned.
- [ ] Prevent use-after-close of sessions/transports during shutdown.
- [ ] Prevent response completion after request state has been destroyed/reused.
- [ ] Ensure cancellation state is safely visible across worker contexts.
- [ ] Avoid holding global locks while invoking user-supplied handlers.
- [ ] Bound lock wait time or expose lock contention metrics where relevant.

### Race test scenarios
- [ ] Dispatch many concurrent calls to the same export.
- [ ] Dispatch concurrent calls across many exports/interfaces.
- [ ] Concurrently register the same export from multiple workers and prove only one wins.
- [ ] Concurrently register different exports while dispatching.
- [ ] Race deadline expiration against handler completion.
- [ ] Race cancellation against completion and response write.
- [ ] Race connection close against in-flight dispatch.
- [ ] Race graceful drain against new request admission.
- [ ] Race configuration reload against request validation/authorization.
- [ ] Race certificate/policy rotation against authenticated sessions if applicable.
- [ ] Race replay/idempotency record creation for identical request IDs.
- [ ] Race circuit-breaker state transitions under high failure volume.

### Determinism/invariant testing
- [ ] Define invariants such as non-negative counters, unique export keys, one terminal state per request, one response per request, and at-most-once commit where applicable.
- [ ] Add stress tests that repeat concurrency scenarios thousands of iterations.
- [ ] Randomize scheduling/yield points where supported.
- [ ] Use deterministic schedulers/model checking for critical state machines if feasible.
- [ ] Add assertions in tests for leaked tasks, threads, sockets, locks, and queues after shutdown.

### Tooling
- [ ] Run Python-specific concurrency stress under supported interpreter builds.
- [ ] Use ThreadSanitizer/RaceSanitizer for any native extensions or companion runtimes.
- [ ] Use async debug modes/task-leak detectors for asyncio/trio-style implementations.
- [ ] Capture deadlock stacks/timeouts automatically in CI.
- [ ] Run concurrency suite under CPU oversubscription and constrained resources.

### Definition of Done / Acceptance Gates
- [ ] The concurrency contract is documented and matches implementation reality.
- [ ] Shared mutable state has explicit synchronization/ownership.
- [ ] High-contention race suites pass repeatedly without deadlock, lost updates, duplicate responses, or invariant violations.
- [ ] Shutdown/reload/cancellation races have deterministic, tested outcomes.

---

## M26 — Adjacent-layer integration tests
**Related audit controls:** C030, C083  
**Objective:** Prove executable interoperability with the architectural neighbors explicitly referenced by INV-61: INV-11, INV-36, INV-60, and INV-65.

### Integration contract inventory
- [ ] Identify the exact version/revision of INV-11 interface contracts required by INV-61.
- [ ] Identify the exact version/revision of INV-36 control transport required by INV-61.
- [ ] Identify the exact version/revision of INV-60 application fabric required by INV-61.
- [ ] Identify the exact version/revision of INV-65 capability providers required by INV-61.
- [ ] Document which side owns each schema, transport primitive, lifecycle signal, and error code.
- [ ] Create a compatibility matrix across supported adjacent-layer versions.
- [ ] Define stable test fixtures/contracts that do not depend on developer-local repositories.

### INV-11 interface-contract integration
- [ ] Load/compile real interface definitions through the intended WIT/binding path.
- [ ] Verify signature fingerprints/digests match the authoritative interface definitions.
- [ ] Verify incompatible interface change is detected before dispatch.
- [ ] Verify compatible evolution path where supported.
- [ ] Exercise representative scalar, compound, result/error, and resource types.

### INV-36 control-transport integration
- [ ] Verify control-plane commands can configure/inspect INV-61 through documented interfaces.
- [ ] Ensure control messages are authenticated/authorized separately from data-plane calls.
- [ ] Test control-channel loss while data plane remains active according to policy.
- [ ] Test emergency disable/drain/quarantine control paths.
- [ ] Verify control messages cannot inject arbitrary RPC payload execution.

### INV-60 application-fabric integration
- [ ] Register/discover INV-61 endpoints through the actual fabric mechanism.
- [ ] Verify fabric deployment/startup/shutdown sequencing.
- [ ] Verify health/readiness propagation into the fabric scheduler/router.
- [ ] Verify rolling upgrade/drain behavior through the fabric.
- [ ] Verify fabric-level routing does not break request identity, deadlines, auth context, or trace context.
- [ ] Test fabric partition/failover scenarios.

### INV-65 capability-provider integration
- [ ] Acquire real capability decisions/tokens through the intended provider API.
- [ ] Enforce provider-issued capability at function/resource dispatch.
- [ ] Test expiry, revocation, wrong audience, wrong tenant, and unavailable-provider behavior.
- [ ] Verify capability metadata survives transport without caller override.
- [ ] Verify audit/telemetry records the provider/policy revision safely.

### End-to-end harness
- [ ] Build an automated multi-component integration environment.
- [ ] Pin every component version/digest in the harness.
- [ ] Start dependencies in deterministic order with readiness gates.
- [ ] Exercise successful end-to-end remote call.
- [ ] Exercise auth denial, capability denial, interface mismatch, timeout, cancellation, overload, and dependency outage.
- [ ] Capture logs/metrics/traces/audit evidence for each scenario.
- [ ] Tear down cleanly and fail on leaked processes/resources.
- [ ] Make the harness runnable in CI and locally from documented commands.

### Definition of Done / Acceptance Gates
- [ ] Supported adjacent-layer versions are explicitly pinned and compatibility-tested.
- [ ] A real automated end-to-end harness exercises all four named integrations.
- [ ] Context propagation and security invariants survive every layer boundary.
- [ ] Failure of one adjacent component produces documented, tested degradation rather than undefined behavior.

---

## M27 — Cross-runtime / cross-architecture compatibility certification
**Related audit controls:** C084, C093  
**Objective:** Establish the exact supported runtime/OS/CPU/Wasm matrix and continuously prove interoperability across it.

### Support matrix definition
- [ ] List supported Python runtime versions and implementations.
- [ ] List supported operating systems/distributions.
- [ ] List supported CPU architectures (for example x86-64, ARM64).
- [ ] List supported Wasm runtimes/component-model engines and versions.
- [ ] List supported transport implementations/libraries and versions.
- [ ] List supported peer protocol versions.
- [ ] Distinguish Tier-1 fully supported, Tier-2 best-effort, and unsupported environments.
- [ ] Define end-of-support policy when a runtime reaches upstream EOL.

### Platform correctness
- [ ] Verify endian-independent wire serialization.
- [ ] Verify integer width assumptions are explicit.
- [ ] Verify floating-point edge handling across architectures where floats exist.
- [ ] Verify monotonic/wall-clock deadline behavior across OSes.
- [ ] Verify path/file permission semantics for configuration/keys on Windows and Unix-like systems.
- [ ] Verify socket behavior, IPv6, DNS, and TLS trust-store differences.
- [ ] Verify process signal/service-shutdown semantics per OS.

### Runtime/Wasm interoperability
- [ ] Run the same golden WIT/wire fixtures through each supported Wasm runtime.
- [ ] Verify generated bindings compile/load on each supported toolchain.
- [ ] Verify resource handle/lifetime semantics across runtimes.
- [ ] Verify traps/exceptions map to consistent RPC statuses.
- [ ] Verify runtime sandbox/capability settings required by INV-61.
- [ ] Test runtime upgrades for compatibility regression.

### CI matrix
- [ ] Implement CI jobs for every Tier-1 OS × runtime combination.
- [ ] Include at least one ARM64 execution environment if ARM64 is supported.
- [ ] Run unit, protocol, integration, and selected performance tests per Tier-1 platform.
- [ ] Run cross-version peer tests (old client↔new server and new client↔old server) where supported.
- [ ] Store platform-specific artifacts and logs.
- [ ] Fail release qualification if a Tier-1 matrix leg is skipped.

### Reproducibility
- [ ] Pin toolchains/container/base images by digest where practical.
- [ ] Record compiler/interpreter/runtime versions in build provenance.
- [ ] Avoid hidden dependence on host-local locale/timezone/default encoding.
- [ ] Test non-UTF-8 locale environments if the runtime could encounter them.
- [ ] Normalize filesystem case-sensitivity assumptions.

### Definition of Done / Acceptance Gates
- [ ] A versioned support matrix exists and is reflected in automated CI.
- [ ] Tier-1 combinations pass protocol/integration tests with no unexpected skips.
- [ ] Cross-runtime golden fixtures are byte/behavior compatible.
- [ ] Unsupported combinations fail clearly or are documented rather than silently drifting.

---

## M28 — Performance, capacity, power, and regression certification
**Related audit controls:** C061–C070, C088  
**Objective:** Quantify RPC overhead and safe operating limits with repeatable benchmarks, overload characterization, and release regression gates.

### Benchmark specification
- [ ] Define benchmark hardware/VM characteristics, CPU governor, memory, NIC, OS, runtime, and affinity settings.
- [ ] Pin benchmark software/toolchain versions.
- [ ] Define warmup, run duration, repetitions, confidence interval, and outlier policy.
- [ ] Separate in-process protocol cost from serialization, transport, auth, policy, and handler cost.
- [ ] Define payload profiles: tiny, small, medium, large, and maximum supported.
- [ ] Define concurrency profiles and request-rate profiles.
- [ ] Define local, same-zone, cross-zone, and cross-site network profiles if relevant.

### Latency/throughput measurements
- [ ] Measure p50, p90, p95, p99, p99.9, max, and standard deviation where useful.
- [ ] Measure sustainable requests/sec at target SLO.
- [ ] Measure connection establishment and secure-handshake latency.
- [ ] Measure serialization/deserialization latency independently.
- [ ] Measure queue wait versus handler execution.
- [ ] Measure retry/circuit-breaker overhead under partial failure.
- [ ] Measure tracing/metrics/logging overhead enabled versus disabled.

### Resource measurements
- [ ] Measure CPU utilization/cycles per request where practical.
- [ ] Measure RSS/heap allocation per request and under concurrency.
- [ ] Measure peak memory under maximum legal payload.
- [ ] Measure network bytes per RPC including framing/security overhead.
- [ ] Measure socket/FD/task/thread usage versus concurrency.
- [ ] Measure GC pressure/pause behavior where relevant.
- [ ] Measure buffer copies or zero-copy effectiveness where applicable.

### Capacity model
- [ ] Define tested maximum concurrent connections.
- [ ] Define tested maximum inflight requests.
- [ ] Define safe queue depth/high-water marks.
- [ ] Determine saturation point for CPU, memory, network, or dependency bottleneck.
- [ ] Define headroom policy for production sizing.
- [ ] Derive capacity per node and minimum replica count for target workload.
- [ ] Validate model against a realistic mixed workload.

### Burst/overload behavior
- [ ] Run sudden burst tests above nominal rate.
- [ ] Run sustained overload until stable shedding state.
- [ ] Verify latency does not grow unbounded before admission control activates.
- [ ] Verify memory remains bounded.
- [ ] Verify retry hints/backpressure reduce rather than amplify overload.
- [ ] Measure recovery time after overload clears.

### Power/edge characterization
- [ ] If constrained-edge operation is in scope, measure energy/power under idle, nominal, and peak RPC load.
- [ ] Measure cost of encryption, serialization, tracing, and retries on target edge hardware.
- [ ] Define thermal/throttling assumptions.
- [ ] Establish acceptable power/energy budget per workload class.

### Regression gates
- [ ] Establish baseline benchmark results by release.
- [ ] Define allowed regression percentage for latency, throughput, memory, and CPU.
- [ ] Fail CI/release qualification on statistically significant regression above threshold.
- [ ] Store raw benchmark data and environment metadata.
- [ ] Require explicit approved waiver for accepted regression.

### Definition of Done / Acceptance Gates
- [ ] The stated p99 framing-overhead/SLO claims have reproducible evidence.
- [ ] Safe per-node capacity and saturation behavior are quantified.
- [ ] Overload remains bounded and recovers predictably.
- [ ] Release performance gates detect meaningful regressions.
- [ ] Edge/power requirements are either measured or formally declared out of scope.

---

## M29 — Fault-injection, soak, disaster, and degraded-control-plane tests
**Related audit controls:** C060, C088, C089  
**Objective:** Demonstrate long-duration stability and predictable recovery during real dependency, network, host, and control-plane failures.

### Fault-injection framework
- [ ] Build or integrate a repeatable chaos/fault injection harness.
- [ ] Support packet loss, latency, jitter, duplication, reordering, partition, and connection reset.
- [ ] Support process kill/crash and forced restart.
- [ ] Support CPU starvation, memory pressure, disk pressure, FD exhaustion, and clock skew where applicable.
- [ ] Support dependency unavailability/slow responses/malformed responses.
- [ ] Support certificate expiry/revocation and identity/policy/config service outages.
- [ ] Record exact fault parameters and random seeds for reproducibility.

### Dependency outage campaigns
- [ ] Identity provider unavailable.
- [ ] Authorization/policy engine unavailable.
- [ ] Config source unavailable/stale.
- [ ] Audit sink unavailable/backpressured.
- [ ] Metrics/log/trace collectors unavailable.
- [ ] State/replay/idempotency store unavailable.
- [ ] Service discovery/DNS failure.
- [ ] Transport broker/fabric failure where applicable.
- [ ] Validate each dependency's documented fail-open/fail-closed behavior.

### Network/distributed failure campaigns
- [ ] Full client↔server partition.
- [ ] Asymmetric partition.
- [ ] Multi-zone/site partition.
- [ ] High packet loss/jitter.
- [ ] Long-lived half-open connections.
- [ ] Reconnect storm after outage.
- [ ] Failover during mutating request.
- [ ] Split-brain/dual-owner attempt.

### Soak/endurance testing
- [ ] Run nominal workload for extended duration representative of production duty cycle.
- [ ] Track memory growth/leaks.
- [ ] Track file descriptor/socket/task/thread leaks.
- [ ] Track latency drift and GC behavior.
- [ ] Rotate credentials/config during soak.
- [ ] Perform rolling restart/upgrade during soak.
- [ ] Inject intermittent dependency failures during soak.
- [ ] Confirm telemetry storage/cardinality remains bounded over time.

### Disaster/recovery testing
- [ ] Simulate total node loss.
- [ ] Simulate multi-node/site loss according to deployment topology.
- [ ] Restore from backup/checkpoint if durable state exists.
- [ ] Verify RPO/RTO against declared objectives.
- [ ] Verify replay/idempotency/security state after recovery.
- [ ] Validate operator runbooks step-by-step.
- [ ] Capture recovery evidence and gaps.

### Degraded-control-plane mode
- [ ] Define what data-plane operations remain permitted when control plane is unavailable.
- [ ] Define TTL for cached policy/config/identity information.
- [ ] Prevent indefinite operation on stale revoked policy/credentials.
- [ ] Preserve emergency local disable where required.
- [ ] Expose degraded-mode health/metrics/logs.
- [ ] Test control-plane recovery and convergence.

### Definition of Done / Acceptance Gates
- [ ] Major dependency, host, and network failures have automated injection scenarios.
- [ ] Long-running soak shows no unbounded resource growth or latent correctness degradation.
- [ ] Recovery meets documented RPO/RTO or the exception is explicitly accepted.
- [ ] Degraded-control-plane behavior is safe, bounded in time, and observable.

---

## M30 — Supply-chain provenance, artifact verification, and SBOM
**Related audit controls:** C045, C090  
**Objective:** Make every release artifact traceable to reviewed source/toolchains/dependencies and independently verifiable before execution.

### SBOM
- [ ] Generate an SBOM in CycloneDX, SPDX, or approved format for every release artifact.
- [ ] Include direct/transitive Python dependencies, native libraries, generated Wasm components, container base images, and vendored code.
- [ ] Include package versions, hashes, licenses, and source locations where available.
- [ ] Version the SBOM schema/tooling.
- [ ] Attach SBOM to release artifacts and retain it with provenance.

### Dependency/security scanning
- [ ] Scan dependencies against current vulnerability databases during CI/release.
- [ ] Define severity thresholds that block release.
- [ ] Define false-positive/risk-acceptance workflow with expiry.
- [ ] Scan container/base images if used.
- [ ] Scan licenses against approved/denied policy.
- [ ] Scan secrets in source/build artifacts.

### Build provenance
- [ ] Record source repository and immutable commit/tag.
- [ ] Record dirty-tree status; prohibit release from uncommitted source.
- [ ] Record build system/tool versions, runtime, OS/image digest, and dependency lock digest.
- [ ] Generate SLSA/in-toto or equivalent signed provenance attestation.
- [ ] Record build identity and CI job/run identifier.
- [ ] Record artifact SHA-256 or stronger digest.

### Artifact signing and verification
- [ ] Sign release archives/wheels/images/components with an approved signing system.
- [ ] Publish detached checksums/signatures.
- [ ] Verify signatures/digests during deployment/bootstrap.
- [ ] Define trusted signer/root rotation procedure.
- [ ] Define emergency key compromise/revocation procedure.
- [ ] Prevent unsigned/unapproved artifacts from production deployment.

### Reproducible builds
- [ ] Remove non-deterministic timestamps/orderings where practical.
- [ ] Pin build dependencies/toolchains.
- [ ] Compare rebuild digests from independent clean environments.
- [ ] Document accepted non-reproducible fields if perfect bit reproducibility is infeasible.
- [ ] Verify generated code/artifacts are reproducible from source.

### Release manifest
- [ ] Create one machine-readable manifest containing version, files, hashes, SBOM digest, provenance digest, signature references, compatibility matrix, and build metadata.
- [ ] Ensure deployment tooling consumes/validates the manifest.
- [ ] Archive prior manifests for audit and rollback verification.

### Definition of Done / Acceptance Gates
- [ ] Every production artifact has SBOM, digest, signed provenance, and signature/checksum verification.
- [ ] Dependency/security/license policy gates run before release.
- [ ] Deployment refuses untrusted or tampered artifacts.
- [ ] A clean independent rebuild can verify provenance/reproducibility expectations.

---

## M31 — Production packaging/bootstrap artifact
**Related audit controls:** C031–C040  
**Objective:** Provide a deterministic, supportable installation/deployment path from an empty node to a versioned, configured, verifiable INV-61 service.

### Package definition
- [ ] Add `pyproject.toml` or equivalent build metadata.
- [ ] Define package name, version source, Python/runtime constraints, dependencies, optional extras, and license metadata.
- [ ] Ensure package version is sourced from one authoritative mechanism and matches `VERSION`/release metadata.
- [ ] Build wheel/sdist or the approved deployable component/container artifact.
- [ ] Exclude tests/dev-only files from production package unless intentionally required.
- [ ] Include WIT/schema/config assets required at runtime.

### Deterministic bootstrap
- [ ] Provide one documented bootstrap/install command/path.
- [ ] Pin dependency sources and lock versions.
- [ ] Verify artifact hashes/signatures before install.
- [ ] Create isolated runtime environment.
- [ ] Avoid writes to unexpected user/profile locations unless documented.
- [ ] Support non-interactive installation for automation.
- [ ] Return stable exit codes for success, dependency failure, config failure, permission failure, and verification failure.
- [ ] Make bootstrap idempotent or clearly define reinstall behavior.

### Deployment artifact
- [ ] Provide systemd/Windows Service/Kubernetes/container/component deployment definition as applicable.
- [ ] Define service account/identity and least-required OS permissions.
- [ ] Define ports, network policy, volumes, secret mounts, and config locations.
- [ ] Define CPU/memory/FD limits and requests/reservations.
- [ ] Define health/readiness probes.
- [ ] Define graceful stop timeout and drain hook.
- [ ] Define restart policy that avoids crash loops.

### Configuration/bootstrap validation
- [ ] Validate configuration before service start.
- [ ] Validate certificates/identity prerequisites.
- [ ] Validate required adjacent services are discoverable or clearly report deferred readiness.
- [ ] Verify supported runtime/platform before installing.
- [ ] Provide a `--check`/preflight mode that makes no mutating changes.
- [ ] Provide post-install self-test/diagnostic command.

### Upgrade/rollback
- [ ] Define in-place versus side-by-side upgrade strategy.
- [ ] Preserve compatible configuration/state safely.
- [ ] Run pre-upgrade compatibility checks.
- [ ] Support rollback to last-known-good artifact/config within documented constraints.
- [ ] Define migration behavior for incompatible persisted state/schema.
- [ ] Verify rolling upgrade with mixed-version peers.

### Clean-environment verification
- [ ] Install on a freshly provisioned supported Windows environment if Windows is supported.
- [ ] Install on a freshly provisioned supported Linux environment if Linux is supported.
- [ ] Install with no pre-existing `pk_core` or developer environment leakage.
- [ ] Verify uninstall/cleanup behavior where required.
- [ ] Verify package from release artifact, not source tree, passes smoke/integration tests.

### Definition of Done / Acceptance Gates
- [ ] A clean supported node can install/start/verify INV-61 from signed release artifacts using documented steps.
- [ ] Packaging includes all required runtime assets and no undeclared dependency on the developer machine.
- [ ] Upgrade/rollback and graceful shutdown are automated and tested.
- [ ] Deployment configuration enforces resource/security/health requirements.

---

## M32 — Formal operations/release/governance package
**Related audit controls:** C091–C100  
**Objective:** Establish production operating standards, staged release controls, incident response, rollback/emergency procedures, vulnerability lifecycle, reviews, waivers, and exit criteria.

### SLO/SLA and service objectives
- [ ] Define availability objective and measurement window.
- [ ] Define latency objectives by operation/workload class.
- [ ] Define error-rate objective.
- [ ] Define saturation/capacity objective.
- [ ] Define recovery objectives (RTO/RPO) where state exists.
- [ ] Define support hours/escalation expectations.
- [ ] Define error budget and policy for release velocity when budget is exhausted.
- [ ] Map every SLO to concrete telemetry queries and alerts.

### Release process
- [ ] Define branch/tag/versioning policy.
- [ ] Define mandatory CI gates: unit, integration, security, fuzz, concurrency, compatibility, performance, packaging, SBOM/provenance.
- [ ] Define release candidate creation process.
- [ ] Require change log/release notes including breaking/security/operational changes.
- [ ] Require compatibility matrix update when applicable.
- [ ] Require artifact signing and provenance verification.
- [ ] Define approver roles for production promotion.

### Canary/staged rollout
- [ ] Define rollout stages and population percentages/scopes.
- [ ] Define automatic and manual promotion criteria.
- [ ] Define SLO/error/saturation/security signals that halt promotion.
- [ ] Define minimum observation period per stage.
- [ ] Support draining old instances safely.
- [ ] Verify mixed-version compatibility during rollout.
- [ ] Preserve ability to pause without continuing background rollout.

### Rollback
- [ ] Define rollback trigger thresholds.
- [ ] Maintain last-known-good signed artifact/config references.
- [ ] Define rollback command/procedure and required permissions.
- [ ] Define persisted-state/schema rollback constraints.
- [ ] Verify rollback under active traffic.
- [ ] Record rollback events in audit/release history.
- [ ] Require post-rollback validation before declaring recovery complete.

### Emergency disable / kill switch
- [ ] Define scope: function, interface, tenant, node, version, feature, or entire service.
- [ ] Require strong authentication/authorization for activation.
- [ ] Ensure emergency disable works when normal control plane is degraded if required.
- [ ] Define fail-safe local mechanism where justified.
- [ ] Audit activation/deactivation with actor/reason/time.
- [ ] Test kill switch under overload and dependency outage.
- [ ] Define re-enable validation/approval procedure.

### Incident response
- [ ] Define severity taxonomy.
- [ ] Define paging/escalation targets.
- [ ] Create runbooks for auth outage, policy outage, cert expiry, transport outage, overload, latency spike, error spike, partition/failover, audit loss, and suspected compromise.
- [ ] Define evidence preservation/log/trace/audit collection steps.
- [ ] Define customer/tenant communication ownership where applicable.
- [ ] Conduct tabletop exercises.
- [ ] Require post-incident review with tracked corrective actions.

### Vulnerability/security lifecycle
- [ ] Define vulnerability reporting channel.
- [ ] Define triage severity model.
- [ ] Define remediation SLA by severity.
- [ ] Define coordinated disclosure process where applicable.
- [ ] Define emergency dependency/artifact revocation process.
- [ ] Define supported-version security patch policy.
- [ ] Define EOL notification timeline.
- [ ] Track known vulnerabilities/risk acceptances to closure.

### Maintenance/EOL
- [ ] Define supported release branches and maintenance duration.
- [ ] Define runtime/OS/dependency EOL response.
- [ ] Define data/config migration path between supported major versions.
- [ ] Define deprecation warning mechanism and timeline.
- [ ] Archive release artifacts/SBOM/provenance for required duration.

### Review cadence
- [ ] Schedule periodic architecture review.
- [ ] Schedule threat-model/security review.
- [ ] Schedule SLO/capacity review.
- [ ] Schedule dependency/SBOM review.
- [ ] Schedule DR/restore/failover exercise.
- [ ] Schedule runbook/tabletop review.
- [ ] Record review decisions and action owners.

### Exception/waiver register
- [ ] Create a versioned register for unmet requirements.
- [ ] Require requirement/control ID, rationale, risk, compensating controls, owner, approver, creation date, review date, and expiry.
- [ ] Prohibit indefinite waivers without reapproval.
- [ ] Surface active high-risk waivers in production-exit review.
- [ ] Link waivers to technical-debt items and remediation milestones.

### Technical-debt register
- [ ] Record debt item, impacted component/requirement, severity, operational/security effect, owner, target release, and acceptance criteria.
- [ ] Distinguish intentional simplification from unknown/untriaged defect.
- [ ] Track debt aging and missed remediation dates.
- [ ] Escalate debt that threatens SLO/security/supportability.

### Formal production exit gate
- [ ] Create a signed/versioned production-readiness checklist.
- [ ] Require all M01–M32 Definition-of-Done gates to be satisfied, out-of-scope by approved architecture decision, or covered by time-bounded waiver.
- [ ] Require zero unresolved critical/high security findings unless formally risk-accepted by authorized role.
- [ ] Require Tier-1 compatibility matrix pass.
- [ ] Require performance/capacity evidence against current target workload.
- [ ] Require fault/soak/DR evidence.
- [ ] Require packaging/bootstrap/rollback evidence from clean environments.
- [ ] Require SBOM/provenance/signature verification.
- [ ] Require dashboards/alerts/runbooks and on-call ownership.
- [ ] Record final approver roles, release artifact digests, configuration schema/hash, and date.

### Definition of Done / Acceptance Gates
- [ ] SLOs, alerts, error budgets, runbooks, ownership, and incident process are operational.
- [ ] Releases use staged promotion with tested rollback and emergency-disable controls.
- [ ] Security vulnerability, dependency, and EOL lifecycle is documented and enforced.
- [ ] Active exceptions/debt are explicitly reviewed, owned, and time-bounded.
- [ ] Production readiness is decided from evidence attached to a formal exit-gate artifact—not from repository completeness claims alone.

---

# Cross-Component Completion Ledger

Use this summary only after the detailed per-component acceptance gates above have been satisfied.

- [ ] M01 — `pk_core` dependency and reproducible dependency manifest
- [ ] M02 — Historical master-source artifact / formal replacement
- [ ] M03 — Real cross-host network transport adapter
- [ ] M04 — WIT parser/bindings and canonical wire serialization
- [ ] M05 — Protocol negotiation and compatibility matrix
- [ ] M06 — Peer/node/workload authentication
- [ ] M07 — Authorization/capability enforcement
- [ ] M08 — Transport encryption/key lifecycle
- [ ] M09 — Replay/spoofing defenses and request identity
- [ ] M10 — Cancellation/idempotency/retry/reconnect semantics
- [ ] M11 — Backpressure/admission control/circuit breaking
- [ ] M12 — Configuration subsystem/provenance
- [ ] M13 — Tamper-evident audit event pipeline
- [ ] M14 — Health/readiness/dependency status
- [ ] M15 — Production metrics exporter
- [ ] M16 — Structured operational logging
- [ ] M17 — Distributed trace propagation
- [ ] M18 — Telemetry retention/privacy/export policy
- [ ] M19 — Failover/partition/split-brain/duplicate-execution controls
- [ ] M20 — Durable/restart/replay semantics
- [ ] M21 — Requirements specification/traceability matrix
- [ ] M22 — Owner/escalation/ADR
- [ ] M23 — Security architecture/adversarial test suite
- [ ] M24 — Parser/protocol fuzzing/property tests
- [ ] M25 — Concurrency/race-condition tests
- [ ] M26 — Adjacent-layer integration tests
- [ ] M27 — Cross-runtime/cross-architecture certification
- [ ] M28 — Performance/capacity/power/regression certification
- [ ] M29 — Fault-injection/soak/disaster/degraded-control-plane tests
- [ ] M30 — Supply-chain provenance/artifact verification/SBOM
- [ ] M31 — Production packaging/bootstrap artifact
- [ ] M32 — Formal operations/release/governance package

## Final production-exit evidence bundle

- [ ] Requirements/traceability matrix exported and complete.
- [ ] Architecture and security ADRs approved.
- [ ] Threat model and adversarial suite current.
- [ ] All Tier-1 tests pass with zero unexpected skips.
- [ ] Integration, interoperability, concurrency, fuzz, performance, soak, fault, and recovery evidence archived.
- [ ] SBOM, provenance, release manifest, checksums, and signatures generated and verified.
- [ ] Clean-node install/upgrade/rollback evidence archived.
- [ ] Current configuration schema and production config provenance recorded.
- [ ] Dashboards, alerts, runbooks, ownership, and escalation paths validated.
- [ ] Active waivers/risk acceptances reviewed and unexpired.
- [ ] Release artifact digest and production approval recorded.
