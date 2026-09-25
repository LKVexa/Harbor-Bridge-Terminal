# INV-13 System Interface v4.2.0 — Production Missing-Component Engineering Checklists

**Source baseline:** INV-13 System Interface v4.2.0 hardened reference package  
**Checklist version:** 1.0.0  
**Scope:** MC-001 through MC-032 from the v4.2.0 missing-production-components register  
**Intended use:** architecture review, implementation planning, security review, verification, release gating, and production-readiness evidence collection.

## Checklist conventions

- `[ ]` = not yet evidenced; `[x]` = objectively evidenced and reviewed.
- **P0** items block a credible production security boundary.
- **P1** items block normal production readiness/certification.
- **P2** items are maturity, assurance, or constrained-environment capabilities.
- A checkbox is complete only when implementation/configuration **and** reproducible evidence exist.
- Mock-only, prose-only, or unreviewed evidence does not close P0/P1 items.
- Every production artifact should be versioned, attributable to a release, and retained with its verification output.

---

## MC-001 — Concrete versioned WIT/world definitions — P0

> **v4.3.0 execution status: PARTIAL** — evidence: `wit/inv13-system-interface.wit`, `WIT.lock`, `APPROVED_SURFACE.json`, `host/wit_surface.py`, `tests/test_wit_wasm.py::WitSurface`
> **Open gaps:** No wit-bindgen generated bindings, canonical-ABI validation, cross-language conformance or generated docs (toolchain absent); security approval of the world set pending named reviewers.

**Objective:** Establish the exact, versioned component contract that defines the authority and ABI exposed to guest components.

- [x] **Target selection:** Declare the exact WASI proposal/profile and component-model version(s) supported, including any preview/revision identifiers and vendor extensions.
- [x] **Package namespace:** Define stable WIT package namespaces, semantic versions, ownership, and publication location; prohibit ambiguous unversioned imports in release builds.
- [x] **World decomposition:** Split worlds by least-privilege role rather than convenience; document why every imported interface is required by each workload class.
- [x] **Capability mapping:** Map every WIT import/export to the corresponding INV-13 capability token and enforcement path; identify any interface that implies multiple authorities.
- [~] **Type design:** Define resource, record, variant, enum, flag, option, result, stream, future, and error types with explicit size/semantic constraints.
- [~] **Resource ownership:** Encode owned versus borrowed resources intentionally; document transfer, drop, aliasing, and lifetime expectations.
- [x] **Error surface:** Use stable typed errors; ensure host-internal paths, errno details, secrets, stack traces, and implementation-specific identifiers cannot cross unintentionally.
- [~] **String/byte semantics:** Specify encoding, normalization, maximum lengths, invalid-sequence behavior, and binary-vs-text distinctions for every externally supplied string/byte field.
- [x] **Compatibility policy:** Define allowed additive changes, forbidden breaking changes, deprecation windows, migration rules, and version-negotiation behavior.
- [x] **Locking/pinning:** Check in exact WIT dependency locks or immutable digests so generated bindings are reproducible.
- [ ] **Code generation:** Pin generator versions and flags; generate bindings for every supported host language/runtime and fail CI on uncommitted generated diffs.
- [ ] **Canonical ABI validation:** Verify generated lowering/lifting behavior for strings, lists, resources, reallocations, alignment, discriminants, and trap/error propagation.
- [x] **Surface-diff gate:** Add CI that computes the declared world surface and fails on unauthorized import/export additions.
- [x] **Negative contract tests:** Prove components importing undeclared or unsupported interfaces fail instantiation without acquiring fallback/ambient authority.
- [~] **Schema fuzzing:** Fuzz malformed component metadata, oversized type values, invalid discriminants, and hostile nested structures at the WIT boundary.
- [ ] **Cross-language conformance:** Round-trip representative calls through at least two independent generated binding stacks when multiple languages are supported.
- [ ] **Documentation generation:** Produce human-readable interface docs directly from the versioned WIT source; do not maintain divergent handwritten signatures.
- [x] **Release tagging:** Bind the WIT package version and content digest into release metadata, SBOM, and runtime compatibility manifest.
- [~] **Review ownership:** Require architecture and security approval for any world expansion that increases authority.
- [~] **Deprecation tests:** Maintain fixtures for previous supported interface versions and prove promised compatibility behavior.

**Exit evidence**
- [~] Immutable WIT source and dependency lock are present in the release.
- [ ] Generated binding artifacts reproduce bit-for-bit or normalize to an approved deterministic representation.
- [~] Contract/conformance tests pass against the production runtime adapter.
- [ ] Security review confirms the exposed world equals the approved least-authority design.

---

## MC-002 — Real WASI host/runtime adapter — P0

> **v4.3.0 execution status: PARTIAL** — evidence: `host/runtime_adapter.py`, `host/adapter_v8.mjs`, `host/wasm_loader.py`, `tests/test_wit_wasm.py::V8Adapter`
> **Open gaps:** Engine is V8 via Node for core Wasm only (process-per-run, wall-time limit, no fuel/memory caps inside the engine); Component-model binaries refused; no Wasmtime binding, canonical ABI, multi-runtime tests; fs/net/http providers not yet bound into the engine import table.

**Objective:** Replace reference-only policy logic with a production adapter that instantiates components in selected Wasm runtimes while preserving capability boundaries.

- [~] **Runtime selection:** Document supported runtime(s), exact versions, security-support policy, embedding API, and required feature flags.
- [x] **Adapter boundary:** Define one narrow host abstraction between INV-13 policy decisions and runtime-specific APIs; prohibit policy logic from being duplicated inconsistently in runtime glue.
- [x] **Component loading:** Validate component/module format, target features, declared imports/exports, size limits, and signatures/digests before instantiation.
- [x] **Instantiation sequence:** Specify order for identity validation, policy evaluation, resource-table creation, preopen construction, provider binding, and guest start.
- [x] **World enforcement:** Bind only the interfaces granted by the approved world; do not register broad host functions and rely on guest non-use.
- [ ] **Canonical ABI:** Verify lowering/lifting, memory ownership, realloc handling, resource indices, traps, and host exception conversion.
- [~] **Store/isolate design:** Ensure tenant/workload state is isolated per store/instance as appropriate; prevent cross-instance resource-table access.
- [~] **Lifecycle:** Define create/start/ready/drain/stop/drop states and legal transitions; make teardown idempotent.
- [~] **Fuel/epoch limits:** Configure execution quotas, interruption, epoch/fuel accounting, and runaway guest handling where supported.
- [ ] **Memory limits:** Enforce linear-memory/table/instance limits and deterministic failure on limit breach.
- [x] **Provider injection:** Inject clock/random/network/filesystem/http providers only through explicit capabilities and validated configuration.
- [x] **Trap classification:** Translate runtime traps into the structured INV-13 error taxonomy without leaking host internals.
- [x] **Panic containment:** Ensure guest traps or provider exceptions cannot crash the hosting process or corrupt adjacent instances.
- [ ] **Cancellation:** Propagate cancellation and shutdown signals across guest/host async boundaries without orphaning resources.
- [ ] **Hot-path locking:** Review adapter synchronization for reentrancy, deadlock, resource-table races, and callback inversion.
- [~] **Version negotiation:** Refuse unsupported runtime/component/WIT combinations before workload execution.
- [x] **Security defaults:** Disable runtime features not required by the declared target, including experimental host integrations that create ambient authority.
- [~] **Integration tests:** Execute real components exercising every granted/denied interface, teardown path, trap path, and resource-lifecycle path.
- [ ] **Multi-runtime tests:** If more than one runtime is supported, run identical conformance suites and document semantic differences.
- [~] **Operational diagnostics:** Emit runtime version, component digest, world version, policy version, instance ID, and termination classification in safe structured telemetry.

**Exit evidence**
- [ ] Production adapter compiles/packages against pinned runtime versions.
- [ ] Full adjacent-layer integration suite passes with no mock runtime.
- [~] Denied capabilities are demonstrably unregistered/unreachable.
- [~] Failure injection proves guest faults do not create authority expansion or cross-instance contamination.

---

## MC-003 — Descriptor/handle-relative filesystem resolver — P0

> **v4.3.0 execution status: IMPLEMENTED (POSIX host provider)** — evidence: `host/fs.py`, `tests/test_fs_descriptor.py`, `docs/adr/ADR-003-filesystem-strategy.md`
> **Open gaps:** Windows handle-relative implementation absent (fails closed); FIFO/device special-file policy only via O_NOFOLLOW + type checks on read; independent static review pending.

**Objective:** Enforce filesystem confinement using already-open directory handles/descriptors rather than string-reconstructed host paths.

- [x] **Descriptor-root model:** Represent each preopen with an authoritative open directory handle plus immutable metadata, not only a host path string.
- [~] **Open-time validation:** Open preopen roots under privileged setup code, validate directory type/ownership/policy, then drop unnecessary broader authority.
- [x] **Relative traversal:** Resolve guest paths relative to the preopen descriptor using platform-safe handle-relative APIs.
- [x] **No string re-resolution:** Prohibit joining a validated string path and reopening it through the process CWD/root namespace.
- [x] **Symlink policy:** Define whether symlinks are forbidden, followed only beneath the same descriptor tree, or supported under a controlled resolver; test each rule.
- [x] **TOCTOU resistance:** Use open-at/handle-relative semantics and post-open verification so path validation and object use cannot be separated by rename/swap races.
- [x] **Parent traversal:** Reject or safely resolve `..` components without escaping the preopen root, including encoded/unicode edge cases where applicable.
- [x] **Absolute paths:** Reject guest absolute/rooted paths and platform-specific rooted forms before host API invocation.
- [~] **Special files:** Define policy for devices, FIFOs, sockets, procfs/sysfs, reparse points, mount points, named streams, and other non-regular filesystem objects.
- [x] **Mount boundary:** Decide whether traversal may cross mount/volume boundaries; enforce using stable filesystem identity when the platform permits.
- [ ] **Windows semantics:** Explicitly handle drive-relative paths, UNC paths, device namespaces, junctions/reparse points, case folding, alternate data streams, and reserved names.
- [x] **POSIX semantics:** Handle hard links, symlinks, bind mounts, deleted-but-open directories, rename races, and permission changes safely.
- [x] **Descriptor rights:** Associate read/write/create/delete/metadata rights with each preopen and check rights before each operation.
- [x] **Creation semantics:** For create/rename/link operations, keep both source and destination authority handle-relative and verify atomicity expectations.
- [x] **Deletion semantics:** Prevent deletion/rename operations from escaping via attacker-controlled directory mutation.
- [x] **Revocation:** Define behavior of already-open descendant handles after preopen revocation; make the choice explicit and test it.
- [x] **Path limits:** Bound component count, byte length, nesting depth, symlink depth, and expansion work to prevent algorithmic DoS.
- [x] **Race harness:** Build adversarial tests that continuously swap symlinks, rename directories, replace mount points, and mutate parents during operations.
- [~] **Privilege tests:** Run tests as unprivileged and elevated users to detect accidental reliance on host-wide privileges.
- [~] **Audit fields:** Log stable preopen ID, relative guest path classification, operation, result, and denial reason without emitting sensitive full host paths by default.

**Exit evidence**
- [x] No production filesystem operation reopens a resource by concatenated host path.
- [x] Symlink/rename/mount-race adversarial suite passes on every supported OS/filesystem class.
- [~] Static review confirms descriptor rights and revocation rules are enforced at each filesystem syscall boundary.
- [~] Security test demonstrates a hostile guest cannot escape a preopen under concurrent filesystem mutation.

---

## MC-004 — Capability-descriptor integration — P0

> **v4.3.0 execution status: IMPLEMENTED (reference table; INV-42 service external)** — evidence: `host/descriptors.py`, `tests/test_authz.py::Descriptors`, `tests/test_adversarial.py::Races`
> **Open gaps:** No expiry, persistence, reconciliation, serialization/migration; authoritative INV-42 service must implement the DescriptorTable interface.

**Objective:** Bind INV-13 authority decisions to the authoritative capability-descriptor system with stable identity, provenance, ownership, and revocation semantics.

