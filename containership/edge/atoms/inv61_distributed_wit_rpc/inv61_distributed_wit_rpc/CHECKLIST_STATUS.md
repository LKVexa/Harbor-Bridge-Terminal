# INV-61 v4.3.0 — completion checklist status

`[x]` locally verified · `[~]` documented or partial · `[ ]` open · `[!]` blocked. A box is only `[x]` when code and an executed test in this build back it. Production use is **not** authorised.

| Component | LOCALLY_VERIFIED | DOCUMENTED | PARTIAL | OPEN | BLOCKED |
|---|---|---|---|---|---|
| M01 `pk_core` dependency and reproducible dependency manifest | 1 | 2 | 9 | 2 | 27 |
| M02 Missing historical master-source artifact (`MASTER.md`) | 0 | 1 | 2 | 8 | 18 |
| M03 Real cross-host network transport adapter | 19 | 0 | 23 | 3 | 5 |
| M04 WIT parser/bindings and canonical wire serialization | 13 | 1 | 15 | 13 | 5 |
| M05 Protocol negotiation and supported-version compatibility matrix | 8 | 1 | 12 | 11 | 2 |
| M06 Peer/node/workload authentication integration | 11 | 1 | 13 | 9 | 3 |
| M07 Authorization and capability enforcement | 11 | 3 | 14 | 7 | 1 |
| M08 Transport encryption and key lifecycle | 10 | 1 | 10 | 5 | 9 |
| M09 Replay/spoofing defenses and request identity | 10 | 1 | 22 | 6 | 0 |
| M10 Cancellation, idempotency, retry, and reconnect semantics | 11 | 1 | 17 | 14 | 1 |
| M11 Backpressure, admission control, and circuit breaking | 10 | 0 | 20 | 14 | 0 |
| M12 Configuration subsystem and provenance | 14 | 0 | 17 | 15 | 1 |
| M13 Tamper-evident security audit event pipeline | 6 | 0 | 16 | 8 | 4 |
| M14 Health/readiness/dependency status endpoint | 3 | 0 | 12 | 13 | 2 |
| M15 Production metrics exporter | 3 | 0 | 14 | 20 | 4 |
| M16 Structured operational logging | 4 | 0 | 15 | 10 | 2 |
| M17 Distributed trace propagation | 4 | 1 | 15 | 11 | 5 |
| M18 Telemetry retention/privacy/export policy | 1 | 1 | 9 | 17 | 9 |
| M19 Failover, partition, split-brain, duplicate-execution controls | 4 | 1 | 12 | 19 | 4 |
| M20 Durable/restart/replay semantics for mutable state | 3 | 0 | 13 | 20 | 1 |
| M21 Requirements specification and traceability matrix | 0 | 6 | 18 | 11 | 2 |
| M22 Owner, escalation path, and approved architecture decision record | 0 | 2 | 6 | 3 | 18 |
| M23 Security architecture and adversarial test suite | 13 | 0 | 16 | 8 | 9 |
| M24 Parser/protocol fuzzing and property tests | 9 | 1 | 8 | 18 | 5 |
| M25 Concurrency and race-condition tests | 4 | 0 | 14 | 24 | 1 |
| M26 Adjacent-layer integration tests | 2 | 0 | 6 | 1 | 31 |
| M27 Cross-runtime / cross-architecture compatibility certification | 2 | 4 | 6 | 6 | 18 |
| M28 Performance, capacity, power, and regression certification | 1 | 0 | 16 | 25 | 6 |
| M29 Fault-injection, soak, disaster, and degraded-control-plane tests | 3 | 0 | 20 | 17 | 9 |
| M30 Supply-chain provenance, artifact verification, and SBOM | 1 | 0 | 8 | 10 | 16 |
| M31 Production packaging/bootstrap artifact | 2 | 2 | 14 | 15 | 9 |
| M32 Formal operations/release/governance package | 1 | 5 | 48 | 39 | 37 |
| **Total** | **184** | **35** | **460** | **402** | **264** |

## M01 — `pk_core` dependency and reproducible dependency manifest

### Dependency definition and source control
- [!] **M01-001** Determine whether `pk_core` is an internal package, public package, vendored module, monorepo workspace dependency, or generated artifact.  
  _BLOCKED_ — pk_core origin unknown and absent (docs/DEPENDENCIES.md); owner must name it.
- [!] **M01-002** Record the canonical source repository, package name, package index, and responsible owner.  
  _BLOCKED_ — Repo/index/owner unknown; DEPENDENCIES.md lists them as unknown; needs owner.
- [!] **M01-003** Pin an exact compatible `pk_core` version or immutable source revision; do not rely on an unbounded version range.  
  _BLOCKED_ — No pk_core pin possible; pyproject.toml gate=[] ; source unknown.
- [!] **M01-004** Document the minimum and maximum supported versions if compatibility across multiple versions is intentionally supported.  
  _BLOCKED_ — No pk_core version range known; needs pk_core source.
- [!] **M01-005** Add a package/build manifest (`pyproject.toml` or equivalent) declaring `pk_core` as an explicit dependency.  
  _BLOCKED_ — pyproject.toml does not declare pk_core (optional 'gate' is empty); source unknown.
- [!] **M01-006** Add a reproducible lock artifact containing resolved transitive dependency versions and hashes.  
  _BLOCKED_ — requirements.lock has no hashes and cffi unpinned; package index unreachable.
- [!] **M01-007** Ensure dependency resolution is deterministic across supported platforms and Python versions.  
  _BLOCKED_ — Cross-platform/Python resolution needs CI runner (inv61-ci.yml not executed) and hashed lock.
- [!] **M01-008** If vendoring is required, define the vendoring procedure, upstream revision, patch set, and update policy.  
  _BLOCKED_ — Vendoring decision depends on unknown pk_core source/owner.
- [~] **M01-009** Prohibit silent fallback to a different locally installed `pk_core` version.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: wrpc/pkcore_compat.py::probe checks symbols only; REQUIRED_VERSION/REQUIRED_SHA256 are None so any installed pk_core is accepted.
- [~] **M01-010** Fail startup/build clearly when the required version is absent or incompatible.  
  _PARTIAL_ — probe raises PkCoreUnavailable (test_pk_core_compat.PkCoreProbeTest.test_absent_package_raises_with_requirement) but is never called at startup and no version check exists.

### Integrity and supply-chain controls
- [!] **M01-011** Record SHA-256 or stronger digests for distributable dependency artifacts.  
  _BLOCKED_ — No artifact digests; package index unreachable, pk_core absent.
- [!] **M01-012** Verify hashes during bootstrap/install before use.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: No --require-hashes install; needs index + hashes.
- [!] **M01-013** Require signed artifacts or repository commit verification where supported.  
  _BLOCKED_ — No signing/commit verification; needs signing keys/PKI and pk_core source.
- [~] **M01-014** Generate dependency provenance showing package source, version, digest, resolver, and build timestamp.  
  _PARTIAL_ — tools/sbom.py records names/versions/file hashes but no source, resolver or timestamp by default; no generated SBOM in evidence/.
- [~] **M01-015** Include `pk_core` in SBOM generation and vulnerability/license scanning.  
  _PARTIAL_ — tools/sbom.py lists pk_core as UNRESOLVED; no vulnerability/license scanning; SBOM not present in evidence/.
- [!] **M01-016** Define an allow-list of approved `pk_core` versions/revisions.  
  _BLOCKED_ — Allow-list needs known pk_core versions and owner approval.
- [~] **M01-017** Define a procedure for urgent revocation of a compromised dependency revision.  
  _DOCUMENTED_ — Unchanged after 4.3.0 re-check: docs/DEPENDENCIES.md 'Update policy': remove pin, patch release, record in waiver register.
- [!] **M01-018** Prevent dependency confusion by pinning the intended package index/namespace.  
  _BLOCKED_ — Index/namespace pinning requires knowing pk_core's canonical index.
- [ ] **M01-019** Verify that local editable installs cannot accidentally shadow the production dependency in CI/release builds.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No check that pk_core resolves from an approved location; test_component adds parent dirs/PK_CORE_PATH to sys.path (shadowing possible).

### Runtime and API compatibility
- [x] **M01-020** Enumerate every symbol imported from `pk_core` by INV-61.  
  _LOCALLY_VERIFIED_ — wrpc/pkcore_compat.py::REQUIRED_SYMBOLS; test_pk_core_compat.PkCoreProbeTest.test_symbol_inventory_matches_source_imports.
- [~] **M01-021** Add explicit compatibility checks for required APIs at startup/test time.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: probe() verified with fakes (test_pk_core_compat.PkCoreProbeTest.test_missing_symbol_detected) but not invoked at startup; real check test_release_gate_requires_pk_core skips locally.
- [!] **M01-022** Validate the expected `pk_core` schema/inventory contract version.  
  _BLOCKED_ — pk_core schema/inventory contract version unknown.
- [~] **M01-023** Add negative tests for missing symbols, incompatible return types, malformed inventory data, and version drift.  
  _PARTIAL_ — Only missing-symbol negative test exists (test_missing_symbol_detected); no return-type, malformed-inventory or version-drift tests.
- [!] **M01-024** Add a compatibility shim only if necessary; version and test it independently.  
  _BLOCKED_ — Need for a shim cannot be decided without pk_core source.
- [~] **M01-025** Ensure errors identify the required package version without exposing sensitive environment data.  
  _PARTIAL_ — Error names required symbols and asserts no HOME leak (test_absent_package_raises_with_requirement) but cannot name a required version (UNPINNED).

### Reproducibility and verification
- [!] **M01-026** Add a clean-environment CI job that installs from the manifest/lock only.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: CI job defined but never executed (no CI runner); the job also has no dependency install step.
- [!] **M01-027** Run the three currently skipped `pk_core` conformance tests in that clean environment.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: pk_core absent; test_component.ConformanceTest skips.
- [!] **M01-028** Fail CI if any `pk_core` conformance test is skipped unexpectedly.  
  _BLOCKED_ — Release-gate job (INV61_REQUIRE_PK_CORE=1, tools/run_gate_tests.py) never executed - needs CI runner and pk_core. test_component.ConformanceTest.test_version now reads VERSION but is still skipped (pk_core absent).
- [ ] **M01-029** Add an offline/restricted-network build test if offline deployment is a requirement.  
  _OPEN_ — No offline/restricted-network build test.
- [!] **M01-030** Verify bootstrap from an empty virtual environment on every supported Python runtime.  
  _BLOCKED_ — Needs CI runner across Python versions.
- [!] **M01-031** Verify dependency resolution on Windows and at least one Linux distribution if both are supported.  
  _BLOCKED_ — Needs Windows/other Linux hosts (CI matrix not executed).
- [~] **M01-032** Capture a machine-readable dependency tree as a release artifact.  
  _PARTIAL_ — tools/sbom.py emits flat component list, not a dependency tree; no artifact produced in evidence/.

### Documentation and operations
- [~] **M01-033** Document installation, upgrade, rollback, cache/offline-mirror, and troubleshooting procedures.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: docs/OPERATIONS.md §1/§5 cover install and rollback; no upgrade, offline-mirror or troubleshooting procedure.
- [!] **M01-034** Record the dependency owner and escalation path.  
  _BLOCKED_ — Owner and escalation UNASSIGNED (ADR-0001, OPERATIONS.md §6).
- [~] **M01-035** Define cadence for dependency review and update qualification.  
  _DOCUMENTED_ — docs/DEPENDENCIES.md 'Update policy' (monthly/on advisory) and OPERATIONS.md §7 review cadence (proposed).
- [!] **M01-036** Document compatibility expectations between INV-61 and `pk_core` releases.  
  _BLOCKED_ — Compatibility expectations need pk_core release info.

### Definition of Done / Acceptance Gates
- [!] **M01-037** A clean checkout can install all dependencies using only committed manifests/locks and approved package sources.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: pk_core not installable; no hashes; index unreachable.
- [!] **M01-038** `pk_core` version and artifact integrity are deterministic and verifiable.  
  _BLOCKED_ — No pk_core version/digest exists.
- [!] **M01-039** Original `pk_core` conformance suite executes with **zero unexpected skips** and passes.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: pk_core absent; conformance tests skip.
- [!] **M01-040** SBOM/provenance include `pk_core` and its transitive dependencies.  
  _BLOCKED_ — pk_core UNRESOLVED in SBOM; transitive deps unknown.
- [!] **M01-041** Upgrade and rollback procedures have been exercised in CI or a release-candidate environment.  
  _BLOCKED_ — Needs CI/release-candidate environment.

## M02 — Missing historical master-source artifact (`MASTER.md`)

### Source recovery and provenance
- [!] **M02-001** Search authoritative source control history, release archives, build outputs, and documentation stores for the original `MASTER.md`.  
  _BLOCKED_ — docs/MASTER_SOURCE.md: MASTER.md not in archive; authoritative stores not accessible.
- [!] **M02-002** Verify recovered content against prior release hashes, tags, or review records where available.  
  _BLOCKED_ — Nothing recovered; prior release hashes unavailable.
- [!] **M02-003** Record source revision, author/owner, recovery date, and provenance evidence.  
  _BLOCKED_ — No recovered content; owner needed.
- [~] **M02-004** If the original cannot be recovered, create a formal loss record describing what is missing and why.  
  _DOCUMENTED_ — docs/MASTER_SOURCE.md records the loss and reason (absent from archive, not reconstructed).
- [!] **M02-005** Decide whether the authoritative replacement is `MASTER.md`, `CHECKLIST.json`, generated documentation, or another versioned artifact.  
  _BLOCKED_ — MASTER_SOURCE.md defers the decision to owner signing a supersession record.
- [!] **M02-006** Document the supersession decision in an ADR.  
  _BLOCKED_ — No ADR; requires owner/approver.

### Content integrity and traceability
- [!] **M02-007** Ensure all 100 expected master prompts/workflows are present exactly once.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Needs MASTER.md to compare; CHECKLIST.json has item_count 100 but no test.
- [!] **M02-008** Assign stable IDs that map unambiguously to C001–C100 or the intended control numbering.  
  _BLOCKED_ — Mapping to source requires MASTER.md.
- [!] **M02-009** Cross-reference each source item to its corresponding structured checklist entry.  
  _BLOCKED_ — Cross-reference requires MASTER.md.
- [ ] **M02-010** Add a generation/validation script that detects missing, duplicate, reordered, or orphaned entries.  
  _OPEN_ — tools/checklist_status.py now exists but validates the status register, not master content for missing/duplicate/reordered/orphaned entries; its --check crashes (FileNotFoundError: CHECKLIST_STATUS.json absent).
- [!] **M02-011** Validate Markdown structure, headings, anchors, and machine-readable metadata if retained as Markdown.  
  _BLOCKED_ — Markdown master missing.
- [!] **M02-012** Preserve historical wording separately if a normalized/generated form is introduced.  
  _BLOCKED_ — Historical wording missing.
- [ ] **M02-013** Add a schema/version marker to the master artifact.  
  _OPEN_ — CHECKLIST.json has keys element/name/item_count/items, no schema/version marker.
- [~] **M02-014** Add a checksum/digest for the authoritative source artifact to release metadata.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: MASTER_SOURCE.md claims CHECKLIST.json digest is in SHA256SUMS, but SHA256SUMS does not exist.

### Change management
- [!] **M02-015** Define whether edits occur in `MASTER.md`, `CHECKLIST.json`, or a higher-level source generator.  
  _BLOCKED_ — Edit-location decision pending owner (MASTER_SOURCE.md).
- [ ] **M02-016** Prevent dual-authoritative sources from drifting silently.  
  _OPEN_ — No drift control between sources.
- [ ] **M02-017** Add CI that regenerates derived artifacts and fails on uncommitted differences.  
  _OPEN_ — No regeneration CI.
- [!] **M02-018** Require review for changes affecting requirement intent or control semantics.  
  _BLOCKED_ — Needs reviewer/approver.
- [~] **M02-019** Maintain changelog entries for material requirement changes.  
  _PARTIAL_ — CHANGELOG.md now has a 4.3.0 entry (Added/Fixed) but no requirement-ID-level change entries, and it points to CHECKLIST_STATUS.json which does not exist in the package.
- [ ] **M02-020** Define backward-compatibility expectations for control IDs and references.  
  _OPEN_ — No control-ID compatibility policy.

### Verification
- [ ] **M02-021** Add tests confirming the expected count of 100 items.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No test asserts 100 items (only pk_core-dependent test_component, skipped).
- [ ] **M02-022** Add tests confirming unique control IDs.  
  _OPEN_ — No test for unique IDs.
- [!] **M02-023** Add tests confirming every checklist control has a source entry and vice versa.  
  _BLOCKED_ — Bidirectional check needs MASTER.md.
- [!] **M02-024** Add a content digest comparison or signed manifest in release CI.  
  _BLOCKED_ — Release CI / signing not available.
- [ ] **M02-025** Validate that README claims match actual repository contents.  
  _OPEN_ — No test. README now says 4.3.0 but still lists 'Transport encryption' under 'Explicitly does not own' although wrpc/security.py implements AES-256-GCM records; stale claims remain undetected.

### Definition of Done / Acceptance Gates
- [!] **M02-026** A single authoritative master-source artifact is present or a formally documented replacement is established.  
  _BLOCKED_ — Replacement not formally established; owner signature needed.
- [!] **M02-027** All 100 controls have bidirectional traceability to the source.  
  _BLOCKED_ — MASTER.md missing.
- [!] **M02-028** CI prevents missing/duplicate/drifted master content.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: No CI and no master source.
- [!] **M02-029** Provenance and change-management rules are documented and reviewed.  
  _BLOCKED_ — Rules not documented; review requires human reviewer.

## M03 — Real cross-host network transport adapter

### Transport architecture
- [!] **M03-001** Select and document the production transport (for example QUIC, HTTP/2, HTTP/3, TCP+TLS, NATS, or an approved message fabric).  
  _BLOCKED_ — ADR-0001 proposes TCP+PSK/AES-GCM but is PROPOSED with owner/approver UNASSIGNED and names mTLS as preferred production.
- [~] **M03-002** Define why the selected transport satisfies latency, reliability, deployment, firewall/NAT, and security requirements.  
  _PARTIAL_ — ADR-0001 covers security rationale only; no latency, firewall/NAT, deployment rationale.
- [ ] **M03-003** Specify client/server connection lifecycle states and transitions.  
  _OPEN_ — No connection lifecycle state/transition specification.
- [~] **M03-004** Define stream/connection multiplexing semantics and maximum concurrent in-flight calls.  
  _PARTIAL_ — No multiplexing (Client serialises calls under a lock, one request per record); max_inflight exists but semantics undocumented.
- [ ] **M03-005** Define request/response correlation rules.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Responses are correlated only by strict ordering; response does not echo request_id; not specified.
- [~] **M03-006** Define connection pooling, idle timeout, keepalive, reconnect, and drain behavior.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: idle_timeout_s, Client reconnect, drain() exist; no pooling/keepalive definition.
- [~] **M03-007** Define DNS/service-discovery and endpoint-selection behavior.  
  _PARTIAL_ — Discovery declared not-owned (contract.py not_owns); endpoint selection undefined (Client takes host:port).
- [~] **M03-008** Define behavior for IPv4/IPv6, proxy traversal, NAT, and dual-stack environments as applicable.  
  _PARTIAL_ — node.py Node.start picks AF_INET6 if ':' in host; no dual-stack/NAT/proxy definition.
- [x] **M03-009** Specify maximum frame/message sizes before allocating full payload buffers.  
  _LOCALLY_VERIFIED_ — node.py::_recv refuses length > limit before read; R-CODEC-02; test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation.
- [~] **M03-010** Define transport-level flow control and interaction with application backpressure.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Admission backpressure (overloaded+retry_after_ms) exists; no transport flow control defined.

### Adapter implementation
- [~] **M03-011** Implement a transport-neutral client interface that accepts typed/canonical RPC frames.  
  _PARTIAL_ — node.py::Client is TCP-specific; no transport-neutral interface.
- [x] **M03-012** Implement a server listener/acceptor that emits validated frame bytes to the decoder.  
  _LOCALLY_VERIFIED_ — node.py::Node._accept_loop/_serve; test_node_e2e.EndToEndTest.test_typed_round_trip.
- [x] **M03-013** Keep transport bytes separate from decoded application values until validation succeeds.  
  _LOCALLY_VERIFIED_ — codec.py::decode_header returns undecoded payload; test_wit_codec.CodecTest.test_envelope_header_decoded_without_touching_args, test_node_e2e.EndToEndTest.test_signature_drift_rejected_before_args_decoded.
- [x] **M03-014** Enforce bounded reads and reject oversized length prefixes before allocation.  
  _LOCALLY_VERIFIED_ — node.py::_recv; test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation.
- [~] **M03-015** Enforce read/write/connect/handshake/idle deadlines.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: handshake/connect/idle/per-call socket timeouts exist; only handshake (test_slowloris_handshake_times_out) and call deadline tested; idle/connect/write untested.
- [~] **M03-016** Implement graceful connection shutdown/draining.  
  _PARTIAL_ — wrpc/node.py::Node.drain now fails readiness, _accept_loop refuses connections, handle answers 'unavailable', and waits for Admission.inflight; test_node_e2e.DefectRegressionTest.test_drain_refuses_new_work_and_readiness_fails covers only the no-inflight case. TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested.
- [x] **M03-017** Implement deterministic error mapping from transport failures to RPC status codes.  
  _LOCALLY_VERIFIED_ — node.py::Client.call maps timeout->deadline-exceeded, other->transport; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer, FaultInjectionTest.test_breaker_opens_on_dead_peer_then_recovers.
- [~] **M03-018** Ensure partial reads/writes and fragmented frames are handled correctly.  
  _PARTIAL_ — node.py::_recv_exact loops over partial reads; no positive fragmented-frame test.
- [x] **M03-019** Protect against request smuggling, truncation, and frame boundary confusion.  
  _LOCALLY_VERIFIED_ — length prefix + AEAD + trailing-bytes rejection; test_wit_codec.CodecTest.test_envelope_header_decoded_without_touching_args, test_security.ChannelTest.test_tampered_ciphertext_and_seq_rejected.
- [~] **M03-020** Ensure network-facing parser code never uses `pickle`, `eval`, arbitrary object deserialization, or unsafe dynamic imports.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Inspection: only json/struct parsing, no pickle/eval; no automated scan or test enforces it.

### Security integration
- [x] **M03-021** Require authenticated encrypted channels for production transport.  
  _LOCALLY_VERIFIED_ — Node._serve always handshakes then AES-GCM Channel; test_security.HandshakeTest.test_mutual_auth_and_channel, test_node_e2e.AdversarialTest.test_garbage_handshake.
- [x] **M03-022** Bind authenticated peer identity into RPC request context.  
  _LOCALLY_VERIFIED_ — Node._serve binds peer->tenant and passes to handle; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [~] **M03-023** Enforce host/peer verification and certificate validation.  
  _PARTIAL_ — Server name pinned (test_security.HandshakeTest.test_server_identity_pinned); no certificates/PKI (blocked).
- [x] **M03-024** Define allowed cipher/protocol versions and disable insecure legacy negotiation.  
  _LOCALLY_VERIFIED_ — SUPPORTED_VERSIONS=('wrpc/2',), AES-256-GCM only (SUPPORT_MATRIX.md, ADR-0001); test_security.NegotiationTest.test_no_common, test_server_choosing_unoffered_version_rejected.
- [ ] **M03-025** Rate-limit connection establishment and failed handshakes.  
  _OPEN_ — Only a global connection cap; no rate limit on connects or failed handshakes (THREAT_MODEL T-08 residual).
- [x] **M03-026** Prevent unauthenticated peers from reaching dispatcher logic.  
  _LOCALLY_VERIFIED_ — handle only reached after hs.complete; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer, test_garbage_handshake.

### Reliability behavior
- [~] **M03-027** Define retry-safe versus non-retry-safe transport errors.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: controls.RETRYABLE defined and test_controls_ops.IdempotencyRetryTest.test_retry_only_idempotent_retryable_and_within_deadline, but server caches 'overloaded' under the same request_id so retries of overload can never succeed (DEFECT).
- [x] **M03-028** Define behavior for mid-flight disconnects and ambiguous completion.  
  _LOCALLY_VERIFIED_ — R-DEADLINE-02 in REQUIREMENTS.md; request-id dedup across reconnect; test_node_e2e.EndToEndTest.test_retry_with_same_request_id_executes_once.
- [~] **M03-029** Ensure duplicate execution cannot be silently caused by reconnect/retry behavior.  
  _PARTIAL_ — IdempotencyCache now binds call_digest (test_node_e2e.DefectRegressionTest.test_request_id_reuse_across_functions_conflicts) and does not cache transient outcomes, but dedup is per node (OPERATIONS.md §4) and capacity eviction silently shrinks the dedup window below TTL (soak rate ~2.2k calls/s -> ~45 s vs 600 s TTL); evictions counter is not exported as a metric.
- [~] **M03-030** Propagate cancellation and deadlines through the transport.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Deadline carried in frame and enforced; CancelToken (controls.py) not wired into Client/Node, no cancellation propagation.
- [x] **M03-031** Implement bounded queues for accepted but undispatched work.  
  _LOCALLY_VERIFIED_ — controls.Admission max_queue; test_controls_ops.AdmissionBreakerLeaseTest.test_admission_bounds_and_per_tenant_fairness, test_node_e2e.FaultInjectionTest.test_overload_sheds_with_typed_error.
- [~] **M03-032** Reject new work during graceful drain when required.  
  _PARTIAL_ — Implemented: Node.handle returns 'unavailable' while draining; asserted by test_node_e2e.DefectRegressionTest.test_drain_refuses_new_work_and_readiness_fails. Missing: TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested.

### Verification and interoperability
- [x] **M03-033** Add loopback integration tests over real sockets, not only direct function calls.  
  _LOCALLY_VERIFIED_ — node.py over real loopback TCP: test_node_e2e.EndToEndTest.test_typed_round_trip, test_node_e2e.AdversarialTest.test_record_replay_on_live_session_kills_session, test_two_process.TwoProcessTest.test_separate_server_process.
- [x] **M03-034** Add two-process tests proving independent client/server process operation.  
  _LOCALLY_VERIFIED_ — test_two_process.TwoProcessTest.test_separate_server_process (tools/serve.py subprocess, remote pid asserted).
- [!] **M03-035** Add two-host/container/network-namespace tests proving cross-host behavior.  
  _BLOCKED_ — Requires multiple hosts/containers not available.
- [~] **M03-036** Test packet fragmentation, delayed packets, disconnects, resets, half-close, and timeout paths.  
  _PARTIAL_ — Disconnect (server crash) and timeouts tested; no fragmentation, delayed-packet, reset or half-close tests.
- [x] **M03-037** Test malformed length fields and intentionally truncated frames.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation, test_wit_codec.CodecTest.test_envelope_header_decoded_without_touching_args (truncated), test_negative_paths.
- [x] **M03-038** Test concurrency at the configured maximum and above it.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_connection_limit, FaultInjectionTest.test_overload_sheds_with_typed_error.
- [!] **M03-039** Add interoperability tests with at least one independently implemented peer if the protocol is intended to be open/interoperable.  
  _BLOCKED_ — No independent peer implementation available.
- [x] **M03-040** Benchmark framing and transport overhead separately.  
  _LOCALLY_VERIFIED_ — tools/bench.py; evidence/bench.json separates framing, framing_plus_args, loopback (single platform).

### Observability and operations
- [~] **M03-041** Emit connection, handshake, stream, byte, retry, timeout, and failure metrics.  
  _PARTIAL_ — handshakes, record rejects, calls, rejected connections; no byte, retry, timeout, active-connection metrics.
- [~] **M03-042** Emit structured connection lifecycle logs without leaking credentials or payload secrets.  
  _PARTIAL_ — Only per-call log line; connection/handshake lifecycle only in audit, not structured logs.
- [x] **M03-043** Propagate trace context at the transport boundary.  
  _LOCALLY_VERIFIED_ — traceparent in envelope; test_node_e2e.EndToEndTest.test_observability_emitted asserts trace_id.
- [~] **M03-044** Expose active connections, inflight calls, queue depth, and transport saturation in readiness/metrics.  
  _PARTIAL_ — No active connections/inflight/queue-depth gauges or readiness checks.
- [~] **M03-045** Document firewall ports, service discovery, certificates, proxies, and operational limits.  
  _PARTIAL_ — OPERATIONS.md gives limits via config only; no ports/firewall/proxy/certificate docs.

### Definition of Done / Acceptance Gates
- [!] **M03-046** Cross-host invocation succeeds between isolated processes/machines using the production adapter.  
  _BLOCKED_ — Two-process on one host only; cross-machine needs multiple hosts.
- [x] **M03-047** Malformed/oversized/unauthenticated network traffic is rejected before dispatch.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_malformed_frame_inside_valid_session, test_oversize_length_prefix_refused_without_allocation, test_unknown_peer_and_unenrolled_peer, test_garbage_handshake.
- [~] **M03-048** Deadline, cancellation, reconnect, and graceful-drain semantics have automated coverage.  
  _PARTIAL_ — Deadline and reconnect covered; drain covered only with no in-flight work; CancelToken still not wired into Node/Client, so cancellation has no coverage.
- [~] **M03-049** Transport resource limits are measurable and enforced.  
  _PARTIAL_ — Conn cap/frame size/admission enforced and tested; saturation not measurable (no gauges).
- [!] **M03-050** Interoperability, security, and performance test evidence is attached to the release candidate.  
  _BLOCKED_ — Needs release candidate, independent interop peer and security review.

## M04 — WIT parser/bindings and canonical wire serialization

### WIT source model
- [ ] **M04-001** Define the authoritative WIT package/world/interface files and repository locations.  
  _OPEN_ — No authoritative .wit files; WIT exists only as strings in tests/tools.
- [ ] **M04-002** Pin the WIT/component-model specification version targeted by the implementation.  
  _OPEN_ — No component-model/WIT spec version pinned (SUPPORT_MATRIX lists a subset only).
- [~] **M04-003** Define naming/versioning conventions for packages, interfaces, worlds, resources, and functions.  
  _PARTIAL_ — wit.py enforces kebab-case idents and ns:name@semver; conventions not documented.
- [!] **M04-004** Validate WIT sources during CI with an approved parser/toolchain.  
  _BLOCKED_ — Needs approved external toolchain (e.g. wasm-tools) and CI runner.
- [~] **M04-005** Fail builds on unresolved imports, duplicate definitions, unsupported types, or semantic errors.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: wit.parse rejects undefined/duplicate/unsupported (test_wit_codec.WitParserTest.test_rejections_are_stable) but no build/CI integration; no import resolution (use rejected).
- [~] **M04-006** Record a normalized interface digest used for compatibility checks.  
  _PARTIAL_ — Per-function fingerprints (Node.fps) only; no interface-level normalized digest recorded.

### Binding generation
- [ ] **M04-007** Select or implement a deterministic binding generator.  
  _OPEN_ — No binding generator; dynamic codec only.
- [ ] **M04-008** Generate host/client and guest/server bindings as applicable.  
  _OPEN_ — No generated bindings.
- [ ] **M04-009** Ensure generated bindings are reproducible from committed WIT sources.  
  _OPEN_ — No generated bindings.
- [ ] **M04-010** Version generated-code templates/tooling.  
  _OPEN_ — No templates/tooling.
- [ ] **M04-011** Add CI that regenerates bindings and fails on drift.  
  _OPEN_ — No regeneration CI.
- [ ] **M04-012** Document when generated files are committed versus built on demand.  
  _OPEN_ — Not documented.
- [ ] **M04-013** Ensure generated code does not contain unsafe deserialization shortcuts.  
  _OPEN_ — No generated code exists to assess.

### Canonical value mapping
- [x] **M04-014** Define mapping for all supported WIT scalar types.  
  _LOCALLY_VERIFIED_ — codec.py docstring rules; test_wit_codec.CodecTest.test_golden_vectors, test_signed_extremes.