- [x] **Descriptor schema:** Define versioned descriptor fields for capability kind, scope, rights, owner, issuer, subject, provenance, expiry, revocation state, and stable ID.
- [x] **Stable identity:** Use non-reusable opaque descriptor IDs; prevent stale IDs from resolving to newly allocated authority.
- [x] **Binding:** Map each `World` capability and preopen to one or more authoritative descriptors; eliminate shadow authority represented only in local mutable state.
- [~] **Issuance policy:** Permit descriptor issuance only after authenticated policy approval; record issuer, policy version, request ID, and reason.
- [x] **Ownership:** Define whether descriptors are owned, borrowed, delegated, or shared; enforce transfer rules in code.
- [x] **Inheritance:** Specify whether child components/processes/instances inherit descriptors; default to no inheritance unless explicitly authorized.
- [x] **Delegation:** If delegation is supported, constrain attenuation so children cannot gain rights absent from the parent descriptor.
- [x] **Revocation:** Support targeted revocation by descriptor ID, workload, tenant, capability class, or policy release; define propagation latency.
- [~] **Generation protection:** Include generation/epoch checks so resource-ID reuse cannot resurrect revoked capability state.
- [ ] **Expiry:** Enforce descriptor TTL/lease semantics at use time, not only at grant time.
- [x] **Provenance chain:** Preserve immutable links from active authority to configuration, policy decision, issuer identity, workload identity, and release.
- [ ] **Serialization:** If descriptors cross process/node boundaries, use authenticated canonical serialization and reject unknown critical fields.
- [ ] **Confidentiality:** Avoid placing host paths, secrets, or sensitive tenant metadata in bearer-visible descriptor material unless required.
- [ ] **Persistence:** Define whether descriptors survive host restart; if yes, protect storage integrity and replay semantics.
- [ ] **Reconciliation:** Compare local descriptor state with authoritative control-plane state after reconnect/restart and fail closed on ambiguity.
- [x] **Concurrency:** Make issue/use/revoke/expire operations linearizable or document weaker guarantees with compensating controls.
- [~] **Audit:** Emit descriptor lifecycle events with actor, subject, policy version, old/new state, and reason code.
- [x] **API abuse tests:** Fuzz descriptor IDs, stale generations, forged serialized descriptors, duplicate issuance, and revocation races.
- [x] **Cross-component tests:** Verify filesystem/network/http/resource-table adapters all consult the same descriptor authority.
- [ ] **Migration:** Define conversion from legacy local capabilities/preopens to descriptors without broadening rights.

**Exit evidence**
- [~] Every active production capability can be traced to one authoritative descriptor/provenance chain.
- [x] Revocation tests prove new operations are denied within the documented revocation SLA.
- [x] Stale/reused descriptor identifiers cannot regain authority.
- [ ] Security review verifies no parallel authority path bypasses the descriptor system.

---

## MC-005 — Authorization policy enforcement point — P0

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/policy.py`, `tests/test_authz.py::Policy`, `tests/test_adversarial.py::Fuzz.test_policy_property_no_undeclared_authority`
> **Open gaps:** No policy simulation/dry-run tooling, no decision caching, policy bundles unsigned, independent tenant-isolation review pending.

**Objective:** Decide and enforce exactly which capabilities, descriptors, worlds, and preopens a workload may receive.

- [x] **Policy model:** Define subjects, resources, actions, conditions, tenant boundaries, environment, risk context, and explicit deny semantics.
- [x] **Deny by default:** Treat missing policy, parse failure, dependency outage, unknown subject, and unknown capability as deny unless an approved emergency mode says otherwise.
- [x] **Decision API:** Expose a versioned authorization decision interface returning allow/deny plus stable machine-readable reason and policy revision.
- [x] **Pre-instantiation gate:** Require successful authorization before runtime adapter/provider registration or descriptor issuance.
- [x] **Use-time checks:** Identify authorities requiring continuous/use-time checks versus grant-time-only evaluation and justify each choice.
- [x] **Tenant isolation:** Include immutable tenant/workspace scope in every request and reject cross-tenant identifiers before rule evaluation.
- [x] **Policy input validation:** Canonicalize and bound all policy inputs; reject duplicate/ambiguous fields and untrusted derived claims.
- [x] **Policy provenance:** Version/sign policy bundles and record author, approver, deployment, digest, and effective interval.
- [~] **Separation of duties:** Require review/approval for policy changes that add capability classes, wildcard resources, or broad tenant scope.
- [ ] **Simulation:** Provide dry-run impact analysis showing newly allowed/denied subjects and capabilities before activation.
- [x] **Atomic activation:** Activate policy as an immutable snapshot so one decision cannot observe mixed revisions.
- [x] **Rollback:** Support immediate rollback to a known-good policy snapshot and preserve audit linkage.
- [x] **Reason safety:** Return useful reason codes without exposing policy internals that help an attacker enumerate protected resources.
- [ ] **Caching:** If decisions are cached, bind cache keys to all security-relevant inputs, enforce TTL, and invalidate on revocation/policy changes.
- [x] **Emergency controls:** Define break-glass workflows, scoped duration, required approvers, enhanced logging, and automatic expiry.
- [x] **Property tests:** Assert invariants such as “no undeclared world capability is ever allowed” and “tenant A policy cannot authorize tenant B resource.”
- [~] **Mutation tests:** Verify policy parser/evaluator tests fail when allow/deny branches, tenant predicates, or capability predicates are altered.
- [x] **Outage tests:** Simulate policy-store/network/control-plane failure and prove no ambient fallback authorization occurs.
- [~] **Decision telemetry:** Measure allow/deny/error latency, cache behavior, policy revision, and reason-class rates without leaking sensitive request content.
- [ ] **Periodic review:** Automate detection of unused grants, broad wildcards, stale exceptions, and expired workload identities.

**Exit evidence**
- [x] Policy decisions are required and enforced on the real production instantiation path.
- [x] Outage and malformed-policy tests fail closed.
- [ ] Policy release artifacts are signed/versioned and can be rolled back atomically.
- [ ] Independent review confirms tenant and least-authority invariants.

---

## MC-006 — Host/control-plane identity and attestation — P0

> **v4.3.0 execution status: PARTIAL (reference HMAC identity; PKI/attestation external)** — evidence: `host/identity.py`, `tests/test_authz.py::Identity`
> **Open gaps:** Shared-key HMAC is not production identity; no X.509/SPIFFE, key custody, revocation lists, channel binding or real TEE verifier. Fuzzing found and fixed a token-malleability defect (non-canonical base64).

**Objective:** Authenticate runtime nodes, control-plane actors, and workloads before authority is issued or accepted.

- [~] **Identity taxonomy:** Define node, runtime process, control-plane service, operator, tenant, workload, and component identities and their trust relationships.
- [~] **Credential type:** Select mutually authenticated credential mechanisms appropriate to deployment, with rotation and revocation support.
- [x] **Workload binding:** Bind workload identity to component digest, deployment identity, tenant, policy scope, and runtime instance.
- [ ] **Node identity:** Provision unique node identities; prohibit shared static credentials across hosts.
- [~] **Attestation scope:** Define when hardware/VM/container/runtime attestation is required and which measurements/claims are authoritative.
- [~] **Verifier policy:** Pin accepted roots, algorithms, measurements, freshness windows, nonce/challenge requirements, and revocation data.
- [x] **Freshness:** Reject replayed/stale attestations using nonces, timestamps/epochs, or verifier-issued challenges.
- [x] **Failure behavior:** Deny privileged capability issuance when required identity or attestation is missing, unverifiable, expired, or revoked.
- [ ] **Bootstrap:** Define first-trust enrollment without embedding universal secrets in images or installers.
- [~] **Rotation:** Rotate credentials without restarting all workloads where feasible; handle overlap and rollback safely.
- [ ] **Revocation:** Distribute identity/attestation revocation rapidly and bind it to descriptor/policy revocation paths.
- [ ] **Key protection:** Keep private keys in protected platform keystores/HSM/TPM facilities where required; prohibit plaintext key persistence.
- [x] **Clock dependence:** Document any time-validation dependency and safe behavior when trusted time is unavailable.
- [x] **Claims minimization:** Pass only necessary identity claims into policy evaluation; prevent untrusted workload-supplied claims from becoming authoritative.
- [ ] **Channel binding:** Bind authenticated control-plane sessions to node identity and protect against credential forwarding/confused-deputy attacks.
- [ ] **Multi-tenant tests:** Prove identity from one tenant cannot request/receive descriptors scoped to another.
- [x] **Replay/forgery tests:** Exercise forged tokens, old certificates, revoked keys, modified attestations, nonce replay, and wrong audience/issuer.
- [x] **Degraded mode:** Define whether existing workloads continue during verifier outage and exactly which new grants/rotations are blocked.
- [~] **Audit:** Record identity principal, credential/attestation class, verifier result, policy revision, and issuance decision without logging secrets.
- [ ] **Incident runbook:** Define compromise response for node key theft, verifier compromise, CA/root rotation, and mass revocation.

**Exit evidence**
- [ ] Every authority grant can be tied to authenticated workload and host/control-plane identities.
- [ ] Required attestation is cryptographically verified with replay protection.
- [~] Revoked/expired identities cannot obtain new capability descriptors.
- [ ] Compromise/recovery exercises demonstrate safe credential rotation and mass revocation.

---

## MC-007 — Network/socket capability implementation — P0

> **v4.3.0 execution status: IMPLEMENTED (host provider); engine binding open** — evidence: `host/net.py`, `tests/test_net_http.py::Sockets`
> **Open gaps:** Accepted-socket inheritance, proxy semantics, UDP data path, race tests and platform matrix not done; not bound into guest ABI yet.

**Objective:** Provide explicit, least-authority network access with no ambient socket/DNS capability.

- [x] **Capability taxonomy:** Separate DNS resolution, outbound connect, inbound bind/listen/accept, datagram, raw socket, multicast, and interface-enumeration authorities.
- [x] **Address policy:** Express destination/source CIDRs, hostnames, ports, protocols, address families, and interface scopes explicitly.
- [x] **DNS authority:** Treat DNS as separate authority; define resolver sources, suffix/search behavior, caching, DNSSEC expectations, and rebinding defenses.
- [x] **Hostname binding:** Define whether authorization applies to requested hostname, resolved IP, both, or a pinned resolution set; prevent post-check DNS rebinding.
- [x] **Connect gate:** Enforce policy immediately before socket creation/connect using canonical destination data.
- [x] **Bind/listen gate:** Restrict local addresses, ports, reuse flags, wildcard binds, privileged ports, and external exposure.
- [ ] **Accepted-socket inheritance:** Define exact rights inherited by accepted connections and ensure they cannot exceed listener authority.
- [x] **Protocol restrictions:** Reject unsupported/raw protocols and dangerous socket options unless explicitly granted.
- [x] **IPv4/IPv6:** Handle mapped addresses, scope IDs, link-local addresses, NAT64, loopback, and family translation consistently.
- [~] **Local metadata protection:** Block cloud metadata/control-plane/link-local destinations by default unless specifically authorized.
- [ ] **Proxy behavior:** Define whether system/environment proxies are ignored or explicitly injected; prevent proxy variables from creating ambient egress.
- [x] **Quota:** Limit sockets, connection attempts, DNS queries, bytes, concurrent handshakes, and listener backlog per workload/tenant.
- [~] **Timeout/cancel:** Bound resolve/connect/read/write/accept time and ensure cancellation releases resources promptly.
- [ ] **TLS boundary:** If TLS is in scope, define certificate validation, trust roots, SNI/ALPN, client credentials, and revocation behavior.
- [x] **Error mapping:** Normalize host socket errors into stable capability/network error types without exposing sensitive topology.
- [x] **No ambient fallback:** Ensure denied/custom network provider failure never falls back to host-default socket APIs.
- [x] **Egress adversarial tests:** Test loopback, RFC1918, link-local, IPv6 equivalents, alternate encodings, redirects via higher layers, and DNS rebinding.
- [ ] **Race tests:** Exercise policy revocation concurrent with resolve/connect/accept and document already-open connection semantics.
- [~] **Telemetry:** Record policy class, destination category, protocol, result, bytes, duration, and denial reason with privacy controls.
- [ ] **Platform matrix:** Verify behavior across Windows/Linux/macOS socket stacks and container/network namespaces where supported.

**Exit evidence**
- [x] A component with no network capability cannot create, resolve, bind, or connect any socket path.
- [~] Destination-policy and DNS-rebinding adversarial tests pass.
- [~] Quota/timeout/revocation behavior is deterministic and evidenced.
- [ ] Network access is traceable to an explicit descriptor/policy grant.

---

## MC-008 — Environment/stdio/argument/secret boundary — P0

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/stdio_env.py`, `tests/test_providers.py::EnvStdio`
> **Open gaps:** Locale/timezone, cwd semantics, fd inheritance for spawned engine only partly (clean env passed to node), secret rotation.

**Objective:** Define and enforce exactly which process-like inputs/outputs and secret references are exposed to components.

- [x] **Environment allowlist:** Build guest environment from an explicit allowlist/template; never inherit the host process environment wholesale.
- [x] **Argument policy:** Validate argument count, byte length, encoding, forbidden control/NUL characters, and provenance.
- [x] **Secret separation:** Represent secrets as typed references/capabilities where possible rather than environment plaintext.
- [x] **Secret retrieval:** Authenticate and authorize every secret fetch; bind to workload identity, tenant, purpose, and lifetime.
- [~] **Secret lifetime:** Minimize in-memory retention; zero or release buffers where practical; avoid copies in logs/exceptions/crash dumps.
- [x] **Stdio model:** Define stdin/stdout/stderr providers, ownership, encoding/binary behavior, buffering, maximum line/frame sizes, and blocking semantics.
- [x] **Output quotas:** Bound stdout/stderr bytes/rate and define truncation/backpressure behavior to prevent log amplification DoS.
- [~] **Input quotas:** Bound stdin/message size and processing time; handle closed/broken streams deterministically.
- [x] **Redaction:** Apply structured redaction to known secret fields/tokens before logs, traces, audit events, and support bundles.
- [x] **No secret inheritance:** Prove host credentials, CI tokens, proxy secrets, cloud metadata tokens, SSH agents, and unrelated env vars are absent from guests.
- [ ] **File-descriptor inheritance:** Close or explicitly bind inherited host descriptors/handles; verify no accidental stdin-like or pipe handles leak.
- [ ] **Locale/timezone:** Treat locale, timezone, home/tmp paths, and platform variables as explicit configuration rather than implicit host inheritance.
- [ ] **Working-directory semantics:** Define guest CWD independently of host process CWD and tie it to an authorized preopen if supported.
- [ ] **Crash safety:** Ensure panic/trap/error formatting cannot dump environment, args, or secret values.
- [~] **Encoding normalization:** Decide UTF-8/binary behavior and reject ambiguous malformed encodings rather than silently converting.
- [ ] **Rotation:** Support secret rotation/revocation and document semantics for already materialized values.
- [x] **Test fixtures:** Inject canary secrets into the host environment and verify they never appear in guest-visible surfaces or telemetry.
- [ ] **Fuzzing:** Fuzz huge env/arg sets, duplicated names, case-collision on Windows, unusual Unicode, embedded NUL, and binary stdio payloads.
- [~] **Audit:** Record secret reference identifiers and access outcomes, never raw values; record environment profile/version.
- [~] **Documentation:** Publish per-world data-exposure contracts listing every environment key, argument source, stream, and secret class.

**Exit evidence**
- [x] Guest-visible env/args/stdio are produced exclusively from explicit configuration/providers.
- [x] Canary-secret leakage tests pass across logs, traces, exceptions, crash reports, and guest reads.
- [x] Secret access is identity/policy bound and revocable.
- [x] Resource/rate limits prevent unbounded stdio or environment abuse.

---
## MC-009 — Clock providers and precision policy — P0

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/clocks.py`, `tests/test_providers.py::Clocks`
> **Open gaps:** No timer/sleep API, no trusted-time dependency handling, side-channel review needs a human reviewer.

**Objective:** Provide explicit time authorities with bounded precision, deterministic behavior where required, and no accidental ambient clock access.

- [x] **Clock taxonomy:** Separate wall-clock, monotonic, process/runtime elapsed time, timer/sleep, and timezone/calendar concerns into distinct authorities.
- [x] **Provider binding:** Inject clocks only when the world grants the corresponding capability; do not expose host default clocks implicitly.
- [x] **Wall-clock semantics:** Define epoch, range, leap-second handling, timezone independence, precision, and behavior during host time corrections.
- [x] **Monotonic semantics:** Guarantee non-decreasing values within documented limits; specify suspend/resume behavior and counter wrap handling.
- [x] **Precision policy:** Establish per-world minimum/maximum resolution and rounding/jitter policy to reduce side-channel fidelity where appropriate.
- [~] **Timer API:** Bound timer counts, maximum duration, minimum granularity, cancellation behavior, and wakeup coalescing.
- [x] **Deterministic mode:** Implement a virtual/replay clock for tests and deterministic workloads; make production enablement impossible without explicit signed configuration.
- [ ] **Trusted-time dependency:** Identify features that require trusted wall time such as certificate validation, leases, or audit timestamps and define safe failure behavior.
- [x] **Backward jumps:** Specify how wall-clock regressions affect TTLs, leases, logs, and policy; never use wall time where monotonic time is required.
- [~] **Forward jumps:** Test large NTP/manual jumps and ensure timers, credential expiry, and retries behave predictably.
- [x] **Clock denial:** Return a typed capability-denied result when time is absent rather than substituting another clock source.
- [~] **Side-channel review:** Analyze whether high-resolution clocks materially increase cache/timing side channels and reduce resolution for untrusted workloads as needed.
- [ ] **Rate limits:** Prevent timer-flood or ultra-short sleep loops from causing scheduler/CPU denial of service.
- [ ] **Cross-platform normalization:** Account for Windows/POSIX timer source differences and document the common semantic contract.
- [ ] **Virtualization effects:** Test VM pause/resume, container migration, host suspend, and CPU frequency changes against monotonic guarantees.
- [x] **Error mapping:** Normalize unavailable/overflow/invalid-duration provider errors into stable machine-readable results.
- [x] **Replay tests:** Run deterministic fixtures twice and verify identical clock-observable behavior and event ordering.
- [ ] **Boundary fuzzing:** Fuzz zero, negative, huge, near-overflow, sub-resolution, and cancellation-race durations.
- [ ] **Telemetry:** Record clock-provider class, effective precision, timer saturation, and provider failures without exposing unnecessary timing detail.
- [ ] **Documentation:** Publish exactly which worlds receive which clock types and precision guarantees.

**Exit evidence**
- [x] No world without clock authority can observe host time through INV-13 providers.
- [~] Monotonic, wall-clock, precision, jump, suspend, and deterministic-mode tests pass on all supported platforms.
- [x] Deterministic test clock cannot be activated accidentally in production.
- [ ] Side-channel review approves exposed precision per workload trust class.

---

## MC-010 — Cryptographic randomness provider — P0

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/randomness.py`, `tests/test_providers.py::Randomness`
> **Open gaps:** FIPS mode and fork/snapshot reseed semantics are delegated to the OS; no dependency review sign-off.

**Objective:** Bind guest randomness to an approved CSPRNG with explicit failure, quota, and deterministic-test semantics.

- [x] **Source selection:** Use OS/runtime CSPRNG facilities approved for the deployment; prohibit non-cryptographic PRNGs for production randomness.
- [x] **Capability gating:** Expose random bytes only through an explicit capability/provider registration.
- [~] **Provider health:** Define startup and runtime behavior when the entropy source is unavailable, blocked, or reports failure.
- [x] **No silent downgrade:** Never fall back to time, PID, deterministic seed, language default PRNG, or reused buffers after CSPRNG failure.
- [x] **Request bounds:** Enforce maximum bytes per call and per time window to prevent memory/entropy-service abuse.
- [x] **Backpressure:** Define queueing or rejection under excessive demand; do not allow unbounded allocation.
- [ ] **Buffer safety:** Fully initialize returned buffers and prevent reuse of stale sensitive memory.
- [~] **Concurrency:** Verify provider thread safety and independence among workloads/tenants.
- [ ] **Fork/snapshot safety:** If applicable, ensure VM/process snapshots, fork, or restore cannot cause repeated random streams.
- [ ] **FIPS/compliance mode:** Where required, identify certified modules, runtime mode, self-test behavior, and evidence artifacts.
- [x] **Deterministic provider:** Implement deterministic seeded randomness only for test/replay, with explicit non-production type/configuration separation.
- [x] **Production guard:** Fail startup if deterministic provider is selected in production deployment profiles.
- [ ] **Seed handling:** Protect deterministic test seeds as test data and make them visible in reproducibility metadata, not hidden global state.
- [x] **Error taxonomy:** Map entropy/provider failures to stable retryable/nonretryable error codes.
- [x] **Statistical smoke tests:** Run basic health/sanity checks for catastrophic provider misuse without treating statistical tests as proof of cryptographic quality.
- [~] **Known-answer tests:** Where the underlying approved provider supports it, validate configured deterministic/DRBG modes against published vectors.
- [ ] **Isolation tests:** Demonstrate separate workloads do not receive correlated/repeated sequences due to shared buffering or seed reuse.
- [ ] **Stress tests:** Exercise large concurrent requests, cancellation, shutdown, provider failure, and memory pressure.
- [ ] **Telemetry:** Expose counts/bytes/failures/throttling only; never log generated random material.
- [ ] **Dependency review:** Track the cryptographic provider implementation/version in SBOM and vulnerability response processes.

**Exit evidence**
- [x] Production random provider is cryptographically approved and pinned.
- [x] Failure tests prove no insecure fallback occurs.
- [x] Deterministic provider is mechanically excluded from production profiles.
- [x] Load/quota tests demonstrate bounded behavior under abusive demand.

---

## MC-011 — Resource-table lifecycle — P0

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/resources.py`, `tests/test_errors_resources.py::ResourceTableTest`, `tests/test_adversarial.py::Races.test_resource_table_concurrent_push_drop`
> **Open gaps:** 12-bit generation counter wraps after 4095 reuses of one slot (documented residual risk T-10).

**Objective:** Safely represent host-backed resources with typed, generation-protected ownership and deterministic cleanup.

- [x] **Table architecture:** Define per-instance or per-store resource tables and prohibit cross-tenant/global lookup by raw numeric handle.
- [x] **Typed entries:** Associate each entry with an immutable resource type and reject type-confused lookup/drop operations.
- [x] **Opaque handles:** Expose opaque indices/IDs only; never expose host pointers or reusable OS handle values directly.
- [x] **Generation counters:** Pair slot indexes with generations/nonces so stale handles cannot target newly allocated resources.
- [x] **Ownership:** Implement owned, borrowed, shared, and transferred states explicitly; reject double ownership and use-after-transfer.
- [x] **Borrow lifetime:** Tie borrowed handles to the parent call/resource lifetime and reject storage/use after the borrow expires.
- [x] **Drop semantics:** Make close/drop idempotence rules explicit and guarantee exactly-once host cleanup where required.
- [x] **Parent-child resources:** Model dependencies such as streams from sockets/files; define whether parent drop cascades, blocks, or leaves independent children.
- [~] **Revocation:** Mark affected entries revoked and reject new operations while defining behavior for in-flight operations.
- [x] **Capacity limits:** Set per-instance/per-tenant table limits by resource class and total count.
- [~] **Admission control:** Reject allocation before host-resource creation when limits are exceeded to avoid transient leakage.
- [x] **Leak detection:** Track allocation/drop counts and report resources remaining at normal teardown.
- [x] **Forced teardown:** On instance failure, deterministically cancel operations and close all owned host resources.
- [~] **Exception safety:** Ensure partial construction failures cannot orphan host descriptors or reserve table slots indefinitely.
- [x] **Concurrency control:** Define locking/atomic rules for allocate/get/borrow/transfer/drop/revoke; test concurrent access heavily.
- [x] **ABA defense:** Specifically test rapid slot reuse, wraparound, stale-handle replay, and concurrent drop/reallocate sequences.
- [ ] **Serialization boundary:** Prohibit raw resource handles from being persisted or accepted across restart unless a dedicated secure rebind protocol exists.
- [~] **Metrics:** Emit current/high-water resource counts, allocation failures, leaks, forced cleanup, and stale-handle errors by type.
- [x] **Fuzzing:** Fuzz arbitrary resource IDs, types, drop orders, transfer graphs, and malformed canonical-ABI resource operations.
- [x] **Shutdown tests:** Cover graceful drain, timeout, panic, host crash simulation, and cancellation while resources are active.

**Exit evidence**
- [x] Stale, wrong-type, dropped, revoked, and cross-instance handles fail safely.
- [x] Leak tests return table/host resources to baseline after every lifecycle path.
- [x] Concurrency/race tests show no double close, ABA reuse, or cross-tenant lookup.
- [x] Quota exhaustion does not leak host resources or corrupt the table.

---

## MC-012 — Structured error taxonomy — P0

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/errors.py`, `tests/test_errors_resources.py::ErrorTaxonomy`, `docs/adr/ADR-004-error-model.md`
> **Open gaps:** Localization boundary not addressed; security review pending.

**Objective:** Provide stable, safe, machine-readable errors across host/runtime/provider boundaries without leaking sensitive implementation data.

- [x] **Top-level classes:** Define capability-denied, invalid-input, not-found, conflict, unavailable, quota, timeout, canceled, dependency-failure, unsupported, integrity-failure, and internal/terminal classes.
- [x] **Stable codes:** Assign immutable machine codes independent of localized/human-readable messages.
- [x] **Retry semantics:** Mark whether each code is retryable, conditionally retryable, or terminal and under what idempotency assumptions.
- [x] **Boundary mapping:** Create reviewed mappings from OS errno/Win32 errors, runtime traps, policy errors, TLS/network errors, provider errors, and internal exceptions.
- [x] **No raw passthrough:** Prohibit direct propagation of host exception text, filesystem paths, IP topology, credentials, tokens, or stack traces to guests.
- [x] **Capability denials:** Distinguish denied authority from missing resource and invalid input without enabling sensitive resource enumeration beyond approved semantics.
- [~] **Quota detail:** Return the resource class and safe limit category, not confidential global capacity information.
- [x] **Timeout/cancel distinction:** Keep caller cancellation, policy cancellation, deadline expiry, and host shutdown distinct where operationally meaningful.
- [~] **Integrity failures:** Treat signature/hash/attestation/audit-chain validation errors as explicit high-severity classes.
- [x] **Unknown errors:** Map unknown host failures to a generic internal code with a correlation ID; retain details only in protected operator telemetry.
- [~] **Correlation:** Attach safe request/instance/event identifiers for debugging without exposing sequential tenant-global IDs if that creates leakage.
- [x] **Versioning:** Define compatibility rules for adding codes/fields and handling unknown future codes.
- [x] **Serialization:** Canonicalize error wire representation and bound message/metadata sizes.
- [ ] **Localization boundary:** Keep localization/human messages separate from machine logic; clients must branch only on codes/typed fields.
- [x] **Redaction tests:** Seed host errors with canary secrets/paths and verify guest-visible errors never contain them.
- [x] **Mapping completeness:** Add CI that enumerates known provider/runtime errors and fails on unmapped critical classes.
- [~] **Fault injection:** Trigger every major error class in real adapters and verify exact code, retry marker, audit event, and resource cleanup.
- [~] **Metrics:** Count error codes/classes separately from messages; alert on integrity/internal/unexpected-code spikes.
- [x] **Documentation:** Publish code definitions, retry rules, caller responsibilities, and versioning guarantees.
- [ ] **Security review:** Review error distinctions for oracle/enumeration risk and minimize externally observable differences where necessary.