- [x] **M04-015** Define mapping for strings, lists, tuples, records, variants, options, results, enums, flags, and resources as applicable.  
  _LOCALLY_VERIFIED_ — codec.py encode_value/decode_value, flags/resources rejected (SUPPORT_MATRIX.md); test_wit_codec.PropertyAndFuzzTest.test_round_trip_property, WitParserTest.test_rejections_are_stable.
- [x] **M04-016** Define integer width/sign behavior and overflow rejection.  
  _LOCALLY_VERIFIED_ — codec.py range checks; test_wit_codec.CodecTest.test_negative_paths (int-range), test_signed_extremes.
- [x] **M04-017** Define UTF-8 validation and invalid-sequence behavior.  
  _LOCALLY_VERIFIED_ — strict utf-8 decode, surrogate reject; test_wit_codec.CodecTest.test_negative_paths (utf8, char surrogate).
- [x] **M04-018** Define floating-point NaN/infinity/canonicalization policy where floats are supported.  
  _LOCALLY_VERIFIED_ — NaN canonicalised; test_wit_codec.CodecTest.test_nan_is_canonicalised_and_foreign_nan_rejected.
- [~] **M04-019** Define maximum nesting depth, collection length, string length, and total decoded size.  
  _PARTIAL_ — MAX_DEPTH/MAX_ELEMENTS/1 MiB frame defined (codec.py) and depth now tested (test_wit_codec.PropertyAndFuzzTest.test_nesting_depth_limit_enforced); no per-string length limit beyond the frame cap.
- [~] **M04-020** Define resource-handle identity/lifetime semantics if resources cross the boundary.  
  _DOCUMENTED_ — Resources rejected with stable code (SUPPORT_MATRIX.md 'WIT rejected').
- [~] **M04-021** Define unknown variant/discriminant handling.  
  _PARTIAL_ — enum-range/variant-range codes exist in codec.py but no targeted test.

### Wire codec
- [~] **M04-022** Specify the byte-level frame format, including magic/version/type/length fields if used.  
  _PARTIAL_ — Envelope layout only in code/docstrings (codec.encode_frame, node.py); no byte-level spec document.
- [x] **M04-023** Specify endianness and canonical integer encoding.  
  _LOCALLY_VERIFIED_ — LEB128/zigzag/big-endian in codec.py docstring and SUPPORT_MATRIX.md; test_wit_codec.CodecTest.test_golden_vectors.
- [x] **M04-024** Ensure the same logical value has one canonical serialized form where required.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error asserts canonical re-encode; CodecTest.test_round_trip_and_canonical.
- [x] **M04-025** Reject trailing bytes, duplicate fields, impossible lengths, and non-canonical encodings.  
  _LOCALLY_VERIFIED_ — trailing-bytes, varint-noncanonical, list-limit; test_wit_codec.CodecTest.test_negative_paths, test_envelope_header_decoded_without_touching_args.
- [~] **M04-026** Parse incrementally with bounded allocations.  
  _PARTIAL_ — Bounded Reader over fully buffered frame; not incremental.
- [x] **M04-027** Enforce maximum frame size prior to full payload allocation.  
  _LOCALLY_VERIFIED_ — node.py::_recv; test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation.
- [x] **M04-028** Keep schema/version negotiation separate from payload decode where practical.  
  _LOCALLY_VERIFIED_ — Negotiation in handshake; decode_header before args; test_wit_codec.CodecTest.test_envelope_header_decoded_without_touching_args.
- [x] **M04-029** Produce deterministic error codes for syntax, schema, type, and bounds failures.  
  _LOCALLY_VERIFIED_ — CodecError/WitError codes; test_wit_codec.CodecTest.test_negative_paths, WitParserTest.test_rejections_are_stable.

### Interoperability fixtures
- [~] **M04-030** Create golden byte fixtures for representative WIT values and full RPC frames.  
  _PARTIAL_ — fixtures/golden_vectors.json has value fixtures only; no full RPC frame fixture.
- [~] **M04-031** Include boundary values for every numeric type.  
  _PARTIAL_ — Few boundary values in fixtures; extremes only in test_signed_extremes, none for u64 max/f32 etc.
- [ ] **M04-032** Include empty/max-length lists and strings.  
  _OPEN_ — No empty/max-length list or string fixtures.
- [ ] **M04-033** Include nested record/variant/result combinations.  
  _OPEN_ — No nested record/variant/result fixtures.
- [~] **M04-034** Include malformed/truncated/oversized/non-canonical fixtures.  
  _PARTIAL_ — Malformed cases inline in test_negative_paths, not as fixtures.
- [!] **M04-035** Validate fixtures with an independent implementation/toolchain.  
  _BLOCKED_ — No independent implementation/toolchain.
- [ ] **M04-036** Store fixture digests and protocol version metadata.  
  _OPEN_ — Fixture file has no digest or protocol version metadata.

### Testing and fuzzing
- [x] **M04-037** Add round-trip encode/decode property tests.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_round_trip_property.
- [~] **M04-038** Add decode(encode(x)) equality tests for all supported value domains.  
  _PARTIAL_ — Property WIT omits f32, char, u8/u16/u32, s8/s16 domains.
- [x] **M04-039** Add canonical re-encoding tests for accepted input.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error.
- [~] **M04-040** Add coverage-guided fuzz targets at raw-byte decode boundaries.  
  _PARTIAL_ — Seeded mutation fuzz only; not coverage-guided.
- [!] **M04-041** Add parser differential tests against an independent WIT implementation where feasible.  
  _BLOCKED_ — No independent WIT implementation.
- [~] **M04-042** Add memory-allocation and nesting-depth adversarial tests.  
  _PARTIAL_ — test_hostile_length_prefix_does_not_allocate and parser type-too-deep; no decode nesting-depth or allocation measurement test.

### Definition of Done / Acceptance Gates
- [ ] **M04-043** WIT sources are authoritative, validated, versioned, and traceable to generated bindings.  
  _OPEN_ — No bindings; WIT sources not authoritative files.
- [~] **M04-044** Canonical byte serialization is specified and covered by golden fixtures.  
  _PARTIAL_ — Specified in codec.py; golden fixtures lack frames/boundaries.
- [!] **M04-045** Independent peer/tooling can exchange representative frames successfully.  
  _BLOCKED_ — No independent peer.
- [~] **M04-046** Malformed byte streams fail closed within explicit CPU/memory bounds.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Fuzz shows CodecError-only failure; no explicit CPU/time bound test.
- [!] **M04-047** Binding and codec generation are reproducible in CI.  
  _BLOCKED_ — Needs CI runner; no binding generation.

## M05 — Protocol negotiation and supported-version compatibility matrix

### Version model
- [~] **M05-001** Define separate versions for transport framing, RPC envelope, WIT schema/interface, and implementation if they evolve independently.  
  _PARTIAL_ — wrpc/2 handshake, WIRE_MAJOR=2, WIT package version, impl 4.3.0 exist; independent evolution not defined.
- [~] **M05-002** Define compatibility semantics for major/minor/patch changes.  
  _PARTIAL_ — R-FRAME-03 exact version match only; no major/minor/patch semantics.
- [ ] **M05-003** Identify which changes are wire-compatible, source-compatible, behavior-compatible, or breaking.  
  _OPEN_ — No classification of change types.
- [~] **M05-004** Define minimum supported peer versions per release.  
  _PARTIAL_ — SUPPORT_MATRIX.md 'wrpc/2 only'; no per-release minimum peer policy.
- [ ] **M05-005** Define deprecation windows and end-of-support policy.  
  _OPEN_ — No deprecation/end-of-support policy (DEPRECATED_VERSIONS empty).
- [ ] **M05-006** Publish a machine-readable compatibility matrix.  
  _OPEN_ — SUPPORT_MATRIX.md is prose, not machine-readable.

### Negotiation protocol
- [x] **M05-007** Define a pre-dispatch negotiation message or handshake capability exchange.  
  _LOCALLY_VERIFIED_ — security.py HELLO/ACCEPT/FINISH; test_security.HandshakeTest.test_mutual_auth_and_channel.
- [~] **M05-008** Advertise supported protocol versions/ranges and optional capabilities.  
  _PARTIAL_ — Versions advertised; no capability exchange.
- [x] **M05-009** Select the highest mutually supported non-prohibited version deterministically.  
  _LOCALLY_VERIFIED_ — security.negotiate; test_security.NegotiationTest.test_highest_common.
- [x] **M05-010** Bind the negotiated version to the authenticated session.  
  _LOCALLY_VERIFIED_ — version in MAC'd transcript; test_security.NegotiationTest.test_downgrade_by_mitm_is_detected.
- [~] **M05-011** Prevent mid-session renegotiation unless explicitly supported.  
  _PARTIAL_ — No renegotiation message exists by construction; untested.
- [x] **M05-012** Reject peers with no compatible version using a stable error code.  
  _LOCALLY_VERIFIED_ — no-common-version code; test_security.NegotiationTest.test_no_common (over the wire the client only sees 'transport').
- [~] **M05-013** Avoid revealing unnecessary implementation details in negotiation failures.  
  _PARTIAL_ — Codes are generic; no test asserting non-disclosure.

### Downgrade protection
- [ ] **M05-014** Define a policy for versions disabled due to security vulnerabilities.  
  _OPEN_ — No policy for security-disabled versions.
- [ ] **M05-015** Refuse negotiation to revoked versions even if both peers technically support them.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No revoked-version list.
- [x] **M05-016** Bind negotiated parameters cryptographically to the secure channel where possible.  
  _LOCALLY_VERIFIED_ — transcript MAC; test_security.NegotiationTest.test_downgrade_by_mitm_is_detected.
- [~] **M05-017** Log attempted prohibited downgrades as security events.  
  _PARTIAL_ — Server audits generic authn deny; client-side downgrade detection not logged as security event.
- [x] **M05-018** Test active downgrade/man-in-the-middle scenarios.  
  _LOCALLY_VERIFIED_ — test_security.NegotiationTest.test_downgrade_by_mitm_is_detected, test_server_choosing_unoffered_version_rejected.

### Migration/adaptation
- [ ] **M05-019** Define adapters for intentionally supported schema migrations.  
  _OPEN_ — No migration adapters.
- [ ] **M05-020** Document lossy versus lossless conversions.  
  _OPEN_ — Not documented.
- [~] **M05-021** Reject fields/types that cannot be safely represented in the negotiated version.  
  _PARTIAL_ — Any signature/version drift is rejected (signature-mismatch/version-mismatch) but no per-version representability check.
- [ ] **M05-022** Ensure compatibility adapters have independent unit and integration tests.  
  _OPEN_ — No adapters.
- [~] **M05-023** Define operational sequencing for rolling upgrades across mixed-version fleets.  
  _PARTIAL_ — OPERATIONS.md §5 staged rollout; exact interface-version match means mixed interface versions fail, not addressed.
- [~] **M05-024** Define rollback expectations after partial rollout.  
  _DOCUMENTED_ — docs/OPERATIONS.md §5 rollback (previous sealed release, ConfigStore.rollback).

### Verification
- [ ] **M05-025** Build a full pairwise version interoperability matrix for supported releases.  
  _OPEN_ — Only one release with this wire; no matrix.
- [~] **M05-026** Test current↔current, current↔oldest-supported, and rolling-upgrade combinations.  
  _PARTIAL_ — current<->current only.
- [x] **M05-027** Add negative tests for unknown future versions.  
  _LOCALLY_VERIFIED_ — test_security.NegotiationTest.test_no_common (wrpc/9), test_wit_codec.CodecTest.test_envelope_header_decoded_without_touching_args (wire-version).
- [ ] **M05-028** Add negative tests for revoked/insecure versions.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No revoked-version concept or tests.
- [x] **M05-029** Add tests for incompatible WIT/interface revisions even when transport versions match.  
  _LOCALLY_VERIFIED_ — test_node_e2e.EndToEndTest.test_signature_drift_rejected_before_args_decoded, test_version_drift_rejected.
- [!] **M05-030** Gate releases on the published compatibility matrix.  
  _BLOCKED_ — Needs release CI.

### Definition of Done / Acceptance Gates
- [ ] **M05-031** Supported peer/version combinations are machine-readable and release-versioned.  
  _OPEN_ — No machine-readable matrix.
- [~] **M05-032** Negotiation selects only mutually supported, policy-approved versions.  
  _PARTIAL_ — Mutual selection verified; no policy-approved list.
- [~] **M05-033** Downgrade attacks and revoked versions are rejected and auditable.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Downgrade rejected; revoked versions unimplemented; audit not specific.
- [!] **M05-034** Rolling upgrade and rollback procedures are tested across supported combinations.  
  _BLOCKED_ — Needs multiple releases/CI environment.

## M06 — Peer/node/workload authentication integration

### Identity architecture
- [~] **M06-001** Define identity principals: node, workload, service, tenant, operator, and/or component instance.  
  _PARTIAL_ — peer, tenant, node_id exist in code; principals not defined in docs.
- [!] **M06-002** Select the identity mechanism (for example mTLS PKI, SPIFFE/SPIRE SVIDs, workload attestation, signed tokens, or approved equivalent).  
  _BLOCKED_ — ADR-0001 PSK choice PROPOSED; mTLS/SPIFFE needs PKI and approver.
- [!] **M06-003** Define trust roots and trust domains.  
  _BLOCKED_ — No PKI/trust roots available.
- [!] **M06-004** Define issuer/CA ownership and rotation responsibilities.  
  _BLOCKED_ — Owner UNASSIGNED; no CA.
- [ ] **M06-005** Define identity naming conventions and uniqueness requirements.  
  _OPEN_ — No naming/uniqueness convention.
- [x] **M06-006** Define how tenant/workload identity maps to WIT interface authorization subjects.  
  _LOCALLY_VERIFIED_ — Node.peer_tenants + controls.Grant; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.

### Authentication implementation
- [x] **M06-007** Authenticate peers before accepting RPC application data.  
  _LOCALLY_VERIFIED_ — Node._serve handshake before records; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer.
- [~] **M06-008** Validate certificate/token signatures, issuer, audience, validity window, and revocation status as applicable.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: PSK expiry/revocation/peer checked (test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code); no certs/tokens.
- [~] **M06-009** Enforce hostname/SPIFFE ID/service identity constraints.  
  _PARTIAL_ — Server name pinned (test_server_identity_pinned); PSK holder can impersonate server to itself; no SPIFFE.
- [x] **M06-010** Bind authenticated identity to the transport/session to prevent identity swapping.  
  _LOCALLY_VERIFIED_ — session keys derived per peer PSK; test_security.HandshakeTest.test_mutual_auth_and_channel, ChannelTest.test_reflection_rejected.
- [~] **M06-011** Pass an immutable authenticated-principal object into `Endpoint.handle`/dispatch context.  
  _PARTIAL_ — handle() receives plain tenant/peer strings, not an immutable principal object; rpc.Endpoint.handle has none.
- [x] **M06-012** Ensure application-provided identity fields cannot override authenticated transport identity.  
  _LOCALLY_VERIFIED_ — tenant from peer_tenants, frame carries no identity; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [x] **M06-013** Reject anonymous identity unless explicitly allowed by policy for a specific endpoint.  
  _LOCALLY_VERIFIED_ — unenrolled peer denied; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer.
- [ ] **M06-014** Define clock-skew tolerance for expiring credentials.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No clock-skew tolerance defined (also absolute wall-clock deadlines assume synced clocks).

### Credential lifecycle
- [ ] **M06-015** Implement automated credential issuance/bootstrap.  
  _OPEN_ — No automated issuance.
- [~] **M06-016** Implement rotation without requiring full fleet restart where feasible.  
  _PARTIAL_ — Keyring.rotate with overlap (test_rotation_overlap_then_old_key_expires); tools/serve.py loads one key at start, no live distribution.
- [ ] **M06-017** Define short-lived credential policy.  
  _OPEN_ — No short-lived policy.
- [x] **M06-018** Implement revocation/emergency disable behavior.  
  _LOCALLY_VERIFIED_ — wrpc/security.py::Keyring.revoke; wrpc/node.py::Node._serve re-checks keyring.lookup on every record and ends the session. test_node_e2e.DefectRegressionTest.test_revoked_key_ends_live_session (asserts transport failure + credential-revoked audit), test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code. Note: an idle revoked session stays open (unusable) until idle timeout.
- [ ] **M06-019** Define behavior during identity-provider or CA outage.  
  _OPEN_ — Not defined.
- [~] **M06-020** Prevent expired credentials from being accepted due to stale caches.  
  _PARTIAL_ — Lookup checks expiry per handshake, but live sessions outlive credential expiry.
- [~] **M06-021** Protect private keys using OS/TPM/HSM/secret-store controls appropriate to the deployment tier.  
  _PARTIAL_ — psk_ref env:/file: references (ops.resolve_secret); no permission checks or OS/HSM store.

### Security controls
- [ ] **M06-022** Rate-limit authentication failures.  
  _OPEN_ — No auth-failure rate limiting.
- [x] **M06-023** Avoid credential/token contents in logs.  
  _LOCALLY_VERIFIED_ — JsonLogger/Tracer key redaction; test_controls_ops.OpsTest.test_logger_redacts_truncates_filters_ratelimits, test_traceparent.
- [x] **M06-024** Detect and audit identity mismatch or impersonation attempts.  
  _LOCALLY_VERIFIED_ — authn denies audited with reason; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer.
- [~] **M06-025** Define protection against token replay if bearer tokens are used.  
  _DOCUMENTED_ — No bearer tokens; wrpc/security.py docstring: nonce-bound HMAC handshake and anti-replay.
- [x] **M06-026** Require mutual authentication for privileged/admin/control-plane RPC.  
  _LOCALLY_VERIFIED_ — All sessions mutually authenticated; test_security.HandshakeTest.test_forged_client_finish_rejected, test_wrong_psk_fails_both_directions.
- [~] **M06-027** Test unknown CA, expired cert, revoked cert, wrong audience, wrong service identity, and malformed credential cases.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Expired/revoked/wrong-peer/malformed tested; CA/cert/audience cases blocked (no PKI).

### Observability and operations
- [~] **M06-028** Emit authentication success/failure counters partitioned by non-sensitive reason codes.  
  _PARTIAL_ — inv61_handshakes_total{outcome} emitted but no test asserts it.
- [x] **M06-029** Include authenticated principal IDs in authorized audit events subject to privacy rules.  
  _LOCALLY_VERIFIED_ — audit records peer; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [ ] **M06-030** Expose credential-expiry horizon metrics without exposing secrets.  
  _OPEN_ — No expiry-horizon metric.
- [ ] **M06-031** Alert on elevated authentication failure rates and imminent fleet credential expiry.  
  _OPEN_ — No auth-failure/expiry alerts in OPERATIONS.md §3.
- [ ] **M06-032** Provide runbooks for rotation, revocation, trust-root rollover, and identity-provider outage.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No runbooks.

### Definition of Done / Acceptance Gates
- [x] **M06-033** Every production RPC session has a verified principal before dispatch.  
  _LOCALLY_VERIFIED_ — Handshake precedes dispatch; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer, test_garbage_handshake.
- [~] **M06-034** Principal identity is immutable and available to authorization/audit layers.  
  _PARTIAL_ — Principal passed as mutable strings; audit has it.
- [~] **M06-035** Credential rotation and revocation are automated and tested.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Rotation/revocation tested but not automated.
- [~] **M06-036** Negative authentication tests and outage scenarios pass.  
  _PARTIAL_ — Negative tests pass; no outage scenarios.
- [~] **M06-037** No secrets/private keys/tokens are emitted in logs or error responses.  
  _PARTIAL_ — Key-name redaction only; value-pattern redaction missing (THREAT_MODEL T-13).

## M07 — Authorization and capability enforcement

### Policy model
- [~] **M07-001** Define authorization subjects, resources, actions, conditions, and decision outcomes.  
  _DOCUMENTED_ — controls.py Authorizer/Grant docstrings and REQUIREMENTS.md R-AUTHZ-01.
- [x] **M07-002** Map WIT package/interface/function/resource operations to stable authorization resource IDs.  
  _LOCALLY_VERIFIED_ — qualified 'ns:name/iface' + function; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [x] **M07-003** Define tenant boundaries and cross-tenant access rules.  
  _LOCALLY_VERIFIED_ — exact tenant match; test_controls_ops.AuthorizerTest.test_no_cross_tenant_glob_and_expiry_and_revoke.
- [~] **M07-004** Define capability grant format, scope, expiration, delegation, and revocation semantics.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Scope/expiry/revoke defined; delegation undefined.
- [~] **M07-005** Choose RBAC, ABAC, capability tokens, policy engine, or a documented combination.  
  _DOCUMENTED_ — controls.Authorizer docstring: default-deny capability table.
- [x] **M07-006** Define default-deny behavior for unknown resources/actions.  
  _LOCALLY_VERIFIED_ — test_controls_ops.AuthorizerTest.test_default_deny_grant_and_deny_precedence.
- [x] **M07-007** Define policy precedence and conflict resolution.  
  _LOCALLY_VERIFIED_ — deny beats allow; test_controls_ops.AuthorizerTest.test_default_deny_grant_and_deny_precedence.

### Enforcement points
- [x] **M07-008** Enforce authorization after authentication but before user function dispatch.  
  _LOCALLY_VERIFIED_ — Node.handle authz after handshake before dispatch; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [x] **M07-009** Enforce at both interface and function level where required.  
  _LOCALLY_VERIFIED_ — interface/function patterns; test_controls_ops.AuthorizerTest.test_default_deny_grant_and_deny_precedence.
- [~] **M07-010** Enforce per-resource instance ownership/capability for stateful WIT resources.  
  _DOCUMENTED_ — Resources unsupported (SUPPORT_MATRIX.md).
- [x] **M07-011** Ensure authorization checks use trusted authenticated context, not caller-controlled identity fields.  
  _LOCALLY_VERIFIED_ — test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [~] **M07-012** Prevent registration of exported functions that bypass policy hooks.  
  _PARTIAL_ — Node routes all calls through authz, but rpc.Endpoint (public API) exports have no policy hook; untested.
- [ ] **M07-013** Ensure internal/admin functions have separate, stricter policy controls.  
  _OPEN_ — No admin/internal function class.
- [~] **M07-014** Deny calls if the policy engine is unavailable unless an explicitly approved fail-open exception exists.  
  _PARTIAL_ — In-process authorizer; exception would drop session (fail closed) but untested/undefined.

### Capability lifecycle
- [!] **M07-015** Implement issuance/grant workflow with owner approval where required.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Needs owner approval workflow.
- [x] **M07-016** Implement expiration and revocation.  
  _LOCALLY_VERIFIED_ — not_after + revoke; test_controls_ops.AuthorizerTest.test_no_cross_tenant_glob_and_expiry_and_revoke.
- [x] **M07-017** Prevent capability replay outside allowed subject/session/audience.  
  _LOCALLY_VERIFIED_ — grants bound to tenant+peer; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [ ] **M07-018** Define delegation and attenuation semantics if delegation is supported.  
  _OPEN_ — Delegation undefined.
- [ ] **M07-019** Record provenance for grants and revocations.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Grant/revoke not audited, no provenance.
- [~] **M07-020** Prevent capability escalation through wildcard or overly broad pattern matching.  
  _PARTIAL_ — Tenant exact, but unrestricted fnmatch globs on peer/interface/function.

### Decision auditing
- [~] **M07-021** Emit stable authorization decision IDs/reason codes.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Reason codes exist but rule IDs are list indices (grant[i]) that shift after revoke.
- [~] **M07-022** Audit denials and privileged grants without logging secret tokens.  
  _PARTIAL_ — Allow/deny decisions audited; grant issuance not audited.
- [~] **M07-023** Correlate authorization decisions with request/trace IDs.  
  _PARTIAL_ — Node.handle authz audit subject now contains rid=<request_id>; no trace id in audit records and no test asserts the correlation.
- [ ] **M07-024** Record policy version/hash used for each auditable decision.  
  _OPEN_ — No policy version/hash.
- [~] **M07-025** Expose metrics for allow/deny/error outcomes and policy latency.  
  _PARTIAL_ — Only calls_total{outcome=permission-denied}; no allow/latency metrics.

### Verification
- [~] **M07-026** Add positive tests for every intended authorized role/capability.  
  _PARTIAL_ — Few positive cases.
- [~] **M07-027** Add negative tests for missing, expired, revoked, wrong-tenant, wrong-interface, and wrong-function permissions.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Expired/revoked/wrong-tenant/wrong-function tested; wrong-interface not.
- [~] **M07-028** Add privilege-escalation tests for wildcard, inheritance, delegation, and confused-deputy cases.  
  _PARTIAL_ — Wildcard cross-tenant only; no delegation/confused-deputy tests.
- [ ] **M07-029** Add policy-engine outage and stale-cache tests.  
  _OPEN_ — No outage/stale-cache tests.
- [x] **M07-030** Add cross-tenant isolation tests.  
  _LOCALLY_VERIFIED_ — test_controls_ops.AuthorizerTest.test_no_cross_tenant_glob_and_expiry_and_revoke, test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [ ] **M07-031** Add mutation tests ensuring a removed check causes test failure.  
  _OPEN_ — No mutation testing.

### Definition of Done / Acceptance Gates
- [~] **M07-032** All dispatchable operations have an explicit authorization policy mapping.  
  _PARTIAL_ — Default-deny covers all, no explicit mapping.
- [x] **M07-033** Default-deny is enforced for unspecified access.  
  _LOCALLY_VERIFIED_ — test_controls_ops.AuthorizerTest.test_default_deny_grant_and_deny_precedence, test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [~] **M07-034** Privilege-escalation and cross-tenant negative tests pass.  
  _PARTIAL_ — Escalation tests limited to cross-tenant glob.
- [~] **M07-035** Policy decisions are auditable and tied to immutable policy versions.  
  _PARTIAL_ — Audited but no immutable policy versions.
- [ ] **M07-036** Grant/revoke lifecycle is operationally documented and exercised.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Grant/revoke lifecycle not documented.

## M08 — Transport encryption and key lifecycle

### Cryptographic architecture
- [!] **M08-001** Require TLS 1.3, QUIC TLS, or an equivalently approved authenticated encryption channel for production.  
  _BLOCKED_ — Custom AES-GCM channel per ADR-0001 PROPOSED; approval/PKI for TLS needed.
- [~] **M08-002** Define approved cipher suites and key exchange algorithms.  
  _DOCUMENTED_ — ADR-0001 Decision 2-3: HKDF/HMAC-SHA256 PSK auth, AES-256-GCM records.
- [~] **M08-003** Disable insecure protocol versions, renegotiation modes, and weak algorithms.  
  _PARTIAL_ — Single version, no renegotiation by construction; not tested/scanned.
- [~] **M08-004** Define certificate/key sizes and cryptoperiods.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: PSK >=32 bytes (test_security.HandshakeTest.test_weak_and_duplicate_keys_rejected); no cryptoperiod defined.
- [!] **M08-005** Define trust-root storage and rollover procedures.  
  _BLOCKED_ — No trust roots/PKI.
- [~] **M08-006** Document whether payload-level encryption/signatures are needed in addition to transport security.  
  _PARTIAL_ — ADR-0001 mentions INV-36 control sealing; payload-level need not stated.

### Channel establishment
- [x] **M08-007** Validate peer identity during the secure handshake.  
  _LOCALLY_VERIFIED_ — test_security.HandshakeTest.test_server_identity_pinned, test_wrong_psk_fails_both_directions.
- [!] **M08-008** Require mutual TLS for service-to-service production traffic where appropriate.  
  _BLOCKED_ — mTLS needs PKI.
- [~] **M08-009** Enforce server name/SPIFFE/service identity verification.  
  _PARTIAL_ — Server name pinned; no SPIFFE/SNI.
- [x] **M08-010** Bind RPC negotiation and authenticated identity to the established channel.  
  _LOCALLY_VERIFIED_ — transcript binding; test_security.NegotiationTest.test_downgrade_by_mitm_is_detected.
- [x] **M08-011** Ensure application data is never dispatched before secure-channel establishment completes.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_garbage_handshake, test_unknown_peer_and_unenrolled_peer.
- [x] **M08-012** Configure handshake timeouts and resource bounds.  
  _LOCALLY_VERIFIED_ — handshake_timeout_s, HS_LIMIT; test_node_e2e.AdversarialTest.test_slowloris_handshake_times_out.

### Key protection and rotation
- [~] **M08-013** Store private keys in protected OS stores, HSMs, TPMs, or approved secret managers.  
  _PARTIAL_ — env/file references only.
- [ ] **M08-014** Restrict key file permissions and process access.  
  _OPEN_ — No key file permission checks.
- [!] **M08-015** Automate certificate issuance and renewal.  
  _BLOCKED_ — Needs PKI.
- [x] **M08-016** Support overlap windows for zero-downtime rotation.  
  _LOCALLY_VERIFIED_ — Keyring.rotate; test_security.HandshakeTest.test_rotation_overlap_then_old_key_expires.
- [~] **M08-017** Define emergency revocation and compromised-key replacement procedure.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Keyring.revoke exists; no compromised-key procedure documented.
- [!] **M08-018** Test trust-root rollover with mixed old/new certificates.  
  _BLOCKED_ — No trust roots.
- [x] **M08-019** Prevent stale session resumption from bypassing revocation policy where relevant.  
  _LOCALLY_VERIFIED_ — No session resumption exists; live sessions are re-validated per record in wrpc/node.py::Node._serve. test_node_e2e.DefectRegressionTest.test_revoked_key_ends_live_session. (Expiry-on-live-session uses the same Keyring.lookup path but has no dedicated test.)

### Failure and outage semantics
- [x] **M08-020** Define fail-closed behavior when certificates are expired, revoked, malformed, or unverifiable.  
  _LOCALLY_VERIFIED_ — expired/revoked/malformed -> authentication-failed; test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code, test_malformed_hello_variants.
- [ ] **M08-021** Define behavior when OCSP/CRL/identity service is temporarily unavailable.  
  _OPEN_ — Not defined (no OCSP/CRL).
- [x] **M08-022** Prevent fallback to plaintext on secure-channel failure.  
  _LOCALLY_VERIFIED_ — no plaintext path in Node; test_node_e2e.AdversarialTest.test_garbage_handshake.
- [x] **M08-023** Emit clear but non-sensitive failure reason codes.  
  _LOCALLY_VERIFIED_ — one generic code; test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code.
- [ ] **M08-024** Rate-limit repeated failed handshakes.  
  _OPEN_ — No handshake-failure rate limiting.

### Verification
- [x] **M08-025** Test plaintext connection rejection.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_garbage_handshake.
- [!] **M08-026** Test expired, not-yet-valid, revoked, wrong-host, wrong-trust-domain, and self-signed certificates.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Needs certificates/PKI.
- [~] **M08-027** Test supported and prohibited protocol/cipher combinations.  
  _PARTIAL_ — Version combos tested; cipher fixed, no prohibited cipher tests.
- [ ] **M08-028** Test rotation under active load.  
  _OPEN_ — No rotation-under-load test.
- [~] **M08-029** Test key compromise/revocation and recovery procedure.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Revocation tested; recovery procedure absent.
- [ ] **M08-030** Add automated configuration scanning for insecure TLS settings.  
  _OPEN_ — No config scanning.

### Definition of Done / Acceptance Gates
- [!] **M08-031** All production network paths are authenticated and encrypted with approved algorithms.  
  _BLOCKED_ — Production paths/approved algorithms require approver.
- [~] **M08-032** Plaintext fallback is impossible in production configuration.  
  _PARTIAL_ — No plaintext mode exists, but crypto-unavailable fail-closed path untested (pragma: no cover).
- [~] **M08-033** Key/certificate rotation and revocation have automated tests and runbooks.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Automated tests exist; no runbooks.
- [!] **M08-034** Trust-root rollover is validated without uncontrolled outage.  
  _BLOCKED_ — No trust roots.