**Exit evidence**
- [x] Error conformance tests cover all production adapters and provider classes.
- [x] Canary leakage tests pass for guest-visible errors and logs.
- [~] Retry/idempotency behavior is documented and exercised.
- [x] Unknown failures fail safely with protected diagnostic correlation.

---

## MC-013 — Async polling, cancellation, timeout, and backpressure semantics — P1

> **v4.3.0 execution status: PARTIAL** — evidence: `host/aio.py`, `tests/test_providers.py::Async`
> **Open gaps:** asyncio reference only; not wired to engine pollables/futures; no fairness, partial-I/O or load tests.

**Objective:** Define bounded asynchronous behavior across pollables, futures, streams, and provider operations.

- [~] **Async model:** Select and document the target runtime’s poll/future/stream primitives and their mapping to WIT/component resources.
- [~] **Readiness semantics:** Define edge/level behavior, spurious wakeups, ordering, fairness, and one-shot versus reusable pollables.
- [x] **Cancellation ownership:** Specify who may cancel an operation and which resources/results remain valid after cancellation.
- [x] **Propagation:** Carry guest cancellation through runtime adapter to provider/OS operation wherever supported.
- [x] **Deadlines:** Represent absolute/relative deadlines using the correct clock and avoid wall-clock dependency for elapsed-time limits.
- [~] **Timeout hierarchy:** Define precedence among per-call, per-resource, workload, and shutdown deadlines.
- [x] **Bounded queues:** Cap pending futures, pollables, stream buffers, provider work, and callback queues per workload/tenant.
- [x] **Backpressure:** Propagate downstream saturation upstream rather than buffering without bound.
- [ ] **Partial I/O:** Define semantics for partial writes/reads when timeout or cancellation occurs; preserve data-integrity guarantees.
- [x] **Idempotency:** Label operations safe/unsafe to retry after timeout, cancellation, or uncertain completion.
- [ ] **Orphan prevention:** Ensure canceled/dropped guest futures cannot leave unbounded host operations running.
- [~] **Shutdown:** Drain or cancel outstanding operations within a bounded interval and account for all resources.
- [ ] **Fairness:** Prevent one workload’s ready-loop or stream flood from starving other tenants.
- [ ] **Reentrancy:** Review callbacks/completions for reentrant resource-table access and deadlock potential.
- [ ] **Race semantics:** Test complete-vs-cancel, timeout-vs-complete, drop-vs-callback, revoke-vs-I/O, and shutdown-vs-allocation races.
- [ ] **Fault behavior:** Simulate provider stalls, half-open sockets, blocked filesystem operations, and never-completing futures.
- [ ] **Metrics:** Track queue depth, wait time, cancellations, timeouts, backpressure activations, dropped work, and completion latency.
- [ ] **Load tests:** Verify bounded memory/CPU under sustained overload and burst traffic.
- [~] **Deterministic tests:** Use controlled clocks/schedulers where possible to make race and timeout tests reproducible.
- [ ] **API documentation:** State exactly when callers must poll, drop, retry, or expect partial results.

**Exit evidence**
- [x] No async queue or buffer grows unbounded under designed overload tests.
- [ ] Cancellation/timeout races pass under stress and sanitizers/race detectors where available.
- [ ] Shutdown returns resources to baseline within the documented deadline.
- [ ] Retry guidance matches measured provider completion semantics.

---

## MC-014 — Atomic configuration and policy activation — P1

> **v4.3.0 execution status: IMPLEMENTED (single node)** — evidence: `host/config.py`, `tests/test_ops.py::Config`, `tests/test_adversarial.py::Races.test_concurrent_config_writers_single_winner`
> **Open gaps:** No distributed consistency / multi-node activation, approval gates, impact analysis or schema migration.

**Objective:** Apply world, preopen, provider, and policy configuration as validated immutable snapshots with safe rollback.

- [x] **Declarative schema:** Define versioned configuration for worlds, capability descriptors, preopens, quotas, provider bindings, and policy references.
- [x] **Strict validation:** Reject unknown critical fields, duplicates, invalid roots, unsupported capabilities, bad references, and out-of-range limits before activation.
- [x] **Canonical form:** Normalize configuration for deterministic digesting/signing without changing authority semantics.
- [x] **Provenance:** Record source repository/revision, author, approver, build pipeline, signature, and artifact digest.
- [x] **Immutable snapshot:** Compile validated input into a read-only activation object identified by a stable version/digest.
- [x] **Staging:** Load and validate a candidate snapshot without affecting active workloads.
- [ ] **Impact analysis:** Diff current/candidate authority, highlighting newly added capabilities, wider roots, larger CIDRs, quota increases, and exception changes.
- [ ] **Approval gates:** Require elevated review for authority-expanding changes and emergency/break-glass changes.
- [x] **Atomic switch:** Activate the entire configuration/policy snapshot atomically; never expose mixed old/new rules within one decision path.
- [ ] **Workload semantics:** Define whether existing instances retain old snapshots, live-update, or are restarted/rebound.
- [x] **Rollback:** Retain known-good snapshots and perform one-step rollback with complete provenance.
- [x] **Crash consistency:** Recover deterministically if host/control-plane crashes before, during, or after activation commit.
- [ ] **Distributed consistency:** If multiple nodes are involved, define rollout ordering, quorum/acknowledgment, maximum skew, and safe behavior for stale nodes.
- [~] **Stale-policy guard:** Prevent nodes beyond allowed configuration age from issuing new privileged descriptors.
- [ ] **Revocation priority:** Ensure emergency deny/revocation can supersede ordinary staged rollout when required.
- [ ] **Secrets separation:** Keep secret values out of general configuration artifacts; reference secret providers by identity.
- [ ] **Schema migration:** Support explicit migrations with forward/backward compatibility and rollback tests.
- [x] **Fault injection:** Kill processes, partition control-plane links, corrupt candidate bundles, and exhaust disk during activation.
- [x] **Audit:** Emit candidate validation, approval, activation, rollback, failure, and actor/reason events.
- [~] **Drift detection:** Continuously compare runtime-active digest to desired state and alert/quarantine unexpected drift.

**Exit evidence**
- [x] Activation tests prove no mixed snapshot is observable.
- [x] Rollback restores the prior known-good digest and authority set.
- [~] Crash/partition tests do not result in permissive fallback.
- [ ] Every active node can report and prove its exact configuration/policy digest.

---

## MC-015 — Durable tamper-evident audit sink — P1

> **v4.3.0 execution status: PARTIAL (durable local sink; WORM/KMS external)** — evidence: `host/audit_sink.py`, `tests/test_ops.py::Audit`, `docs/adr/ADR-005-audit-and-export.md`
> **Open gaps:** No remote/WORM transport, checkpoint key rotation/custody, tenant-separated streams, access monitoring.

**Objective:** Export security events from the in-process chain into durable, independently verifiable, retention-controlled storage.

- [x] **Event schema:** Define immutable versioned fields for event ID, chain predecessor, instance/workload/node, actor, action, subject, result, policy/config version, reason, and safe metadata.
- [x] **Canonical encoding:** Use deterministic serialization before hashing/signing so independent verifiers reproduce digests.
- [x] **Chain construction:** Bind each event cryptographically to its predecessor and define chain segmentation/checkpoint rules.
- [x] **Node identity binding:** Sign or MAC checkpoints/events with keys tied to authenticated node identity where threat model requires it.
- [~] **Durable transport:** Use acknowledged append/export semantics with bounded local spool and no silent loss.
- [~] **Backpressure policy:** Define what happens when audit storage is slow/full; distinguish operations allowed to continue from security-critical operations that must fail closed.
- [x] **Crash recovery:** Persist enough chain/spool state to resume after restart without undetected gaps or duplicate ambiguity.
- [x] **Sequence/gap detection:** Include monotonic sequence or equivalent so collectors can detect missing/reordered events.
- [x] **Clock handling:** If timestamps are added, record time source/trust and keep ordering verifiable independently of wall time.
- [x] **Privacy:** Minimize host paths, network endpoints, user content, environment values, and secret data; classify each retained field.
- [ ] **Tenant separation:** Enforce access control and query isolation for tenant-scoped audit data.
- [~] **Retention:** Define immutable retention periods, legal hold, deletion/anonymization exceptions, and region-specific requirements.
- [ ] **Key rotation:** Rotate signing/MAC keys with verifiable continuity and preserve old verification material.
- [x] **Independent verifier:** Ship a separate tool/library that checks canonicalization, signatures/checkpoints, chain continuity, and schema compatibility.
- [ ] **Cross-system correlation:** Link audit entries to policy decisions, descriptor lifecycle, runtime instance, release artifact, and incident IDs.
- [x] **Tamper tests:** Modify/delete/reorder/duplicate events and prove independent verification detects each class.
- [~] **Outage tests:** Simulate collector loss, disk full, network partition, restart, and long backlog drain.
- [ ] **Access monitoring:** Audit audit-log access/export itself and alert on unusual bulk access.
- [ ] **Operational queries:** Provide tested queries for capability grant/revoke, preopen change, denied escape attempt, identity failure, and emergency action.
- [~] **Evidence export:** Generate release/incident evidence bundles containing chain verification results and relevant signed checkpoints.

**Exit evidence**
- [x] Independent verifier detects modification, deletion, insertion, and reordering in test fixtures.
- [ ] Security-critical audit events survive restart/partition within documented durability guarantees.
- [ ] Retention/privacy/access controls are configured and tested.
- [~] Audit records bind back to authenticated identity, policy/config, workload, and release artifacts.

---

## MC-016 — Metrics/logs/tracing/exporters — P1