- [!] **M08-035** Crypto configuration is continuously checked in CI/release validation.  
  _BLOCKED_ — Needs CI.

## M09 — Replay/spoofing defenses and request identity

### Request identity model
- [~] **M09-001** Define a globally unique request ID format with sufficient entropy (for example UUIDv7/128-bit random or equivalent).  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: codec.py decode_header fixes request_id as 16 random bytes (Client.call os.urandom(16)); no doc states the ID format/entropy requirement.
- [ ] **M09-002** Separate request ID, attempt ID, trace ID, and idempotency key; document each semantic role.  
  _OPEN_ — Unchanged after 4.3.0 re-check: request_id and traceparent exist but no attempt ID; idempotency key is conflated with request_id; no doc separating roles.
- [~] **M09-003** Require request IDs on all production calls before dispatch.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: PK_WRPC_FRAME/2 header requires a 16-byte request_id (codec.py:348) but no test asserts a frame without one is rejected.
- [~] **M09-004** Validate request ID syntax/length and reject malformed identifiers before expensive processing.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: decode_header reads fixed 16 bytes so length is structurally bounded; malformed header -> malformed-frame covered generically by test_wit_codec.PropertyAndFuzzTest.test_header_fuzz, not request-id specific.
- [~] **M09-005** Bind authenticated sender identity, destination, interface, function, negotiated version, and request ID into the authenticated session/envelope.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Handshake binds peer/version into MAC'd transcript and records are AEAD under session keys (security.py), but request ID/function are not bound to authenticated principal beyond channel; tenant comes from peer_tenants.
- [x] **M09-006** Prevent callers from supplying a sender identity that overrides the transport-authenticated principal.  
  _LOCALLY_VERIFIED_ — node.py Node._serve derives tenant from authenticated peer (peer_tenants), frame has no sender field; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation.
- [~] **M09-007** Define request ID retention duration sufficient for deduplication/audit requirements.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: idempotency_ttl_s=600 and ReplayWindow request_ttl_s=300 exist in code; no doc justifies retention for dedup/audit.

### Anti-replay mechanism
- [~] **M09-008** Select nonce, monotonic sequence, timestamp-window, idempotency-ledger, or signed-envelope replay protection appropriate to the transport.  
  _DOCUMENTED_ — Unchanged after 4.3.0 re-check: docs/ADR-0001-wire-and-security.md Decision 3 selects monotonic sequence + AEAD per-record replay protection.
- [ ] **M09-009** Define replay window size and maximum accepted clock skew if timestamps are used.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Record window is strict monotonic (no window size); request-level window uses wall-clock deadline with no documented max clock skew.
- [~] **M09-010** Persist replay state where restart would otherwise reopen the replay window.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Idempotency Journal persists outcomes across restart (test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay), but ReplayWindow is in-memory and unused; no explicit replay rejection state persisted.
- [~] **M09-011** Key replay detection by authenticated principal and security context, not by request ID alone.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: IdempotencyCache key is (tenant, request_id) (node.py handle); per-session seq window; but not keyed by principal/security context beyond tenant, and security.ReplayWindow.check_request (request_id alone) is dead code.
- [x] **M09-012** Reject exact duplicate envelopes deterministically.  
  _LOCALLY_VERIFIED_ — security.Channel.open/ReplayWindow.check_seq reject duplicate records; test_security.ChannelTest.test_replayed_record_rejected and test_node_e2e.AdversarialTest.test_record_replay_on_live_session_kills_session.
- [~] **M09-013** Distinguish legitimate idempotent retries from hostile replay.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Same request_id on a new session is served from IdempotencyCache (treated as retry); there is no mechanism to distinguish hostile replay of a request across sessions—it is silently answered, not flagged.
- [~] **M09-014** Bound replay-cache memory and define eviction behavior that does not silently weaken security.  
  _PARTIAL_ — ReplayWindow fails closed when full (test_security.ChannelTest.test_request_id_window). IdempotencyCache now evicts oldest (test_controls_ops.IdempotencyRetryTest.test_capacity_evicts_oldest_instead_of_refusing): eviction is only an in-object counter, not a metric/alert, and silently weakens dedup below TTL under load.
- [ ] **M09-015** Define behavior during cache/state-store outage; default to fail closed for security-sensitive operations.  
  _OPEN_ — Undefined. Defect: controls.py IdempotencyCache.run lines 115-117 - if journal.append raises after the callee ran, the outcome is neither cached nor returned; the exception escapes Node.handle into _serve (OSError caught) and kills the session, so a retry re-executes the side effect. Untested.

### Spoofing/tamper resistance
- [x] **M09-016** Authenticate the sender and receiver endpoints.  
  _LOCALLY_VERIFIED_ — security.ServerHandshake/ClientHandshake mutual HMAC auth with server identity pinning; test_security.HandshakeTest.test_mutual_auth_and_channel, test_server_identity_pinned, test_forged_client_finish_rejected.
- [x] **M09-017** Integrity-protect request metadata including request ID, method, interface version, deadline, and capability context.  
  _LOCALLY_VERIFIED_ — Whole frame incl. request_id/function/version/deadline sealed with AES-GCM (Channel.seal/open); test_security.ChannelTest.test_tampered_ciphertext_and_seq_rejected.
- [~] **M09-018** Reject messages whose authenticated channel identity conflicts with envelope identity.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Envelope carries no identity so conflict cannot arise; no explicit check or test of conflicting envelope identity.
- [~] **M09-019** Detect invalid sequence/nonce reuse and raise a security event.  
  _PARTIAL_ — Channel.open raises replay; Node._serve audits record-reject and counts metric (node.py) but no test asserts the audit/security event.
- [x] **M09-020** Ensure intermediaries cannot rewrite authorization-relevant fields without detection.  
  _LOCALLY_VERIFIED_ — AEAD over full frame; test_security.ChannelTest.test_tampered_ciphertext_and_seq_rejected and test_forgery_does_not_advance_window.
- [x] **M09-021** Prohibit unsigned/unbound caller-supplied audit identities.  
  _LOCALLY_VERIFIED_ — Audit identities come from authenticated peer/tenant in Node._serve/handle, never from frame; test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation asserts audit peer=svc-b.

### Duplicate execution handling
- [~] **M09-022** Define exactly-once, at-most-once, or at-least-once expectations per operation class.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: docs/REQUIREMENTS.md R-IDEM-01/R-RETRY-01 describe dedup per request id, but no per-operation-class exactly/at-most/at-least-once definition; OPERATIONS.md §4 admits cross-node re-execution.
- [ ] **M09-023** Require idempotency keys for retriable mutating operations where applicable.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No operation metadata requires idempotency keys; Client auto-generates request_id.
- [x] **M09-024** Cache completed idempotent results for a bounded retention period.  
  _LOCALLY_VERIFIED_ — controls.IdempotencyCache TTL/max_entries; test_controls_ops.IdempotencyRetryTest.test_ttl_expiry_and_tenant_scoping.
- [~] **M09-025** Return the original result/status for a recognized idempotent retry when safe.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Returns first outcome (test_controls_ops.IdempotencyRetryTest.test_duplicate_returns_first_outcome_without_reexecution) but DEFECT: transient errors like 'overloaded' are cached too, and key ignores function/args so a different call with same id returns another call's result.
- [x] **M09-026** Define outcome for duplicate non-idempotent requests (reject, conflict, or manual resolution).  
  _LOCALLY_VERIFIED_ — Defined in docs/REQUIREMENTS.md R-IDEM-01 (same id+same call -> first final outcome; different call -> idempotency-conflict); wrpc/controls.py::IdempotencyCache.run call_digest; test_controls_ops.IdempotencyRetryTest.test_request_id_reuse_for_different_call_conflicts, test_node_e2e.DefectRegressionTest.test_request_id_reuse_across_functions_conflicts, test_node_e2e.EndToEndTest.test_retry_with_same_request_id_executes_once.
- [~] **M09-027** Ensure ambiguous network failure does not trigger unconditional re-execution.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: RetryPolicy.call does not retry when idempotent=False (test_controls_ops.IdempotencyRetryTest.test_retry_only_idempotent_retryable_and_within_deadline); ambiguous 'transport' failure on idempotent call is retried unconditionally.

### Testing and evidence
- [x] **M09-028** Test identical request replay on the same connection.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_record_replay_on_live_session_kills_session and test_security.ChannelTest.test_replayed_record_rejected.
- [~] **M09-029** Test replay across reconnects/new sessions.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: test_node_e2e.EndToEndTest.test_retry_with_same_request_id_executes_once covers same-id across reconnect (dedup), but no test replays a captured record into a new session.
- [~] **M09-030** Test replay after server restart.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay covers dedup after restart, not hostile replay rejection.
- [~] **M09-031** Test nonce/sequence wraparound and out-of-order windows if applicable.  
  _PARTIAL_ — Reorder tested (test_security.ChannelTest.test_reordered_record_rejected); wraparound only guarded by rekey-required at 2^63 in Channel.seal, untested.
- [~] **M09-032** Test spoofed request IDs and spoofed sender identities.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Spoofed sender covered by auth tests (test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code); spoofed request IDs (cross-tenant/cross-function reuse) not tested.
- [x] **M09-033** Test replay cache saturation/eviction behavior.  
  _LOCALLY_VERIFIED_ — test_security.ChannelTest.test_request_id_window (ReplayWindow saturation fails closed with replay-cache-full, expiry evicts) and test_controls_ops.IdempotencyRetryTest.test_capacity_evicts_oldest_instead_of_refusing (evicts oldest, counts evictions). Caveat: ReplayWindow is not used by Node.
- [~] **M09-034** Test legitimate retries remain functional without weakening replay controls.  
  _PARTIAL_ — Retry across reconnect (test_node_e2e.EndToEndTest.test_retry_with_same_request_id_executes_once) and after overload (test_node_e2e.DefectRegressionTest.test_retry_after_overload_eventually_executes) now work; but capacity eviction weakens dedup under load and cross-node retries re-execute.
- [~] **M09-035** Verify audit records correlate replay rejection with request and principal IDs.  
  _PARTIAL_ — record-reject audit now carries subject session:<key_id> and peer (asserted reason only in test_node_e2e.DefectRegressionTest.test_revoked_key_ends_live_session); no request id (rejected before decode) and no test of correlation fields.

### Definition of Done / Acceptance Gates
- [~] **M09-036** Every call has a stable request identity and authenticated principal binding.  
  _PARTIAL_ — Every frame has request_id and handshake-derived tenant; request_id now bound to call digest in IdempotencyCache; not bound cryptographically across nodes; DoD not fully evidenced.
- [~] **M09-037** Replay attempts are detected across the defined threat window, including restart where required.  
  _PARTIAL_ — Record replay detected within a session only; cross-session/restart replay is answered from cache rather than detected.
- [ ] **M09-038** Duplicate execution semantics are formally documented per operation class.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No per-operation-class duplicate execution semantics document.
- [ ] **M09-039** Security/audit events distinguish replay, malformed identity, duplicate retry, and spoofing.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Audit events only distinguish authn/authz/record-reject; no distinct malformed-identity, duplicate-retry, or spoofing events.

## M10 — Cancellation, idempotency, retry, and reconnect semantics

### Deadline and cancellation semantics
- [~] **M10-001** Define absolute deadline representation and clock domain.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Deadline is absolute float epoch seconds (codec.py:306 docstring); clock domain (wall clock, cross-host skew) not specified.
- [~] **M10-002** Specify client-to-server deadline propagation and maximum deadline horizon.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Client propagates absolute deadline in frame (Node.Client.call), server enforces (R-DEADLINE-01); no maximum deadline horizon defined or enforced.
- [~] **M10-003** Distinguish deadline expiration from explicit caller cancellation.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: deadline-exceeded is a typed error; CancelToken exists but no explicit cancellation status on wire.
- [ ] **M10-004** Propagate cancellation to in-flight handlers using a cancellable context/token.  
  _OPEN_ — controls.CancelToken is not wired into Node or handlers; no cancel propagation to in-flight handlers.
- [ ] **M10-005** Define whether cancellation is cooperative, preemptive, or advisory for each execution tier.  
  _OPEN_ — No doc defines cooperative/preemptive/advisory cancellation.
- [ ] **M10-006** Ensure handlers can observe cancellation without polling unsafe global state.  
  _OPEN_ — Handlers receive no context/token.
- [~] **M10-007** Define cleanup guarantees for partially executed calls.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: docs/REQUIREMENTS.md R-DEADLINE-02 notes side effect may have happened; no cleanup guarantees defined.
- [x] **M10-008** Return stable cancellation/deadline status codes.  
  _LOCALLY_VERIFIED_ — Stable 'deadline-exceeded' code: test_node_e2e.EndToEndTest.test_typed_errors_not_transport_failures, test_node_e2e.AdversarialTest.test_expired_deadline_never_dispatches; no cancellation code though (deadline only).
- [~] **M10-009** Prevent cancellation after a committed side effect from being reported as if nothing happened.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Node._execute returns deadline-exceeded after a committed side effect (R-DEADLINE-02) - exactly the anti-pattern; only mitigated by request-id dedup, and no commit status reported.

### Idempotency model
- [ ] **M10-010** Classify operations as safe/read-only, idempotent-mutating, non-idempotent, streaming, or transactional.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No operation classification; only a boolean idempotent flag per client call.
- [ ] **M10-011** Encode retry/idempotency policy in interface metadata or generated bindings.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Retry/idempotency policy not in WIT metadata or bindings; caller passes idempotent= flag (default True).
- [~] **M10-012** Define idempotency-key format, scope, TTL, and collision handling.  
  _PARTIAL_ — Key=(tenant, 32-hex request_id), TTL idempotency_ttl_s, collision -> idempotency-conflict (R-IDEM-01, tested). Key format/retention and eviction-shrinks-window behaviour not documented as a spec.
- [x] **M10-013** Persist idempotency results for the required retry horizon.  
  _LOCALLY_VERIFIED_ — ops.Journal persists outcomes; test_controls_ops.IdempotencyRetryTest.test_journal_survives_restart_and_torn_tail, test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay.
- [x] **M10-014** Ensure result caching cannot leak data across tenants/principals.  
  _LOCALLY_VERIFIED_ — Key includes tenant; test_controls_ops.IdempotencyRetryTest.test_ttl_expiry_and_tenant_scoping.