> **v4.3.0 execution status: PARTIAL** — evidence: `host/telemetry.py`, `tests/test_ops.py::Telemetry`, `tests/test_integration.py`
> **Open gaps:** No OTLP exporter, secure transport, dashboards, alert rules or runbook links (needs the org's observability stack).

**Objective:** Provide operational observability that distinguishes denial, attack, dependency failure, overload, and product defects without leaking sensitive data.

- [~] **Telemetry schema:** Define stable names/units/types for counters, gauges, histograms, structured logs, and trace attributes.
- [~] **Golden signals:** Measure operation rate, error rate, latency distributions, saturation, queue depth, resource use, and provider health.
- [x] **Security classes:** Separate expected policy denials from suspicious traversal/forgery attempts, integrity failures, and internal defects.
- [~] **Identity fields:** Include safe node/tenant/workload/instance/release/policy/config identifiers with clear cardinality bounds.
- [x] **Correlation:** Propagate trace/request/event correlation across policy, descriptor, runtime, filesystem, network, HTTP, and audit layers.
- [x] **Cardinality control:** Prohibit raw guest paths, arbitrary URLs, secret names/values, stack traces, and unbounded user input as metric labels.
- [x] **Histogram design:** Choose meaningful latency/size buckets or native histograms and preserve p50/p95/p99 interpretation.
- [x] **Structured logging:** Emit machine-parseable events with stable severity and error codes rather than free-form-only text.
- [ ] **Sampling:** Define trace/log sampling that preserves rare security failures and high-severity events even under load.
- [x] **Redaction:** Apply central redaction/classification before export and test against canary secrets and sensitive host metadata.
- [ ] **Exporter isolation:** Bound exporter CPU/memory/queues and ensure telemetry failure cannot crash the runtime or widen authority.
- [x] **Backpressure/drop accounting:** Expose telemetry drops explicitly; never silently block critical runtime paths indefinitely.
- [ ] **Secure transport:** Authenticate/encrypt telemetry export and validate collector identity where applicable.
- [~] **Tenant/privacy routing:** Prevent cross-tenant visibility and route regionally restricted telemetry according to policy.
- [ ] **Dashboards:** Build release/runtime, capability denial, resource saturation, policy health, provider health, and security-event dashboards.
- [ ] **Alerts:** Define thresholds/SLO-based alerts for unexpected denials, integrity failures, descriptor leaks, audit gaps, quota saturation, and latency regression.
- [ ] **Runbook links:** Attach alert metadata to actionable runbooks and ownership/escalation information.
- [ ] **Load validation:** Measure telemetry overhead at steady state, burst, and failure conditions.
- [ ] **Schema compatibility:** Gate incompatible telemetry field changes and version dashboards/alerts with releases.
- [ ] **Support bundle:** Provide a privacy-filtered diagnostic export containing versions, health, counters, selected traces/logs, and configuration digests.

**Exit evidence**
- [ ] Dashboards/alerts distinguish policy denial, hostile input, provider outage, overload, and internal defect.
- [x] Canary-secret/privacy tests pass across every exporter.
- [x] Telemetry remains bounded and non-blocking under collector failure.
- [ ] Production incidents can be correlated end-to-end using stable IDs without raw sensitive data.

---
## MC-017 — Resource quotas and admission control — P1

> **v4.3.0 execution status: PARTIAL** — evidence: `host/quotas.py`, `tests/test_ops.py::Quotas`, `tests/test_integration.py::test_quota_quarantine_revocation`
> **Open gaps:** No priority classes, soft limits/burst, dynamic updates, memory-pressure limits inside the engine, operator overrides.

**Objective:** Enforce bounded, fair resource consumption per tenant/workload before host resources are exhausted.

- [x] **Resource inventory:** Enumerate every exhaustible resource: descriptors, preopens, sockets, streams, resource-table entries, buffers, timers, pending futures, HTTP connections, memory, CPU/fuel, audit spool, and provider fan-out.
- [x] **Quota hierarchy:** Define global, node, tenant, workload, world, and instance limits and deterministic precedence when multiple scopes apply.
- [~] **Reservation model:** Reserve quota before allocating the corresponding host resource; roll back reservations on partial failure.
- [ ] **Hard versus soft limits:** Mark limits as hard reject, throttle, shed, or advisory; avoid hidden implicit limits.
- [ ] **Burst policy:** Define bounded burst credits and refill behavior without enabling prolonged starvation of other tenants.
- [x] **Admission gate:** Evaluate capacity and policy before instantiating workloads likely to exceed minimum required resources.
- [x] **Fairness:** Implement fair scheduling/limiting so one noisy tenant cannot consume all shared provider capacity.
- [ ] **Priority classes:** If priority exists, document starvation protections and who may assign elevated priority.
- [x] **Atomic accounting:** Make acquire/release counters race-safe and resistant to double release, underflow, or orphaned reservations.
- [ ] **Crash recovery:** Reconcile quota accounting after process/node restart so stale reservations do not permanently reduce capacity.
- [ ] **Dynamic updates:** Define how lower limits apply to already-running workloads and prevent abrupt unsafe overcommit behavior.
- [~] **Backpressure integration:** Couple quota pressure to async/provider queues so overload is rejected near the source.
- [x] **Error semantics:** Return stable quota/exhaustion codes distinct from policy denial and transient provider failure.
- [ ] **Memory pressure:** Integrate allocator/buffer limits with host memory pressure and emergency shedding.
- [x] **Descriptor pressure:** Protect host OS descriptor/handle limits with safety headroom reserved for control-plane and cleanup paths.
- [x] **Abuse tests:** Attempt rapid allocate/drop loops, fan-out storms, many tiny resources, and near-limit race conditions.
- [x] **Cross-tenant tests:** Prove one tenant hitting limits does not consume another tenant’s reserved capacity or alter their counters.
- [ ] **Saturation metrics:** Export utilization, rejected admissions, throttles, high-water marks, and recovery time by safe scope.
- [~] **Capacity model:** Document expected per-instance baseline and worst-case resource cost for placement/scheduling decisions.
- [ ] **Operational override:** Provide tightly controlled temporary quota override with approval, expiry, and audit trail.

**Exit evidence**
- [ ] All exhaustible runtime/provider resources have enforced limits and accounting tests.
- [ ] Load tests demonstrate bounded memory/descriptor/queue growth at and beyond saturation.
- [~] Fairness tests show abusive tenants do not starve unrelated workloads.
- [ ] Quota overrides are time-bounded, attributable, and automatically revert.

---

## MC-018 — Real HTTP outgoing adapter — P1

> **v4.3.0 execution status: PARTIAL** — evidence: `host/http_out.py`, `tests/test_net_http.py::Http`
> **Open gaps:** No connection pooling, proxy semantics, retry policy, HTTP/2 controls; not bound to guest ABI.

**Objective:** Provide policy-controlled outbound HTTP without SSRF, credential leakage, redirect escape, or unbounded connection use.

- [~] **Capability binding:** Require explicit `http-outgoing` authority and a destination policy descriptor before creating requests.
- [~] **Typed resources:** Implement request, response, body, headers, trailers, stream, and connection/pool resources with resource-table lifecycle rules.
- [x] **Method policy:** Define allowed HTTP methods and deny unusual methods unless explicitly required.
- [x] **URL parsing:** Use one standards-compliant parser; reject ambiguous authority, userinfo tricks, malformed ports, embedded controls, and unsupported schemes.
- [x] **Scheme policy:** Permit only approved schemes, normally HTTPS by default; require explicit authorization for plaintext HTTP.
- [x] **Destination authorization:** Evaluate canonical hostname/IP/port before connection and after resolution according to network policy.
- [x] **SSRF defense:** Deny loopback, link-local, metadata, control-plane, private/internal ranges, unix/local sockets, and other protected destinations unless specifically granted.
- [x] **DNS rebinding defense:** Bind authorization to resolution results and validate each new connection/re-resolution.
- [x] **Redirect policy:** Bound redirect count; re-authorize every redirect destination; restrict scheme downgrade and credential/header forwarding.
- [~] **Header policy:** Normalize header names/values, reject CRLF injection, bound count/size, and strip hop-by-hop or privileged headers as required.
- [x] **Credential isolation:** Never inject host proxy/cloud/user credentials implicitly; bind explicit client credentials to destination and workload identity.
- [x] **TLS validation:** Validate hostname, trust chain, expiry, algorithms, and revocation policy; define custom CA handling and pinning if supported.
- [ ] **Proxy semantics:** Treat proxy access as explicit configuration/capability; authorize both proxy and final target and prevent environment-variable proxy inheritance.
- [ ] **Connection pooling:** Partition pools by tenant/workload/security context; prevent credential, cookie, TLS-session, or destination-policy cross-contamination.
- [x] **Body limits:** Bound request and response body sizes, decompression ratios, chunk/frame sizes, and streaming buffers.
- [x] **Timeouts:** Configure resolve/connect/TLS/header/body/idle/overall deadlines and cancellation propagation.
- [ ] **Retry policy:** Retry only idempotent or explicitly marked safe operations; cap attempts and jitter/backoff resources.
- [ ] **Protocol controls:** Configure HTTP/1.1, HTTP/2, and HTTP/3 support deliberately; test request-smuggling/desync relevant to each stack.
- [x] **Error mapping:** Normalize DNS/TLS/connect/protocol/timeout/quota/policy failures into the shared error taxonomy.
- [x] **Adversarial tests:** Cover alternate IP encodings, IPv6, redirects to private space, DNS rebinding, oversized headers, compression bombs, slowloris responses, and malformed protocol frames.
- [ ] **Observability:** Record method class, destination category, status class, duration, bytes, policy result, and error code without logging secrets/bodies by default.

**Exit evidence**
- [x] SSRF suite cannot reach protected destinations without explicit policy.
- [ ] Redirects, DNS changes, and pooled connections are revalidated against authority.
- [~] TLS, timeout, quota, cancellation, and body-size tests pass under the production HTTP stack.
- [x] No implicit host credentials/proxy settings are inherited.

---

## MC-019 — Interface/version negotiation and compatibility matrix — P1

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/compat.py`, `COMPAT_MATRIX.json`, `tests/test_wit_wasm.py::Negotiation`
> **Open gaps:** No rolling-upgrade/state-compat scenarios, generated-binding matrix.

**Objective:** Make supported runtime/WASI/WIT/adapter combinations explicit, testable, and release-gated.

- [x] **Version dimensions:** Enumerate component model, WASI interfaces, WIT packages, host adapter, runtime, provider protocols, configuration schema, and artifact format versions.
- [x] **Compatibility matrix:** Publish supported combinations and distinguish fully certified, compatibility-only, deprecated, experimental, and unsupported states.
- [x] **Negotiation protocol:** Define how peers/components declare versions and how the host selects or rejects a compatible contract.
- [x] **No best-effort ambiguity:** Reject unsupported combinations rather than silently choosing a nearby version with different authority semantics.
- [ ] **Feature detection:** Use explicit negotiated feature flags where version alone is insufficient; avoid behavioral probing that may create side effects.
- [x] **Backward compatibility:** Test every version promised within the support window against current host releases.
- [ ] **Forward handling:** Define behavior for unknown optional fields/capabilities and reject unknown critical semantics.
- [x] **Deprecation policy:** Set announcement, warning, support, and removal dates with migration guidance.
- [x] **EOL enforcement:** Prevent new deployments on expired combinations unless an approved exception exists.
- [x] **Semantic diff:** Automatically compare WIT/config/error/resource semantics between releases and flag security-relevant changes.
- [ ] **Generated-binding matrix:** Build bindings with each supported generator/toolchain combination or pin one exact stack and document it.
- [~] **Provider compatibility:** Validate network/filesystem/http/clock/random provider protocol versions independently from runtime version.
- [ ] **Rolling upgrade:** Test old host/new component, new host/old component, mixed-node clusters, rollback, and partial deployment states.
- [ ] **State compatibility:** Verify persisted configuration/audit/resource metadata needed across restart can be read or migrated safely.
- [x] **Negative tests:** Attempt unsupported, future, malformed, downgraded, and conflicting version declarations.
- [x] **Downgrade resistance:** Prevent attackers or misconfiguration from negotiating an older less-secure interface when policy requires newer semantics.
- [x] **Release gate:** Fail release if any supported matrix cell lacks passing conformance/security tests.
- [~] **Artifact metadata:** Embed version tuple and compatibility manifest in release artifacts and support bundles.
- [ ] **Operational diagnostics:** Surface exact negotiated versions in safe telemetry and health endpoints.
- [~] **Documentation:** Keep compatibility documentation generated from the same machine-readable matrix used by CI.

**Exit evidence**
- [x] Machine-readable compatibility matrix drives CI and release gating.
- [x] Unsupported/downgrade attempts fail deterministically before privileged execution.
- [ ] Rolling upgrade and rollback scenarios pass for every supported transition.
- [ ] Published EOL/deprecation state matches enforcement logic.

---

## MC-020 — Cross-platform/architecture certification — P1

> **v4.3.0 execution status: PARTIAL (1 of 16 declared cells executed)** — evidence: `ci/matrix.yml`, `COMPAT_MATRIX.json`, `evidence/`
> **Open gaps:** Only linux/x86_64/Python 3.11/Node 22 executed; Windows fs provider absent; ARM64/macOS unrun.

**Objective:** Prove consistent security and runtime semantics across every claimed OS, architecture, runtime, and filesystem environment.

- [x] **Support matrix:** Declare exact Windows/Linux/macOS versions, x86-64/ARM64 targets, runtimes, libc variants, container modes, and filesystems in scope.
- [~] **Native CI:** Run tests on real/native target architectures where practical; do not rely only on emulation for certification.
- [~] **Filesystem matrix:** Include NTFS/ReFS where relevant, ext4/xfs/btrfs/APFS or supported equivalents, plus network/container filesystems if claimed.
- [ ] **Path semantics:** Test separators, case sensitivity, Unicode normalization, reserved names, junctions/reparse points, symlinks, mount boundaries, and long paths.
- [ ] **Handle semantics:** Verify descriptor inheritance, duplication, close-on-exec, deletion/rename behavior, and stale-handle behavior on each OS.
- [ ] **Network semantics:** Test IPv4/IPv6, dual-stack defaults, DNS resolver behavior, local-address classes, and socket option differences.
- [ ] **Clock semantics:** Validate monotonic source behavior, timer resolution, suspend/resume, and wall-clock correction on each platform.
- [ ] **Random provider:** Verify each platform’s CSPRNG binding and error semantics.
- [ ] **Resource limits:** Characterize OS descriptor/handle ceilings, thread/task limits, address-space behavior, and default kernel limits.
- [ ] **Runtime features:** Confirm component-model/WASI feature parity for each runtime/architecture combination.
- [ ] **Endian/alignment:** Where architectures vary, test canonical-ABI alignment, integer width, pointer assumptions, and serialization explicitly.
- [ ] **Atomic/concurrency behavior:** Run race/stress tests under platform-specific schedulers and memory models.
- [ ] **Signal/termination:** Normalize process/service shutdown, signals, job objects, service controls, and crash behavior.
- [ ] **Packaging:** Build native release artifacts with correct code signing/notarization/package metadata per platform.
- [ ] **Security hardening:** Validate DEP/NX, ASLR, stack protections, control-flow protections, sandbox profiles, and platform mitigations where applicable.
- [ ] **Privilege model:** Test under normal user/service identities and least-privilege deployment; document required OS privileges.
- [ ] **Localization:** Test non-English locales/timezones and Unicode paths without changing policy semantics.
- [~] **Performance baseline:** Establish platform-specific performance ranges and detect architecture-specific regressions.
- [~] **Reproducibility:** Record runner images, kernel/OS build, compiler/toolchain, runtime, filesystem, and CPU details for every certification run.
- [ ] **Release policy:** Make unsupported matrix cells impossible to advertise automatically as certified.

**Exit evidence**
- [ ] Every marketed platform/architecture has a passing native certification run tied to the release digest.
- [ ] Platform-specific security/path/network tests pass with documented exceptions only.
- [ ] Packaging/signing and least-privilege installation are validated per platform.
- [ ] Certification metadata is reproducible and retained as release evidence.

---

## MC-021 — Fuzz/property/adversarial test harness — P1

> **v4.3.0 execution status: IMPLEMENTED (stdlib seeded fuzzing)** — evidence: `tests/test_adversarial.py::Fuzz`
> **Open gaps:** No coverage-guided fuzzer (Atheris/libFuzzer), sanitizers, corpus minimisation or long campaigns.

**Objective:** Continuously search for parser, boundary, state-machine, and authority-invariant failures beyond hand-authored tests.

- [~] **Threat-driven corpus:** Seed fuzzers with traversal, malformed WIT, forged descriptor, stale handle, malformed URL/socket, error-mapping, and configuration attack cases.
- [x] **Path fuzzer:** Generate separators, dot segments, encodings, unicode, reserved names, long paths, symlink components, and platform-specific rooted forms.
- [x] **World/capability fuzzer:** Fuzz capability names, duplicates, unknown values, size limits, mutable/immutable conversions, and malformed configuration.
- [~] **WIT/ABI fuzzer:** Exercise malformed component metadata, discriminants, lengths, resources, nested values, allocation edges, and trap paths.
- [x] **Resource-ID fuzzer:** Generate stale/wrong-type/out-of-range/reused IDs and random operation sequences.
- [ ] **Provider-response fuzzer:** Inject malformed/partial/oversized network, HTTP, clock, identity, and policy provider responses.
- [ ] **State-machine fuzzing:** Randomize grant/revoke/replace/resolve/drop/cancel/restart sequences and assert legal transitions.
- [x] **Property invariants:** Encode properties including “no undeclared authority becomes reachable,” “revoked authority cannot authorize new work,” and “resource use never crosses tenant ownership.”
- [~] **Differential testing:** Compare independent implementations or reference model versus production adapter for equivalent policy outcomes.
- [ ] **Coverage guidance:** Measure edge/branch/function/state coverage and focus mutations on security-critical modules.
- [ ] **Sanitizers:** Run ASan/UBSan/MSan or language/runtime equivalents for native components where supported.
- [ ] **OOM/limit fuzzing:** Combine malformed input with low memory/descriptor/quota conditions.
- [~] **Timeout containment:** Bound each fuzz case and detect hangs/deadlocks, not only crashes.
- [x] **Determinism:** Persist exact seed/input/environment/runtime metadata for every failure and ensure local reproduction.
- [ ] **Minimization:** Automatically minimize crashing/property-violating inputs while preserving the failure.
- [ ] **Corpus retention:** Version regression corpora and keep fixed bugs as permanent seed/test cases.
- [ ] **CI cadence:** Run fast fuzz smoke jobs per change and longer campaigns on schedule/release candidates.
- [~] **Crash triage:** Deduplicate by stable signatures and assign severity based on authority impact, integrity, availability, and exploitability.
- [x] **Regression gate:** Prevent release if known high-severity fuzz findings remain open without approved risk acceptance.
- [ ] **Metrics:** Track exec/s, unique paths/states, corpus growth, crashes, hangs, invariant failures, and time-to-fix.

**Exit evidence**
- [ ] Security-critical parsers/state machines have active fuzz/property harnesses with retained corpora.
- [~] Every historical security-relevant fuzz bug has a minimized regression case.
- [ ] Long-running release campaign completes without unresolved P0/P1 findings.
- [x] Authority invariants execute continuously against the production adapter, not only the reference model.

---

## MC-022 — Concurrency/race test suite — P1

> **v4.3.0 execution status: PARTIAL** — evidence: `tests/test_adversarial.py::Races`, `tests/test_fs_descriptor.py::*test_symlink_swap_race`
> **Open gaps:** No race detectors/sanitizers (pure Python), deterministic scheduler, identity-rotation or audit-chain race suites.

**Objective:** Prove grant/revoke/use/resource lifecycle remains safe under parallel execution and hostile scheduling.

- [ ] **Concurrency model:** Document which objects are thread-safe, single-thread confined, lock-free, or externally synchronized.
- [x] **Grant/revoke race:** Concurrently grant, revoke, resolve, and use capabilities; define linearization point and expected winner semantics.
- [ ] **Preopen replacement race:** Exercise replace/revoke/resolve against in-flight filesystem calls and prove no mixed authority root is observed.
- [x] **Descriptor reuse race:** Stress allocate/drop/reallocate with stale handles to expose ABA and generation errors.
- [x] **Resource-table race:** Parallel get/borrow/transfer/drop/revoke operations across many resource types.
- [~] **Cancellation race:** Complete operations concurrently with timeout, user cancellation, resource drop, and host shutdown.
- [x] **Policy activation race:** Make decisions during atomic policy/config switch and assert each uses one complete snapshot.
- [ ] **Identity rotation race:** Rotate/revoke credentials while new descriptors are issued and existing sessions operate.
- [x] **Quota race:** Saturate acquire/release paths and prove limits cannot be exceeded through check-then-act interleavings.
- [ ] **Audit chain race:** Emit events from parallel operations and verify total ordering/chain integrity or documented sharded-chain semantics.
- [ ] **Telemetry race:** Ensure metrics/logging callbacks cannot deadlock runtime/resource locks.
- [~] **Shutdown race:** Start new work while draining/stopping and prove post-drain admissions are rejected consistently.
- [x] **Stress scheduler:** Use randomized sleeps/yields, CPU oversubscription, and repeated high-iteration runs to vary interleavings.
- [ ] **Race detectors:** Run ThreadSanitizer or equivalent where supported; retain suppression files under review.
- [ ] **Deadlock detection:** Enforce test deadlines and capture lock/thread/task state on timeout.
- [ ] **Memory-order review:** For lock-free/atomic structures, document required ordering and test on ARM64 as well as x86-64.
- [ ] **Fault combination:** Inject provider errors/revocations while concurrency stress is active.
- [ ] **Deterministic scheduler:** Where feasible, use controlled schedulers/model checking for small critical state machines.
- [~] **Leak accounting:** Verify resource/quota/audit counters return to baseline after concurrent storms.
- [ ] **Regression retention:** Preserve every found race as a focused deterministic or high-probability regression test.

**Exit evidence**
- [ ] Race detector/sanitizer runs are clean for supported native components.
- [~] No tested interleaving broadens authority or violates quota/resource ownership.
- [ ] Shutdown/cancellation/revocation races terminate within bounded time and release resources.
- [ ] Concurrency semantics and linearization guarantees are documented for callers.

---

## MC-023 — Fault-injection and degraded-operation suite — P1

> **v4.3.0 execution status: IMPLEMENTED (in-process)** — evidence: `tests/test_adversarial.py::Faults`, `tests/test_ops.py::Config.test_crash_between_steps_leaves_old_config`
> **Open gaps:** No network partition, split-brain or memory-pressure chaos; no alert validation.

**Objective:** Prove failures, outages, corruption, and recovery cannot create ambient authority or uncontrolled inconsistency.

- [x] **Failure catalog:** Enumerate runtime crash, process kill, provider outage, policy outage, identity outage, clock failure, random failure, disk pressure, network partition, collector loss, and corrupted state.
- [~] **Injection framework:** Provide deterministic hooks/proxies to fail before/during/after each security-critical operation.
- [x] **Runtime crash:** Kill guest/runtime during resource use and verify forced cleanup, audit continuity, and safe restart.
- [x] **Control-plane loss:** Partition nodes from policy/config/identity services and verify documented stale-state behavior.
- [x] **Policy outage:** Confirm new privileged grants fail closed while permitted continuity behavior is bounded and auditable.
- [x] **Identity outage:** Confirm new identity-bound issuance fails as designed and cached credentials respect expiry/revocation windows.
- [x] **Filesystem failures:** Inject permission changes, ENOSPC, readonly remount, handle invalidation, and disappearing roots.
- [~] **Network failures:** Inject DNS failure, connect resets, packet loss, partition, proxy failure, TLS failure, and partial responses.
- [ ] **Clock anomalies:** Simulate clock unavailability, large jumps, frozen time, and monotonic-source errors where feasible.
- [x] **Random-provider failure:** Prove cryptographic operations/requesters receive explicit failure without deterministic fallback.
- [x] **Disk pressure:** Fill audit/config/cache volumes and validate reserved-space/emergency behavior.
- [ ] **Memory pressure:** Force allocation failures at adapter/resource/provider boundaries and verify no partial authority/resource leaks.
- [x] **Corruption:** Corrupt configuration, descriptor persistence, audit spool, cache entries, and release metadata; detect and quarantine.
- [~] **Restart/reconciliation:** Restart after partial operations and reconcile descriptors, quota, audit, and configuration state deterministically.
- [ ] **Split-brain:** Where distributed control exists, simulate divergent policy/config revisions and enforce safe stale-node rules.
- [~] **Recovery ordering:** Document dependencies required to restore service without issuing authority before identity/policy integrity is re-established.
- [ ] **Chaos scope:** Run controlled fault campaigns in staging and, where approved, limited production-like environments with blast-radius controls.
- [ ] **Observability validation:** Ensure every injected failure produces the expected code, metric, alert, audit event, and runbook signal.
- [x] **No silent recovery:** Detect fallbacks that bypass configured providers or weaken security to regain availability.
- [ ] **Post-recovery checks:** Verify resource counts, audit chain, policy/config digest, credentials, and capability state return to consistent baseline.

**Exit evidence**
- [~] Fault matrix covers every P0 dependency and security-critical state transition.
- [x] No injected outage results in ambient/fallback authority.
- [ ] Recovery tests restore a verifiably consistent state with complete diagnostic evidence.
- [ ] Runbooks and alerting are validated against observed failure signatures.

---

## MC-024 — Performance/scale benchmark harness — P1

> **v4.3.0 execution status: IMPLEMENTED — with finding B-01 (resolve SLO missed)** — evidence: `tools/bench.py`, `BENCH_BASELINE.json`, `evidence/bench.json`
> **Open gaps:** Lexical resolve p99 ≈ 61 µs vs the contract's 1 µs target (see AUDIT_REPORT B-01); single-host, short soak; no cross-platform baselines.

**Objective:** Produce reproducible latency, throughput, startup, resource-density, overload, and recovery evidence with regression gates.

- [x] **Benchmark taxonomy:** Define microbenchmarks for policy/descriptor/resource operations and end-to-end scenarios for real component workloads.
- [x] **Environment pinning:** Record CPU, memory, NUMA, OS/kernel, runtime, compiler, power mode, filesystem, network, and background-load controls.
- [x] **Warm/cold states:** Measure cold startup, warm caches, steady state, and post-restart behavior separately.
- [x] **Startup metrics:** Measure load, validation, policy, binding, instantiation, first call, and ready latency.
- [x] **Operation latency:** Capture p50/p95/p99/p99.9 and max for filesystem, network, HTTP, clock, random, resource-table, and policy paths.
- [~] **Throughput:** Measure sustainable operations/requests/bytes per second before SLO violation.
- [ ] **CPU cost:** Report CPU time per operation and per active instance under representative concurrency.
- [~] **Memory cost:** Report baseline/peak RSS, per-instance growth, resource-table density, buffering, and leak trends.
- [x] **Descriptor density:** Characterize host handle/socket/file limits and performance as tables approach configured ceilings.
- [ ] **Concurrency scaling:** Sweep instance/workload/connection counts and identify contention knees.
- [~] **Burst test:** Apply rapid demand spikes and measure admission, queueing, shedding, tail latency, and recovery.
- [x] **Overload test:** Sustain demand beyond capacity and verify bounded resources plus intentional load shedding.
- [ ] **Recovery test:** Measure time to return to normal latency/queue/resource levels after overload or provider recovery.
- [x] **Soak test:** Run long-duration workloads to detect leaks, counter drift, latency creep, fragmentation, and audit/telemetry accumulation.
- [~] **Security-overhead test:** Quantify cost of policy, descriptor checks, audit chaining, TLS, attestation, and telemetry rather than disabling them for benchmarks.
- [ ] **Cross-platform baseline:** Maintain separate baselines for each certified OS/architecture/runtime combination.
- [ ] **Noise controls:** Use repeated trials, confidence intervals/dispersion, outlier policy, and machine isolation appropriate to the target precision.
- [x] **Regression threshold:** Define statistically and operationally meaningful release gates, not a single aspirational microsecond target.
- [ ] **Result integrity:** Store raw results, harness version, commit/release digest, environment manifest, and analysis script.
- [~] **Capacity planning:** Convert benchmark curves into documented safe deployment limits with reserved headroom.

**Exit evidence**
- [ ] Release candidate has reproducible raw benchmark results on representative hardware.
- [~] Tail latency, saturation, resource usage, and recovery meet documented SLO/capacity targets.
- [ ] Performance gates include all production security/observability features enabled.
- [ ] Capacity limits are derived from measured data rather than unverified assumptions.

---
## MC-025 — Supply-chain/provenance controls — P1

> **v4.3.0 execution status: PARTIAL** — evidence: `tools/build.py`, `SBOM.cdx.json`, `PROVENANCE.intoto.json`, `MANIFEST.sha256`
> **Open gaps:** Artifacts unsigned (no KMS), no vulnerability/secret scanning service, pk_core version unpinned.

**Objective:** Make every source, dependency, build input, generated binding, and released artifact traceable, reviewable, and cryptographically verifiable.

- [x] **Dependency manifest:** Maintain a complete machine-readable dependency graph for runtime, bindings, Python/tooling, native libraries, generators, and build utilities.
- [~] **Version locking:** Pin exact versions/digests for production dependencies; prohibit floating branches/tags in release builds.
- [~] **Transitive visibility:** Capture transitive dependencies, features, optional packages, native system dependencies, and runtime-downloaded assets.
- [x] **SBOM generation:** Produce SPDX or CycloneDX SBOMs for each release artifact and include component versions, licenses, and hashes.
- [ ] **Source provenance:** Record repository URL, commit digest, submodule/vendor digests, and patch set for every built component.
- [x] **Build provenance:** Emit signed provenance describing builder identity, workflow, inputs, environment image, commands, and outputs.
- [x] **Artifact hashing:** Publish SHA-256 or stronger digests for all archives/binaries/packages/config bundles and verify before deployment.
- [ ] **Artifact signing:** Sign release artifacts with protected release keys and verify signatures at installation/deployment.
- [ ] **Key custody:** Store signing keys in protected signing services/HSMs where appropriate; enforce least privilege and audit use.
- [x] **Reproducible inputs:** Pin compiler/runtime/container base images and package indexes/mirrors using immutable references.
- [x] **Reproducibility:** Establish deterministic or independently reproducible builds for critical artifacts; document nondeterministic fields and normalization.
- [ ] **Generated-code provenance:** Tie generated WIT bindings/config schemas/docs to exact generator version and source digest.
- [ ] **Vulnerability scanning:** Scan dependencies/artifacts/container images continuously and at release; define severity-based blocking rules.
- [ ] **Malware/secrets scanning:** Scan source/build artifacts for malicious content, embedded credentials, private keys, and accidental sensitive files.
- [~] **License policy:** Inventory licenses and fail builds for unapproved/incompatible license classes.
- [ ] **Dependency review:** Require explicit review for new dependencies, especially network/crypto/parser/runtime/security-critical packages.
- [ ] **Typosquat protection:** Restrict package sources/registries and verify expected publisher/project identity for new packages.
- [ ] **Build isolation:** Run release builds in clean, ephemeral, least-privilege environments with controlled network access.
- [ ] **CI integrity:** Protect release branches/tags/workflows, require reviewed changes, and prevent untrusted pull requests from using production signing secrets.
- [ ] **Update process:** Define emergency dependency patch flow, regression validation, artifact re-signing, and notification.
- [ ] **Approved-version enforcement:** Prevent deployment of artifacts whose digest/version/provenance is not present in the approved release manifest.

**Exit evidence**
- [ ] Release SBOM, provenance statement, signatures, and digests are generated and independently verifiable.
- [ ] Deployment verifies artifact identity before activation.
- [ ] Vulnerability/license/secret scans satisfy documented release gates.
- [~] Rebuild or reproducibility check confirms critical artifacts originate from the recorded source/input set.

---

## MC-026 — Packaging/build metadata — P1

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `pyproject.toml`, `tools/build_backend.py`, `tools/build.py`, `evidence/gate.json (wheel install)`
> **Open gaps:** No signature verification on install, uninstall/upgrade tests.

**Objective:** Define deterministic installation/build artifacts and explicit dependency/runtime requirements for INV-13 and its external framework/runtime dependencies.

- [x] **Packaging strategy:** Decide supported artifact forms such as wheel/source distribution, native service package, OCI image, runtime bundle, or embedded library.
- [x] **Metadata:** Declare package name, semantic version, license, authorship/ownership, supported platforms, architecture, runtime requirements, and homepage/source provenance.
- [x] **`pk_core` dependency:** Define the exact supported `pk_core` package/source/version/API contract rather than relying on an undeclared external module.
- [x] **Runtime dependency:** Declare exact supported Wasm runtime/binding packages and native shared-library requirements.
- [x] **Python policy:** If Python remains in the implementation/toolchain, publish supported Python versions/architectures and end-of-support schedule.
- [x] **Build backend:** Pin build backend/tool versions and avoid developer-machine implicit dependencies.
- [ ] **Lock files:** Check in reproducible lock/constraints files for build and runtime dependencies.
- [x] **Optional features:** Encode feature extras explicitly and ensure optional dependencies cannot silently add ambient authority.
- [ ] **Native linkage:** Document static/dynamic linkage, runtime search paths, DLL/shared-object deployment, and minimum OS runtime requirements.
- [~] **Build isolation:** Verify clean builds on machines without repository-local caches or globally installed dependencies.
- [x] **Artifact contents:** Maintain allowlist/manifest for packaged files and exclude tests/secrets/dev configs/caches unless intentionally shipped.
- [ ] **Path safety:** Validate archive members against traversal, absolute paths, symlinks/hardlinks, reserved Windows names, and excessive path lengths.
- [ ] **Install location:** Avoid privileged/global writes unless required; define service/user data/config/cache locations separately from immutable program files.
- [ ] **Permissions:** Set restrictive default file/directory permissions and ownership for config, keys, audit spool, and executables.
- [~] **Upgrade semantics:** Define in-place upgrade, side-by-side install, migration, and rollback behavior.
- [ ] **Uninstall semantics:** Remove program artifacts without deleting operator/tenant data unexpectedly; document retained state.
- [ ] **Signature verification:** Ensure package/install tooling validates release signatures/digests where supported.
- [x] **Smoke test:** Install from the final artifact into a clean environment and run import/startup/self-check/integration smoke tests.
- [x] **Offline install:** Where edge/offline operation is required, produce a complete verified dependency bundle with no network fetch at runtime.
- [x] **Deterministic archive:** Normalize timestamps/order/permissions where feasible and publish artifact hash.
- [ ] **Metadata validation:** Add CI checks for version consistency across source, package metadata, runtime banners, docs, and release manifest.

**Exit evidence**
- [~] Clean-machine installation succeeds using only declared dependencies/artifacts.
- [ ] Package manifest contains no undeclared or sensitive files.
- [~] Version/runtime/dependency metadata is consistent and machine-verifiable.
- [ ] Upgrade/rollback/uninstall tests pass on each supported platform.

---

## MC-027 — Production rollback/quarantine/emergency-disable control — P1

> **v4.3.0 execution status: IMPLEMENTED** — evidence: `host/control.py`, `tests/test_ops.py::Controls`, `tests/test_integration.py::test_quota_quarantine_revocation`
> **Open gaps:** No two-person rule, partition behaviour or alerting; artifact (binary) rollback relies on release tooling.

**Objective:** Give authorized operators bounded, auditable mechanisms to contain unsafe workloads, capabilities, policies, or releases rapidly.

- [x] **Control taxonomy:** Define revoke descriptor, revoke preopen, disable capability class, quarantine workload, quarantine node/runtime, freeze mutations, rollback policy/config, and rollback artifact actions.
- [x] **Authorization:** Restrict emergency controls to authenticated roles with least privilege and separation of duties appropriate to impact.
- [x] **Scope targeting:** Support precise targeting by tenant, workload, instance, descriptor, capability, node, release, and policy version.
- [ ] **Fail-safe defaults:** Ensure malformed/partial emergency commands cannot accidentally broaden authority.
- [ ] **Idempotency:** Make repeated containment actions safe and return current state clearly.
- [ ] **Propagation:** Define maximum propagation delay and acknowledgment semantics across nodes/control-plane partitions.
- [x] **Local kill switch:** Provide a bounded local mechanism for isolating a compromised node when central control is unavailable.
- [x] **Quarantine semantics:** Specify what traffic/resources remain available for diagnostics and what is immediately denied.
- [x] **In-flight operations:** Define whether current filesystem/network/HTTP operations are canceled, drained, or allowed to complete after quarantine/revoke.
- [x] **Mutation freeze:** Prevent new grants/config changes while preserving required recovery/forensics access.
- [~] **Artifact rollback:** Retain last-known-good signed artifacts and verify digest/signature before rollback activation.
- [x] **Policy rollback:** Atomically restore a prior policy/config snapshot without mixing states.
- [ ] **Data migration safety:** Verify rollback compatibility with state/config schema; block unsafe downgrade if irreversible migrations occurred.
- [~] **Break-glass mode:** Require reason, incident reference, scope, duration, approver(s), and automatic expiry for extraordinary access.
- [x] **Audit:** Record actor identity, command, target, previous/new state, reason, approvals, propagation acknowledgments, and outcome.
- [ ] **Alerting:** Trigger high-priority operational/security alerts for quarantine, mass revoke, emergency disable, and rollback.
- [~] **Recovery:** Define explicit de-quarantine/re-enable criteria; never auto-restore authority solely because time elapsed unless policy says so.
- [x] **Drill:** Run periodic containment drills including compromised workload, bad policy rollout, bad runtime release, and disconnected node.
- [ ] **API/CLI safety:** Require explicit target and confirmation/noninteractive guard tokens for broad destructive actions; support dry-run impact preview.
- [ ] **Post-incident verification:** After containment/recovery, verify active digests, descriptors, preopens, resources, audit chain, and node health.

**Exit evidence**
- [x] Emergency revoke/quarantine reaches targeted nodes within the documented SLA under normal connectivity.
- [ ] Partition tests demonstrate safe local/stale-node behavior.
- [ ] Rollback restores a signed known-good release/policy without authority expansion.
- [~] Containment drills produce complete audit and recovery evidence.

---

## MC-028 — Ownership, incident, and escalation package — P1

> **v4.3.0 execution status: OPEN (template only)** — evidence: `OWNERSHIP.md`, `EXCEPTIONS.json`
> **Open gaps:** Named owners, on-call, escalation, reviews and drills must be supplied by the organisation.

**Objective:** Establish accountable operation, review, incident response, exception governance, and maintenance ownership.

- [ ] **Service owner:** Name the accountable engineering/service owner for INV-13 production operation.
- [ ] **Security owner:** Assign a security contact responsible for threat model, vulnerability triage, and authority-boundary review.
- [ ] **On-call:** Define 24x7 or required-coverage on-call rotation, paging channels, handoff, and backup escalation.
- [~] **Severity model:** Define incident severities using confidentiality, integrity, authority expansion, availability, tenant scope, and exploitability.
- [ ] **Escalation matrix:** Map severity to responders, leadership/security/legal/privacy contacts, notification deadlines, and communication channels.
- [~] **Runbooks:** Create tested runbooks for capability escape, descriptor compromise, bad policy, identity failure, audit gap, resource exhaustion, runtime crash, and supply-chain compromise.
- [~] **Containment playbooks:** Include exact quarantine/revoke/rollback commands, validation steps, expected telemetry, and safe stop conditions.
- [ ] **Evidence preservation:** Define collection of logs, audit chains, memory/core artifacts where permitted, configuration digests, and release provenance while preserving chain of custody.
- [ ] **Access review:** Review production/admin/policy/signing/audit access on a defined cadence and after role changes.
- [ ] **Least privilege:** Maintain role definitions for developers, release engineers, operators, security reviewers, and auditors.
- [~] **Exception process:** Require owner, rationale, compensating controls, scope, approval, and expiry for waived production gates.
- [ ] **Waiver inventory:** Keep machine-readable active exceptions and alert before expiry.
- [ ] **Policy review:** Schedule review of worlds, capabilities, preopens, network destinations, quota overrides, and broad wildcards.
- [ ] **Dependency ownership:** Assign responders for runtime, `pk_core`, crypto, HTTP, and other critical third-party vulnerabilities.
- [ ] **Release authority:** Define who can approve/sign production releases and emergency patches.
- [ ] **Change management:** Link production changes to reviewed tickets/commits/release evidence and define emergency change process.
- [ ] **Postmortems:** Require blameless technical postmortems for qualifying incidents with causal chain, corrective actions, owners, and deadlines.
- [ ] **Corrective-action tracking:** Track incident/test/audit findings to verified closure; prevent recurring unresolved high-risk findings.
- [ ] **Training:** Train responders on capability model, filesystem confinement, revocation, audit verification, and emergency controls.
- [ ] **Tabletop exercises:** Run recurring scenarios for authority escape, signing-key compromise, control-plane outage, and malicious workload.
- [ ] **Documentation durability:** Store runbooks/contact maps where they remain accessible during primary control-plane or identity outages.

**Exit evidence**
- [ ] Named owners/on-call/escalation paths are current and tested.
- [ ] Critical runbooks have been exercised against staging or controlled fault scenarios.
- [ ] Access/policy/exception reviews produce retained evidence on schedule.
- [ ] Open high-severity corrective actions block release unless formally risk-accepted.

---

## MC-029 — Data residency/privacy policy for interface telemetry — P2

> **v4.3.0 execution status: PARTIAL (enforced in code; legal sign-off open)** — evidence: `PRIVACY_POLICY.md`, `host/telemetry.py::PrivacyFilter`, `tests/test_ops.py`
> **Open gaps:** Retention/deletion enforcement, regional routing, access logging are policy text only.

**Objective:** Control collection, retention, access, and geographic movement of interface telemetry and audit data.

- [x] **Data inventory:** Enumerate every telemetry/audit field including tenant/workload IDs, host paths, guest paths, URLs/endpoints, environment metadata, denial reasons, traces, and resource identifiers.
- [x] **Classification:** Assign privacy/sensitivity classification and business/security purpose to each field.
- [x] **Minimization:** Remove fields not necessary for security, reliability, billing, compliance, or support objectives.
- [x] **Pseudonymization:** Use stable scoped hashes/tokens where raw tenant/workload/user identifiers are unnecessary.
- [x] **Path policy:** Prefer preopen ID plus relative/sanitized path class; avoid full host paths and sensitive filenames by default.
- [ ] **Network metadata policy:** Define when hostnames/IPs/URLs may be retained and whether query/path components must be dropped/redacted.
- [x] **Secret/content exclusion:** Explicitly ban secrets, request/response bodies, environment values, authentication tokens, and random bytes from normal telemetry.
- [~] **Regional routing:** Map tenant/data classifications to approved collector/storage regions and prevent prohibited cross-region export.
- [~] **Retention:** Define retention by event type and region, including shorter defaults for high-detail traces.
- [ ] **Deletion:** Implement deletion/anonymization workflows consistent with applicable obligations while preserving required security/audit records.
- [ ] **Legal hold:** Define controlled exception path for records subject to preservation requirements.
- [ ] **Access control:** Restrict raw telemetry/audit access by role, tenant scope, purpose, and region.
- [ ] **Access logging:** Audit queries/exports of sensitive telemetry and alert on bulk or anomalous access.
- [ ] **Encryption:** Encrypt telemetry in transit and at rest with managed key rotation.
- [ ] **Processor inventory:** Document external collectors/processors/subprocessors and the exact data sent to each.
- [ ] **Sampling privacy:** Ensure trace sampling does not preferentially retain sensitive payloads or identifiers.
- [ ] **Support bundles:** Apply the same minimization/redaction/residency rules to exported diagnostic bundles.
- [ ] **Test data:** Use synthetic/canary sensitive values in CI to verify redaction and routing rules.
- [x] **Configuration enforcement:** Make prohibited exporter destinations/fields fail validation, not merely depend on operator guidance.
- [~] **Review cadence:** Reassess telemetry fields and retention when interfaces/capabilities/providers change.

**Exit evidence**
- [x] Field-level inventory maps every collected item to purpose, classification, retention, and residency rule.
- [x] Canary tests prove secret/content fields are not exported.
- [ ] Regional routing and access-control tests pass for representative tenant classes.
- [ ] Retention/deletion/access logs are operationally verified.

---

## MC-030 — Power/thermal and constrained-edge characterization — P2

> **v4.3.0 execution status: PARTIAL** — evidence: `EDGE_CHARACTERIZATION.md`, `evidence/bench.json`
> **Open gaps:** Power/thermal/battery measurements need physical edge hardware.

**Objective:** Characterize and bound INV-13 behavior on power-, thermal-, memory-, connectivity-, and storage-constrained edge nodes.

- [ ] **Target profiles:** Define representative edge hardware classes with CPU, RAM, storage, thermal envelope, power source, accelerator, and connectivity constraints.
- [ ] **Baseline draw:** Measure idle/active power and thermal behavior of the node before INV-13 workloads.
- [ ] **Runtime overhead:** Measure incremental power/CPU/memory cost of runtime, policy checks, descriptors, audit, telemetry, and providers.
- [ ] **Thermal throttling:** Exercise sustained workloads through thermal throttling and record latency/throughput/correctness changes.
- [ ] **Battery/DC behavior:** Where applicable, measure behavior under low-battery, brownout, power-mode, and abrupt power-loss conditions.
- [~] **Memory ceiling:** Configure and test low-memory profiles, allocator failure, buffer limits, and resource-table density.
- [ ] **Storage ceiling:** Bound logs/audit spool/cache/config storage and define cleanup/reserved-space behavior.
- [x] **Offline operation:** Define which capabilities continue without control-plane connectivity, maximum offline age, and what new grants are prohibited.
- [ ] **Reconnect:** Reconcile policy/config/identity/audit state after long offline intervals without accepting stale authority.
- [ ] **Clock drift:** Characterize RTC/time-sync loss and its effect on identity, certificate, lease, and audit behavior.
- [~] **Restart behavior:** Test watchdog reset, abrupt power loss, repeated reboot, and partial persistent-state writes.
- [~] **Replay recovery:** Verify queued audit/config/control messages replay idempotently after reconnect.
- [~] **Capacity model:** Define safe concurrent workload/resource counts per node profile with thermal and power headroom.
- [ ] **Power-aware admission:** If supported, reject/defer workload admission when power/thermal margins are insufficient.
- [ ] **Graceful degradation:** Define what observability or performance features may reduce under constrained mode without weakening security boundaries.
- [x] **No insecure fallback:** Verify loss of TPM/HSM/network/time/provider does not silently disable authentication or authorization.
- [ ] **Environmental tests:** Where hardware requirements demand it, include temperature range, vibration, unreliable network, or intermittent storage testing.
- [~] **Soak:** Run multi-day constrained workloads to observe thermal cycling, memory/storage drift, and retry storms.
- [ ] **Metrics:** Expose safe power/thermal/capacity signals needed for scheduling without high-cardinality device leakage.
- [ ] **Profile certification:** Tie each supported edge profile to tested software/runtime/config versions and measured limits.

**Exit evidence**
- [ ] Each supported edge profile has measured power, thermal, memory, storage, and offline/reconnect limits.
- [ ] Abrupt power/restart tests preserve authority and audit/config consistency guarantees.
- [ ] Capacity/admission limits include thermal/power headroom, not only CPU throughput.
- [ ] Constrained-mode behavior never weakens authentication, authorization, or confinement.

---

## MC-031 — Formal traceability/evidence bundle — P2

> **v4.3.0 execution status: IMPLEMENTED (unsigned)** — evidence: `tools/gate.py`, `TRACEABILITY.json`, `evidence/EVIDENCE_MANIFEST.json`
> **Open gaps:** Manifest not signed; human approval step pending.

**Objective:** Build a release-verifiable chain from requirement to design, code/config, test, benchmark, security evidence, and approval.

- [x] **Requirement IDs:** Assign stable identifiers to production/security requirements, including every MC item and critical invariant.
- [x] **Bidirectional matrix:** Map requirement → design/ADR → implementation/config → test → evidence and evidence → originating requirement.
- [x] **Code references:** Record stable repository paths/symbols/commit digests for each implemented control.
- [ ] **Configuration references:** Include policy/config/WIT/descriptor schema versions and exact digests.
- [x] **Test references:** Link each requirement to automated test IDs, harness version, environment, and raw result artifact.
- [x] **Security evidence:** Include threat-model cases, adversarial/fuzz/race/fault-injection results, static analysis, and review approvals.
- [x] **Performance evidence:** Link production limits/SLOs to benchmark IDs and raw measurements.
- [~] **Platform evidence:** Record certification matrix cells and native-run outputs per supported OS/architecture/runtime.
- [x] **Supply-chain evidence:** Include SBOM, provenance, dependency scan, signatures, artifact hashes, and reproducibility status.
- [ ] **Operational evidence:** Include runbook drill results, alert/dashboard validation, rollback/quarantine exercises, and owner approvals.
- [~] **Exception evidence:** List open deviations/waivers with scope, rationale, compensating control, approver, and expiry.
- [x] **Immutable manifest:** Generate a canonical release evidence manifest with hashes for every referenced artifact.
- [ ] **Manifest signing:** Sign the evidence manifest with release/attestation key and publish alongside the artifact.
- [x] **Independent verifier:** Provide tooling that validates referenced artifact hashes/signatures and reports missing/stale evidence.
- [~] **Freshness rules:** Define which evidence must be regenerated per commit, per release, per platform, or on a scheduled cadence.
- [x] **Coverage gate:** Fail release if mandatory P0/P1 requirements lack implementation plus passing evidence.
- [ ] **Change impact:** Detect code/config/interface changes and invalidate affected evidence automatically.
- [ ] **Evidence retention:** Store bundles immutably for the required lifecycle and make retrieval independent of ephemeral CI logs.
- [ ] **Human approval:** Capture architecture/security/release approvals as attributable signed or authenticated records.
- [x] **Machine readability:** Use structured JSON/YAML/attestation formats in addition to human-readable summary reports.

**Exit evidence**
- [ ] One signed manifest can reconstruct the complete evidence set for a release digest.
- [~] Automated verification reports zero missing mandatory P0/P1 links.
- [ ] Evidence invalidation/change-impact logic is tested with deliberate code/config changes.
- [~] Independent reviewer can reproduce the release-gate decision from retained artifacts.

---

## MC-032 — Architecture decision and threat-model artifacts — P2

> **v4.3.0 execution status: PARTIAL (drafted; approvals pending)** — evidence: `docs/adr/`, `THREAT_MODEL.md`
> **Open gaps:** No ADRs for network/HTTP, identity, async/resource; ADR approval by named deciders pending.

**Objective:** Maintain explicit, reviewed architectural decisions and a living threat model that drives implementation and security testing.

- [~] **System context:** Document trust boundaries among guest component, INV-13 adapter, Wasm runtime, host OS, filesystem, network, providers, policy plane, identity plane, audit/telemetry, and operators.
- [ ] **Data flows:** Diagram authority/data flows for instantiation, capability issuance, filesystem access, socket/HTTP access, clock/random, resource lifecycle, audit, and shutdown.
- [ ] **Asset inventory:** Identify protected assets including host filesystem, network reachability, credentials, tenant isolation, policy integrity, descriptor integrity, release keys, and audit evidence.
- [x] **Adversary model:** Define malicious guest, compromised workload, malicious tenant, compromised node, insider/operator error, supply-chain attacker, and network attacker capabilities.
- [~] **Trust assumptions:** List assumptions explicitly and mark those requiring external controls or attestation.
- [x] **ADR — runtime:** Record selected runtime(s), rejected alternatives, security/update rationale, and migration triggers.
- [x] **ADR — WASI/WIT target:** Record interface versions, compatibility strategy, and authority implications.
- [x] **ADR — capability model:** Define world/capability/descriptor relationships, grant/use/revoke semantics, and no-ambient-authority rule.
- [x] **ADR — filesystem:** Document descriptor-relative design, symlink/mount/reparse policy, platform differences, and revocation semantics.
- [ ] **ADR — network/HTTP:** Define DNS resolution trust, destination authorization, redirects, proxies, TLS, and SSRF controls.
- [ ] **ADR — identity/attestation:** Document principals, credential/attestation mechanisms, freshness, and degraded behavior.
- [x] **ADR — error model:** Define stable errors, redaction, retry semantics, and information-disclosure constraints.
- [x] **ADR — audit:** Define chain/signing/durability, privacy, retention, and independent verification.
- [ ] **ADR — async/resource model:** Document ownership, borrowing, cancellation, timeout, backpressure, and concurrency guarantees.
- [x] **Threat enumeration:** Use STRIDE/LINDDUN/attack-tree or equivalent structured method to enumerate threats per data flow/trust boundary.
- [~] **Abuse cases:** Include path escape, symlink race, stale descriptor, forged identity, policy downgrade, DNS rebinding, SSRF, resource exhaustion, telemetry exfiltration, and rollback abuse.
- [x] **Control mapping:** Map every material threat to preventive/detective/recovery controls and specific test IDs.
- [x] **Residual risk:** Record accepted residual risks with owner, rationale, compensating controls, and review/expiry date.
- [~] **Security invariants:** State machine-checkable properties such as no undeclared authority, tenant isolation, revoked-grant denial, and no insecure provider fallback.
- [~] **Review triggers:** Require threat-model/ADR review when worlds, runtimes, providers, privilege model, platform matrix, or trust boundaries change.
- [x] **Security-test derivation:** Create adversarial/fuzz/fault/race tests directly from threat scenarios and track coverage.

**Exit evidence**
- [ ] Current approved ADR set covers all material architecture choices and rejected alternatives.
- [~] Threat model contains explicit trust boundaries, assets, adversaries, threats, controls, and residual risks.
- [x] Every high-impact threat maps to at least one implemented control and executable security test.
- [ ] Release change-impact review confirms architecture/threat artifacts are current for the shipped system.

---

# Program-level completion and release gates

The component-level checklists above should be integrated into a single production-readiness gate. A release should not be designated production-ready until all applicable conditions below are satisfied.

- [ ] All **P0** component exit-evidence items are complete with objective artifacts from the production implementation.
- [ ] All required **P1** component exit-evidence items are complete or covered by a formally approved, time-bounded exception with compensating controls.
- [ ] Applicable **P2** items required by deployment environment, compliance commitments, or edge constraints are complete.
- [ ] The deployed WIT/world surface exactly matches the approved least-authority contract.
- [ ] The real runtime adapter, descriptor system, filesystem resolver, policy engine, identity system, network/http providers, clocks, randomness, and resource tables are tested together end-to-end.
- [ ] No production boundary relies solely on the v4.2.0 lexical/reference-model checks where an OS/runtime enforcement primitive is required.
- [ ] Fuzz, race, adversarial, fault-injection, cross-platform, and performance gates pass against the release candidate.
- [ ] No unresolved P0 security finding remains; P1 security findings require explicit release authority approval and documented expiry/remediation.
- [ ] SBOM, provenance, artifact signatures/digests, vulnerability results, and release evidence manifest are complete and verifiable.
- [ ] Rollback/quarantine/revocation drills have been exercised on the current architecture and are operationally available.
- [ ] Audit-chain verification, telemetry alerts, resource/quota dashboards, and incident runbooks are validated.
- [ ] Runtime/config/policy/WIT compatibility matrix identifies the exact supported deployment combination.
- [ ] Ownership/on-call/escalation and exception records are current.
- [ ] The release evidence bundle can be independently verified from retained artifacts without relying on undocumented CI state.

## Recommended status fields for execution tracking

For implementation tracking, augment each checkbox with: **Owner**, **Target release**, **Status**, **Evidence URI/ID**, **Reviewer**, **Verification date**, and **Exception/expiry**. P0/P1 items should not be closed by a status claim alone; attach the test/config/build/audit artifact that proves the requirement.