- [x] **M10-015** Define conflict semantics when the same key is reused with different arguments.  
  _LOCALLY_VERIFIED_ — docs/REQUIREMENTS.md R-IDEM-01; wrpc/node.py::Node.handle computes sha256(iface#fn#fp#payload) digest; wrpc/controls.py::IdempotencyCache.run returns idempotency-conflict. test_controls_ops.IdempotencyRetryTest.test_request_id_reuse_for_different_call_conflicts, test_node_e2e.DefectRegressionTest.test_request_id_reuse_across_functions_conflicts.

### Retry policy
- [~] **M10-016** Define which status/error classes are retriable.  
  _DOCUMENTED_ — docs/REQUIREMENTS.md Failure taxonomy lists retryable set; controls.RETRYABLE.
- [x] **M10-017** Prohibit automatic retry of non-idempotent operations unless an explicit idempotency mechanism exists.  
  _LOCALLY_VERIFIED_ — RetryPolicy.call returns immediately when not idempotent; test_controls_ops.IdempotencyRetryTest.test_retry_only_idempotent_retryable_and_within_deadline.
- [x] **M10-018** Implement bounded exponential backoff with jitter.  
  _LOCALLY_VERIFIED_ — RetryPolicy.backoff full jitter capped at cap_s; test_controls_ops.IdempotencyRetryTest.test_backoff_bounded.
- [~] **M10-019** Define max attempts, max total retry duration, and per-attempt deadline budgeting.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: max_attempts and deadline stop retries; no per-attempt deadline budgeting (each attempt uses remaining overall deadline).
- [x] **M10-020** Respect `Retry-After`/server retry hints if the protocol supports them.  
  _LOCALLY_VERIFIED_ — wrpc/controls.py::RetryPolicy.call uses retry_after_ms hint; test_controls_ops.IdempotencyRetryTest.test_retry_honours_retry_after_hint asserts sleep==[0.4]; server emits retry_after_ms (Node._execute/handle).
- [~] **M10-021** Stop retries when the original call deadline/cancellation fires.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Retries stop at deadline (test_retry_only_idempotent_retryable_and_within_deadline); cancellation not supported.
- [x] **M10-022** Prevent synchronized retry storms through jitter and server overload hints.  
  _LOCALLY_VERIFIED_ — RetryPolicy full-jitter backoff, retry budget and retry_after hint: test_controls_ops.IdempotencyRetryTest.test_backoff_bounded, test_controls_ops.IdempotencyRetryTest.test_retry_budget_caps_amplification, test_controls_ops.IdempotencyRetryTest.test_retry_honours_retry_after_hint. (Jitter distribution itself not statistically asserted.)

### Reconnect/resume state machine
- [ ] **M10-023** Define connection states and transitions: disconnected, connecting, authenticated, ready, draining, failed, closed.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No connection state machine; Client has only socket present/absent.
- [ ] **M10-024** Define how in-flight requests are classified after disconnect: definitely not sent, maybe sent, completed-unknown, completed-known.  
  _OPEN_ — No in-flight classification after disconnect; all map to 'transport'.
- [~] **M10-025** Retry only calls whose semantics permit it.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Retry gated on client idempotent flag only (RetryPolicy.call), not on declared operation semantics.
- [ ] **M10-026** Define session resumption requirements and security binding.  
  _OPEN_ — No session resumption; each reconnect is a full handshake, undocumented.
- [~] **M10-027** Avoid reusing stale authentication/authorization state after reconnect.  
  _PARTIAL_ — Reconnect performs fresh handshake (Client._connect) so no stale session reuse; authz rechecked per call; not tested explicitly.
- [~] **M10-028** Re-run version/capability negotiation after reconnect where required.  
  _PARTIAL_ — Version negotiation reruns in every handshake by construction; no test after reconnect asserts it.

### Observability
- [ ] **M10-029** Emit attempts-per-call, retry delay, cancellation, deadline, ambiguous completion, and reconnect metrics.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No attempts/retry-delay/cancel/reconnect metrics; client has no metrics.
- [ ] **M10-030** Log reason-coded retries/cancellations without payload secrets.  
  _OPEN_ — No retry/cancel logging on client.
- [~] **M10-031** Correlate all attempts to one logical request ID.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Same request_id reused across attempts (Client.call), but attempts not individually identified/logged.
- [ ] **M10-032** Trace retry attempts as child spans/linked spans with consistent semantics.  
  _OPEN_ — No per-attempt spans.

### Verification
- [ ] **M10-033** Test cancellation before dispatch, during queue wait, during handler execution, and during response write.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Only expired-before-dispatch deadline tested; no cancellation tests.
- [x] **M10-034** Test timeout exactly at deadline boundary.  
  _LOCALLY_VERIFIED_ — test_rpc.RpcProtocolTest.test_deadline_is_exclusive (rpc.Endpoint) plus Node now>=deadline check.
- [x] **M10-035** Test retriable and non-retriable error classification.  
  _LOCALLY_VERIFIED_ — test_controls_ops.IdempotencyRetryTest.test_retry_only_idempotent_retryable_and_within_deadline.
- [x] **M10-036** Test duplicate suppression for idempotent retries.  
  _LOCALLY_VERIFIED_ — test_controls_ops.IdempotencyRetryTest.test_concurrent_duplicates_execute_once, test_node_e2e.EndToEndTest.test_retry_with_same_request_id_executes_once.
- [ ] **M10-037** Test disconnect before request bytes, mid-request, after request/ before response, and mid-response.  
  _OPEN_ — No disconnect-phase tests (only server killed between calls).
- [~] **M10-038** Test retry exhaustion and backoff caps.  
  _PARTIAL_ — test_backoff_bounded and test_retry_budget_caps_amplification; max_attempts exhaustion not explicitly asserted.
- [~] **M10-039** Test server restart during in-flight calls.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay restarts between calls, not during an in-flight call.
- [!] **M10-040** Test reconnect under rolling deployment and certificate rotation.  
  _BLOCKED_ — Rolling deployment/certificate rotation needs multiple hosts and PKI (none; T-12).

### Definition of Done / Acceptance Gates
- [~] **M10-041** Retry behavior is deterministic and derived from documented operation semantics.  
  _PARTIAL_ — Retry is deterministic given flags but not derived from documented operation semantics (none exist).
- [~] **M10-042** Non-idempotent side effects cannot be duplicated by automatic reconnect/retry logic.  
  _PARTIAL_ — idempotent=False disables retry and dedup now digest-bound, but OPERATIONS.md §4 admits cross-node re-execution, capacity eviction can drop a record, and journal-write failure after execution re-executes on retry.
- [~] **M10-043** Cancellation/deadline propagation is end-to-end tested.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Deadline propagation tested end to end; cancellation not implemented.
- [ ] **M10-044** Reconnect state is observable and produces no hidden infinite retry loops.  
  _OPEN_ — No reconnect state observability.

## M11 — Backpressure, admission control, and circuit breaking

### Resource limits
- [x] **M11-001** Define max encoded frame bytes.  
  _LOCALLY_VERIFIED_ — cfg max_frame_bytes and HS_LIMIT enforced in node._recv; test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation.
- [x] **M11-002** Define max decoded payload bytes.  
  _LOCALLY_VERIFIED_ — codec.Reader bounds (R-CODEC-02, 1 MiB); test_wit_codec.PropertyAndFuzzTest.test_hostile_length_prefix_does_not_allocate.
- [~] **M11-003** Define max argument count, collection length, string length, nesting depth, and resource-handle count.  
  _PARTIAL_ — Element count 65536 and depth 32 bounded in codec (R-CODEC-02); no separate string-length/arg-count/resource-handle limits defined.
- [~] **M11-004** Define max concurrent connections per node and per principal/tenant.  
  _PARTIAL_ — max_connections per node (test_node_e2e.AdversarialTest.test_connection_limit); no per-principal connection limit (THREAT_MODEL T-08).
- [~] **M11-005** Define max concurrent requests globally and per interface/function.  
  _PARTIAL_ — max_inflight global and per_tenant_inflight; no per-interface/function limits.
- [~] **M11-006** Define max queued requests and queue memory budget.  
  _PARTIAL_ — max_queue bounds waiter count; no queue memory budget.
- [~] **M11-007** Define max response size and streaming buffer size.  
  _PARTIAL_ — Channel MAX_RECORD 1 MiB bounds responses; no streaming (unsupported).
- [x] **M11-008** Enforce limits before unbounded allocation whenever possible.  
  _LOCALLY_VERIFIED_ — node._recv refuses length before allocating; test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation, test_wit_codec...test_hostile_length_prefix_does_not_allocate.

### Admission control
- [x] **M11-009** Implement bounded admission queues.  
  _LOCALLY_VERIFIED_ — controls.Admission bounded queue; test_controls_ops.AdmissionBreakerLeaseTest.test_admission_bounds_and_per_tenant_fairness, test_admission_queue_wakes_waiter.
- [ ] **M11-010** Define priority classes and starvation/fairness rules if priorities exist.  
  _OPEN_ — No priority classes and no doc stating none exist.
- [x] **M11-011** Implement per-tenant/principal quotas.  
  _LOCALLY_VERIFIED_ — Admission per_tenant cap; test_controls_ops.AdmissionBreakerLeaseTest.test_admission_bounds_and_per_tenant_fairness.
- [ ] **M11-012** Implement token/leaky bucket or equivalent request-rate limiting.  
  _OPEN_ — No token/leaky bucket rate limiter; only concurrency caps.
- [x] **M11-013** Define overload rejection status and retry hints.  
  _LOCALLY_VERIFIED_ — docs/REQUIREMENTS.md R-ADMIT-01 ('overloaded'+retry_after_ms); Node._execute; test_node_e2e.FaultInjectionTest.test_overload_sheds_with_typed_error, test_node_e2e.DefectRegressionTest.test_retry_after_overload_eventually_executes, test_controls_ops.IdempotencyRetryTest.test_retry_honours_retry_after_hint.
- [x] **M11-014** Ensure rejected calls do not consume normal execution slots.  
  _LOCALLY_VERIFIED_ — Admission refusal returns (outcome, final=False) before any slot/side effect and is not cached: wrpc/node.py::Node._execute, wrpc/controls.py::IdempotencyCache.run. test_controls_ops.IdempotencyRetryTest.test_transient_outcome_not_cached_so_retry_runs, test_node_e2e.DefectRegressionTest.test_retry_after_overload_eventually_executes.
- [ ] **M11-015** Reserve capacity for health/control/admin traffic if operationally necessary.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No reserved control/admin capacity.
- [ ] **M11-016** Define burst capacity separately from sustained rate.  
  _OPEN_ — No burst vs sustained rate distinction.

### Backpressure propagation
- [~] **M11-017** Propagate receiver saturation to senders rather than buffering indefinitely.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Overload rejected with typed error rather than buffered; connection loop is synchronous per conn; no explicit backpressure signal beyond error.
- [ ] **M11-018** Integrate transport flow control with RPC queue limits.  
  _OPEN_ — No integration with transport flow control.
- [ ] **M11-019** Bound producer speed for streaming operations.  
  _OPEN_ — Streaming unsupported (docs/SUPPORT_MATRIX.md rejects stream); no producer bounding defined.
- [ ] **M11-020** Expose queue depth/high-water marks to adaptive clients.  
  _OPEN_ — Queue depth not exposed to clients or metrics.
- [ ] **M11-021** Define behavior when downstream dependencies apply backpressure.  
  _OPEN_ — Downstream backpressure behavior undefined.

### Circuit breakers
- [x] **M11-022** Implement breaker states (closed/open/half-open) with deterministic transitions.  
  _LOCALLY_VERIFIED_ — controls.CircuitBreaker; test_controls_ops.AdmissionBreakerLeaseTest.test_breaker_state_machine, test_node_e2e.FaultInjectionTest.test_breaker_opens_on_dead_peer_then_recovers.
- [~] **M11-023** Define failure types counted toward breaker trip thresholds.  
  _PARTIAL_ — Only transport/timeout failures recorded (Client.call attempt); not documented.
- [~] **M11-024** Exclude caller errors that should not penalize dependency health.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Typed server errors record success so caller errors don't penalize, by code; not documented or tested explicitly.
- [~] **M11-025** Define rolling window, failure threshold, open duration, and probe policy.  
  _PARTIAL_ — threshold/cooldown/single probe implemented (consecutive, no rolling window); breaker_threshold/cooldown config keys exist but are not wired into Client.
- [~] **M11-026** Scope breakers appropriately per dependency/endpoint/tenant.  
  _PARTIAL_ — Breaker per Client instance (per endpoint); no per-tenant scoping, not documented.
- [ ] **M11-027** Emit state-transition events and metrics.  
  _OPEN_ — No breaker transition events/metrics.
- [ ] **M11-028** Prevent breaker oscillation through hysteresis/backoff.  
  _OPEN_ — No hysteresis/backoff on reopen; fixed cooldown.

### Overload safety
- [~] **M11-029** Shed load before memory/FD/thread/task exhaustion.  
  _PARTIAL_ — Concurrency/connection caps and shedding exist; evidence/soak.json (regenerated): RSS 25,784->110,392 KB over 60 s/131,413 calls; OPERATIONS.md §4 attributes it to the 100k idempotency cache but no run shows RSS plateauing.
- [~] **M11-030** Ensure overload errors are cheap to generate.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Overload error is a small JSON built in _execute, but it happens after authz audit append (fsync if file) and IdempotencyCache insertion - not cheap.
- [x] **M11-031** Prevent unauthenticated clients from consuming protected queue capacity.  
  _LOCALLY_VERIFIED_ — Handshake required before any frame, per-tenant caps; test_node_e2e.AdversarialTest.test_unknown_peer_and_unenrolled_peer, test_slowloris_handshake_times_out. (Unauth clients can still hold connection slots up to handshake_timeout.)
- [ ] **M11-032** Define degraded-mode feature shedding order.  
  _OPEN_ — No degraded-mode shedding order.
- [ ] **M11-033** Validate that administrative/emergency-disable channels remain available under overload.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No admin channel; drain() is in-process only; untested under overload.

### Verification
- [ ] **M11-034** Test every configured hard limit at limit-1, limit, and limit+1.  
  _OPEN_ — No limit-1/limit/limit+1 tests for configured limits.
- [~] **M11-035** Run burst and sustained overload tests.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: evidence/soak.json 60s 8-client run and test_overload_sheds_with_typed_error; no burst vs sustained distinction.
- [~] **M11-036** Verify bounded memory under malicious oversized/slow clients.  
  _PARTIAL_ — Oversize and slowloris handshake tested; slow client during records and memory bound not measured (soak RSS grew 3.5x).
- [~] **M11-037** Verify fairness across tenants under contention.  
  _PARTIAL_ — test_admission_bounds_and_per_tenant_fairness checks per-tenant cap in unit only; no contention fairness test.
- [x] **M11-038** Verify circuit breaker opens, probes, recovers, and reopens correctly.  
  _LOCALLY_VERIFIED_ — test_controls_ops.AdmissionBreakerLeaseTest.test_breaker_state_machine and FaultInjectionTest.test_breaker_opens_on_dead_peer_then_recovers.
- [ ] **M11-039** Test downstream outage with caller retry pressure.  
  _OPEN_ — No downstream outage + retry pressure test.
- [~] **M11-040** Verify graceful degradation rather than process crash/OOM.  
  _PARTIAL_ — Soak shows no crash; no OOM/degradation tests.

### Definition of Done / Acceptance Gates
- [~] **M11-041** CPU, memory, connection, queue, and concurrency limits are explicit and enforced.  
  _PARTIAL_ — Memory/connection/queue/concurrency limits explicit; no CPU limit, no memory enforcement.
- [~] **M11-042** Overload results in bounded rejection/degradation, not unbounded queuing or resource exhaustion.  
  _PARTIAL_ — Bounded rejection tested (test_node_e2e.FaultInjectionTest.test_overload_sheds_with_typed_error); overload no longer cached; evidence/soak.json (regenerated): RSS 25,784->110,392 KB over 60 s/131,413 calls; OPERATIONS.md §4 attributes it to the 100k idempotency cache but no run shows RSS plateauing.
- [~] **M11-043** Per-tenant fairness and protected control capacity are validated.  
  _PARTIAL_ — Per-tenant cap unit-tested; protected control capacity absent.
- [~] **M11-044** Circuit-breaker behavior is observable and tested under real failure scenarios.  
  _PARTIAL_ — Breaker tested with dead peer; no breaker observability.

## M12 — Configuration subsystem and provenance

### Configuration model
- [x] **M12-001** Define all runtime configuration keys in a typed schema.  
  _LOCALLY_VERIFIED_ — ops.SCHEMA typed schema; test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback.
- [ ] **M12-002** Classify settings as immutable-at-startup, hot-reloadable, secret, policy-controlled, or derived.  
  _OPEN_ — No classification of settings (hot-reload/secret/immutable).
- [~] **M12-003** Define defaults explicitly and prohibit hidden environment-dependent defaults for security-critical settings.  
  _PARTIAL_ — ops.DEFAULTS explicit, no env-dependent defaults; but security minima (e.g. non-loopback) not enforced; not documented.
- [x] **M12-004** Assign units/ranges/enums for numeric and enumerated settings.  
  _LOCALLY_VERIFIED_ — SCHEMA ranges/enums enforced; test_config_layers_provenance_validation_rollback tests range and enum rejection (units only implicit via _s suffix).
- [~] **M12-005** Define required versus optional values.  
  _PARTIAL_ — All keys required after defaults merge (validate_config missing check); no required-vs-optional classification.
- [~] **M12-006** Define precedence among defaults, file, environment, CLI, orchestrator, and remote config.  
  _PARTIAL_ — defaults<file<env documented in OPERATIONS.md §1 and ConfigStore docstring, but precedence is caller-supplied layer order; CLI/orchestrator/remote not defined.
- [x] **M12-007** Reject unknown keys unless forward-compatible behavior is explicitly designed.  
  _LOCALLY_VERIFIED_ — validate_config rejects unknown keys; test_config_layers_provenance_validation_rollback ({'nope':1}).

### Validation
- [x] **M12-008** Validate syntax and schema before activation.  
  _LOCALLY_VERIFIED_ — ConfigStore.activate validates before swap; test_config_layers_provenance_validation_rollback.
- [~] **M12-009** Validate semantic invariants across related fields.  
  _PARTIAL_ — Only one cross-field check (dev PSK on non-loopback, ops.py:72), untested; e.g. max_queue vs max_inflight not checked.
- [ ] **M12-010** Validate referenced files/certificates/endpoints without exposing secrets.  
  _OPEN_ — psk_ref syntax checked but referenced file/env not validated at config time.
- [ ] **M12-011** Validate security minima (TLS, auth, size limits, retry ceilings) cannot be disabled accidentally in production profile.  
  _OPEN_ — No production profile; frame size etc. can be set to any in-range value; no TLS/auth toggle.
- [~] **M12-012** Fail startup on invalid required configuration.  
  _PARTIAL_ — ConfigError raised by build; tools/serve.py startup path not tested.
- [~] **M12-013** Return stable validation errors identifying the offending key and constraint.  
  _PARTIAL_ — ConfigError message names key and constraint, but as free text not stable codes; tests only assertRaises.

### Provenance
- [x] **M12-014** Compute a canonical configuration hash.  
  _LOCALLY_VERIFIED_ — ConfigStore.build sha256 of canonical JSON; test_config_layers_provenance_validation_rollback asserts digests differ and rollback digest restores.
- [x] **M12-015** Record source/provenance for each effective value where practical.  
  _LOCALLY_VERIFIED_ — provenance['sources'] per key; test_config_layers_provenance_validation_rollback asserts source 'file'. (rollback loses per-key sources.)
- [ ] **M12-016** Expose non-secret effective configuration metadata through diagnostics.  
  _OPEN_ — No diagnostics endpoint exposing effective config.
- [ ] **M12-017** Record config version/hash in logs, traces, audit events, and release evidence.  
  _OPEN_ — Config digest not recorded in logs/traces/audit/evidence; Node takes a dict with no digest.
- [!] **M12-018** Associate configuration changes with actor, reason, approval, and deployment ID.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Actor/approval association needs an owner/approver workflow (UNASSIGNED).

### Atomic activation and rollback
- [x] **M12-019** Parse and validate candidate configuration before replacing active configuration.  
  _LOCALLY_VERIFIED_ — activate builds/validates before swap; test_config_layers_provenance_validation_rollback asserts failed activation left active unchanged.
- [x] **M12-020** Activate multi-key changes atomically.  
  _LOCALLY_VERIFIED_ — ConfigStore.activate validates then swaps under one lock; test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback asserts a failed multi-key activation changed nothing.
- [x] **M12-021** Preserve last-known-good configuration.  
  _LOCALLY_VERIFIED_ — ConfigStore.previous + rollback(); test_config_layers_provenance_validation_rollback.
- [ ] **M12-022** Automatically roll back on activation failure where safe.  
  _OPEN_ — No automatic rollback; manual rollback() only and Node never consumes ConfigStore.
- [ ] **M12-023** Define reload concurrency semantics for in-flight calls.  
  _OPEN_ — No reload of running Node; semantics undefined.
- [~] **M12-024** Prevent partial security-policy updates.  
  _PARTIAL_ — Atomic swap covers config, but authorizer grants are separate mutable state; not tested.
- [ ] **M12-025** Provide explicit reload success/failure health signal.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No reload health signal.

### Secret separation
- [x] **M12-026** Keep credentials/private keys/tokens out of ordinary config files where possible.  
  _LOCALLY_VERIFIED_ — psk_ref must be env:/file: reference (validate_config); test_config_layers_provenance_validation_rollback rejects inline hex.
- [~] **M12-027** Reference secret-manager identifiers rather than raw secret values.  
  _PARTIAL_ — env:/file: references only, no secret-manager identifiers.
- [~] **M12-028** Redact secret values from diagnostics/errors/logs.  
  _PARTIAL_ — JsonLogger key redaction tested (test_logger_redacts_truncates_filters_ratelimits); ConfigError messages untested; resolve_secret bytes.fromhex error could leak? no value echoed.
- [ ] **M12-029** Enforce restrictive file/secret permissions.  
  _OPEN_ — resolve_secret does not check file permissions.
- [~] **M12-030** Define secret rotation/reload behavior.  
  _PARTIAL_ — Keyring.rotate with overlap tested (test_security.HandshakeTest.test_rotation_overlap_then_old_key_expires); no config-level reload of secrets.
- [x] **M12-031** Ensure configuration snapshots/backups do not accidentally contain plaintext secrets.  
  _LOCALLY_VERIFIED_ — Config only holds references (validate_config regex); test_config_layers_provenance_validation_rollback.

### Environment overlays
- [~] **M12-032** Define base/site/environment/tenant override model.  
  _PARTIAL_ — Generic ordered layers; no base/site/env/tenant model defined.
- [x] **M12-033** Validate overlays against the same schema.  
  _LOCALLY_VERIFIED_ — ConfigStore.build merges every layer then validates against one schema; test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback.
- [ ] **M12-034** Detect conflicting or shadowed settings.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No conflict/shadow detection (later layer silently wins).
- [~] **M12-035** Make effective configuration deterministic regardless of file enumeration order.  
  _PARTIAL_ — Layer order is explicit arg order, not file enumeration; untested.
- [ ] **M12-036** Test development, staging, and production profiles separately.  
  _OPEN_ — No dev/staging/prod profiles.

### Verification
- [~] **M12-037** Add schema unit tests for every key.  
  _PARTIAL_ — Test covers a few keys only, not every key.
- [x] **M12-038** Add invalid type/range/unknown key tests.  
  _LOCALLY_VERIFIED_ — test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback covers unknown key, range, type, enum.
- [x] **M12-039** Add atomic rollback tests.  
  _LOCALLY_VERIFIED_ — test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback (failed activate unchanged + rollback).
- [ ] **M12-040** Add hot-reload race tests if reload is supported.  
  _OPEN_ — No hot-reload race tests.
- [~] **M12-041** Add secret-redaction tests.  
  _PARTIAL_ — Log redaction tested; no config/diagnostic redaction tests.
- [ ] **M12-042** Add golden effective-config snapshots for representative deployments.  
  _OPEN_ — No golden effective-config snapshots.

### Definition of Done / Acceptance Gates
- [~] **M12-043** Effective configuration is typed, validated, reproducible, and provenance-addressable.  
  _PARTIAL_ — Typed/validated/digest yes; reproducibility across deployments and provenance through runtime not evidenced.
- [ ] **M12-044** Security-critical defaults cannot silently degrade.  
  _OPEN_ — No production security minima enforcement.
- [~] **M12-045** Updates are atomic and rollback-capable.  
  _PARTIAL_ — ConfigStore atomic+rollback, but running Node never reloads config.
- [~] **M12-046** Secrets are isolated and redaction is verified.  
  _PARTIAL_ — References only and log redaction tested; file permission checks and full redaction verification missing.
- [ ] **M12-047** Release artifacts identify the configuration schema/version they support.  
  _OPEN_ — No config schema version in release artifacts/SBOM.

## M13 — Tamper-evident security audit event pipeline

### Audit event schema
- [~] **M13-001** Define stable event IDs and schema version.  
  _PARTIAL_ — seq is a stable record ID; no schema version field in AUDIT_FIELDS.
- [~] **M13-002** Include event time, monotonic sequence if available, node/service identity, authenticated principal, request/trace ID, event type, outcome, and reason code.  
  _PARTIAL_ — ts, seq, tenant, peer, event, decision, reason; missing node identity, request/trace ID.
- [ ] **M13-003** Include policy/config version hashes relevant to the decision.  
  _OPEN_ — No policy/config hashes in audit records.
- [~] **M13-004** Include target interface/function/resource identifiers without sensitive payload content.  
  _PARTIAL_ — authz subject 'iface#fn' without payload; other events have empty subject.
- [~] **M13-005** Define mandatory events: auth success/failure, authorization denial, replay rejection, version/signature drift, config change, key rotation, emergency disable, privileged operation, and audit pipeline failure.  
  _PARTIAL_ — authn/authz/record-reject/node-start/stop emitted; no version/signature drift, config change, key rotation audits; no doc defining mandatory set.
- [~] **M13-006** Define data classification and privacy/redaction rules for every field.  
  _PARTIAL_ — docs/TELEMETRY_POLICY.md classifies audit as restricted overall, not per field.

### Tamper evidence
- [x] **M13-007** Chain records using cryptographic hashes or use an append-only integrity-protected backend.  
  _LOCALLY_VERIFIED_ — ops.AuditLog hash chain; test_controls_ops.OpsTest.test_audit_chain_detects_edit_delete_reorder_truncate.
- [!] **M13-008** Sign batches/checkpoints with a protected signing key where required.  
  _BLOCKED_ — No signing key/PKI available.
- [x] **M13-009** Include sequence numbers to detect deletion/reordering.  
  _LOCALLY_VERIFIED_ — seq in chain; test_audit_chain_detects_edit_delete_reorder_truncate (delete/reorder).
- [!] **M13-010** Store checkpoints outside the service trust boundary where feasible.  
  _BLOCKED_ — Needs external storage outside trust boundary (THREAT_MODEL T-10 'head must be stored off-host by operations').
- [~] **M13-011** Define verification tooling to validate chain/signatures.  
  _PARTIAL_ — AuditLog.verify exists as library function; no CLI tool, and window mode trusts first record.
- [!] **M13-012** Protect audit signing keys separately from application data-plane keys.  
  _BLOCKED_ — No audit signing keys exist.

### Durability and delivery
- [~] **M13-013** Use bounded local buffering with explicit overflow policy.  
  _PARTIAL_ — Memory deque bounded (test_audit_memory_window_is_bounded_and_verifiable) but file is unbounded and no overflow policy.
- [ ] **M13-014** Define whether security-sensitive operations fail closed if audit delivery is unavailable.  
  _OPEN_ — Undefined; append exceptions (disk full) would propagate into request handling uncaught in Node.handle.
- [ ] **M13-015** Retry export with bounded backoff.  
  _OPEN_ — No export/retry.
- [x] **M13-016** Persist unshipped critical audit events across restart if required.  
  _LOCALLY_VERIFIED_ — Synchronous fsync'd append means nothing is unshipped locally; test_node_e2e.FaultInjectionTest.test_audit_log_survives_restart_and_verifies.
- [ ] **M13-017** Prevent unauthenticated callers from flooding audit storage unchecked.  
  _OPEN_ — Failed handshakes append an audit record each with no rate limiting (Node._serve).
- [~] **M13-018** Track dropped/deferred audit events as health/metrics.  
  _PARTIAL_ — Node._audit counts inv61_audit_failures_total and flips 'audit-writable' (test_node_e2e.DefectRegressionTest.test_audit_failure_fails_closed_and_flips_readiness asserts health only); suppressed deny-audits counted as inv61_audit_suppressed_total but untested; metric values never asserted; health never recovers once a failure occurred.

### Access and retention
- [~] **M13-019** Define retention duration by event class.  
  _PARTIAL_ — TELEMETRY_POLICY.md: audit 1 year (proposed, pending owner), not by event class.
- [!] **M13-020** Restrict audit read access using least privilege.  
  _BLOCKED_ — Access control needs deployment/owner; nothing in code.
- [x] **M13-021** Separate operational logs from immutable security audit records.  
  _LOCALLY_VERIFIED_ — AuditLog separate from JsonLogger; test_node_e2e.EndToEndTest.test_observability_emitted checks both.
- [~] **M13-022** Define legal/privacy deletion exceptions and procedures where applicable.  
  _PARTIAL_ — TELEMETRY_POLICY.md says audit retained under audit policy; no procedure.
- [ ] **M13-023** Encrypt audit data in transit and at rest.  
  _OPEN_ — Audit file plaintext; no transit.

### Verification
- [~] **M13-024** Test every required event type.  
  _PARTIAL_ — authz allow/deny tested; authn deny, record-reject audits not asserted.
- [ ] **M13-025** Test redaction of secrets/tokens/payloads.  
  _OPEN_ — No audit redaction tests.
- [x] **M13-026** Tamper with stored records and verify detection.  
  _LOCALLY_VERIFIED_ — test_controls_ops.OpsTest.test_audit_chain_detects_edit_delete_reorder_truncate.
- [x] **M13-027** Delete/reorder records and verify sequence/chain detection.  
  _LOCALLY_VERIFIED_ — test_controls_ops.OpsTest.test_audit_chain_detects_edit_delete_reorder_truncate covers delete, reorder and truncation-with-head.
- [~] **M13-028** Simulate sink outage, disk full, backpressure, and restart.  
  _PARTIAL_ — Restart covered (test_audit_log_survives_restart_and_verifies); no sink outage/disk full/backpressure.
- [ ] **M13-029** Verify time synchronization/clock anomaly handling in event ordering.  
  _OPEN_ — No clock anomaly tests.
- [ ] **M13-030** Exercise forensic reconstruction from a representative incident trace.  
  _OPEN_ — No forensic reconstruction exercise.

### Definition of Done / Acceptance Gates
- [~] **M13-031** Required security decisions generate durable, schema-valid audit events.  
  _PARTIAL_ — authn/authz durable and chained; schema validation and complete event set missing.
- [~] **M13-032** Record deletion/modification/reordering is detectable within the defined threat model.  
  _PARTIAL_ — Detectable given external head (T-10), but off-host head storage BLOCKED and AuditLog loads file without verifying.
- [~] **M13-033** Audit sink failure is observable and handled according to documented fail-open/fail-closed policy.  
  _PARTIAL_ — Fail-closed for authz audit documented (REQUIREMENTS.md R-AUDIT-02) and tested (test_node_e2e.DefectRegressionTest.test_audit_failure_fails_closed_and_flips_readiness). Failures of authn/record-reject/node-start audit writes are silently fail-open (only counted) with no documented policy; audit-writable never resets after a transient failure.
- [~] **M13-034** Forensic correlation across principal/request/policy/config versions is demonstrable.  
  _PARTIAL_ — authz audit subject now includes request id; no policy/config version or trace id in audit records; not demonstrated.

## M14 — Health/readiness/dependency status endpoint

### Health model
- [~] **M14-001** Define separate liveness, readiness, startup, and dependency health semantics.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: live()/ready() in ops.Health and OPERATIONS.md §2; no startup probe semantics.
- [~] **M14-002** Define component states such as starting, ready, degraded, draining, not-ready, failed.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: pass/warn/fail + draining; no starting/failed states.
- [ ] **M14-003** Define transition criteria and debounce/hysteresis rules.  
  _OPEN_ — No debounce/hysteresis beyond cache_s.
- [x] **M14-004** Ensure liveness does not depend on optional external dependencies.  
  _LOCALLY_VERIFIED_ — Health.live returns pass unconditionally; test_controls_ops.OpsTest.test_health_readiness (live pass while dep failing).
- [~] **M14-005** Ensure readiness reflects ability to serve requests safely, including auth/policy/config/transport prerequisites.  
  _PARTIAL_ — Readiness now depends on listener and a real audit-writable check (node.py) plus draining; no auth/keyring/config prerequisites in readiness.
- [ ] **M14-006** Define stall detection for event loop/thread pool/queue progress.  
  _OPEN_ — live() is constant; no stall detection.

### Dependency checks
- [ ] **M14-007** Enumerate critical dependencies: identity provider, policy engine, state store, transport broker, config source, audit sink, etc.  
  _OPEN_ — No enumeration of critical dependencies.
- [~] **M14-008** Define per-dependency timeout and freshness threshold.  
  _PARTIAL_ — ops.Health runs each check in a thread with a single global check_timeout_s (0.5 s) - tested by test_controls_ops.OpsTest.test_health_check_is_time_boxed; no per-dependency timeout/freshness thresholds; a hung check leaks a daemon thread per probe.
- [~] **M14-009** Avoid expensive synchronous deep checks on every probe.  
  _PARTIAL_ — Cache avoids re-running checks within cache_s; untested with non-zero cache.
- [~] **M14-010** Cache dependency health with bounded staleness.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Cache with cache_s staleness; untested.
- [x] **M14-011** Expose degraded-but-serving versus hard-not-ready distinctions.  
  _LOCALLY_VERIFIED_ — warn vs fail distinction; test_controls_ops.OpsTest.test_health_readiness.

### Endpoint design
- [ ] **M14-012** Provide machine-readable status with schema version.  
  _OPEN_ — No schema version; no endpoint (in-process dict only).
- [ ] **M14-013** Include service version/build ID/config hash/protocol version where safe.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No version/build/config hash in health output.
- [~] **M14-014** Include reason-coded component states.  
  _PARTIAL_ — Per-check status + exception type detail; no reason codes.
- [~] **M14-015** Do not expose credentials, internal topology, stack traces, or sensitive endpoint details.  
  _PARTIAL_ — Only exception type name exposed; untested.
- [ ] **M14-016** Separate public/basic health from authenticated detailed diagnostics if necessary.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No endpoint.
- [ ] **M14-017** Make health endpoint resource use bounded and independent of normal request backlog where possible.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No endpoint; not separated from backlog.

### Orchestrator integration
- [ ] **M14-018** Document probe intervals, timeouts, failure thresholds, and initial delay.  
  _OPEN_ — No probe intervals/timeouts documented.
- [!] **M14-019** Validate Kubernetes/systemd/orchestrator integration if used.  
  _BLOCKED_ — Requires orchestrator (Kubernetes/systemd) environment.
- [~] **M14-020** Ensure drain sets readiness false before terminating active work.  
  _PARTIAL_ — Node.drain sets health.draining first, then waits; readiness fail asserted in test_node_e2e.DefectRegressionTest.test_drain_refuses_new_work_and_readiness_fails, but no test has in-flight work during drain; TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested.
- [ ] **M14-021** Ensure transient dependency blips do not cause restart storms.  
  _OPEN_ — No restart-storm protection.

### Verification
- [~] **M14-022** Test healthy, degraded, not-ready, draining, and failed states.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: pass/warn/fail/draining tested in test_health_readiness and test_observability_emitted; no failed/not-ready distinct states.
- [x] **M14-023** Test dependency timeout/outage and recovery transitions.  
  _LOCALLY_VERIFIED_ — ops.Health: outage/recovery in test_controls_ops.OpsTest.test_health_readiness; timeout in test_controls_ops.OpsTest.test_health_check_is_time_boxed (asserts <1 s and detail 'timeout').
- [ ] **M14-024** Test event-loop/thread stall simulation.  
  _OPEN_ — No stall simulation.
- [ ] **M14-025** Verify probe endpoints remain responsive under overload.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No probe under overload test.
- [ ] **M14-026** Verify sensitive data never appears in health output.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No test.

### Definition of Done / Acceptance Gates
- [~] **M14-027** Operators/orchestrators can distinguish alive, ready, degraded, and draining states.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: alive/ready/degraded(warn)/draining distinguishable in-process only; no endpoint.
- [ ] **M14-028** Critical dependency failures drive documented readiness behavior.  
  _OPEN_ — No documented dependency-readiness mapping.
- [~] **M14-029** Health checks are bounded, non-sensitive, and overload-resilient.  
  _PARTIAL_ — Checks now time-boxed (test_controls_ops.OpsTest.test_health_check_is_time_boxed); non-sensitive output and overload resilience untested.
- [!] **M14-030** Probe configuration is included in deployment artifacts and tested.  
  _BLOCKED_ — No deployment artifacts/orchestrator.

## M15 — Production metrics exporter

### Metric taxonomy
- [~] **M15-001** Define service-level request count, error count, and duration histograms.  
  _PARTIAL_ — inv61_calls_total and inv61_handle_seconds (OPERATIONS.md §3); no separate error count, unlabelled histogram.
- [~] **M15-002** Define transport connection/stream metrics.  
  _PARTIAL_ — handshakes/connections_rejected counters; no active connection gauge.
- [ ] **M15-003** Define inflight requests, queue depth, queue wait, and rejection metrics.  
  _OPEN_ — No inflight/queue depth/queue wait metrics.
- [ ] **M15-004** Define retry/cancellation/deadline metrics.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No retry/cancel metrics (deadline only via outcome label).
- [~] **M15-005** Define authentication/authorization outcome metrics with safe reason labels.  
  _PARTIAL_ — inv61_handshakes_total{outcome} for authn; authz only via calls outcome=permission-denied.
- [~] **M15-006** Define version/signature/serialization mismatch counters.  
  _PARTIAL_ — Via inv61_calls_total outcome labels; no dedicated counters.
- [ ] **M15-007** Define circuit-breaker state and trip counters.  
  _OPEN_ — None.
- [ ] **M15-008** Define CPU, memory, FD/socket, thread/task, and network byte metrics.  
  _OPEN_ — None.
- [ ] **M15-009** Define audit exporter/config/identity dependency health metrics.  
  _OPEN_ — Unchanged after 4.3.0 re-check: None.
- [ ] **M15-010** Define build/version/config metadata as info metrics with bounded labels.  
  _OPEN_ — No info metric.

### Histogram/SLO design
- [~] **M15-011** Choose histogram buckets appropriate to p50/p95/p99 latency targets.  
  _PARTIAL_ — Fixed buckets 10us-5s in Metrics.BUCKETS; not justified against SLO targets.
- [ ] **M15-012** Separate queue time, handler time, serialization time, and transport time where useful.  
  _OPEN_ — Only whole handle time.
- [ ] **M15-013** Measure request and response payload size distributions.  
  _OPEN_ — No size histograms.
- [ ] **M15-014** Define saturation indicators used for capacity planning.  
  _OPEN_ — None defined.
- [ ] **M15-015** Define error-budget/SLO metric formulas.  
  _OPEN_ — None.

### Cardinality controls
- [x] **M15-016** Prohibit raw request IDs, user IDs, unbounded resource IDs, URLs, stack traces, or arbitrary error text as metric labels.  
  _LOCALLY_VERIFIED_ — Metrics.ALLOWED_LABELS allow-list; test_controls_ops.OpsTest.test_metrics_exposition_and_cardinality_cap (request_id label raises).
- [~] **M15-017** Define bounded enumerations for interface/function labels or aggregate where count is high.  
  _PARTIAL_ — Node maps unknown interfaces to 'other' (node.py handle); function label unused; untested for node path.
- [~] **M15-018** Implement unknown/other buckets for unexpected reason codes.  
  _PARTIAL_ — Interface 'other' bucket; outcome from handshake e.code is bounded by code; no generic unknown bucket.
- [x] **M15-019** Add tests/linting for label cardinality policy.  
  _LOCALLY_VERIFIED_ — test_controls_ops.OpsTest.test_metrics_exposition_and_cardinality_cap (series cap + label allow-list).
- [ ] **M15-020** Document estimated time-series cardinality at expected deployment scale.  
  _OPEN_ — No cardinality estimate.

### Exporter implementation
- [~] **M15-021** Implement Prometheus/OpenMetrics, OpenTelemetry Metrics, or approved exporter.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Metrics.render produces Prometheus text 0.0.4; no HTTP exporter exposed.
- [~] **M15-022** Ensure scraping/export does not block the RPC critical path.  
  _PARTIAL_ — render is in-process under a lock shared with inc; no scrape path exists.
- [ ] **M15-023** Bound exporter queues and retry behavior.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No exporter.
- [ ] **M15-024** Define exporter authentication/TLS if remote push is used.  
  _OPEN_ — Unchanged after 4.3.0 re-check: N/A undefined.
- [ ] **M15-025** Define behavior when metrics backend is unavailable.  
  _OPEN_ — Undefined.
- [ ] **M15-026** Expose process start time and exporter health.  
  _OPEN_ — Unchanged after 4.3.0 re-check: None.

### Dashboards and alerts
- [ ] **M15-027** Provide baseline service health dashboard.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No dashboards.
- [ ] **M15-028** Provide latency/error/saturation dashboard by bounded dimensions.  
  _OPEN_ — No dashboards.
- [ ] **M15-029** Provide transport/retry/circuit-breaker dashboard.  
  _OPEN_ — No dashboards.
- [ ] **M15-030** Provide auth/security anomaly dashboard.  
  _OPEN_ — No dashboards.
- [~] **M15-031** Define alerts for error-rate, p99, saturation, queue growth, readiness, dependency failure, cert expiry, and audit loss.  
  _PARTIAL_ — OPERATIONS.md §3 proposes 4 alerts (not agreed); missing readiness, cert expiry, audit loss, queue growth.
- [!] **M15-032** Tie alerts to runbooks and owners.  
  _BLOCKED_ — Runbook owners/paging roster UNASSIGNED.

### Verification
- [x] **M15-033** Unit-test metric increments and label sets.  
  _LOCALLY_VERIFIED_ — test_controls_ops.OpsTest.test_metrics_exposition_and_cardinality_cap, ConcurrencyTest.test_metrics_and_audit_under_threads.
- [~] **M15-034** Verify counters are monotonic and histograms use correct units.  
  _PARTIAL_ — Counter exact totals tested under threads; histogram unit (seconds) implicit, no monotonicity test.
- [ ] **M15-035** Verify no high-cardinality labels under fuzzed method/error inputs.  
  _OPEN_ — No fuzzed label tests.
- [!] **M15-036** Load-test exporter overhead.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Load/exporter overhead measurement needs metrics backend; evidence/bench.json excludes exporter.
- [!] **M15-037** Validate dashboards/alerts against injected failures.  
  _BLOCKED_ — Needs dashboards/alert backend.

### Definition of Done / Acceptance Gates
- [~] **M15-038** Metrics cover latency, errors, traffic, saturation, security, dependency, and release metadata.  
  _PARTIAL_ — Latency/traffic/errors basic; saturation, dependency, release metadata missing.
- [~] **M15-039** Cardinality is bounded and documented.  
  _PARTIAL_ — Bounded by cap and tested; not documented with estimates.
- [~] **M15-040** Exporter failure cannot take down request serving.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: No remote exporter so cannot fail; untested.
- [!] **M15-041** Dashboards and alerts are validated using controlled fault injection.  
  _BLOCKED_ — Needs dashboards/alerting backend and fault injection environment.

## M16 — Structured operational logging

### Log schema
- [~] **M16-001** Choose a structured format such as JSON with explicit schema version.  
  _PARTIAL_ — JsonLogger one JSON object per line; no schema version field.
- [~] **M16-002** Define required fields: timestamp, severity, service, version/build, node/instance, event name, request/trace ID, interface/function, outcome, and reason code.  
  _PARTIAL_ — ts, level, component, event, tenant, peer, interface, function, outcome, duration; missing version/build, node/instance, request/trace ID.
- [~] **M16-003** Include tenant/workload/principal identifiers only where permitted and normalized.  
  _PARTIAL_ — tenant/peer logged raw; not normalized; policy in TELEMETRY_POLICY.md.
- [~] **M16-004** Use stable event names and reason-code enums rather than arbitrary prose for automation.  
  _PARTIAL_ — event 'call' and outcome codes are stable enums; only one event type logged.
- [ ] **M16-005** Include configuration/protocol version metadata where relevant.  
  _OPEN_ — No config/protocol version in logs.
- [~] **M16-006** Standardize duration/byte units.  
  _PARTIAL_ — duration_s in seconds only; no byte fields.

### Privacy and redaction
- [~] **M16-007** Classify fields as public, internal, sensitive, secret, or prohibited.  
  _PARTIAL_ — TELEMETRY_POLICY.md classifies signals, not fields.
- [x] **M16-008** Never log passwords, bearer tokens, private keys, session secrets, or raw capabilities.  
  _LOCALLY_VERIFIED_ — JsonLogger key-based redaction; test_controls_ops.OpsTest.test_logger_redacts_truncates_filters_ratelimits (value-pattern redaction missing per T-13).
- [x] **M16-009** Define payload logging policy; default to no payloads for RPC data.  
  _LOCALLY_VERIFIED_ — Args/payload redacted and never logged; TELEMETRY_POLICY.md; test_logger_redacts_truncates_filters_ratelimits asserts args redacted.
- [ ] **M16-010** Redact or hash identifiers according to privacy requirements.  
  _OPEN_ — Identifiers logged raw, no hashing policy.
- [~] **M16-011** Sanitize attacker-controlled strings to prevent log forging/injection.  
  _PARTIAL_ — json.dumps escapes control chars so line forging is structurally prevented; no test (M16-025).
- [~] **M16-012** Limit stack traces to controlled debug contexts and scrub secrets.  
  _PARTIAL_ — Node never logs stack traces (callee-trap generic); test_rpc.RpcProtocolTest.test_trap_is_typed_without_exception_detail_leak for rpc.Endpoint.

### Logging behavior
- [~] **M16-013** Define severity mapping for normal rejection versus operational fault versus security event.  
  _PARTIAL_ — INFO for ok, WARNING otherwise (node.py handle); security events not distinguished; undocumented.
- [~] **M16-014** Avoid per-request info logs at high volume unless sampling is intentional.  
  _PARTIAL_ — Per-call INFO log with rate limiter; no sampling policy.
- [ ] **M16-015** Implement bounded asynchronous logging or non-blocking sink integration.  
  _OPEN_ — Logging is synchronous sink call.
- [ ] **M16-016** Define behavior on sink backpressure/disk full.  
  _OPEN_ — Undefined; sink exceptions propagate.
- [x] **M16-017** Implement rate limiting/deduplication for repetitive errors.  
  _LOCALLY_VERIFIED_ — JsonLogger rate limit; test_logger_redacts_truncates_filters_ratelimits (suppressed count). No dedup.
- [~] **M16-018** Ensure logging failures do not recursively generate unbounded logs.  
  _PARTIAL_ — Logger never logs its own failures; untested.

### Correlation
- [x] **M16-019** Correlate logs with request ID and trace/span ID.  
  _LOCALLY_VERIFIED_ — Node.handle logs request_id and trace_id; test_node_e2e.DefectRegressionTest.test_span_status_reflects_typed_error_and_logs_correlate asserts trace_id and 32-char request_id in the log record. (No span id.)
- [~] **M16-020** Correlate retries/attempts to the same logical request.  
  _PARTIAL_ — Retries reuse request_id so logs share it, but there is no attempt id/number in logs or tests.
- [ ] **M16-021** Correlate configuration/policy/key changes with audit event IDs.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No config/key change audit events.
- [ ] **M16-022** Ensure cross-host timestamps have documented synchronization assumptions.  
  _OPEN_ — No documented time sync assumptions.

### Verification
- [ ] **M16-023** Add schema validation tests for representative log events.  
  _OPEN_ — No log schema validation test.
- [~] **M16-024** Add redaction tests using known secret canaries.  
  _PARTIAL_ — Redaction test uses psk/args/token keys, not canaries in values.
- [ ] **M16-025** Add log injection tests with newline/control-character/unicode attacker input.  
  _OPEN_ — No log injection tests.
- [ ] **M16-026** Add load tests for logging overhead/backpressure.  
  _OPEN_ — No logging load tests.
- [!] **M16-027** Verify retention/export pipeline preserves structured fields.  
  _BLOCKED_ — Needs external log pipeline.

### Definition of Done / Acceptance Gates
- [~] **M16-028** Production logs are structured, schema-versioned, correlated, and bounded.  
  _PARTIAL_ — Structured, redacted, rate-bounded, now request/trace-correlated; no schema version field in log records.
- [~] **M16-029** Secret leakage tests pass.  
  _PARTIAL_ — Key-based redaction tests pass; value-based leakage untested (T-13).
- [ ] **M16-030** Log sink failure/backpressure cannot cause unbounded request latency or memory growth.  
  _OPEN_ — Synchronous sink; unbounded latency if sink blocks.
- [!] **M16-031** Operators can trace a representative request/failure across hosts using stable identifiers.  
  _BLOCKED_ — Cross-host tracing needs multiple hosts; logs also lack request/trace IDs.

## M17 — Distributed trace propagation

### Trace context model
- [~] **M17-001** Select a standard propagation format such as W3C Trace Context plus baggage where appropriate.  
  _DOCUMENTED_ — docs/REQUIREMENTS.md R-OBS-01 selects W3C traceparent (ops.parse_traceparent); baggage not addressed but item says 'where appropriate'.
- [~] **M17-002** Define trace ID, span ID, parent relationship, sampling flag, and tracestate handling.  
  _PARTIAL_ — ops.parse_traceparent/child_traceparent implement trace id/span id/sampled flag; parent span id is dropped (never exported) and tracestate is not handled or defined anywhere.
- [x] **M17-003** Specify which RPC envelope fields carry trace context.  
  _LOCALLY_VERIFIED_ — codec.encode_frame/decode_header carry a 'traceparent' header field; test_node_e2e.EndToEndTest.test_observability_emitted asserts trace id arrives server-side.
- [x] **M17-004** Validate trace header lengths/characters before use.  
  _LOCALLY_VERIFIED_ — codec.decode_header bounds traceparent to 128 ASCII bytes and ops.parse_traceparent regex-validates; test_controls_ops.OpsTest.test_traceparent asserts bad values -> None.
- [~] **M17-005** Reject or sanitize malformed propagation data without breaking the underlying RPC where policy allows.  
  _PARTIAL_ — Format-invalid ASCII traceparent is regenerated (child_traceparent), but non-ASCII or >128-byte traceparent fails the whole frame as malformed-frame (codec.py:350-355); no e2e test of either path.
- [ ] **M17-006** Define whether untrusted callers may supply trace IDs and how trust boundaries are represented.  
  _OPEN_ — No doc defines whether untrusted callers may supply trace ids; Node.handle trusts any caller traceparent including its sampled flag.
- [ ] **M17-007** Prevent caller-provided baggage from becoming an unbounded metadata channel.  
  _OPEN_ — No baggage support or policy; only traceparent is carried (bounded 128 bytes).

### Span lifecycle
- [ ] **M17-008** Create a client span for outbound calls.  
  _OPEN_ — node.Client.call only generates a traceparent (node.py:292); no client span is created or exported.
- [x] **M17-009** Create a server span for inbound calls after minimal frame validation.  
  _LOCALLY_VERIFIED_ — Node.handle opens tracer.span('inv61.handle') after decode_header; test_node_e2e.EndToEndTest.test_observability_emitted checks exported span trace id.
- [~] **M17-010** Record interface, function, protocol version, retry attempt, and bounded status metadata.  
  _PARTIAL_ — Span attrs are only interface/function (node.py:191); no protocol version, retry attempt or status metadata.
- [ ] **M17-011** Record queue wait, serialization, transport, and handler phases as child spans/events where justified.  
  _OPEN_ — No queue-wait/serialization/transport/handler child spans or events.
- [~] **M17-012** Mark deadline, cancellation, auth denial, version drift, and serialization failures with stable semantic status.  
  _PARTIAL_ — Span status now derived from outcome (status_fn) with error=<code>; only permission-denied asserted (test_node_e2e.DefectRegressionTest.test_span_status_reflects_typed_error_and_logs_correlate); cancellation has no status; deadline/version/serialization statuses untested.
- [~] **M17-013** End spans on all success/error/cancel/timeout paths.  
  _PARTIAL_ — Context manager ends span on every return path of Node.handle, but no test asserts spans end on error/timeout/cancel paths and the recorded status is wrong.
- [ ] **M17-014** Link retry attempts to the same logical operation.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Retries reuse the same traceparent/request id, but no span links or attempt attribute exist and no client span exists.

### Security/privacy controls
- [~] **M17-015** Do not place payloads, credentials, capabilities, or unrestricted user input in span attributes.  
  _PARTIAL_ — Tracer drops attrs whose key matches _REDACT_KEYS (test_controls_ops.OpsTest.test_traceparent); values are unrestricted and function/interface names come from untrusted frames.
- [~] **M17-016** Define an allow-list of attribute keys and bounded value lengths.  
  _PARTIAL_ — Tracer has max_attrs=16 and key deny-list, not an allow-list; no value length bound.
- [ ] **M17-017** Define tenant/principal trace-identification policy.  
  _OPEN_ — No tenant/principal trace-identification policy documented.
- [ ] **M17-018** Ensure baggage propagation across tenant/security boundaries is explicitly controlled.  
  _OPEN_ — No baggage; no cross-tenant propagation control documented.
- [x] **M17-019** Prevent high-cardinality request IDs from being indexed as unbounded metric dimensions even if present in traces.  
  _LOCALLY_VERIFIED_ — ops.Metrics.ALLOWED_LABELS excludes request ids; test_controls_ops.OpsTest.test_metrics_exposition_and_cardinality_cap asserts request_id label raises.

### Sampling/export
- [~] **M17-020** Define head/tail/adaptive sampling policy.  
  _PARTIAL_ — Head sampling via trace_sample_ratio exists; caller sampled flag overrides it (test_traceparent asserts 'parent's sampled flag wins'); no documented head/tail/adaptive policy.
- [ ] **M17-021** Preserve or force sampling for critical security/incident traces where approved.  
  _OPEN_ — No forced sampling for security/incident traces.
- [ ] **M17-022** Bound trace exporter queue memory and retry behavior.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Exporter is a synchronous callback; no queue, bound, or retry behavior.
- [~] **M17-023** Define behavior when collector is unavailable.  
  _PARTIAL_ — Tracer swallows exporter exceptions and counts export_failures (test_controls_ops.OpsTest.test_tracer_exporter_failure_never_fails_call); behaviour not documented in TELEMETRY_POLICY.md; synchronous exporter still blocks the call if the collector hangs.
- [!] **M17-024** Configure authenticated/encrypted trace export.  
  _BLOCKED_ — Authenticated/encrypted export needs a real collector and PKI/credentials not available to this build.
- [ ] **M17-025** Document expected tracing overhead at nominal and peak traffic.  
  _OPEN_ — No tracing-overhead figures; evidence/bench.json does not isolate tracing.

### Verification
- [!] **M17-026** Test trace propagation across at least two process/host hops.  
  _BLOCKED_ — Requires multiple hosts; test_two_process.TwoProcessTest is single-host, one hop, and asserts no trace data.
- [ ] **M17-027** Test retry/cancellation/deadline trace relationships.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No test of retry/cancel/deadline trace relationships.
- [~] **M17-028** Test malformed trace context.  
  _PARTIAL_ — test_controls_ops.OpsTest.test_traceparent checks parse_traceparent rejects bad strings; no e2e test of malformed traceparent in a frame.
- [~] **M17-029** Test no-context calls and context regeneration policy.  
  _PARTIAL_ — test_traceparent covers child_traceparent(None) generating a new trace; no policy doc and no e2e no-context call assertion.
- [~] **M17-030** Test sampling on/off paths.  
  _PARTIAL_ — test_traceparent asserts sampled flag propagation; no test that unsampled spans are not exported.
- [~] **M17-031** Verify attributes comply with cardinality/privacy policy.  
  _PARTIAL_ — Key redaction tested in test_traceparent; no privacy/cardinality review of values.
- [!] **M17-032** Validate a representative trace in the chosen backend/collector.  
  _BLOCKED_ — Needs a real trace backend/collector.

### Definition of Done / Acceptance Gates
- [!] **M17-033** Cross-host calls can be followed as one causal trace.  
  _BLOCKED_ — Needs multiple hosts and a collector.
- [~] **M17-034** Retry/error/cancellation semantics are visible and correctly linked.  
  _PARTIAL_ — Error semantics now visible in span status; retry/cancel not linked.
- [!] **M17-035** Trace metadata is bounded and privacy-reviewed.  
  _BLOCKED_ — Privacy review requires a human reviewer; bounding is also incomplete.
- [~] **M17-036** Collector failure does not break the RPC data plane.  
  _PARTIAL_ — Tracer exporter exceptions isolated (test_controls_ops.OpsTest.test_tracer_exporter_failure_never_fails_call, unit level only); a hanging exporter blocks the data plane (synchronous); log sink exceptions are NOT isolated (ops.py JsonLogger.log calls sink unguarded inside Node.handle finally).

## M18 — Telemetry retention/privacy/export policy

### Data inventory and classification
- [~] **M18-001** Enumerate every telemetry stream and exporter.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: docs/TELEMETRY_POLICY.md lists metrics/logs/traces/audit signals; exporters are not enumerated (all are injected callbacks).
- [~] **M18-002** Classify fields as operational, security, tenant metadata, personal data, secret, or prohibited.  
  _PARTIAL_ — TELEMETRY_POLICY.md gives one classification per signal, not per field, and not in the item's categories.
- [!] **M18-003** Document lawful/contractual basis for collecting sensitive fields where applicable.  
  _BLOCKED_ — Lawful/contractual basis needs legal/privacy sign-off.
- [ ] **M18-004** Mark fields that must never leave a tenant/site/region.  
  _OPEN_ — No fields marked tenant/site/region-bound.
- [ ] **M18-005** Define data residency requirements by deployment.  
  _OPEN_ — No data residency requirements defined.
- [ ] **M18-006** Maintain a schema registry or versioned telemetry dictionary.  
  _OPEN_ — No versioned telemetry schema/dictionary.

### Collection minimization
- [~] **M18-007** Collect only fields required for operational/security objectives.  
  _DOCUMENTED_ — TELEMETRY_POLICY.md 'Minimisation is enforced in code' and field table state what each signal contains.
- [x] **M18-008** Prohibit raw RPC payload collection by default.  
  _LOCALLY_VERIFIED_ — Payloads never passed to logger/tracer (node.py handle); JsonLogger redacts args/payload keys, asserted in test_controls_ops.OpsTest.test_logger_redacts_truncates_filters_ratelimits.
- [ ] **M18-009** Define hashing/pseudonymization rules for identifiers.  
  _OPEN_ — No hashing/pseudonymization rules; tenant and peer ids are logged in clear.
- [~] **M18-010** Bound free-form text fields and sanitize attacker-controlled content.  
  _PARTIAL_ — JsonLogger truncates strings to max_field (tested in test_logger_redacts_truncates_filters_ratelimits); Tracer attr values are unbounded and nothing escapes attacker-controlled content beyond JSON encoding.
- [~] **M18-011** Apply sampling before export where full fidelity is unnecessary.  
  _PARTIAL_ — Trace head sampling exists (trace_sample_ratio) but callers can force sampled=1; logs/metrics unsampled.

### Retention and deletion
- [~] **M18-012** Define retention per logs/metrics/traces/security audit class.  
  _PARTIAL_ — TELEMETRY_POLICY.md gives retention per class but explicitly as unapproved proposals.
- [ ] **M18-013** Define hot/warm/cold storage if applicable.  
  _OPEN_ — No hot/warm/cold storage definition.
- [ ] **M18-014** Define deletion/expiry enforcement and evidence.  
  _OPEN_ — No deletion/expiry enforcement mechanism or evidence.
- [ ] **M18-015** Define exception handling for legal hold/security investigations.  
  _OPEN_ — No legal-hold exception process defined.
- [!] **M18-016** Test retention enforcement in representative backends.  
  _BLOCKED_ — Needs representative telemetry backends.
- [ ] **M18-017** Document backup retention interaction.  
  _OPEN_ — Backup retention interaction not documented.

### Export governance
- [ ] **M18-018** Maintain an exporter destination allow-list.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No exporter destination allow-list; exporters are arbitrary callables.
- [!] **M18-019** Require authentication and encryption for remote exporters.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Needs remote collector and PKI/credentials.
- [ ] **M18-020** Prevent dynamic arbitrary exporter destinations in production unless policy-approved.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No control against arbitrary exporter destinations.
- [ ] **M18-021** Define proxy/firewall/network egress restrictions.  
  _OPEN_ — No egress restrictions defined.
- [!] **M18-022** Validate exporter certificates and endpoint identities.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Needs PKI/exporter certificates.
- [ ] **M18-023** Define behavior when export is unavailable or throttled.  
  _OPEN_ — Export unavailable/throttled behavior not defined (only logger local rate limit).

### Tenant/privacy isolation
- [ ] **M18-024** Enforce tenant-scoped access to tenant-specific telemetry.  
  _OPEN_ — No telemetry access control; TELEMETRY_POLICY only says tenant label is opt-in.
- [!] **M18-025** Verify dashboards/queries cannot cross tenant boundaries unintentionally.  
  _BLOCKED_ — Needs real dashboards/query backend.
- [ ] **M18-026** Define operator/admin access logging.  
  _OPEN_ — No operator/admin access logging definition.
- [~] **M18-027** Redact shared-platform telemetry where tenant identifiers are unnecessary.  
  _PARTIAL_ — Tenant metrics label is opt-in per TELEMETRY_POLICY.md, but logs always include tenant.
- [ ] **M18-028** Document support/incident access procedures.  
  _OPEN_ — No support/incident access procedure.

### Verification and review
- [~] **M18-029** Add automated secret-canary tests across all telemetry exporters.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Key-name redaction tests exist for logger and tracer (test_logger_redacts_truncates_filters_ratelimits, test_traceparent); no secret-canary test across metrics/audit/exporters or value-based detection.
- [~] **M18-030** Test high-cardinality/large-value inputs.  
  _PARTIAL_ — test_metrics_exposition_and_cardinality_cap and logger truncation test cover metrics/logs; tracer large values untested.
- [ ] **M18-031** Test export destination allow-list enforcement.  
  _OPEN_ — No allow-list to test.
- [!] **M18-032** Review telemetry schema on every material protocol change.  
  _BLOCKED_ — Recurring review needs an owner/process.
- [!] **M18-033** Perform periodic privacy/security review of retention and access.  
  _BLOCKED_ — Periodic privacy/security review needs human reviewers.

### Definition of Done / Acceptance Gates
- [!] **M18-034** Every telemetry field has an owner/classification/retention/export policy.  
  _BLOCKED_ — No per-field owner; owners UNASSIGNED.
- [~] **M18-035** Secrets and prohibited payload data are excluded by testable controls.  
  _PARTIAL_ — Key-based redaction is tested; value-pattern redaction not implemented (THREAT_MODEL T-13).
- [ ] **M18-036** Export destinations and tenant access are policy-enforced.  
  _OPEN_ — Export destinations and tenant access not policy-enforced.
- [!] **M18-037** Retention/deletion requirements are demonstrably operational.  
  _BLOCKED_ — Needs operational backends and approved retention.

## M19 — Failover, partition, split-brain, duplicate-execution controls

### Ownership/leadership model
- [~] **M19-001** Define whether INV-61 itself owns distributed work/state or delegates ownership to adjacent layers.  
  _DOCUMENTED_ — Unchanged after 4.3.0 re-check: docs/OPERATIONS.md §4: INV-61 stateless per call except idempotency cache; single-writer keys use LeaseTable.
- [~] **M19-002** If ownership exists, define authoritative owner/leader election mechanism.  
  _PARTIAL_ — controls.LeaseTable provides lease-based ownership, but it is in-memory, not wired into Node, and no election mechanism is defined.
- [x] **M19-003** Define fencing tokens/epochs for exclusive writers/executors.  
  _LOCALLY_VERIFIED_ — controls.LeaseTable fencing tokens; test_controls_ops.AdmissionBreakerLeaseTest.test_fencing_prevents_duplicate_owner_writes.
- [x] **M19-004** Reject work from stale leaders/epochs.  
  _LOCALLY_VERIFIED_ — LeaseTable.check refuses stale token; test_fencing_prevents_duplicate_owner_writes asserts check(k,t1) False after failover.
- [~] **M19-005** Define lease duration, renewal, clock assumptions, and expiration semantics.  
  _PARTIAL_ — LeaseTable has ttl and monotonic clock; renewal semantics/clock assumptions not documented.
- [ ] **M19-006** Define ownership handoff protocol and in-flight request treatment.  
  _OPEN_ — No handoff protocol or in-flight treatment.

### Partition semantics
- [ ] **M19-007** Define behavior for client↔server, server↔dependency, and multi-site partitions.  
  _OPEN_ — Partition behavior not defined.
- [ ] **M19-008** Explicitly choose consistency/availability behavior per operation class.  
  _OPEN_ — No per-operation-class CAP choice.
- [ ] **M19-009** Define whether isolated partitions may accept reads/writes.  
  _OPEN_ — Not defined.
- [~] **M19-010** Prevent dual-primary/split-brain side effects.  
  _PARTIAL_ — Fencing tokens exist but are not integrated into dispatch; OPERATIONS.md §4 admits a retry on another node can re-execute.
- [ ] **M19-011** Define quorum requirements if replicated coordination is used.  
  _OPEN_ — No quorum definition.
- [ ] **M19-012** Define stale-read tolerance where applicable.  
  _OPEN_ — Not defined.

### Failover/recovery
- [ ] **M19-013** Define failure detector and false-positive tolerance.  
  _OPEN_ — Only client CircuitBreaker; no failure detector definition.
- [ ] **M19-014** Define automatic versus operator-controlled failover triggers.  
  _OPEN_ — Not defined.
- [ ] **M19-015** Define maximum failover time and recovery objective.  
  _OPEN_ — Not defined.
- [x] **M19-016** Preserve request/idempotency state across failover where needed.  
  _LOCALLY_VERIFIED_ — ops.Journal persists idempotency outcomes; test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay asserts exec_count 0 after restart (single node only).
- [ ] **M19-017** Ensure new owner can distinguish completed, in-flight, and unknown operations.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Journal records only completed outcomes; in-flight/unknown not distinguishable.
- [ ] **M19-018** Define response semantics for calls interrupted by ownership transition.  
  _OPEN_ — Not defined.
- [ ] **M19-019** Implement graceful return-to-primary or rebalancing rules.  
  _OPEN_ — Not implemented.

### Duplicate execution prevention
- [~] **M19-020** Bind mutating operations to request/idempotency IDs and fencing epochs.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Mutations bound to (tenant, request_id) in IdempotencyCache; not bound to fencing epochs, nor to interface/function.
- [~] **M19-021** Reject stale epoch writes/dispatch.  
  _PARTIAL_ — LeaseTable.check tested in isolation; Node dispatch never checks epochs.
- [~] **M19-022** Ensure retries after failover do not execute already committed operations twice.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Single-node journal replay tested; cross-node retries re-execute (OPERATIONS.md §4).
- [ ] **M19-023** Define deduplication ledger durability/retention.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Journal has no retention/compaction; TTL applied only in memory.
- [ ] **M19-024** Test ambiguous completion at exact failover boundary.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Crash between execution and Journal.append (controls.py IdempotencyCache.run) untested and ambiguous.

### Quarantine/freeze controls
- [~] **M19-025** Implement operator-triggered quarantine for unhealthy/compromised nodes.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: LeaseTable.freeze is per-key quarantine (tested); no node-level quarantine.
- [~] **M19-026** Implement emergency freeze of mutating operations where required.  
  _PARTIAL_ — freeze per key only; no global mutating-freeze in Node.
- [ ] **M19-027** Define controlled recovery/rejoin validation.  
  _OPEN_ — No rejoin validation.
- [ ] **M19-028** Audit all quarantine/freeze/rejoin actions.  
  _OPEN_ — freeze/thaw are not audited.

### Verification
- [~] **M19-029** Inject hard node crash during request execution.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: test_server_crash_reconnect_and_journal_replay closes the server between calls, not during request execution.
- [!] **M19-030** Inject network partition between peers.  
  _BLOCKED_ — Requires multi-host network fault injection.
- [!] **M19-031** Inject asymmetric partition where each side sees different connectivity.  
  _BLOCKED_ — Requires multi-host network fault injection.
- [~] **M19-032** Inject delayed/duplicated packets/messages.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Record replay/reorder tested at record layer (test_security.ChannelTest.test_replayed_record_rejected, test_reordered_record_rejected); no delayed/duplicated message injection harness.
- [x] **M19-033** Test stale leader/fencing token rejection.  
  _LOCALLY_VERIFIED_ — test_controls_ops.AdmissionBreakerLeaseTest.test_fencing_prevents_duplicate_owner_writes.
- [!] **M19-034** Test failover under peak traffic.  
  _BLOCKED_ — Failover under peak traffic needs multiple nodes/hosts.
- [ ] **M19-035** Test failback/rebalance.  
  _OPEN_ — No failback implementation.
- [~] **M19-036** Prove no duplicate side effects for protected operation classes.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Single-node duplicate suppression proven; multi-node not implemented.

### Definition of Done / Acceptance Gates
- [ ] **M19-037** Partition/failover behavior is explicitly specified by operation class.  
  _OPEN_ — No per-operation-class spec.
- [ ] **M19-038** Split-brain cannot produce uncontrolled duplicate mutation.  
  _OPEN_ — Unchanged after 4.3.0 re-check: OPERATIONS.md §4 states cross-node re-execution is possible.
- [~] **M19-039** Fencing/deduplication controls survive restart/failover as required.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Idempotency journal survives restart; fencing tokens are in-memory and do not survive restart.
- [!] **M19-040** Failure-injection evidence demonstrates bounded recovery and correct outcomes.  
  _BLOCKED_ — Needs multi-node failure-injection infrastructure.

## M20 — Durable/restart/replay semantics for mutable state

### State inventory
- [~] **M20-001** Enumerate all mutable state: registrations, stats, sessions, replay cache, idempotency records, negotiated capabilities, queues, breaker state, config, audit buffers, etc.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: OPERATIONS.md §4 mentions idempotency cache and leases; no enumeration of registrations, stats, sessions, replay windows, config, breaker state.
- [ ] **M20-002** Classify each state item as ephemeral, reconstructable, durable, security-critical, or externally authoritative.  
  _OPEN_ — No classification of state items.
- [ ] **M20-003** Document ownership and lifecycle for each state class.  
  _OPEN_ — No lifecycle/ownership per state class.
- [ ] **M20-004** Define confidentiality/integrity requirements for persisted state.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Journal/audit files have no confidentiality/integrity requirements beyond audit hash chain.

### Stateless-service option
- [~] **M20-005** If production service is intended to be stateless, document the statelessness invariant explicitly.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: OPERATIONS.md §4 states 'stateless per call except for the idempotency cache' but not as a full invariant.
- [ ] **M20-006** Move durable responsibilities to named external systems.  
  _OPEN_ — Durable responsibilities kept in local files; no named external system.
- [~] **M20-007** Prove restart does not weaken replay/idempotency/security guarantees.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Journal replay after restart tested (test_server_crash_reconnect_and_journal_replay); replay windows reset per session by design; no proof overall and journaling is optional (journal=None default).
- [ ] **M20-008** Prove registrations/config can be deterministically reconstructed.  
  _OPEN_ — No reconstruction proof.
- [ ] **M20-009** Define whether local stats may reset and how monitoring handles resets.  
  _OPEN_ — Stats reset behavior undefined.

### Persistence design
- [~] **M20-010** Select durable storage for required state.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Local JSONL files (ops.Journal, ops.AuditLog) chosen implicitly; not a documented selection.
- [~] **M20-011** Define transactional boundaries and crash-consistency model.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Journal fsyncs per append; crash-consistency model undocumented and memory is updated before fsync.
- [~] **M20-012** Define write-ahead/checkpoint strategy where necessary.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Append-only fsync'd journal; no checkpoint/compaction.
- [~] **M20-013** Include schema version in persisted records.  
  _PARTIAL_ — Journal records now carry v=INV61_JOURNAL/2 and replay rejects unknown schemas (ops.Journal); audit log records carry no schema version; unknown-schema rejection untested.
- [ ] **M20-014** Define encryption-at-rest and access controls.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No encryption at rest; journal stores outcomes in cleartext.
- [ ] **M20-015** Define retention/compaction/garbage collection.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Journal grows unbounded; TTL is only in memory.
- [ ] **M20-016** Define maximum recovery dataset and recovery-time target.  
  _OPEN_ — Not defined.

### Restart/recovery semantics
- [ ] **M20-017** Define cold start, graceful restart, crash restart, and version-upgrade recovery paths.  
  _OPEN_ — Not defined.
- [~] **M20-018** Reconstruct registrations/policy/config before readiness.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: IdempotencyCache replays journal in constructor before Node.start; no readiness gating on config/registration reconstruction.
- [x] **M20-019** Restore replay/idempotency state before accepting retriable mutations if required.  
  _LOCALLY_VERIFIED_ — IdempotencyCache.__init__ replays journal before serving; test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay.
- [x] **M20-020** Detect partial/corrupt checkpoints and fail safely.  
  _LOCALLY_VERIFIED_ — ops.Journal.replay tolerates torn tail, fails closed mid-file; test_controls_ops.IdempotencyRetryTest.test_journal_survives_restart_and_torn_tail.
- [ ] **M20-021** Define migration procedure for persisted schema changes.  
  _OPEN_ — No migration procedure.
- [ ] **M20-022** Prevent downgrade from opening data with unsupported newer schema unless explicitly safe.  
  _OPEN_ — No schema version so downgrade cannot be prevented.

### Backup/restore
- [ ] **M20-023** Define whether state requires backup beyond replication.  
  _OPEN_ — Not defined.
- [ ] **M20-024** Define backup frequency, retention, encryption, and integrity checks.  
  _OPEN_ — Not defined.
- [ ] **M20-025** Perform automated restore tests.  
  _OPEN_ — No restore tests.
- [ ] **M20-026** Document RPO/RTO.  
  _OPEN_ — No RPO/RTO.
- [ ] **M20-027** Validate recovery after total local storage loss if applicable.  
  _OPEN_ — Not validated.

### Verification
- [~] **M20-028** Crash process at controlled points during state mutation.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Torn-write simulated by appending a partial line (test_journal_survives_restart_and_torn_tail); no real process kill at controlled points.
- [~] **M20-029** Restart and verify invariants.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Journal/audit restart invariants tested (test_server_crash_reconnect_and_journal_replay, test_audit_log_survives_restart_and_verifies); not a general invariant check.
- [x] **M20-030** Test corrupted/truncated state records.  
  _LOCALLY_VERIFIED_ — test_controls_ops.IdempotencyRetryTest.test_journal_survives_restart_and_torn_tail (torn + corrupt), OpsTest.test_audit_chain_detects_edit_delete_reorder_truncate.
- [ ] **M20-031** Test schema migration forward and rollback constraints.  
  _OPEN_ — No schema versioning to migrate.
- [~] **M20-032** Test restored state against replay/idempotency semantics.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Journal-restored dedup tested; TTL of restored entries and cross-function key collisions untested.
- [!] **M20-033** Test concurrent restart across multiple nodes.  
  _BLOCKED_ — Requires multiple nodes/hosts.

### Definition of Done / Acceptance Gates
- [ ] **M20-034** Every mutable state item has documented durability/reconstruction semantics.  
  _OPEN_ — No per-item durability doc.
- [~] **M20-035** Restart cannot silently weaken security or duplicate-execution guarantees.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Optional journal only; default Node (journal=None) loses idempotency on restart, and overloaded outcomes are cached (defect).
- [~] **M20-036** Crash recovery and, where applicable, backup restore are automated and tested.  
  _PARTIAL_ — Crash recovery partially tested; no backup/restore.
- [ ] **M20-037** Recovery time/data-loss characteristics meet documented objectives.  
  _OPEN_ — No objectives documented.

## M21 — Requirements specification and traceability matrix

### Normative requirements
- [~] **M21-001** Create a requirements specification with stable IDs (for example RPC-REQ-0001...).  
  _DOCUMENTED_ — docs/REQUIREMENTS.md has stable IDs R-FRAME-01..R-DEP-01.
- [~] **M21-002** Use `MUST`, `SHOULD`, and `MAY` consistently.  
  _DOCUMENTED_ — docs/REQUIREMENTS.md uses RFC 2119 MUST/SHOULD/MAY.
- [~] **M21-003** Ensure every requirement is atomic and objectively verifiable.  
  _PARTIAL_ — Several rows bundle multiple clauses (e.g. R-AUTHZ-01, R-OBS-01, R-CONF-01) - not atomic.
- [ ] **M21-004** Separate functional, security, reliability, performance, compatibility, operations, and governance requirements.  
  _OPEN_ — Requirements are a single table, not separated by category.
- [~] **M21-005** Define assumptions and out-of-scope boundaries.  
  _PARTIAL_ — ADR-0001 Context notes excluded transport encryption/discovery; no assumptions/out-of-scope section.
- [ ] **M21-006** Define glossary for terms such as endpoint, peer, principal, request, attempt, interface version, signature fingerprint, deadline, and capability.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No glossary.

### Protocol/lifecycle specification
- [ ] **M21-007** Define client/server state machines.  
  _OPEN_ — No client/server state machines documented.
- [~] **M21-008** Define request/response lifecycle from creation through completion/cancel/timeout.  
  _PARTIAL_ — REQUIREMENTS.md 'Precedence of checks' covers server receive order; no full lifecycle incl. cancel.
- [ ] **M21-009** Define registration lifecycle.  
  _OPEN_ — Not defined.
- [~] **M21-010** Define negotiation lifecycle.  
  _PARTIAL_ — R-NEG-01/02 only; no lifecycle.
- [~] **M21-011** Define authentication/authorization sequence.  
  _PARTIAL_ — R-AUTHN-01 and precedence list order authn before authz; no sequence spec.
- [~] **M21-012** Define retry/reconnect/failover interactions.  
  _PARTIAL_ — R-RETRY-01, R-BREAK-01; failover interaction undefined.
- [~] **M21-013** Define drain/shutdown behavior.  
  _DOCUMENTED_ — docs/OPERATIONS.md §2 and REQUIREMENTS.md R-LIFE-01 define drain: fail readiness, refuse connections, answer 'unavailable', wait for in-flight, then stop() tears down sessions.

### Failure taxonomy
- [~] **M21-014** Define stable error/status code namespace.  
  _DOCUMENTED_ — REQUIREMENTS.md 'Failure taxonomy (PK_WRPC_ERROR/1)'.
- [~] **M21-015** Classify caller, protocol, auth, authorization, overload, timeout, cancellation, dependency, internal, and transport failures.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Taxonomy lists codes but does not classify them into the item's categories.
- [~] **M21-016** Define retryability for each code.  
  _DOCUMENTED_ — Unchanged after 4.3.0 re-check: REQUIREMENTS.md taxonomy: 'Retryable: overloaded, transport, circuit-open, unavailable'.
- [~] **M21-017** Define what details may be exposed to remote callers.  
  _PARTIAL_ — Precedence section limits authz leakage; no general client-visible detail policy.
- [ ] **M21-018** Define operator diagnostic mapping separate from client-visible errors.  
  _OPEN_ — No operator diagnostic mapping.

### Conflict/precedence model
- [ ] **M21-019** Define precedence among security, safety, residency, correctness, availability, latency/SLO, and cost requirements.  
  _OPEN_ — No precedence among security/safety/residency/etc.
- [~] **M21-020** Document fail-open/fail-closed decisions for each critical dependency.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Health.ready fails on critical dependency (ops.Health); no per-dependency fail-open/closed doc.
- [ ] **M21-021** Define behavior when policy conflicts with requested compatibility/performance modes.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Not defined.
- [~] **M21-022** Capture unresolved tradeoffs as ADRs/risk records.  
  _PARTIAL_ — ADR-0001 exists (PROPOSED); open tradeoffs listed in OPERATIONS.md §7 debt register, not as ADRs/risk records.

### Traceability matrix
- [ ] **M21-023** Map each C001–C100 checklist control to one or more normative requirements.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No mapping of C001-C100 controls to requirements (CHECKLIST_STATUS.json referenced but absent).
- [~] **M21-024** Map each requirement to implementation module/path.  
  _DOCUMENTED_ — REQUIREMENTS.md 'Code' column maps each R- id to a module/symbol.
- [~] **M21-025** Map each requirement to one or more tests/evidence artifacts.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: REQUIREMENTS.md 'Test' column exists, but some ids are wildcards/partial (test_metrics_*, HandshakeTest.*) and the claimed checker tools/checklist_status.py does not exist.
- [~] **M21-026** Map security requirements to threat/abuse cases.  
  _PARTIAL_ — THREAT_MODEL.md maps threats to tests, not to R- ids.
- [~] **M21-027** Map SLO requirements to benchmarks/metrics/alerts.  
  _PARTIAL_ — OPERATIONS.md §3 proposes alerts; not mapped to requirement ids.
- [~] **M21-028** Detect requirements with no implementation or no test automatically.  
  _PARTIAL_ — tools/checklist_status.py --check detects missing cited test ids, but it has never run successfully: CHECKLIST_STATUS.json is absent and --check crashes with FileNotFoundError; no test of the tool.
- [ ] **M21-029** Detect tests with no linked requirement where traceability is expected.  
  _OPEN_ — No such detection.

### Review/change control
- [!] **M21-030** Require review/approval for normative requirement changes.  
  _BLOCKED_ — Needs an approver; owners UNASSIGNED.
- [~] **M21-031** Version the requirements schema/document.  
  _PARTIAL_ — Title says v4.3.0; no schema/document version field or history.
- [~] **M21-032** Maintain change history and compatibility impact.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: CHANGELOG.md exists at root; no requirement-level compatibility impact.
- [ ] **M21-033** Re-run impacted verification automatically based on requirement tags where practical.  
  _OPEN_ — No tag-based re-run.

### Definition of Done / Acceptance Gates
- [ ] **M21-034** All production behavior is covered by uniquely identified normative requirements.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Many behaviors (tracing status, leases, journal) lack requirements.
- [!] **M21-035** Every requirement has implementation and verification evidence or an approved waiver.  
  _BLOCKED_ — Waivers require an approver; waiver register empty.
- [~] **M21-036** Failure semantics and requirement-precedence rules are explicit.  
  _PARTIAL_ — Check precedence explicit; requirement precedence (M21-019) absent.
- [~] **M21-037** CI can report orphaned/unverified requirements.  
  _PARTIAL_ — Checker exists (tools/checklist_status.py) and CI release-gate calls it, but it crashes today (no CHECKLIST_STATUS.json) and CI is not executed (BLOCKED part); it does not report requirements lacking implementation.

## M22 — Owner, escalation path, and approved architecture decision record

### Ownership
- [!] **M22-001** Name the service/component owner role/team.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-002** Name security, operations/SRE, and protocol/schema owners.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-003** Define code ownership/reviewer requirements for critical paths.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-004** Define on-call or incident ownership for production deployments.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-005** Define dependency ownership for `pk_core`, identity, policy, transport, and observability integrations.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-006** Record ownership in repository metadata (`CODEOWNERS`, service catalog, or equivalent).  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.

### Escalation
- [~] **M22-007** Define severity levels and response expectations.  
  _PARTIAL_ — docs/OPERATIONS.md §6 Incidents defines SEV1-SEV3; response expectations are not given (partial on SLA).
- [!] **M22-008** Define primary and secondary escalation paths.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-009** Define security-incident escalation separately if required.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-010** Define after-hours/on-call contact mechanism without embedding personal secrets in source.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [ ] **M22-011** Define escalation for dependency/vendor failures.  
  _OPEN_ — No dependency/vendor escalation defined.
- [!] **M22-012** Link alerts/runbooks to owning team.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.

### Architecture Decision Record
- [~] **M22-013** Create ADR describing the problem/context solved by distributed WIT RPC.  
  _DOCUMENTED_ — docs/ADR-0001-wire-and-security.md Context section.
- [~] **M22-014** Document considered alternatives and why they were accepted/rejected.  
  _DOCUMENTED_ — ADR-0001 'Alternatives considered' (mTLS, Noise, status quo).
- [~] **M22-015** Document transport, WIT/component-model, versioning, auth, authorization, retry, state, and observability choices.  
  _PARTIAL_ — ADR-0001 covers transport, auth, versioning; not WIT/component-model, authorization, retry, state, observability.
- [~] **M22-016** Document assumptions and constraints.  
  _PARTIAL_ — ADR-0001 context implies constraints; no explicit assumptions section.
- [~] **M22-017** Document security/privacy implications.  
  _PARTIAL_ — ADR-0001 Consequences notes PSK/no forward secrecy; no privacy implications.
- [ ] **M22-018** Document performance/capacity expectations.  
  _OPEN_ — No performance/capacity expectations in ADR.
- [~] **M22-019** Document dependencies on INV-11/36/60/65 and ownership boundaries.  
  _PARTIAL_ — ADR-0001 mentions INV-36/INV-11/INV-60; INV-65 boundary not documented.
- [~] **M22-020** Document consequences, unresolved risks, and future migration triggers.  
  _PARTIAL_ — ADR-0001 Consequences lists risks; no migration triggers.
- [!] **M22-021** Obtain named role-based approval/review.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.

### Governance
- [ ] **M22-022** Define ADR supersession/change process.  
  _OPEN_ — No supersession process.
- [!] **M22-023** Review ownership and escalation data periodically.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-024** Ensure release/incident processes reference the current ADR and owners.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-025** Define succession/handover procedure when teams change.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.

### Definition of Done / Acceptance Gates
- [!] **M22-026** Production responsibility is unambiguous across engineering, security, and operations.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-027** An approved ADR captures architectural rationale and tradeoffs.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-028** Alerts/incidents have a documented escalation destination.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.
- [!] **M22-029** Ownership metadata is versioned and periodically reviewed.  
  _BLOCKED_ — Owner/approver roles are UNASSIGNED (ADR-0001, OPERATIONS.md §6); needs a human owner.

## M23 — Security architecture and adversarial test suite

### Threat model
- [~] **M23-001** Define assets: code execution, tenant data, credentials, capabilities, protocol integrity, availability, audit trail, configuration, and control plane.  
  _PARTIAL_ — THREAT_MODEL.md lists 5 assets; missing credentials, capabilities, configuration, telemetry etc.
- [ ] **M23-002** Draw trust boundaries for client, transport, endpoint, policy engine, identity provider, state store, telemetry, and operators.  
  _OPEN_ — No trust-boundary diagram/enumeration.
- [~] **M23-003** Enumerate attacker classes: unauthenticated remote, authenticated low-privilege, compromised workload, malicious tenant, insider/operator, network attacker, compromised dependency.  
  _PARTIAL_ — THREAT_MODEL.md lists 5 adversaries; missing compromised workload, malicious tenant distinct classes, supply chain.
- [ ] **M23-004** Use STRIDE, attack trees, or equivalent systematic methodology.  
  _OPEN_ — No STRIDE/attack-tree methodology stated.
- [~] **M23-005** Include spoofing, tampering, repudiation, information disclosure, denial of service, elevation of privilege, replay, downgrade, confused deputy, and supply-chain threats.  
  _PARTIAL_ — Covers spoofing/tampering/replay/downgrade/DoS; no repudiation analysis beyond audit, no confused deputy/EoP.
- [~] **M23-006** Map each threat to mitigations and verification evidence.  
  _PARTIAL_ — THREAT_MODEL.md maps T-01..T-14 to controls and tests; T-12 has none.
- [~] **M23-007** Record residual risk and owner.  
  _PARTIAL_ — Residual column present; owners UNASSIGNED.
- [!] **M23-008** Review threat model on protocol/architecture changes.  
  _BLOCKED_ — Review cadence needs owner/reviewer.

### Protocol abuse cases
- [x] **M23-009** Malformed frame field sets.  
  _LOCALLY_VERIFIED_ — test_wit_codec.CodecTest.test_negative_paths, PropertyAndFuzzTest.test_header_fuzz; test_node_e2e.AdversarialTest.test_malformed_frame_inside_valid_session.
- [~] **M23-010** Unknown/duplicate fields where schema disallows them.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Binary envelope has fixed field order so duplicates impossible; handshake dict variants tested in test_security.HandshakeTest.test_malformed_hello_variants; no explicit unknown/duplicate field test for dict frames beyond rpc tests.
- [x] **M23-011** Oversized lengths and integer overflows.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_hostile_length_prefix_does_not_allocate, AdversarialTest.test_oversize_length_prefix_refused_without_allocation, CodecTest.test_signed_extremes.
- [~] **M23-012** Deep nesting and decompression/expansion bombs if compression exists.  
  _PARTIAL_ — Depth limit 32 in codec.Reader (R-CODEC-02) but no test exercises max-depth rejection; no compression exists.
- [x] **M23-013** Signature/version/interface spoofing.  
  _LOCALLY_VERIFIED_ — test_node_e2e.EndToEndTest.test_signature_drift_rejected_before_args_decoded, test_version_drift_rejected; test_security.NegotiationTest.test_downgrade_by_mitm_is_detected.
- [x] **M23-014** Deadline extremes, NaN/infinity, negative or far-future values.  
  _LOCALLY_VERIFIED_ — test_rpc.RpcProtocolTest.test_nonfinite_or_boolean_clock_fails_closed, test_node_e2e.AdversarialTest.test_expired_deadline_never_dispatches; codec.decode_header rejects non-finite deadline. Far-future deadlines are accepted unbounded.
- [x] **M23-015** Duplicate request/replay sequences.  
  _LOCALLY_VERIFIED_ — test_security.ChannelTest.test_replayed_record_rejected, test_node_e2e.AdversarialTest.test_record_replay_on_live_session_kills_session, EndToEndTest.test_retry_with_same_request_id_executes_once.
- [~] **M23-016** Truncation, concatenation, smuggling, and partial-frame delivery.  
  _PARTIAL_ — Truncation covered by mutation fuzz (test_mutation_fuzz_only_raises_codec_error); no concatenation/partial-frame-delivery socket test.
- [~] **M23-017** Invalid UTF-8/type discriminants/resource handles.  
  _PARTIAL_ — test_wit_codec.CodecTest.test_negative_paths covers UTF-8/discriminants; resource handles unsupported (rejected by wit.py).

### Identity/authorization abuse cases
- [x] **M23-018** Anonymous access to protected methods.  
  _LOCALLY_VERIFIED_ — test_node_e2e.EndToEndTest.test_authorization_default_deny_and_tenant_isolation, AdversarialTest.test_unknown_peer_and_unenrolled_peer.
- [x] **M23-019** Wrong tenant/principal/capability.  
  _LOCALLY_VERIFIED_ — test_controls_ops.AuthorizerTest.test_no_cross_tenant_glob_and_expiry_and_revoke, test_authorization_default_deny_and_tenant_isolation.
- [x] **M23-020** Expired/revoked/forged credentials.  
  _LOCALLY_VERIFIED_ — test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code, test_forged_client_finish_rejected.
- [ ] **M23-021** Capability replay/delegation escalation.  
  _OPEN_ — No capability/delegation model exists.
- [ ] **M23-022** Confused-deputy attempts through indirect calls.  
  _OPEN_ — No confused-deputy test.
- [ ] **M23-023** Policy-engine outage/stale cache manipulation.  
  _OPEN_ — Authorizer is in-process; no external policy engine/cache.
- [~] **M23-024** Cross-tenant resource reference attacks.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Tenant-scoped idempotency key tested (test_ttl_expiry_and_tenant_scoping); idempotency key ignores interface/function so same-tenant request-id reuse across functions returns another function's result (defect).

### Resource-exhaustion abuse cases
- [x] **M23-025** Slowloris/slow reader/writer behavior.  
  _LOCALLY_VERIFIED_ — test_node_e2e.AdversarialTest.test_slowloris_handshake_times_out (idle timeout for slow reader/writer post-handshake not tested).
- [~] **M23-026** Connection floods and handshake floods.  
  _PARTIAL_ — test_node_e2e.AdversarialTest.test_connection_limit; no handshake-flood rate test or per-IP limits (T-08).
- [x] **M23-027** Request floods per tenant/principal.  
  _LOCALLY_VERIFIED_ — controls.Admission per_tenant; test_controls_ops.AdmissionBreakerLeaseTest.test_admission_bounds_and_per_tenant_fairness, FaultInjectionTest.test_overload_sheds_with_typed_error.
- [x] **M23-028** Queue saturation.  
  _LOCALLY_VERIFIED_ — Admission max_queue; test_admission_bounds_and_per_tenant_fairness, test_admission_queue_wakes_waiter.
- [~] **M23-029** Large payload/string/list/nesting attacks.  
  _PARTIAL_ — Length bounds tested (test_hostile_length_prefix_does_not_allocate); nesting-depth limit untested.
- [~] **M23-030** Trace/log cardinality and telemetry amplification attacks.  
  _PARTIAL_ — Metric series cap tested (test_metrics_exposition_and_cardinality_cap), logger rate limit tested; caller can force trace sampling (amplification) untested.
- [x] **M23-031** Retry storm and circuit-breaker thrash attacks.  
  _LOCALLY_VERIFIED_ — test_controls_ops.IdempotencyRetryTest.test_retry_budget_caps_amplification, AdmissionBreakerLeaseTest.test_breaker_state_machine.

### Secure implementation review
- [ ] **M23-032** Run SAST/linting suitable for Python and native/Wasm adjuncts.  
  _OPEN_ — No SAST/lint configured or evidenced.
- [ ] **M23-033** Scan for unsafe deserialization, command execution, path injection, temp-file misuse, secret handling, and insecure randomness.  
  _OPEN_ — No scan evidence.
- [~] **M23-034** Review exception handling for information disclosure.  
  _PARTIAL_ — test_rpc.RpcProtocolTest.test_trap_is_typed_without_exception_detail_leak; no documented review.
- [!] **M23-035** Review cryptographic API use.  
  _BLOCKED_ — Cryptographic API review requires an independent reviewer (THREAT_MODEL.md: not performed).
- [!] **M23-036** Review concurrency/state synchronization for security invariant races.  
  _BLOCKED_ — Independent review not available; ConcurrencyTest exists but is not a review.
- [!] **M23-037** Review dependency provenance/vulnerabilities.  
  _BLOCKED_ — Package index unreachable; hashes not recorded (DEPENDENCIES.md).

### Adversarial test automation
- [x] **M23-038** Encode abuse cases as repeatable tests, not only manual review notes.  
  _LOCALLY_VERIFIED_ — Abuse cases are executable: test_node_e2e.AdversarialTest.test_oversize_length_prefix_refused_without_allocation, test_node_e2e.AdversarialTest.test_slowloris_handshake_times_out, test_security.NegotiationTest.test_downgrade_by_mitm_is_detected (+ THREAT_MODEL.md table).
- [!] **M23-039** Run security suite in CI for changes to protocol/auth/policy/transport.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: CI workflow committed but not executed (no CI runner); also no path-filtered security job.
- [!] **M23-040** Add periodic deeper fuzz/chaos/security campaigns.  
  _BLOCKED_ — Needs long-running fuzz/chaos infrastructure.
- [ ] **M23-041** Preserve regression inputs for discovered vulnerabilities.  
  _OPEN_ — No regression-input corpus directory.
- [~] **M23-042** Tag security tests to threat IDs and requirements.  
  _PARTIAL_ — THREAT_MODEL.md maps T-ids to tests; tests are not tagged with threat/requirement ids.

### Definition of Done / Acceptance Gates
- [~] **M23-043** Threat model covers all production trust boundaries and attacker classes.  
  _PARTIAL_ — Several boundaries (telemetry, operators, state store) and attacker classes missing.
- [!] **M23-044** Every high/critical threat has a tested mitigation or approved risk acceptance.  
  _BLOCKED_ — T-11/T-12 open; risk acceptance needs an approver.
- [!] **M23-045** Adversarial protocol/identity/authorization/resource tests run automatically.  
  _BLOCKED_ — Automatic execution needs a real CI runner.
- [!] **M23-046** No known critical/high unresolved security findings remain at production exit.  
  _BLOCKED_ — Needs independent security review (not performed).

## M24 — Parser/protocol fuzzing and property tests

### Fuzz target design
- [~] **M24-001** Create raw-byte decoder fuzz target at the earliest network parser boundary.  
  _PARTIAL_ — test_wit_codec.PropertyAndFuzzTest.test_header_fuzz mutates decode_header only (single-byte flips); the socket length-prefix/record/handshake parsers are not fuzzed.
- [ ] **M24-002** Create RPC envelope/state-machine fuzz target.  
  _OPEN_ — No envelope/state-machine fuzz target.
- [x] **M24-003** Create WIT value decoder fuzz target.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error fuzzes codec.decode_args (seeded, 3000 mutations).
- [ ] **M24-004** Create negotiation/version parser fuzz target.  
  _OPEN_ — No negotiation/version parser fuzz target (only handcrafted test_malformed_hello_variants).
- [~] **M24-005** Create authentication metadata parser fuzz target if custom parsing exists.  
  _PARTIAL_ — Handshake JSON parsing has hand-written negatives (test_security.HandshakeTest.test_malformed_hello_variants), no fuzz target.
- [x] **M24-006** Avoid mocks that bypass the real parser logic under test.  
  _LOCALLY_VERIFIED_ — Fuzz tests drive the real codec.decode_args/decode_header, no mocks: test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error, test_wit_codec.PropertyAndFuzzTest.test_header_fuzz.
- [x] **M24-007** Make fuzz targets deterministic and side-effect isolated.  
  _LOCALLY_VERIFIED_ — Seeded random.Random(SEED), pure functions, no I/O: test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error.

### Invariants/properties
- [~] **M24-008** Parser never crashes the process on arbitrary bytes.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: test_mutation_fuzz_only_raises_codec_error/test_header_fuzz assert only CodecError escapes, for 3000 cases; not arbitrary bytes and not long-run.
- [~] **M24-009** Parser never allocates beyond configured hard limits for bounded input.  
  _PARTIAL_ — test_hostile_length_prefix_does_not_allocate covers one case; no memory measurement under fuzz.
- [x] **M24-010** Invalid input never reaches user dispatch.  
  _LOCALLY_VERIFIED_ — test_node_e2e.EndToEndTest.test_signature_drift_rejected_before_args_decoded and AdversarialTest.test_malformed_frame_inside_valid_session / test_expired_deadline_never_dispatches assert no dispatch.
- [x] **M24-011** `decode(encode(x)) == x` for supported canonical values.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_round_trip_property (encode(decode(encode(x)))==encode(x)) and CodecTest.test_round_trip_and_canonical.
- [x] **M24-012** Accepted non-canonical encodings either normalize deterministically or are rejected according to spec.  
  _LOCALLY_VERIFIED_ — test_mutation_fuzz_only_raises_codec_error asserts every accepted mutation re-encodes identically; test_nan_is_canonicalised_and_foreign_nan_rejected.
- [x] **M24-013** Re-encoding a decoded canonical value produces identical bytes.  
  _LOCALLY_VERIFIED_ — test_wit_codec.PropertyAndFuzzTest.test_round_trip_property, test_mutation_fuzz_only_raises_codec_error.
- [ ] **M24-014** Error classification is stable for equivalent malformed cases.  
  _OPEN_ — No test that equivalent malformed inputs yield the same error code.
- [ ] **M24-015** Deadline/version/signature validation invariants hold across generated cases.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No generated-case property tests for deadline/version/signature validation.
- [~] **M24-016** Unauthorized/unverified input cannot change authorization-relevant context.  
  _PARTIAL_ — Tenant bound to authenticated peer (test_authorization_default_deny_and_tenant_isolation); not property-tested.

### Corpus and dictionaries
- [~] **M24-017** Seed corpus with all golden valid frames.  
  _PARTIAL_ — fixtures/golden_vectors.json used in test_golden_vectors, but fuzz seeds are randomly generated, not the golden frames.
- [ ] **M24-018** Seed corpus with known malformed/truncated/oversized cases.  
  _OPEN_ — No malformed seed corpus.
- [ ] **M24-019** Add protocol tokens/field names/type tags to fuzzer dictionary where helpful.  
  _OPEN_ — No fuzzer dictionary.
- [ ] **M24-020** Preserve minimized reproducer inputs for every discovered defect.  
  _OPEN_ — No reproducer storage.
- [ ] **M24-021** Version corpus alongside protocol changes.  
  _OPEN_ — No corpus to version.

### Resource controls
- [ ] **M24-022** Configure timeout/CPU budget per fuzz case.  
  _OPEN_ — No per-case timeout.
- [ ] **M24-023** Configure memory/allocator limits.  
  _OPEN_ — No memory limits configured.
- [ ] **M24-024** Detect pathological super-linear parser behavior.  
  _OPEN_ — No super-linear detection.
- [ ] **M24-025** Track coverage of parsing/state-machine branches.  
  _OPEN_ — No coverage tracking.
- [x] **M24-026** Prevent fuzz harness from making real network/external-service calls.  
  _LOCALLY_VERIFIED_ — Codec fuzz targets are pure in-memory: test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error, test_wit_codec.PropertyAndFuzzTest.test_header_fuzz.

### CI and campaign policy
- [!] **M24-027** Run a short deterministic fuzz smoke gate in normal CI.  
  _BLOCKED_ — Seeded fuzz runs in unittest, but CI is not executed (no runner).
- [!] **M24-028** Run longer scheduled fuzz campaigns.  
  _BLOCKED_ — Needs scheduled long-running fuzz infrastructure.
- [~] **M24-029** Run sanitizer/instrumented builds for native components if any exist.  
  _DOCUMENTED_ — No native components exist (pure Python + cryptography wheel); not applicable - DEPENDENCIES.md lists only cryptography/cffi.
- [!] **M24-030** Define crash triage owner and SLA.  
  _BLOCKED_ — Needs an owner (UNASSIGNED).
- [!] **M24-031** Fail release on unresolved reproducible parser crash/security invariant violation.  
  _BLOCKED_ — Release gate needs CI runner and owner.
- [ ] **M24-032** Track coverage and unique crash history over time.  
  _OPEN_ — No history tracking.

### Property-based tests
- [~] **M24-033** Generate structured valid/invalid frames across boundary values.  
  _PARTIAL_ — Random structured values via _random_value; boundary values only in CodecTest.test_signed_extremes; no invalid-frame generator.
- [ ] **M24-034** Generate nested WIT values up to configured depth limits.  
  _OPEN_ — No generator targeting depth limit.
- [ ] **M24-035** Generate version negotiation combinations.  
  _OPEN_ — No generated negotiation combinations.
- [ ] **M24-036** Generate request/retry/replay sequences against a state model.  
  _OPEN_ — No stateful model-based tests.
- [ ] **M24-037** Shrink failing cases automatically and add regressions.  
  _OPEN_ — No shrinking.

### Definition of Done / Acceptance Gates
- [~] **M24-038** Network/WIT/protocol parsers have active fuzz targets and maintained corpora.  
  _PARTIAL_ — Seconds-long in-test fuzzing of codec only; no maintained corpora.
- [x] **M24-039** Critical parser invariants are encoded as machine-checked properties.  
  _LOCALLY_VERIFIED_ — Round-trip, canonical re-encode and only-CodecError properties: test_wit_codec.PropertyAndFuzzTest.test_round_trip_property, test_wit_codec.PropertyAndFuzzTest.test_mutation_fuzz_only_raises_codec_error.
- [!] **M24-040** CI/scheduled campaigns run within defined resource budgets.  
  _BLOCKED_ — Needs CI runner/scheduled infrastructure.
- [ ] **M24-041** All discovered crashes/invariant violations are reproducible, minimized, and regression-tested.  
  _OPEN_ — No reproducer/regression process.

## M25 — Concurrency and race-condition tests

### Concurrency model
- [~] **M25-001** Declare whether the endpoint is single-threaded, multi-threaded, async-task based, multi-process, or supports multiple execution modes.  
  _PARTIAL_ — Code is threaded (node.py thread-per-connection) but no doc declares the concurrency model.
- [ ] **M25-002** Define which objects are immutable and which are shared mutable state.  
  _OPEN_ — No doc defines immutable vs shared mutable state.
- [ ] **M25-003** Define ownership for export registry, endpoint statistics, replay/idempotency caches, breaker state, config references, and connection/session state.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No ownership definition for registry/stats/caches/breaker/config/session state in docs.
- [ ] **M25-004** Identify every lock, atomic primitive, queue, event, and synchronization boundary.  
  _OPEN_ — Locks exist throughout (rpc.Endpoint._lock, controls.*._lock, node._conns_lock) but no inventory document.
- [ ] **M25-005** Document lock ordering to prevent deadlock.  
  _OPEN_ — No lock-ordering documentation.
- [ ] **M25-006** Define whether handler functions may re-enter the endpoint or register/unregister functions during execution.  
  _OPEN_ — Re-entrancy/registration-during-execution not defined.
- [~] **M25-007** Define safe shutdown/drain interaction with active requests.  
  _PARTIAL_ — OPERATIONS.md §2 now defines drain vs in-flight; implementation has a race: TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested.
- [~] **M25-008** Define safe config reload interaction with active requests.  
  _PARTIAL_ — ConfigStore.activate swaps atomically under lock but Node copies cfg at construction; no doc on reload vs active requests.

### Implementation hardening
- [x] **M25-009** Protect `EndpointStats` mutation with a concurrency-safe strategy or redesign it for per-thread/per-task aggregation.  
  _LOCALLY_VERIFIED_ — rpc.py::Endpoint._count under lock; test_controls_ops.ConcurrencyTest.test_endpoint_stats_exact_under_threads.
- [~] **M25-010** Ensure export registration/lookup cannot observe partially constructed entries.  
  _PARTIAL_ — rpc.Endpoint.export inserts full tuple under lock, but lookup in handle() is unlocked and no test targets partial observation.
- [x] **M25-011** Ensure duplicate-export detection is atomic under concurrent registration.  
  _LOCALLY_VERIFIED_ — rpc.py::Endpoint.export under lock; test_controls_ops.ConcurrencyTest.test_concurrent_export_duplicate_detected_once.
- [ ] **M25-012** Ensure unregister/replace operations, if introduced, are linearizable or explicitly versioned.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No unregister/replace exists and no versioning policy stated (Authorizer.revoke exists but not linearizability-tested).
- [~] **M25-013** Prevent use-after-close of sessions/transports during shutdown.  
  _PARTIAL_ — Node.stop shuts down tracked conns under _conns_lock; no test for use-after-close; Client.close not locked against concurrent call.
- [ ] **M25-014** Prevent response completion after request state has been destroyed/reused.  
  _OPEN_ — No guard or test for response after request state destroyed.
- [~] **M25-015** Ensure cancellation state is safely visible across worker contexts.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: controls.CancelToken uses threading.Event but is not wired into Node/Client; test_controls_ops.IdempotencyRetryTest.test_cancel_token is single-threaded.
- [~] **M25-016** Avoid holding global locks while invoking user-supplied handlers.  
  _PARTIAL_ — Node.handle invokes impl without global lock, but Client.call holds self._lock across network I/O; not documented/tested.
- [ ] **M25-017** Bound lock wait time or expose lock contention metrics where relevant.  
  _OPEN_ — No lock wait bounds or contention metrics.

### Race test scenarios
- [~] **M25-018** Dispatch many concurrent calls to the same export.  
  _PARTIAL_ — ConcurrencyTest.test_endpoint_stats_exact_under_threads covers in-process rpc.Endpoint only; no concurrent same-export test on Node; soak (evidence/soak.json) runs 8 clients but asserts little.
- [ ] **M25-019** Dispatch concurrent calls across many exports/interfaces.  
  _OPEN_ — No concurrent multi-export/multi-interface test.
- [x] **M25-020** Concurrently register the same export from multiple workers and prove only one wins.  
  _LOCALLY_VERIFIED_ — test_controls_ops.ConcurrencyTest.test_concurrent_export_duplicate_detected_once asserts 15 of 16 fail.
- [ ] **M25-021** Concurrently register different exports while dispatching.  
  _OPEN_ — No register-while-dispatching test.
- [~] **M25-022** Race deadline expiration against handler completion.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Node._execute checks deadline after impl; tested only sequentially (EndToEndTest.test_typed_errors_not_transport_failures), no race test.
- [ ] **M25-023** Race cancellation against completion and response write.  
  _OPEN_ — Cancellation not wired into dispatch; no race test.
- [~] **M25-024** Race connection close against in-flight dispatch.  
  _PARTIAL_ — Soak killer thread (tools/soak.py) closes client sockets mid-call; no assertion-bearing unit test.
- [ ] **M25-025** Race graceful drain against new request admission.  
  _OPEN_ — No drain-vs-admission race test; the race exists (TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested).
- [ ] **M25-026** Race configuration reload against request validation/authorization.  
  _OPEN_ — No config-reload race test.
- [ ] **M25-027** Race certificate/policy rotation against authenticated sessions if applicable.  
  _OPEN_ — No key rotation vs live session race test (single-threaded test_rotation_overlap_then_old_key_expires only).
- [x] **M25-028** Race replay/idempotency record creation for identical request IDs.  
  _LOCALLY_VERIFIED_ — controls.IdempotencyCache.run; test_controls_ops.IdempotencyRetryTest.test_concurrent_duplicates_execute_once (16 threads, 1 execution).
- [ ] **M25-029** Race circuit-breaker state transitions under high failure volume.  
  _OPEN_ — CircuitBreaker locked but no concurrent state-transition test.

### Determinism/invariant testing
- [ ] **M25-030** Define invariants such as non-negative counters, unique export keys, one terminal state per request, one response per request, and at-most-once commit where applicable.  
  _OPEN_ — Invariants not defined in any doc.
- [~] **M25-031** Add stress tests that repeat concurrency scenarios thousands of iterations.  
  _PARTIAL_ — Thread stress with 16000 calls exists (ConcurrencyTest) but not repeated scenarios thousands of iterations.
- [ ] **M25-032** Randomize scheduling/yield points where supported.  
  _OPEN_ — No randomized scheduling/yield injection.
- [ ] **M25-033** Use deterministic schedulers/model checking for critical state machines if feasible.  
  _OPEN_ — No deterministic scheduler/model checking.
- [ ] **M25-034** Add assertions in tests for leaked tasks, threads, sockets, locks, and queues after shutdown.  
  _OPEN_ — No leak assertions for threads/sockets after shutdown.

### Tooling
- [~] **M25-035** Run Python-specific concurrency stress under supported interpreter builds.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Stress run only on CPython 3.11 locally; other interpreters need CI (no CI runner: .github/workflows/inv61-ci.yml committed but never executed).
- [ ] **M25-036** Use ThreadSanitizer/RaceSanitizer for any native extensions or companion runtimes.  
  _OPEN_ — No native extensions of our own; no TSAN statement or run (not applicable not declared).
- [ ] **M25-037** Use async debug modes/task-leak detectors for asyncio/trio-style implementations.  
  _OPEN_ — No asyncio used; not declared N/A in docs.
- [!] **M25-038** Capture deadlock stacks/timeouts automatically in CI.  
  _BLOCKED_ — Deadlock stack capture in CI requires a CI runner; nothing implemented (e.g. faulthandler) either.
- [ ] **M25-039** Run concurrency suite under CPU oversubscription and constrained resources.  
  _OPEN_ — No oversubscription/constrained-resource runs.

### Definition of Done / Acceptance Gates
- [ ] **M25-040** The concurrency contract is documented and matches implementation reality.  
  _OPEN_ — No concurrency contract document exists.
- [~] **M25-041** Shared mutable state has explicit synchronization/ownership.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Locks present on shared state, but Health._cache and Node.health.draining unsynchronized; no ownership doc.
- [~] **M25-042** High-contention race suites pass repeatedly without deadlock, lost updates, duplicate responses, or invariant violations.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Some race tests pass in one run; no repeated high-contention suite, no duplicate-response checks.
- [ ] **M25-043** Shutdown/reload/cancellation races have deterministic, tested outcomes.  
  _OPEN_ — Shutdown/reload/cancellation races not tested.

## M26 — Adjacent-layer integration tests

### Integration contract inventory
- [!] **M26-001** Identify the exact version/revision of INV-11 interface contracts required by INV-61.  
  _BLOCKED_ — Real INV-11 implementation/version unavailable.
- [!] **M26-002** Identify the exact version/revision of INV-36 control transport required by INV-61.  
  _BLOCKED_ — Real INV-36 implementation/version unavailable.
- [!] **M26-003** Identify the exact version/revision of INV-60 application fabric required by INV-61.  
  _BLOCKED_ — Real INV-60 implementation/version unavailable.
- [!] **M26-004** Identify the exact version/revision of INV-65 capability providers required by INV-61.  
  _BLOCKED_ — Real INV-65 implementation/version unavailable.
- [~] **M26-005** Document which side owns each schema, transport primitive, lifecycle signal, and error code.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: README Owns/does-not-own and ADR-0001 Boundary cover INV-36 sealing; no per-schema/lifecycle/error-code ownership table.
- [!] **M26-006** Create a compatibility matrix across supported adjacent-layer versions.  
  _BLOCKED_ — Compatibility matrix needs neighbour versions (INV-11/36/60/65 unavailable).
- [~] **M26-007** Define stable test fixtures/contracts that do not depend on developer-local repositories.  
  _PARTIAL_ — fixtures/golden_vectors.json is repo-local; adjacent contract tests are stubs (test_node_e2e.AdjacentLayerContractTest).

### INV-11 interface-contract integration
- [!] **M26-008** Load/compile real interface definitions through the intended WIT/binding path.  
  _BLOCKED_ — Real INV-11 definitions/binding path unavailable; only local wrpc/wit.py parser on test WIT.
- [!] **M26-009** Verify signature fingerprints/digests match the authoritative interface definitions.  
  _BLOCKED_ — Authoritative INV-11 definitions unavailable; AdjacentLayerContractTest.test_inv11_interface_language_feeds_fingerprints only checks fp length is 16.
- [x] **M26-010** Verify incompatible interface change is detected before dispatch.  
  _LOCALLY_VERIFIED_ — Node.handle fp check before decode; test_node_e2e.EndToEndTest.test_signature_drift_rejected_before_args_decoded (local WIT, not INV-11).
- [ ] **M26-011** Verify compatible evolution path where supported.  
  _OPEN_ — Exact-match only; no compatible evolution path (ADR-0001 Consequences says additive change is new wire major).
- [~] **M26-012** Exercise representative scalar, compound, result/error, and resource types.  
  _PARTIAL_ — Scalars/compound/result covered in test_wit_codec; resource types rejected (SUPPORT_MATRIX), so resource path not exercised.

### INV-36 control-transport integration
- [!] **M26-013** Verify control-plane commands can configure/inspect INV-61 through documented interfaces.  
  _BLOCKED_ — Requires INV-36 control plane; no control interface exists.
- [!] **M26-014** Ensure control messages are authenticated/authorized separately from data-plane calls.  
  _BLOCKED_ — Requires INV-36.
- [!] **M26-015** Test control-channel loss while data plane remains active according to policy.  
  _BLOCKED_ — Requires INV-36.
- [!] **M26-016** Test emergency disable/drain/quarantine control paths.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Requires INV-36 control path; only local drain()/LeaseTable.freeze exist.
- [!] **M26-017** Verify control messages cannot inject arbitrary RPC payload execution.  
  _BLOCKED_ — Requires INV-36.

### INV-60 application-fabric integration
- [!] **M26-018** Register/discover INV-61 endpoints through the actual fabric mechanism.  
  _BLOCKED_ — Requires INV-60 fabric.
- [!] **M26-019** Verify fabric deployment/startup/shutdown sequencing.  
  _BLOCKED_ — Requires INV-60 fabric.
- [!] **M26-020** Verify health/readiness propagation into the fabric scheduler/router.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Requires INV-60 fabric.
- [!] **M26-021** Verify rolling upgrade/drain behavior through the fabric.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Requires INV-60 fabric.
- [!] **M26-022** Verify fabric-level routing does not break request identity, deadlines, auth context, or trace context.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Requires INV-60; test_inv60_fabric_routes_opaque_frames only checks header decode.
- [!] **M26-023** Test fabric partition/failover scenarios.  
  _BLOCKED_ — Requires INV-60 fabric.

### INV-65 capability-provider integration
- [!] **M26-024** Acquire real capability decisions/tokens through the intended provider API.  
  _BLOCKED_ — Requires INV-65 provider.
- [!] **M26-025** Enforce provider-issued capability at function/resource dispatch.  
  _BLOCKED_ — Requires INV-65; local Authorizer is not provider-issued capability.
- [!] **M26-026** Test expiry, revocation, wrong audience, wrong tenant, and unavailable-provider behavior.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Requires INV-65 (local Authorizer expiry/revoke/tenant tested in AuthorizerTest but not provider).
- [!] **M26-027** Verify capability metadata survives transport without caller override.  
  _BLOCKED_ — Requires INV-65.
- [!] **M26-028** Verify audit/telemetry records the provider/policy revision safely.  
  _BLOCKED_ — Requires INV-65 policy revisions.

### End-to-end harness
- [!] **M26-029** Build an automated multi-component integration environment.  
  _BLOCKED_ — Multi-component environment needs INV-11/36/60/65 implementations.
- [!] **M26-030** Pin every component version/digest in the harness.  
  _BLOCKED_ — Neighbour versions/digests unknown.
- [!] **M26-031** Start dependencies in deterministic order with readiness gates.  
  _BLOCKED_ — Neighbour components unavailable.
- [x] **M26-032** Exercise successful end-to-end remote call.  
  _LOCALLY_VERIFIED_ — wrpc/node.py Node/Client; test_node_e2e.EndToEndTest.test_typed_round_trip and test_two_process.TwoProcessTest.test_separate_server_process.
- [~] **M26-033** Exercise auth denial, capability denial, interface mismatch, timeout, cancellation, overload, and dependency outage.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Auth denial, mismatch, timeout, overload tested in test_node_e2e; capability-provider denial, cancellation, dependency outage not.
- [~] **M26-034** Capture logs/metrics/traces/audit evidence for each scenario.  
  _PARTIAL_ — EndToEndTest.test_observability_emitted checks telemetry for one path, not per scenario.
- [~] **M26-035** Tear down cleanly and fail on leaked processes/resources.  
  _PARTIAL_ — TwoProcessTest asserts child exit 0; no leak check.
- [!] **M26-036** Make the harness runnable in CI and locally from documented commands.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Local command documented (OPERATIONS.md §1); CI execution blocked: no CI runner: .github/workflows/inv61-ci.yml committed but never executed.

### Definition of Done / Acceptance Gates
- [!] **M26-037** Supported adjacent-layer versions are explicitly pinned and compatibility-tested.  
  _BLOCKED_ — Neighbour versions unavailable.
- [!] **M26-038** A real automated end-to-end harness exercises all four named integrations.  
  _BLOCKED_ — Only stubs; real INV-11/36/60/65 absent.
- [!] **M26-039** Context propagation and security invariants survive every layer boundary.  
  _BLOCKED_ — Cannot verify across real layer boundaries without neighbours.
- [!] **M26-040** Failure of one adjacent component produces documented, tested degradation rather than undefined behavior.  
  _BLOCKED_ — Neighbour failure modes cannot be tested without neighbours.

## M27 — Cross-runtime / cross-architecture compatibility certification

### Support matrix definition
- [~] **M27-001** List supported Python runtime versions and implementations.  
  _DOCUMENTED_ — docs/SUPPORT_MATRIX.md Runtime: CPython 3.11 verified; 3.10-3.13 declared.
- [~] **M27-002** List supported operating systems/distributions.  
  _PARTIAL_ — SUPPORT_MATRIX.md names Linux/Windows/macOS generically; no distributions/versions.
- [~] **M27-003** List supported CPU architectures (for example x86-64, ARM64).  
  _DOCUMENTED_ — SUPPORT_MATRIX.md: Linux x86_64 verified, Linux arm64 declared.
- [~] **M27-004** List supported Wasm runtimes/component-model engines and versions.  
  _PARTIAL_ — SUPPORT_MATRIX.md says Wasm runtimes 'not verified'; none listed with versions.
- [~] **M27-005** List supported transport implementations/libraries and versions.  
  _DOCUMENTED_ — SUPPORT_MATRIX.md/DEPENDENCIES.md: TCP stdlib socket + cryptography==46.0.7 AES-GCM.
- [~] **M27-006** List supported peer protocol versions.  
  _DOCUMENTED_ — SUPPORT_MATRIX.md Protocol: handshake wrpc/2, frame PK_WRPC_FRAME/2.
- [ ] **M27-007** Distinguish Tier-1 fully supported, Tier-2 best-effort, and unsupported environments.  
  _OPEN_ — No Tier-1/Tier-2/unsupported classification (only verified/declared).
- [ ] **M27-008** Define end-of-support policy when a runtime reaches upstream EOL.  
  _OPEN_ — No runtime EOL policy.

### Platform correctness
- [x] **M27-009** Verify endian-independent wire serialization.  
  _LOCALLY_VERIFIED_ — codec.py uses explicit '>' struct; test_wit_codec.CodecTest.test_golden_vectors pins bytes (single host only).
- [x] **M27-010** Verify integer width assumptions are explicit.  
  _LOCALLY_VERIFIED_ — codec.py int-range checks; test_wit_codec.CodecTest.test_signed_extremes and test_negative_paths.
- [!] **M27-011** Verify floating-point edge handling across architectures where floats exist.  
  _BLOCKED_ — NaN canonicalisation tested (test_nan_is_canonicalised_and_foreign_nan_rejected) on x86_64 only; cross-arch needs other hosts.
- [!] **M27-012** Verify monotonic/wall-clock deadline behavior across OSes.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Requires multiple OSes; deadlines use wall clock time.time() (no monotonic).
- [!] **M27-013** Verify path/file permission semantics for configuration/keys on Windows and Unix-like systems.  
  _BLOCKED_ — Requires Windows host; ops.resolve_secret does no permission check at all.
- [!] **M27-014** Verify socket behavior, IPv6, DNS, and TLS trust-store differences.  
  _BLOCKED_ — Requires multiple OSes; no IPv6/DNS/TLS tests.
- [!] **M27-015** Verify process signal/service-shutdown semantics per OS.  
  _BLOCKED_ — Requires multiple OSes; serve.py SIGTERM handler only tested via stdin-close on Linux.

### Runtime/Wasm interoperability
- [!] **M27-016** Run the same golden WIT/wire fixtures through each supported Wasm runtime.  
  _BLOCKED_ — Requires Wasm runtimes.
- [!] **M27-017** Verify generated bindings compile/load on each supported toolchain.  
  _BLOCKED_ — Requires toolchains/Wasm runtimes; no binding generation exists.
- [!] **M27-018** Verify resource handle/lifetime semantics across runtimes.  
  _BLOCKED_ — Resources rejected; requires Wasm runtimes.
- [!] **M27-019** Verify traps/exceptions map to consistent RPC statuses.  
  _BLOCKED_ — Requires Wasm runtimes; Python traps map to callee-trap (test_rpc.test_trap_is_typed_without_exception_detail_leak).
- [!] **M27-020** Verify runtime sandbox/capability settings required by INV-61.  
  _BLOCKED_ — Requires Wasm runtimes.
- [!] **M27-021** Test runtime upgrades for compatibility regression.  
  _BLOCKED_ — Requires Wasm runtimes.

### CI matrix
- [!] **M27-022** Implement CI jobs for every Tier-1 OS × runtime combination.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Workflow matrix defined but no CI runner: .github/workflows/inv61-ci.yml committed but never executed.
- [!] **M27-023** Include at least one ARM64 execution environment if ARM64 is supported.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: ubuntu-24.04-arm leg defined; never executed (no CI runner: .github/workflows/inv61-ci.yml committed but never executed).
- [!] **M27-024** Run unit, protocol, integration, and selected performance tests per Tier-1 platform.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: no CI runner: .github/workflows/inv61-ci.yml committed but never executed; workflow runs unittest discover + bench only.
- [ ] **M27-025** Run cross-version peer tests (old client↔new server and new client↔old server) where supported.  
  _OPEN_ — No old/new peer cross-version tests; only one wire version exists.
- [!] **M27-026** Store platform-specific artifacts and logs.  
  _BLOCKED_ — Workflow now uploads bench artifacts per leg (actions/upload-artifact) - never executed; needs a CI runner.
- [~] **M27-027** Fail release qualification if a Tier-1 matrix leg is skipped.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Workflow has fail-fast:false but no skip-detection; unittest skips (4 locally) pass. Also references missing tools/checklist_status.py.

### Reproducibility
- [ ] **M27-028** Pin toolchains/container/base images by digest where practical.  
  _OPEN_ — Actions pinned by tag (@v4/@v5), not digest; no container images.
- [~] **M27-029** Record compiler/interpreter/runtime versions in build provenance.  
  _PARTIAL_ — bench.json records python/machine/system; no build provenance record.
- [~] **M27-030** Avoid hidden dependence on host-local locale/timezone/default encoding.  
  _PARTIAL_ — Most file opens set encoding='utf-8' but tools/serve.py json.load(open(a.config)) and soak/bench open() use locale default; not tested.
- [ ] **M27-031** Test non-UTF-8 locale environments if the runtime could encounter them.  
  _OPEN_ — No non-UTF-8 locale test.
- [ ] **M27-032** Normalize filesystem case-sensitivity assumptions.  
  _OPEN_ — Not addressed.

### Definition of Done / Acceptance Gates
- [!] **M27-033** A versioned support matrix exists and is reflected in automated CI.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Matrix exists (SUPPORT_MATRIX.md, workflow) but never run in CI.
- [!] **M27-034** Tier-1 combinations pass protocol/integration tests with no unexpected skips.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: no CI runner: .github/workflows/inv61-ci.yml committed but never executed.
- [!] **M27-035** Cross-runtime golden fixtures are byte/behavior compatible.  
  _BLOCKED_ — Only CPython/x86_64 checked against golden vectors; other runtimes unavailable.
- [~] **M27-036** Unsupported combinations fail clearly or are documented rather than silently drifting.  
  _PARTIAL_ — SUPPORT_MATRIX.md documents unverified combos; no runtime guard (requires-python>=3.10 only).

## M28 — Performance, capacity, power, and regression certification

### Benchmark specification
- [~] **M28-001** Define benchmark hardware/VM characteristics, CPU governor, memory, NIC, OS, runtime, and affinity settings.  
  _PARTIAL_ — evidence/bench.json records python/machine/system/RSS only; no CPU governor/memory/NIC/affinity.
- [~] **M28-002** Pin benchmark software/toolchain versions.  
  _PARTIAL_ — cryptography pinned; interpreter version recorded; no pinned benchmark tooling spec.
- [ ] **M28-003** Define warmup, run duration, repetitions, confidence interval, and outlier policy.  
  _OPEN_ — tools/bench.py has no warmup/repetition/CI/outlier policy.
- [~] **M28-004** Separate in-process protocol cost from serialization, transport, auth, policy, and handler cost.  
  _PARTIAL_ — bench.py separates framing, framing+args, loopback; auth/policy/handler cost not separated.
- [ ] **M28-005** Define payload profiles: tiny, small, medium, large, and maximum supported.  
  _OPEN_ — Single ~125-byte payload only.
- [ ] **M28-006** Define concurrency profiles and request-rate profiles.  
  _OPEN_ — Loopback bench is single-client sequential; no concurrency/rate profiles.
- [!] **M28-007** Define local, same-zone, cross-zone, and cross-site network profiles if relevant.  
  _BLOCKED_ — Needs multi-host/zone network.

### Latency/throughput measurements
- [~] **M28-008** Measure p50, p90, p95, p99, p99.9, max, and standard deviation where useful.  
  _PARTIAL_ — evidence/bench.json has p50/p99/mean only; no p90/p95/p99.9/max/stddev.
- [~] **M28-009** Measure sustainable requests/sec at target SLO.  
  _PARTIAL_ — calls_per_s 2818 single-client loopback; not at target SLO under load.
- [ ] **M28-010** Measure connection establishment and secure-handshake latency.  
  _OPEN_ — Handshake latency not measured.
- [x] **M28-011** Measure serialization/deserialization latency independently.  
  _LOCALLY_VERIFIED_ — tools/bench.py::bench_framing/bench_envelope_only; evidence/bench.json framing vs framing_plus_args.
- [ ] **M28-012** Measure queue wait versus handler execution.  
  _OPEN_ — No queue-wait vs handler split.
- [ ] **M28-013** Measure retry/circuit-breaker overhead under partial failure.  
  _OPEN_ — Not measured.
- [ ] **M28-014** Measure tracing/metrics/logging overhead enabled versus disabled.  
  _OPEN_ — Not measured.

### Resource measurements
- [ ] **M28-015** Measure CPU utilization/cycles per request where practical.  
  _OPEN_ — Not measured.
- [~] **M28-016** Measure RSS/heap allocation per request and under concurrency.  
  _PARTIAL_ — max_rss_kb in bench/soak only (peak ru_maxrss); no per-request allocation.
- [ ] **M28-017** Measure peak memory under maximum legal payload.  
  _OPEN_ — Not measured at 1 MiB max frame.
- [ ] **M28-018** Measure network bytes per RPC including framing/security overhead.  
  _OPEN_ — Not measured.
- [ ] **M28-019** Measure socket/FD/task/thread usage versus concurrency.  
  _OPEN_ — Not measured.
- [ ] **M28-020** Measure GC pressure/pause behavior where relevant.  
  _OPEN_ — Not measured.
- [ ] **M28-021** Measure buffer copies or zero-copy effectiveness where applicable.  
  _OPEN_ — Not measured.

### Capacity model
- [~] **M28-022** Define tested maximum concurrent connections.  
  _PARTIAL_ — max_connections config + test_node_e2e.AdversarialTest.test_connection_limit (functional), no tested capacity number.
- [~] **M28-023** Define tested maximum inflight requests.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: max_inflight config + test_overload_sheds_with_typed_error; no tested maximum.
- [ ] **M28-024** Define safe queue depth/high-water marks.  
  _OPEN_ — Defaults exist (max_queue 128) but no safe high-water derivation.
- [ ] **M28-025** Determine saturation point for CPU, memory, network, or dependency bottleneck.  
  _OPEN_ — No saturation study.
- [ ] **M28-026** Define headroom policy for production sizing.  
  _OPEN_ — No headroom policy.
- [ ] **M28-027** Derive capacity per node and minimum replica count for target workload.  
  _OPEN_ — No capacity/replica model.
- [ ] **M28-028** Validate model against a realistic mixed workload.  
  _OPEN_ — No mixed workload validation.

### Burst/overload behavior
- [ ] **M28-029** Run sudden burst tests above nominal rate.  
  _OPEN_ — No burst test.
- [~] **M28-030** Run sustained overload until stable shedding state.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: evidence/soak.json shows overloaded shedding with max_inflight 4 over 60s; not a characterised overload campaign.
- [ ] **M28-031** Verify latency does not grow unbounded before admission control activates.  
  _OPEN_ — Not verified.
- [~] **M28-032** Verify memory remains bounded.  
  _PARTIAL_ — evidence/soak.json (regenerated): RSS 25,784->110,392 KB over 60 s/131,413 calls; OPERATIONS.md §4 attributes it to the 100k idempotency cache but no run shows RSS plateauing; bounded-ness not demonstrated.
- [~] **M28-033** Verify retry hints/backpressure reduce rather than amplify overload.  
  _PARTIAL_ — Client now honours retry_after_ms (test_controls_ops.IdempotencyRetryTest.test_retry_honours_retry_after_hint) plus budget; no measurement showing hints reduce overload.
- [ ] **M28-034** Measure recovery time after overload clears.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Not measured.

### Power/edge characterization
- [!] **M28-035** If constrained-edge operation is in scope, measure energy/power under idle, nominal, and peak RPC load.  
  _BLOCKED_ — Power-measurement hardware unavailable; no scope declaration either.
- [!] **M28-036** Measure cost of encryption, serialization, tracing, and retries on target edge hardware.  
  _BLOCKED_ — Edge hardware unavailable.
- [ ] **M28-037** Define thermal/throttling assumptions.  
  _OPEN_ — No thermal assumptions defined.
- [ ] **M28-038** Establish acceptable power/energy budget per workload class.  
  _OPEN_ — No power budget or out-of-scope declaration.

### Regression gates
- [~] **M28-039** Establish baseline benchmark results by release.  
  _PARTIAL_ — One local run evidence/bench.json; no per-release baseline archive.
- [~] **M28-040** Define allowed regression percentage for latency, throughput, memory, and CPU.  
  _PARTIAL_ — OPERATIONS.md §5: '≤25% p99' latency only; bench.py --max-regress covers framing p99 only; none for throughput/memory/CPU.
- [!] **M28-041** Fail CI/release qualification on statistically significant regression above threshold.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: CI never executed; workflow bench step passes no --baseline, so gate never fires; no statistical test.
- [~] **M28-042** Store raw benchmark data and environment metadata.  
  _PARTIAL_ — bench.json stores summaries + minimal env metadata, not raw samples.
- [!] **M28-043** Require explicit approved waiver for accepted regression.  
  _BLOCKED_ — Waiver approval needs an owner/approver (UNASSIGNED).

### Definition of Done / Acceptance Gates
- [~] **M28-044** The stated p99 framing-overhead/SLO claims have reproducible evidence.  
  _PARTIAL_ — evidence/bench.json framing p99 23us<50us on one host, one run; SLO 'framing' defined as envelope-only (framing_plus_args p99 128us exceeds 50us); no repetition.
- [ ] **M28-045** Safe per-node capacity and saturation behavior are quantified.  
  _OPEN_ — Not quantified.
- [~] **M28-046** Overload remains bounded and recovers predictably.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Shedding observed in soak; recovery not measured, memory growth unexplained.
- [!] **M28-047** Release performance gates detect meaningful regressions.  
  _BLOCKED_ — Regression gate not wired into CI (no --baseline) and CI not executed.
- [ ] **M28-048** Edge/power requirements are either measured or formally declared out of scope.  
  _OPEN_ — Edge/power neither measured nor declared out of scope.

## M29 — Fault-injection, soak, disaster, and degraded-control-plane tests

### Fault-injection framework
- [~] **M29-001** Build or integrate a repeatable chaos/fault injection harness.  
  _PARTIAL_ — tools/soak.py connection-kill + FaultInjectionTest; no general chaos harness.
- [~] **M29-002** Support packet loss, latency, jitter, duplication, reordering, partition, and connection reset.  
  _PARTIAL_ — Only connection reset (soak killer); no loss/latency/jitter/dup/reorder at network level (record-level replay/reorder in ChannelTest).
- [x] **M29-003** Support process kill/crash and forced restart.  
  _LOCALLY_VERIFIED_ — test_node_e2e.FaultInjectionTest.test_server_crash_reconnect_and_journal_replay (in-process stop/restart).
- [ ] **M29-004** Support CPU starvation, memory pressure, disk pressure, FD exhaustion, and clock skew where applicable.  
  _OPEN_ — No CPU/memory/disk/FD/clock-skew injection.
- [~] **M29-005** Support dependency unavailability/slow responses/malformed responses.  
  _PARTIAL_ — Dead peer via test_breaker_opens_on_dead_peer_then_recovers; no slow/malformed dependency responses.
- [~] **M29-006** Support certificate expiry/revocation and identity/policy/config service outages.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Key expiry/revocation tested (test_security.HandshakeTest.test_unknown_expired_revoked_and_wrong_peer_share_one_code); no identity/policy/config service outage.
- [~] **M29-007** Record exact fault parameters and random seeds for reproducibility.  
  _PARTIAL_ — soak.py seeds killer rng=29 but does not record seed/params in evidence/soak.json.

### Dependency outage campaigns
- [!] **M29-008** Identity provider unavailable.  
  _BLOCKED_ — No external identity provider exists (PSK keyring local); needs real neighbour.
- [!] **M29-009** Authorization/policy engine unavailable.  
  _BLOCKED_ — Policy engine is local Authorizer; external engine (INV-65) unavailable.
- [ ] **M29-010** Config source unavailable/stale.  
  _OPEN_ — Config source outage not tested.
- [~] **M29-011** Audit sink unavailable/backpressured.  
  _PARTIAL_ — Audit sink unavailable injected: test_node_e2e.DefectRegressionTest.test_audit_failure_fails_closed_and_flips_readiness; backpressured/slow sink not tested (fsync is synchronous on the request path).
- [ ] **M29-012** Metrics/log/trace collectors unavailable.  
  _OPEN_ — Collector outage not tested.
- [ ] **M29-013** State/replay/idempotency store unavailable.  
  _OPEN_ — Journal unavailability untested; journal append failure after execution kills the session and loses the outcome (controls.py IdempotencyCache.run).
- [ ] **M29-014** Service discovery/DNS failure.  
  _OPEN_ — DNS failure not tested.
- [!] **M29-015** Transport broker/fabric failure where applicable.  
  _BLOCKED_ — INV-60 fabric unavailable.
- [ ] **M29-016** Validate each dependency's documented fail-open/fail-closed behavior.  
  _OPEN_ — Fail-open/closed per dependency not documented or validated.

### Network/distributed failure campaigns
- [~] **M29-017** Full client↔server partition.  
  _PARTIAL_ — Dead peer via server stop (FaultInjectionTest); no true network partition.
- [!] **M29-018** Asymmetric partition.  
  _BLOCKED_ — Needs multi-host network control.
- [!] **M29-019** Multi-zone/site partition.  
  _BLOCKED_ — Needs multiple zones/sites.
- [!] **M29-020** High packet loss/jitter.  
  _BLOCKED_ — Needs network emulation (netem/root) on real network; not available.
- [~] **M29-021** Long-lived half-open connections.  
  _PARTIAL_ — idle_timeout_s exists; no half-open connection test.
- [ ] **M29-022** Reconnect storm after outage.  
  _OPEN_ — No reconnect-storm test.
- [~] **M29-023** Failover during mutating request.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: test_server_crash_reconnect_and_journal_replay covers restart-with-journal on same node; OPERATIONS.md §4 admits cross-node retry re-executes.
- [x] **M29-024** Split-brain/dual-owner attempt.  
  _LOCALLY_VERIFIED_ — controls.LeaseTable; test_controls_ops.AdmissionBreakerLeaseTest.test_fencing_prevents_duplicate_owner_writes (library-level, not wired into Node).

### Soak/endurance testing
- [~] **M29-025** Run nominal workload for extended duration representative of production duty cycle.  
  _PARTIAL_ — evidence/soak.json is 60s only; not production duty cycle.
- [~] **M29-026** Track memory growth/leaks.  
  _PARTIAL_ — evidence/soak.json (regenerated): RSS 25,784->110,392 KB over 60 s/131,413 calls; OPERATIONS.md §4 attributes it to the 100k idempotency cache but no run shows RSS plateauing; no leak analysis.
- [ ] **M29-027** Track file descriptor/socket/task/thread leaks.  
  _OPEN_ — FD/thread tracking not done.
- [ ] **M29-028** Track latency drift and GC behavior.  
  _OPEN_ — Latency drift/GC not tracked.
- [ ] **M29-029** Rotate credentials/config during soak.  
  _OPEN_ — No rotation during soak.
- [ ] **M29-030** Perform rolling restart/upgrade during soak.  
  _OPEN_ — No rolling restart during soak.
- [~] **M29-031** Inject intermittent dependency failures during soak.  
  _PARTIAL_ — Connection kills during soak only.
- [~] **M29-032** Confirm telemetry storage/cardinality remains bounded over time.  
  _PARTIAL_ — Metrics series cap tested (test_metrics_exposition_and_cardinality_cap); audit deque bounded; not tracked over soak.

### Disaster/recovery testing
- [~] **M29-033** Simulate total node loss.  
  _PARTIAL_ — Single node stop/restart in FaultInjectionTest; no total node loss with disk loss.
- [!] **M29-034** Simulate multi-node/site loss according to deployment topology.  
  _BLOCKED_ — Needs multiple nodes/sites.
- [~] **M29-035** Restore from backup/checkpoint if durable state exists.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Journal/audit replay on restart tested (test_journal_survives_restart_and_torn_tail, test_audit_log_survives_restart_and_verifies); no backup/restore.
- [ ] **M29-036** Verify RPO/RTO against declared objectives.  
  _OPEN_ — No RPO/RTO declared.
- [~] **M29-037** Verify replay/idempotency/security state after recovery.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Idempotency state after restart verified; replay-window/keyring state not persisted or verified.
- [!] **M29-038** Validate operator runbooks step-by-step.  
  _BLOCKED_ — Runbook validation needs operators; runbooks mostly absent.
- [ ] **M29-039** Capture recovery evidence and gaps.  
  _OPEN_ — No recovery evidence record.

### Degraded-control-plane mode
- [ ] **M29-040** Define what data-plane operations remain permitted when control plane is unavailable.  
  _OPEN_ — No degraded-control-plane definition.
- [~] **M29-041** Define TTL for cached policy/config/identity information.  
  _PARTIAL_ — Grant.not_after and key not_after exist; no cached-policy TTL definition.
- [x] **M29-042** Prevent indefinite operation on stale revoked policy/credentials.  
  _LOCALLY_VERIFIED_ — Revoked/expired credentials re-checked per record (wrpc/node.py::Node._serve) and Authorizer grants checked per call: test_node_e2e.DefectRegressionTest.test_revoked_key_ends_live_session, test_controls_ops.AuthorizerTest.test_no_cross_tenant_glob_and_expiry_and_revoke.
- [~] **M29-043** Preserve emergency local disable where required.  
  _PARTIAL_ — drain() now refuses new calls/connections and LeaseTable.freeze exists (tested); TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested.
- [ ] **M29-044** Expose degraded-mode health/metrics/logs.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No degraded-mode signals.
- [!] **M29-045** Test control-plane recovery and convergence.  
  _BLOCKED_ — Needs control plane (INV-36).

### Definition of Done / Acceptance Gates
- [~] **M29-046** Major dependency, host, and network failures have automated injection scenarios.  
  _PARTIAL_ — Only process kill/connection reset automated; dependency/network scenarios missing.
- [~] **M29-047** Long-running soak shows no unbounded resource growth or latent correctness degradation.  
  _PARTIAL_ — Soak regenerated: 131,413 ok, no cap at 100k, audit chain ok; evidence/soak.json (regenerated): RSS 25,784->110,392 KB over 60 s/131,413 calls; OPERATIONS.md §4 attributes it to the 100k idempotency cache but no run shows RSS plateauing; only 60 s.
- [ ] **M29-048** Recovery meets documented RPO/RTO or the exception is explicitly accepted.  
  _OPEN_ — No RPO/RTO documented or accepted exception.
- [ ] **M29-049** Degraded-control-plane behavior is safe, bounded in time, and observable.  
  _OPEN_ — Degraded mode undefined.

## M30 — Supply-chain provenance, artifact verification, and SBOM

### SBOM
- [~] **M30-001** Generate an SBOM in CycloneDX, SPDX, or approved format for every release artifact.  
  _PARTIAL_ — tools/sbom.py produces CycloneDX 1.5 (ran here, deterministic); no evidence/sbom file committed, no release artifact.
- [~] **M30-002** Include direct/transitive Python dependencies, native libraries, generated Wasm components, container base images, and vendored code.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: sbom.py lists files + installed dists it queries; cffi/native OpenSSL in cryptography wheel and base images not demonstrably included; pk_core absent.
- [~] **M30-003** Include package versions, hashes, licenses, and source locations where available.  
  _PARTIAL_ — File hashes and dist versions/licences; dependency artifact hashes absent (index unreachable).
- [~] **M30-004** Version the SBOM schema/tooling.  
  _PARTIAL_ — CycloneDX specVersion recorded; tool version not.
- [!] **M30-005** Attach SBOM to release artifacts and retain it with provenance.  
  _BLOCKED_ — No release artifacts/provenance system (signing/PKI, CI).

### Dependency/security scanning
- [!] **M30-006** Scan dependencies against current vulnerability databases during CI/release.  
  _BLOCKED_ — Vulnerability DB/package index unreachable; no scanner step in CI.
- [~] **M30-007** Define severity thresholds that block release.  
  _PARTIAL_ — OPERATIONS.md §7 proposed vuln SLA (critical 7d/high 30d) but no release-blocking threshold.
- [ ] **M30-008** Define false-positive/risk-acceptance workflow with expiry.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No false-positive/risk-acceptance workflow.
- [ ] **M30-009** Scan container/base images if used.  
  _OPEN_ — No containers; N/A not declared.
- [ ] **M30-010** Scan licenses against approved/denied policy.  
  _OPEN_ — No licence policy scan; pyproject licence 'UNDECLARED'.
- [ ] **M30-011** Scan secrets in source/build artifacts.  
  _OPEN_ — No secret scan.

### Build provenance
- [!] **M30-012** Record source repository and immutable commit/tag.  
  _BLOCKED_ — Not a git repository; no source repo/commit available.
- [!] **M30-013** Record dirty-tree status; prohibit release from uncommitted source.  
  _BLOCKED_ — No VCS in build.
- [~] **M30-014** Record build system/tool versions, runtime, OS/image digest, and dependency lock digest.  
  _PARTIAL_ — bench.json records runtime only; no lock digest or build provenance.
- [!] **M30-015** Generate SLSA/in-toto or equivalent signed provenance attestation.  
  _BLOCKED_ — Signing keys/PKI and CI unavailable.
- [!] **M30-016** Record build identity and CI job/run identifier.  
  _BLOCKED_ — No CI run identifier available.
- [~] **M30-017** Record artifact SHA-256 or stronger digest.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: sbom.py writes SHA256SUMS of source files; no built artifact digest; SHA256SUMS not present in package though docs/MASTER_SOURCE.md claims a digest is in it.

### Artifact signing and verification
- [!] **M30-018** Sign release archives/wheels/images/components with an approved signing system.  
  _BLOCKED_ — Signing keys unavailable.
- [!] **M30-019** Publish detached checksums/signatures.  
  _BLOCKED_ — Signatures need keys; checksums generator exists but not published.
- [ ] **M30-020** Verify signatures/digests during deployment/bootstrap.  
  _OPEN_ — Bootstrap (OPERATIONS.md §1) does not verify digests/signatures.
- [!] **M30-021** Define trusted signer/root rotation procedure.  
  _BLOCKED_ — Needs PKI/signer owner.
- [!] **M30-022** Define emergency key compromise/revocation procedure.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Needs PKI/signer owner; DEPENDENCIES.md update policy covers dependency revocation only.
- [!] **M30-023** Prevent unsigned/unapproved artifacts from production deployment.  
  _BLOCKED_ — Needs signing system and deployment gate.

### Reproducible builds
- [x] **M30-024** Remove non-deterministic timestamps/orderings where practical.  
  _LOCALLY_VERIFIED_ — tools/sbom.py omits timestamps and sorts; test_packaging.PackagingTest.test_sbom_is_byte_deterministic runs it twice and compares bytes.
- [~] **M30-025** Pin build dependencies/toolchains.  
  _PARTIAL_ — cryptography pinned; cffi unpinned; no hashes; setuptools>=68 unpinned.
- [!] **M30-026** Compare rebuild digests from independent clean environments.  
  _BLOCKED_ — Requires independent clean environments.
- [ ] **M30-027** Document accepted non-reproducible fields if perfect bit reproducibility is infeasible.  
  _OPEN_ — Not documented.
- [ ] **M30-028** Verify generated code/artifacts are reproducible from source.  
  _OPEN_ — No generated code; not declared.

### Release manifest
- [ ] **M30-029** Create one machine-readable manifest containing version, files, hashes, SBOM digest, provenance digest, signature references, compatibility matrix, and build metadata.  
  _OPEN_ — No release manifest.
- [ ] **M30-030** Ensure deployment tooling consumes/validates the manifest.  
  _OPEN_ — No deployment tooling consuming a manifest.
- [ ] **M30-031** Archive prior manifests for audit and rollback verification.  
  _OPEN_ — No manifest archive.

### Definition of Done / Acceptance Gates
- [!] **M30-032** Every production artifact has SBOM, digest, signed provenance, and signature/checksum verification.  
  _BLOCKED_ — Signed provenance needs keys/CI.
- [!] **M30-033** Dependency/security/license policy gates run before release.  
  _BLOCKED_ — Gates need CI + reachable vuln DB.
- [!] **M30-034** Deployment refuses untrusted or tampered artifacts.  
  _BLOCKED_ — Needs signing/verification system.
- [!] **M30-035** A clean independent rebuild can verify provenance/reproducibility expectations.  
  _BLOCKED_ — Needs independent rebuild environment.

## M31 — Production packaging/bootstrap artifact

### Package definition
- [x] **M31-001** Add `pyproject.toml` or equivalent build metadata.  
  _LOCALLY_VERIFIED_ — pyproject.toml present; test_packaging.PackagingTest.test_pyproject_metadata_matches_version_and_pins checks version == VERSION and exact pins (wheel build itself not run).
- [~] **M31-002** Define package name, version source, Python/runtime constraints, dependencies, optional extras, and license metadata.  
  _PARTIAL_ — pyproject.toml name/version/requires-python/deps/extras set; licence 'UNDECLARED'; gate extra empty (pk_core).
- [~] **M31-003** Ensure package version is sourced from one authoritative mechanism and matches `VERSION`/release metadata.  
  _PARTIAL_ — pyproject version 4.3.0 still hard-coded separately from VERSION; README now 4.3.0; test_component.ConformanceTest.test_version reads VERSION but is skipped (pk_core absent).
- [!] **M31-004** Build wheel/sdist or the approved deployable component/container artifact.  
  _BLOCKED_ — Wheel build needs setuptools from unreachable index (build-system requires); not produced.
- [~] **M31-005** Exclude tests/dev-only files from production package unless intentionally required.  
  _PARTIAL_ — pyproject packages include root package dir '.' which carries tests/tools/docs via package-dir mapping (tests not excluded explicitly); unverified since no build.
- [ ] **M31-006** Include WIT/schema/config assets required at runtime.  
  _OPEN_ — No package-data declaration for fixtures/WIT; demo WIT inline in tools/serve.py.

### Deterministic bootstrap
- [~] **M31-007** Provide one documented bootstrap/install command/path.  
  _DOCUMENTED_ — Unchanged after 4.3.0 re-check: docs/OPERATIONS.md §1 bootstrap commands.
- [~] **M31-008** Pin dependency sources and lock versions.  
  _PARTIAL_ — requirements.lock pins cryptography only; cffi unpinned; no hashes.
- [!] **M31-009** Verify artifact hashes/signatures before install.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Hashes/signatures unavailable (index unreachable, no signing keys).
- [~] **M31-010** Create isolated runtime environment.  
  _DOCUMENTED_ — OPERATIONS.md §1 uses python -m venv .venv (not executed as evidence).
- [ ] **M31-011** Avoid writes to unexpected user/profile locations unless documented.  
  _OPEN_ — Not documented.
- [~] **M31-012** Support non-interactive installation for automation.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Commands are non-interactive but not tested/scripted.
- [ ] **M31-013** Return stable exit codes for success, dependency failure, config failure, permission failure, and verification failure.  
  _OPEN_ — No bootstrap script with defined exit codes.
- [ ] **M31-014** Make bootstrap idempotent or clearly define reinstall behavior.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Not defined.

### Deployment artifact
- [ ] **M31-015** Provide systemd/Windows Service/Kubernetes/container/component deployment definition as applicable.  
  _OPEN_ — No systemd/container/k8s definition.
- [ ] **M31-016** Define service account/identity and least-required OS permissions.  
  _OPEN_ — Not defined.
- [~] **M31-017** Define ports, network policy, volumes, secret mounts, and config locations.  
  _PARTIAL_ — listen_host/port and psk_ref env:/file: defined in ops.SCHEMA; no network policy/volumes.
- [ ] **M31-018** Define CPU/memory/FD limits and requests/reservations.  
  _OPEN_ — Not defined.
- [~] **M31-019** Define health/readiness probes.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: OPERATIONS.md §2 defines Health.live/ready semantics but no HTTP/probe endpoint exists to wire them to.
- [~] **M31-020** Define graceful stop timeout and drain hook.  
  _PARTIAL_ — tools/serve.py calls drain() (default 5 s timeout) then stop(); untested; drain race (TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested).
- [ ] **M31-021** Define restart policy that avoids crash loops.  
  _OPEN_ — Not defined.

### Configuration/bootstrap validation
- [x] **M31-022** Validate configuration before service start.  
  _LOCALLY_VERIFIED_ — ops.validate_config/ConfigStore.build before start (serve.py); test_controls_ops.OpsTest.test_config_layers_provenance_validation_rollback.
- [~] **M31-023** Validate certificates/identity prerequisites.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: resolve_secret fails if unresolved, Keyring.add rejects weak keys (test_weak_and_duplicate_keys_rejected); no preflight command.
- [!] **M31-024** Validate required adjacent services are discoverable or clearly report deferred readiness.  
  _BLOCKED_ — Adjacent services (INV-36/60/65) unavailable.
- [~] **M31-025** Verify supported runtime/platform before installing.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: requires-python>=3.10 only.
- [ ] **M31-026** Provide a `--check`/preflight mode that makes no mutating changes.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No --check preflight mode (and CI references nonexistent tools/checklist_status.py --check).
- [~] **M31-027** Provide post-install self-test/diagnostic command.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Test suite serves as self-test per OPERATIONS.md §1; no diagnostic command.

### Upgrade/rollback
- [ ] **M31-028** Define in-place versus side-by-side upgrade strategy.  
  _OPEN_ — Not defined.
- [ ] **M31-029** Preserve compatible configuration/state safely.  
  _OPEN_ — Not defined.
- [ ] **M31-030** Run pre-upgrade compatibility checks.  
  _OPEN_ — None.
- [~] **M31-031** Support rollback to last-known-good artifact/config within documented constraints.  
  _PARTIAL_ — ConfigStore.rollback tested (test_config_layers_provenance_validation_rollback); artifact rollback only described in OPERATIONS.md §5.
- [ ] **M31-032** Define migration behavior for incompatible persisted state/schema.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Not defined for journal/audit format.
- [!] **M31-033** Verify rolling upgrade with mixed-version peers.  
  _BLOCKED_ — Only one wire version; mixed-version peers unavailable.

### Clean-environment verification
- [!] **M31-034** Install on a freshly provisioned supported Windows environment if Windows is supported.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: No Windows host.
- [!] **M31-035** Install on a freshly provisioned supported Linux environment if Linux is supported.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: No fresh provisioned host; package index unreachable for install.
- [~] **M31-036** Install with no pre-existing `pk_core` or developer environment leakage.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: transport layer has no pk_core import (test_pk_core_compat) but no clean install performed.
- [ ] **M31-037** Verify uninstall/cleanup behavior where required.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Not defined.
- [!] **M31-038** Verify package from release artifact, not source tree, passes smoke/integration tests.  
  _BLOCKED_ — No built artifact (index unreachable).

### Definition of Done / Acceptance Gates
- [!] **M31-039** A clean supported node can install/start/verify INV-61 from signed release artifacts using documented steps.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: No signed artifacts/clean node.
- [!] **M31-040** Packaging includes all required runtime assets and no undeclared dependency on the developer machine.  
  _BLOCKED_ — pk_core undeclared/unavailable.
- [~] **M31-041** Upgrade/rollback and graceful shutdown are automated and tested.  
  _PARTIAL_ — Config rollback + graceful stop tested (TwoProcessTest); artifact upgrade/rollback not automated.
- [ ] **M31-042** Deployment configuration enforces resource/security/health requirements.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No deployment configuration.

## M32 — Formal operations/release/governance package

### SLO/SLA and service objectives
- [ ] **M32-001** Define availability objective and measurement window.  
  _OPEN_ — No availability objective.
- [~] **M32-002** Define latency objectives by operation/workload class.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: README SLO p99 framing <50us; OPERATIONS.md alert p99 handle >50ms; not by workload class.
- [~] **M32-003** Define error-rate objective.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: README SLOs 'no misreads','deadlines' zero; no general error-rate objective.
- [ ] **M32-004** Define saturation/capacity objective.  
  _OPEN_ — None.
- [ ] **M32-005** Define recovery objectives (RTO/RPO) where state exists.  
  _OPEN_ — No RTO/RPO.
- [!] **M32-006** Define support hours/escalation expectations.  
  _BLOCKED_ — Paging roster UNASSIGNED (OPERATIONS.md §6); needs owner.
- [~] **M32-007** Define error budget and policy for release velocity when budget is exhausted.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: README gives error budgets; no release-velocity policy.
- [~] **M32-008** Map every SLO to concrete telemetry queries and alerts.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: OPERATIONS.md §3 lists series and proposed alerts; not every SLO mapped (deadlines SLO).

### Release process
- [ ] **M32-009** Define branch/tag/versioning policy.  
  _OPEN_ — No branch/tag policy.
- [~] **M32-010** Define mandatory CI gates: unit, integration, security, fuzz, concurrency, compatibility, performance, packaging, SBOM/provenance.  
  _PARTIAL_ — OPERATIONS.md §5.1 lists CI/bench/SBOM only; not security/fuzz/concurrency/packaging gates.
- [ ] **M32-011** Define release candidate creation process.  
  _OPEN_ — Not defined.
- [~] **M32-012** Require change log/release notes including breaking/security/operational changes.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: CHANGELOG.md exists; no requirement policy.
- [ ] **M32-013** Require compatibility matrix update when applicable.  
  _OPEN_ — Not required anywhere.
- [!] **M32-014** Require artifact signing and provenance verification.  
  _BLOCKED_ — Signing unavailable.
- [!] **M32-015** Define approver roles for production promotion.  
  _BLOCKED_ — Approver roles UNASSIGNED; owner needed.

### Canary/staged rollout
- [~] **M32-016** Define rollout stages and population percentages/scopes.  
  _DOCUMENTED_ — OPERATIONS.md §5: canary 1 node 5%, then 25/50/100%.
- [~] **M32-017** Define automatic and manual promotion criteria.  
  _PARTIAL_ — Abort criteria stated; promotion criteria not automatic/manual split.
- [~] **M32-018** Define SLO/error/saturation/security signals that halt promotion.  
  _PARTIAL_ — OPERATIONS.md §5.2 halts on signature-mismatch/record_rejects only; no SLO/saturation signals.
- [~] **M32-019** Define minimum observation period per stage.  
  _DOCUMENTED_ — OPERATIONS.md §5: 30 min per stage.
- [~] **M32-020** Support draining old instances safely.  
  _PARTIAL_ — drain() now refuses new work and waits for in-flight; TOCTOU: Node.handle checks health.draining before Admission.acquire in Node._execute, so a call past the check but not yet admitted is invisible to drain()'s inflight==0 wait and can execute after drain() returns True; new-connection refusal while draining is untested; no in-flight drain test.
- [!] **M32-021** Verify mixed-version compatibility during rollout.  
  _BLOCKED_ — Only one version exists; mixed-version fleets unavailable.
- [ ] **M32-022** Preserve ability to pause without continuing background rollout.  
  _OPEN_ — Not defined.

### Rollback
- [ ] **M32-023** Define rollback trigger thresholds.  
  _OPEN_ — No rollback thresholds.
- [!] **M32-024** Maintain last-known-good signed artifact/config references.  
  _BLOCKED_ — No signed artifacts.
- [~] **M32-025** Define rollback command/procedure and required permissions.  
  _PARTIAL_ — OPERATIONS.md §5.4 procedure; permissions not defined.
- [ ] **M32-026** Define persisted-state/schema rollback constraints.  
  _OPEN_ — Not defined.
- [ ] **M32-027** Verify rollback under active traffic.  
  _OPEN_ — Not tested.
- [ ] **M32-028** Record rollback events in audit/release history.  
  _OPEN_ — ConfigStore.rollback not audited.
- [ ] **M32-029** Require post-rollback validation before declaring recovery complete.  
  _OPEN_ — Not required.

### Emergency disable / kill switch
- [~] **M32-030** Define scope: function, interface, tenant, node, version, feature, or entire service.  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: OPERATIONS.md §5.5 emergency disable at node level only (drain, remove component).
- [ ] **M32-031** Require strong authentication/authorization for activation.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No authN/Z on drain().
- [ ] **M32-032** Ensure emergency disable works when normal control plane is degraded if required.  
  _OPEN_ — Not defined.
- [~] **M32-033** Define fail-safe local mechanism where justified.  
  _PARTIAL_ — LeaseTable.freeze local quarantine; not a service kill switch.
- [ ] **M32-034** Audit activation/deactivation with actor/reason/time.  
  _OPEN_ — Unchanged after 4.3.0 re-check: drain() not audited.
- [ ] **M32-035** Test kill switch under overload and dependency outage.  
  _OPEN_ — Unchanged after 4.3.0 re-check: Not tested.
- [ ] **M32-036** Define re-enable validation/approval procedure.  
  _OPEN_ — Not defined.

### Incident response
- [~] **M32-037** Define severity taxonomy.  
  _DOCUMENTED_ — OPERATIONS.md §6 SEV1-3.
- [!] **M32-038** Define paging/escalation targets.  
  _BLOCKED_ — Paging roster UNASSIGNED.
- [ ] **M32-039** Create runbooks for auth outage, policy outage, cert expiry, transport outage, overload, latency spike, error spike, partition/failover, audit loss, and suspected compromise.  
  _OPEN_ — Unchanged after 4.3.0 re-check: No runbooks.
- [ ] **M32-040** Define evidence preservation/log/trace/audit collection steps.  
  _OPEN_ — Not defined.
- [!] **M32-041** Define customer/tenant communication ownership where applicable.  
  _BLOCKED_ — Owner needed.
- [!] **M32-042** Conduct tabletop exercises.  
  _BLOCKED_ — Requires humans.
- [!] **M32-043** Require post-incident review with tracked corrective actions.  
  _BLOCKED_ — Requires owner/process.

### Vulnerability/security lifecycle
- [ ] **M32-044** Define vulnerability reporting channel.  
  _OPEN_ — No reporting channel.
- [ ] **M32-045** Define triage severity model.  
  _OPEN_ — Not defined.
- [~] **M32-046** Define remediation SLA by severity.  
  _PARTIAL_ — OPERATIONS.md §7 'proposed' SLA critical 7d/high 30d, unapproved.
- [ ] **M32-047** Define coordinated disclosure process where applicable.  
  _OPEN_ — Not defined.
- [~] **M32-048** Define emergency dependency/artifact revocation process.  
  _DOCUMENTED_ — Unchanged after 4.3.0 re-check: DEPENDENCIES.md Update policy: revocation of compromised revision.
- [ ] **M32-049** Define supported-version security patch policy.  
  _OPEN_ — Not defined.
- [ ] **M32-050** Define EOL notification timeline.  
  _OPEN_ — Not defined.
- [ ] **M32-051** Track known vulnerabilities/risk acceptances to closure.  
  _OPEN_ — No vulnerability tracking.

### Maintenance/EOL
- [ ] **M32-052** Define supported release branches and maintenance duration.  
  _OPEN_ — Not defined.
- [ ] **M32-053** Define runtime/OS/dependency EOL response.  
  _OPEN_ — Not defined.
- [ ] **M32-054** Define data/config migration path between supported major versions.  
  _OPEN_ — Not defined.
- [~] **M32-055** Define deprecation warning mechanism and timeline.  
  _PARTIAL_ — DEPRECATED_VERSIONS tuple in security.py ('accepted but logged' - no logging implemented); no timeline.
- [ ] **M32-056** Archive release artifacts/SBOM/provenance for required duration.  
  _OPEN_ — Not defined.

### Review cadence
- [~] **M32-057** Schedule periodic architecture review.  
  _PARTIAL_ — OPERATIONS.md §7 proposed quarterly architecture review; not scheduled/owned.
- [ ] **M32-058** Schedule threat-model/security review.  
  _OPEN_ — No threat-model review cadence.
- [ ] **M32-059** Schedule SLO/capacity review.  
  _OPEN_ — Not defined.
- [~] **M32-060** Schedule dependency/SBOM review.  
  _PARTIAL_ — DEPENDENCIES.md 'review monthly'; proposed.
- [ ] **M32-061** Schedule DR/restore/failover exercise.  
  _OPEN_ — Not defined.
- [ ] **M32-062** Schedule runbook/tabletop review.  
  _OPEN_ — Not defined.
- [!] **M32-063** Record review decisions and action owners.  
  _BLOCKED_ — Needs action owners.

### Exception/waiver register
- [~] **M32-064** Create a versioned register for unmet requirements.  
  _PARTIAL_ — OPERATIONS.md §7 and CHANGELOG point to CHECKLIST_STATUS.json, which is still absent; tools/checklist_status.py can build it but has not.
- [ ] **M32-065** Require requirement/control ID, rationale, risk, compensating controls, owner, approver, creation date, review date, and expiry.  
  _OPEN_ — Fields not required.
- [ ] **M32-066** Prohibit indefinite waivers without reapproval.  
  _OPEN_ — Not stated.
- [~] **M32-067** Surface active high-risk waivers in production-exit review.  
  _PARTIAL_ — OPERATIONS.md §8 lists blockers; no waiver surfacing.
- [ ] **M32-068** Link waivers to technical-debt items and remediation milestones.  
  _OPEN_ — Not linked.

### Technical-debt register
- [~] **M32-069** Record debt item, impacted component/requirement, severity, operational/security effect, owner, target release, and acceptance criteria.  
  _PARTIAL_ — Tech-debt list in OPERATIONS.md §7 lacks owner/severity/target/acceptance.
- [ ] **M32-070** Distinguish intentional simplification from unknown/untriaged defect.  
  _OPEN_ — Not distinguished.
- [ ] **M32-071** Track debt aging and missed remediation dates.  
  _OPEN_ — No aging.
- [ ] **M32-072** Escalate debt that threatens SLO/security/supportability.  
  _OPEN_ — No escalation rule.

### Formal production exit gate
- [!] **M32-073** Create a signed/versioned production-readiness checklist.  
  _BLOCKED_ — Signing and approver unavailable.
- [!] **M32-074** Require all M01–M32 Definition-of-Done gates to be satisfied, out-of-scope by approved architecture decision, or covered by time-bounded waiver.  
  _BLOCKED_ — Many DoD gates blocked (pk_core, owner, CI).
- [!] **M32-075** Require zero unresolved critical/high security findings unless formally risk-accepted by authorized role.  
  _BLOCKED_ — Independent security review not performed (THREAT_MODEL.md).
- [!] **M32-076** Require Tier-1 compatibility matrix pass.  
  _BLOCKED_ — CI matrix never executed.
- [~] **M32-077** Require performance/capacity evidence against current target workload.  
  _PARTIAL_ — Single-host bench/soak only.
- [~] **M32-078** Require fault/soak/DR evidence.  
  _PARTIAL_ — 60s soak with growth; no DR.
- [!] **M32-079** Require packaging/bootstrap/rollback evidence from clean environments.  
  _BLOCKED_ — No clean env/artifacts.
- [!] **M32-080** Require SBOM/provenance/signature verification.  
  _BLOCKED_ — No signing.
- [!] **M32-081** Require dashboards/alerts/runbooks and on-call ownership.  
  _BLOCKED_ — On-call UNASSIGNED; no dashboards/runbooks.
- [!] **M32-082** Record final approver roles, release artifact digests, configuration schema/hash, and date.  
  _BLOCKED_ — Approvers UNASSIGNED.

### Definition of Done / Acceptance Gates
- [!] **M32-083** SLOs, alerts, error budgets, runbooks, ownership, and incident process are operational.  
  _BLOCKED_ — Ownership UNASSIGNED.
- [!] **M32-084** Releases use staged promotion with tested rollback and emergency-disable controls.  
  _BLOCKED_ — No real rollout infra; rollback/kill untested.
- [~] **M32-085** Security vulnerability, dependency, and EOL lifecycle is documented and enforced.  
  _PARTIAL_ — Partly documented (DEPENDENCIES.md, OPERATIONS.md §7), not enforced.
- [!] **M32-086** Active exceptions/debt are explicitly reviewed, owned, and time-bounded.  
  _BLOCKED_ — Needs owners.
- [~] **M32-087** Production readiness is decided from evidence attached to a formal exit-gate artifact—not from repository completeness claims alone.  
  _DOCUMENTED_ — OPERATIONS.md §8 states production NOT authorised pending listed blockers (no exit-gate artifact).
- [!] **M32-088** M01 — `pk_core` dependency and reproducible dependency manifest  
  _BLOCKED_ — pk_core source unknown/absent.
- [!] **M32-089** M02 — Historical master-source artifact / formal replacement  
  _BLOCKED_ — MASTER.md absent; owner must supply or supersede (MASTER_SOURCE.md).
- [~] **M32-090** M03 — Real cross-host network transport adapter  
  _PARTIAL_ — Node/Client TCP tested on loopback + two processes; not cross-host.
- [~] **M32-091** M04 — WIT parser/bindings and canonical wire serialization  
  _PARTIAL_ — wit.py/codec.py tested; resources/flags unsupported, no bindings.
- [~] **M32-092** M05 — Protocol negotiation and compatibility matrix  
  _PARTIAL_ — negotiate tested; compatibility matrix single version.
- [~] **M32-093** M06 — Peer/node/workload authentication  
  _PARTIAL_ — PSK mutual auth tested; no PKI/mTLS (T-12).
- [~] **M32-094** M07 — Authorization/capability enforcement  
  _PARTIAL_ — Local Authorizer tested; INV-65 absent.
- [~] **M32-095** M08 — Transport encryption/key lifecycle  
  _PARTIAL_ — AES-GCM tested; no forward secrecy, no rekey (T-11).
- [~] **M32-096** M09 — Replay/spoofing defenses and request identity  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Seq replay tested; ReplayWindow.check_request never used by Node.
- [~] **M32-097** M10 — Cancellation/idempotency/retry/reconnect semantics  
  _PARTIAL_ — Idempotency (digest-bound, transient not cached) and retry-after tested; cancellation still not wired into Node/Client.
- [~] **M32-098** M11 — Backpressure/admission control/circuit breaking  
  _PARTIAL_ — Admission/breaker tested; idempotency cap now evicts instead of refusing; evidence/soak.json (regenerated): RSS 25,784->110,392 KB over 60 s/131,413 calls; OPERATIONS.md §4 attributes it to the 100k idempotency cache but no run shows RSS plateauing.
- [~] **M32-099** M12 — Configuration subsystem/provenance  
  _PARTIAL_ — ConfigStore tested; no hot reload into Node.
- [~] **M32-100** M13 — Tamper-evident audit event pipeline  
  _PARTIAL_ — Audit chain + bounded window tested; audit-writable now real and fail-closed for authz; off-host head not implemented; non-authz audit failures fail open.
- [~] **M32-101** M14 — Health/readiness/dependency status  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Health tested; no probe endpoint.
- [~] **M32-102** M15 — Production metrics exporter  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Metrics render tested; no exporter endpoint.
- [x] **M32-103** M16 — Structured operational logging  
  _LOCALLY_VERIFIED_ — ops.JsonLogger; test_controls_ops.OpsTest.test_logger_redacts_truncates_filters_ratelimits (M16 local scope).
- [~] **M32-104** M17 — Distributed trace propagation  
  _PARTIAL_ — traceparent tested; cross-layer propagation unverified.
- [~] **M32-105** M18 — Telemetry retention/privacy/export policy  
  _PARTIAL_ — TELEMETRY_POLICY.md retention 'proposals pending an owner'.
- [~] **M32-106** M19 — Failover/partition/split-brain/duplicate-execution controls  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: LeaseTable tested; multi-node idempotency not implemented (OPERATIONS.md §4).
- [~] **M32-107** M20 — Durable/restart/replay semantics  
  _PARTIAL_ — Unchanged after 4.3.0 re-check: Journal tested; per-node only.
- [~] **M32-108** M21 — Requirements specification/traceability matrix  
  _PARTIAL_ — REQUIREMENTS.md matrix exists; tools/checklist_status.py now exists but --check crashes (CHECKLIST_STATUS.json absent).
- [!] **M32-109** M22 — Owner/escalation/ADR  
  _BLOCKED_ — Owner/approver UNASSIGNED (ADR-0001 PROPOSED).
- [!] **M32-110** M23 — Security architecture/adversarial test suite  
  _BLOCKED_ — Independent review not performed.
- [~] **M32-111** M24 — Parser/protocol fuzzing/property tests  
  _PARTIAL_ — Seconds-long fuzz only (THREAT_MODEL T-14).
- [~] **M32-112** M25 — Concurrency/race-condition tests  
  _PARTIAL_ — See M25: partial.
- [!] **M32-113** M26 — Adjacent-layer integration tests  
  _BLOCKED_ — Neighbours absent.
- [!] **M32-114** M27 — Cross-runtime/cross-architecture certification  
  _BLOCKED_ — CI/multi-arch unavailable.
- [~] **M32-115** M28 — Performance/capacity/power/regression certification  
  _PARTIAL_ — Single-host bench; power unmeasured.
- [~] **M32-116** M29 — Fault-injection/soak/disaster/degraded-control-plane tests  
  _PARTIAL_ — See M29: partial.
- [!] **M32-117** M30 — Supply-chain provenance/artifact verification/SBOM  
  _BLOCKED_ — Signing/CI unavailable.
- [!] **M32-118** M31 — Production packaging/bootstrap artifact  
  _BLOCKED_ — No clean env/artifacts.
- [!] **M32-119** M32 — Formal operations/release/governance package  
  _BLOCKED_ — Owners/approvers UNASSIGNED.
- [~] **M32-120** Requirements/traceability matrix exported and complete.  
  _PARTIAL_ — docs/REQUIREMENTS.md now 31 reqs; not complete against checklist; CHECKLIST_STATUS.json absent.
- [!] **M32-121** Architecture and security ADRs approved.  
  _BLOCKED_ — ADR-0001 PROPOSED, approver UNASSIGNED.
- [~] **M32-122** Threat model and adversarial suite current.  
  _PARTIAL_ — THREAT_MODEL.md present; suite green (117 run, 4 skipped); T-11/T-12 open; no independent review.
- [!] **M32-123** All Tier-1 tests pass with zero unexpected skips.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: Tier-1 CI not executed; 4 local skips (pk_core).
- [~] **M32-124** Integration, interoperability, concurrency, fuzz, performance, soak, fault, and recovery evidence archived.  
  _PARTIAL_ — bench/soak only; no archived integration/interop/recovery evidence.
- [!] **M32-125** SBOM, provenance, release manifest, checksums, and signatures generated and verified.  
  _BLOCKED_ — Signing unavailable; no manifest.
- [!] **M32-126** Clean-node install/upgrade/rollback evidence archived.  
  _BLOCKED_ — Unchanged after 4.3.0 re-check: No clean nodes.
- [~] **M32-127** Current configuration schema and production config provenance recorded.  
  _PARTIAL_ — Schema in ops.SCHEMA; no production config provenance recorded.
- [!] **M32-128** Dashboards, alerts, runbooks, ownership, and escalation paths validated.  
  _BLOCKED_ — Ownership/on-call UNASSIGNED.
- [!] **M32-129** Active waivers/risk acceptances reviewed and unexpired.  
  _BLOCKED_ — Waiver register empty/approver absent.
- [!] **M32-130** Release artifact digest and production approval recorded.  
  _BLOCKED_ — No approver/artifact.
