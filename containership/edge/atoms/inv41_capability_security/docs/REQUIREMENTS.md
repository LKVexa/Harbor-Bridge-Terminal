# INV-41 normative requirements and operating semantics

Normative language per RFC 2119/8174. The machine-readable source of truth is `requirements/REQUIREMENTS.json`; the table at the end of this file is generated from it by `tools/render_requirements.py` and checked by the traceability gate. Architecture: ADR-0001.

## Operating assumptions

| Area | Assumption | Status | Enforcement |
|---|---|---|---|
| Interpreter | CPython 3.10–3.13, standard object model, no hostile code in-process | prerequisite | `preflight.run` (version, implementation) |
| Threads | GIL or free-threaded; `threading.RLock` provides mutual exclusion | guaranteed by runtime | race suite |
| Entropy | `os.urandom` / `secrets` are cryptographically strong | prerequisite | preflight entropy check |
| Crypto | HMAC-SHA256 correct; `compare_digest` constant-time | prerequisite | preflight RFC 4231 known-answer test |
| Clocks | monotonic clock non-decreasing; wall clock used only for credential validity and audit display | prerequisite / expected | preflight; audit verifier detects monotonic regression |
| Filesystem | not required by the core; config/evidence are optional files | expected | — |
| Node | identity, integrity, reboot: a restart invalidates every reference (by design) | guaranteed by component | `scale_soak.scenario_restart` |
| Network | only the bridge/collector/identity integrations use it; may partition, reorder, duplicate | expected | partition scenario; replay nonce |
| Storage | audit/config persistence is the deployment's; atomic write + backup per OPERATIONS.md | deployment prerequisite | B-KEY-01 |
| Control plane | none today; any future one must fence with monotonic config versions | deployment prerequisite | REQ-RES-006 |
| Isolation | adversarial workloads run behind a process/Wasm/VM boundary | deployment prerequisite | WVR-001 / B-ISO-01 |

## Deployment-context profiles

| Profile | Identity | Attestation | Policy | Keys | Time | Logging/Tracing | Sandbox | Min resources | Fail-start |
|---|---|---|---|---|---|---|---|---|---|
| cloud | required | optional | signed config required | KMS required | NTP required | required | process tier minimum | 1 vCPU, 256 MB | unsigned config, missing audit sink with mandatory audit |
| near-edge | required | optional | signed config | KMS or sealed file | NTP required | buffered | process tier | 1 core, 128 MB | as cloud |
| far-edge / disconnected | cached ≤ 60 s, then fail closed | optional | last signed config | local sealed key | monotonic only; wall clock may drift | buffered, bounded | process tier | 1 core, 64 MB | no signed config |
| workstation | optional | n/a | defaults allowed | dev keys | local | stdout | optional | — | preflight failure |
| test | stubbed | n/a | generated | test keys | injected clock | in-memory | optional | — | preflight failure |

Optional integration **absent** ⇒ feature disabled, health reports it; required integration **unavailable** ⇒ privileged operations refused (`Unavailable`/`Degraded`), readiness 503. Defaults: `config.default_profile(profile)`.

## Outcome and error semantics

Canonical outcomes: success, denied, invalid, revoked, stale, unavailable, retryable, degraded, terminal, internal-fault (`errors.OUTCOMES`, with retryability and caller action). Allowed outcomes per operation: `errors.OPERATION_OUTCOMES`. Exception ↔ code ↔ outcome is one-to-one (`errors.ERROR_CODES`, namespace INV41-ERR/1).

## Lifecycle semantics

* Broker (authority service view): `initializing → ready → {degraded ↔ ready, quiesced, failed, terminated}`; `quiesced → {ready, terminated}`; `failed → terminated`. Illegal transitions raise.
* Reference: active → (attenuated child) → revoked (irreversible) | invalid (forged/foreign). Expiry is **not** supported in-process (time-free semantics by design).
* Membrane: live → revoked (irreversible, idempotent). A descendant is revoked when **any** membrane in its chain is revoked.
* Restart: all references are gone; reconstruction from signed config yields **new** domains; old references never validate.

## Concurrency contract (REQ-CON)

* REQ-CON-001 `Authority`, `Holder`, `Reference` are immutable and safe to share across threads.
* REQ-CON-002 `Membrane` state is guarded by an `RLock`.
* REQ-CON-003 Linearization: once `Membrane.revoke()` has returned, no use/attenuate/wrap/bind of a descendant succeeds. A call that passed its liveness check before `revoke()` began may complete. Maximum post-revoke visibility window: zero after return.
* REQ-CON-004 Config activation is a single pointer swap under a lock; readers see a complete snapshot.

## Compatibility and capacity

SemVer rules, schema versions and refusal behaviour: `contracts/INTERFACES.json`, `contracts/SUPPORT_MATRIX.json`, docs/COMPATIBILITY.md. Hard limits: identifier 256 chars, operation set 256, policy 4096 resources, holder 1024 entries, membrane depth 32; broker admission per profile (`config.default_profile`). Fairness between tenants: one `Authority` (and one broker/admission pool) per tenant — tenants never share an admission queue. Backpressure: early `Overloaded` (INV41-E020) before the queue bound; revocation uses a priority reserve.

## Disconnected / intermittent operation

In-process checks need no external service and stay available. Privileged binding needs identity: unavailable ⇒ fail closed. Cached identity decisions: at most 60 s (`identity.MAX_CACHE_AGE_S`), never for binding a new domain. Expired credentials are never honoured after reconnect (StaleState). Reconciliation: re-authenticate, re-bind (new domain), re-apply newest signed config (monotonic version).

## Precedence

authorization/security > data residency > safety > availability > SLO > performance > compatibility > cost. Authorization/security and residency are **non-overridable**. A conflict is surfaced to the caller as a denial with a reason record (`INV41_REASON/1`) and recorded in the audit chain; operators see it in the explain view.

## Requirements (generated)

| ID | Level | Requirement | Audit | Status |
|---|---|---|---|---|
| REQ-FUN-001 | SHALL | Authority.grant SHALL mint a sealed reference only for a resource declared in the bootstrap policy and only for operations within it; otherwise it SHALL raise InvalidGrant (INV41-E004) or Widening (INV41-E002). | C011, C012 | IMPLEMENTED |
| REQ-FUN-002 | SHALL | Direct construction of Reference or Holder SHALL be refused with Forged (INV41-E001). | C011 | IMPLEMENTED |
| REQ-FUN-003 | SHALL | Every reference SHALL carry an HMAC-SHA256 seal over (authority id, token, resource, sorted operations) keyed by a 256-bit per-authority secret, verified on every use, attenuation, wrap and bind. | C011 | IMPLEMENTED |
| REQ-FUN-004 | SHALL | Attenuation SHALL be monotonic: the derived operation set SHALL be a subset of the parent's; widening SHALL raise Widening. | C011 | IMPLEMENTED |
| REQ-FUN-005 | SHALL | Holders and references SHALL be bound to exactly one authority domain; a reference from another domain (including one with the same textual id) SHALL raise CrossAuthority (INV41-E005). | C011 | IMPLEMENTED |
| REQ-FUN-006 | SHALL | Revoking a membrane SHALL make every live descendant (wrapped, attenuated, nested) unusable for use, attenuation, wrap and bind. | C011 | IMPLEMENTED |
| REQ-FUN-007 | SHALL | No API SHALL return a reference by resource name alone; Holder.use SHALL resolve only explicitly bound aliases. | C011 | IMPLEMENTED |
| REQ-FUN-008 | SHALL | Authority, Holder, Reference and Membrane SHALL refuse pickle, copy and deepcopy with TypeError. | C011, C032 | IMPLEMENTED |
| REQ-FUN-009 | SHALL | repr() of every capability object SHALL NOT contain tokens, signatures or seals. | C039, C047 | IMPLEMENTED |
| REQ-FUN-010 | SHALL | Identifiers (resource, operation, alias, holder, membrane, authority id) SHALL be non-empty str, at most 256 characters, with no C0/DEL control characters; operation elements SHALL be type-checked before hashing. | C011, C028 | IMPLEMENTED |
| REQ-FUN-011 | SHALL | Security checks SHALL NOT depend on assert statements and SHALL behave identically under python -O. | C011 | IMPLEMENTED |
| REQ-FUN-012 | SHALL | Idempotency: revoke() SHALL be idempotent; grant/attenuate SHALL mint a new token each call; invoke SHALL have no side effects. | C025 | IMPLEMENTED |
| REQ-FUN-013 | SHALL | Authority policy/identity, Holder contents and Reference fields SHALL be immutable after construction. | C011 | IMPLEMENTED |
| REQ-IFC-001 | SHALL | Every public/cross-layer boundary SHALL be catalogued in contracts/INTERFACES.json (classification, producer, consumer, trust, authn, authz, version, limits, errors) and every serialized output SHALL have a versioned closed schema with golden valid/invalid vectors. | C021, C022, C082, C023 | IMPLEMENTED |
| REQ-NFR-001 | SHALL | Non-functional requirements SHALL be defined: per-operation p99 latency, memory ceilings, self-check time, throughput floor (perf/slo.json); security SLOs are zero-tolerance (no widening, no cross-authority acceptance, no post-revocation use, no secret leakage); availability applies only to service mode. | C013 | IMPLEMENTED |
| REQ-RES-007 | SHALL | A failure taxonomy SHALL classify failures by layer and class with detection signals and allowed recovery actions. | C051 | IMPLEMENTED |
| REQ-LIM-001 | SHALL | Hard limits SHALL be enforced before HMAC work: 256 chars/identifier, 256 operations/set, 4096 resources/policy, 1024 holder entries, membrane depth 32; violations raise LimitExceeded (INV41-E006). | C017, C028, C067 | IMPLEMENTED |
| REQ-LIM-002 | SHALL | Broker admission SHALL bound concurrency and queue depth and reject excess early with Overloaded (INV41-E020); revocation SHALL use a priority lane. | C017, C054, C067 | IMPLEMENTED |
| REQ-OUT-001 | SHALL | Every refusal SHALL map to exactly one stable error code in namespace INV41-ERR/1 with outcome, severity, retryability and operator action; unknown exceptions SHALL map to INV41-E099 internal-fault and be treated as denial. | C014, C026 | IMPLEMENTED |
| REQ-OUT-002 | SHALL | Each public operation SHALL have a documented allowed outcome set (errors.OPERATION_OUTCOMES). | C014 | IMPLEMENTED |
| REQ-LCY-001 | SHALL | Broker lifecycle SHALL follow initializing->ready->{degraded,quiesced,failed,terminated}; illegal transitions SHALL raise. | C015 | IMPLEMENTED |
| REQ-LCY-002 | SHALL | Reference states: active, attenuated, revoked, invalid. Process restart SHALL invalidate all references; a reconstructed authority SHALL be a distinct domain. | C015, C057 | IMPLEMENTED |
| REQ-CMP-001 | SHALL | API, schema, error-namespace and evidence versions SHALL follow SemVer as in contracts/INTERFACES.json; unsupported config schemas SHALL be refused. | C016, C027 | IMPLEMENTED |
| REQ-CMP-002 | SHALL | Preflight SHALL refuse unsupported interpreter versions/implementations. | C016, C084 | IMPLEMENTED |
| REQ-DIS-001 | SHALL | When identity/policy/key/time services are unavailable, privileged binding SHALL fail closed (Unavailable); expired credentials SHALL never be used after reconnect (StaleState). In-process capability checks need no external service and remain available. | C018, C048 | IMPLEMENTED |
| REQ-PRC-001 | SHALL | Precedence: authorization/security > data residency > safety > availability > SLO > performance > compatibility > cost. Security constraints are non-overridable; conflicts SHALL surface as a denial with a reason record. | C019 | IMPLEMENTED |
| REQ-ASM-001 | SHALL | Detectable runtime assumptions (interpreter, entropy, HMAC known-answer, compare_digest, monotonic clock, profile) SHALL be checked at startup and a failed mandatory check SHALL refuse start. | C005 | IMPLEMENTED |
| REQ-PRF-001 | SHALL | Deployment profiles cloud, near-edge, far-edge, workstation, test SHALL have secure default configurations and documented mandatory/optional integrations. | C012, C033 | IMPLEMENTED |
| REQ-CFG-001 | SHALL | Configuration SHALL be validated (schema, unknown critical fields, enum/range, limits, provenance) before activation; invalid configuration SHALL be rejected (INV41-E030). | C033, C034 | IMPLEMENTED |
| REQ-CFG-002 | SHALL | Configuration SHALL be canonicalized and digested (SHA-256) and SHALL carry a signature from a trusted, unrevoked key; unsigned, untrusted, revoked or tampered configuration SHALL be rejected. | C045, C036 | IMPLEMENTED |
| REQ-CFG-003 | SHALL | Activation SHALL be atomic: readers observe the old or new complete snapshot; a failure in any phase SHALL leave the active configuration unchanged. | C037 | IMPLEMENTED |
| REQ-CFG-004 | SHALL | Config versions SHALL be strictly increasing (rollback attacks refused); operator rollback SHALL require authorization, SHALL mint a fresh domain and SHALL NOT resurrect revoked references. | C038 | IMPLEMENTED |
| REQ-CFG-005 | SHALL | Configuration SHALL record provenance (author, source, change request, created) and the store SHALL record activation time, digest and signer key id. | C036 | IMPLEMENTED |
| REQ-CFG-006 | SHALL | Runtime capability objects SHALL NOT be expressible in configuration or evidence (non-JSON-serializable). | C032 | IMPLEMENTED |
| REQ-CFG-007 | SHALL | Schema migration INV41_CONFIG/0 -> /1 SHALL be supported. | C016 | IMPLEMENTED |
| REQ-IDN-001 | SHALL | Identity adapters SHALL validate issuer, audience, signature, nbf/exp with bounded skew, principal type, single subject, subject revocation and nonce replay. | C044, C023 | IMPLEMENTED |
| REQ-IDN-002 | SHALL | Principal-to-authority binding SHALL be by canonical (issuer,tenant,env,type,id) key to a binder-minted random-id Authority; textual ids SHALL NOT select a domain; authentication SHALL NOT imply authorization. | C044 | IMPLEMENTED |
| REQ-IDN-003 | SHALL | Production identity mechanisms (OIDC/JWT, mTLS/SPIFFE, attestation) and trust anchors SHALL be named by the owner. | C044, C023 | BLOCKED (B-IDN-01) |
| REQ-AUD-001 | SHALL | Security-significant actions SHALL emit INV41_AUDIT_EVENT/1 events that are hash-chained, sequence-numbered, monotonic-clock-stamped and HMAC-sealed with a dedicated audit key. | C049 | IMPLEMENTED |
| REQ-AUD-002 | SHALL | An offline verifier SHALL detect modified, deleted, duplicated, reordered and truncated events and wrong keys. | C049 | IMPLEMENTED |
| REQ-AUD-003 | SHALL | Audit events SHALL refuse forbidden keys and token-like values at emit time. | C049, C039 | IMPLEMENTED |
| REQ-AUD-004 | SHALL | Audit buffering SHALL be bounded; with mandatory audit, an allow that cannot be audited SHALL become a denial. | C049 | IMPLEMENTED |
| REQ-AUD-005 | SHALL | A restarted chain SHALL open a new segment anchored to the previous head. | C049, C057 | IMPLEMENTED |
| REQ-AUD-006 | SHALL | Audit checkpoints SHALL be anchored to an external append-only log / approved signing key and transported over authenticated encryption. | C049, C047 | BLOCKED (B-KEY-01) |
| REQ-RES-001 | SHALL | Only dependency failures SHALL be retried, with full-jitter exponential backoff, bounded attempts and a global retry budget; denials, invalid input and revocation SHALL never be retried. | C053 | IMPLEMENTED |
| REQ-RES-002 | SHALL | Unhealthy dependencies SHALL be isolated by a circuit breaker with hysteresis; denials SHALL NOT count as dependency failures. | C054, C052 | IMPLEMENTED |
| REQ-RES-003 | SHALL | Under injected dependency faults (timeout, unavailable, crash, exhaustion, partition) authorization SHALL never fail open and recovery SHALL never resurrect revoked references. | C060, C055 | IMPLEMENTED |
| REQ-RES-004 | SHALL | Loss of a required dependency SHALL move the broker to degraded (readiness 503) and refuse privileged work; recovery SHALL return it to ready. | C052, C056 | IMPLEMENTED |
| REQ-RES-005 | SHALL | Operators SHALL be able to quarantine an entire authority domain; revocation SHALL remain available while quarantined. | C059 | IMPLEMENTED |
| REQ-RES-006 | SHALL | Split-brain/stale controller: not applicable in library mode (no replicated state); config version monotonicity is the fencing token for any distributed config distribution. | C058 | IMPLEMENTED |
| REQ-OBS-001 | SHALL | Health SHALL expose liveness, readiness, version, config digest, lineage, dependency status, self-check and degraded reason, and SHALL NOT expose secrets. | C071 | IMPLEMENTED |
| REQ-OBS-002 | SHALL | Metrics SHALL be registered (counters, histograms, gauges) with bounded label domains and a series cap; raw identifiers SHALL NOT be labels. | C072 | IMPLEMENTED |
| REQ-OBS-003 | SHALL | Logs SHALL be INV41_LOG/1 JSON lines with deterministic redaction; security failures SHALL never be sampled. | C073 | IMPLEMENTED |
| REQ-OBS-004 | SHALL | W3C trace context SHALL be propagated/started; trace context SHALL never influence authorization. | C074 | IMPLEMENTED |
| REQ-OBS-005 | SHALL | Every broker decision SHALL produce an INV41_REASON/1 record (outcome, code, opaque authority/resource ids, config digest, release, dependency status, correlation id) and an operator explain view SHALL return historical records by correlation id. | C076, C077, C078 | IMPLEMENTED |
| REQ-OBS-006 | SHALL | Telemetry retention/sampling/privacy/export policy, dashboards and alert rules SHALL be documented with owners and runbook links. | C079, C080, C075 | IMPLEMENTED |
| REQ-OBS-007 | SHALL | Telemetry export to a real backend and alert delivery SHALL be wired in a deployment. | C080 | BLOCKED (B-DEPLOY-01) |
| REQ-ISO-001 | SHALL | Untrusted code SHALL run in a separate interpreter process with -I -S -B, empty environment, private cwd, CPU/AS/NOFILE/FSIZE/NPROC rlimits and a wall-clock kill. | C043, C046 | IMPLEMENTED |
| REQ-ISO-002 | SHALL | The bridge SHALL expose only random session-bound handles; unknown handles, wrong principal/session, malformed or oversized messages SHALL be refused; closing the session SHALL revoke across the boundary; no Reference or token SHALL cross. | C043, C046 | IMPLEMENTED |
| REQ-ISO-003 | SHALL | Adversarial production workloads SHALL run behind network/filesystem namespaces and a syscall filter or Wasm/microVM boundary. | C043, C046 | BLOCKED (B-ISO-01) |
| REQ-DAT-001 | SHALL | Seals, tokens, signatures and keys SHALL NOT appear in logs, audit, reasons, health, metrics, traces or errors. | C047, C039, C075 | IMPLEMENTED |
| REQ-DAT-002 | SHALL | Encryption in transit/at rest and managed key rotation SHALL be provided by the deployment per docs/DATA_PROTECTION.md. | C047 | BLOCKED (B-KEY-01) |
| REQ-PER-001 | SHALL | A reproducible benchmark SHALL record environment fingerprint, p50/p95/p99/max, throughput, memory per object and self-check time, and gate against perf/slo.json and a versioned baseline. | C061, C062, C063, C064, C067, C069, C070 | IMPLEMENTED |
| REQ-PER-002 | SHALL | SLO thresholds and the baseline SHALL be approved by the owner on the reference environment. | C062, C070 | BLOCKED (B-OWN-01) |
| REQ-PER-003 | SHOULD | Power/thermal on constrained edge nodes SHOULD be measured. | C068 | BLOCKED (B-EDGE-01) |
| REQ-PER-004 | SHALL | Avoidable copies/serialization SHALL be identified: references are never serialized; costs are O(|ops|)+one HMAC per mint (perf/slo.json complexity). | C065, C066 | IMPLEMENTED |
| REQ-TST-001 | SHALL | Race tests SHALL force adverse interleavings and prove no success after revoke() returns, correct accounting under churn and multi-level graph revocation. | C086 | IMPLEMENTED |
| REQ-TST-002 | SHALL | Property/model-based fuzzing SHALL run with recorded seeds in PR CI and longer campaigns nightly; minimized failures SHALL be pinned. | C085 | IMPLEMENTED |
| REQ-TST-003 | SHALL | Every security control in the threat model SHALL be covered by a mutant that the suite kills. | C087, C050, C041 | IMPLEMENTED |
| REQ-TST-004 | SHALL | Scale, soak, burst, partition/reconnect and restart scenarios SHALL emit machine-readable pass/fail evidence. | C088, C089 | IMPLEMENTED |
| REQ-TST-005 | SHALL | Release-tier soak (hours) and multi-node fleet tests SHALL run before production. | C088, C089 | BLOCKED (B-SOAK-01) |
| REQ-TST-006 | SHALL | Compatibility SHALL be certified on every supported Python/OS/arch combination in CI. | C084, C093 | PARTIAL (B-COMPAT-01) |
| REQ-EST-001 | SHALL | Estate integration (C030/C083/C090/C100) SHALL report explicit PASS/FAIL/BLOCKED; production profile SHALL fail when pk_core or sibling layers are absent. | C030, C083, C090, C100 | IMPLEMENTED |
| REQ-EST-002 | SHALL | Estate tests SHALL pass against the authoritative pinned pk_core baseline. | C030, C083, C090, C100 | BLOCKED (B-EST-01) |
| REQ-SUP-001 | SHALL | Release SHALL produce a deterministic archive (built twice, digests compared), CycloneDX SBOM, SHA-256 manifest of every file, spec/schema/config hashes and SLSA-style provenance. | C031, C045 | IMPLEMENTED |
| REQ-SUP-002 | SHALL | Release manifests SHALL be signed by an approved release-signing identity and verified before install. | C045 | BLOCKED (B-SIGN-01) |
| REQ-SUP-003 | SHALL | A repository LICENSE SHALL be chosen by the owner. |  | BLOCKED (B-LIC-01) |
| REQ-SUP-004 | SHALL | Runtime dependencies SHALL be limited to the Python standard library; any third-party import SHALL fail CI. | C031 | IMPLEMENTED |
| REQ-GOV-001 | SHALL | OWNERS.json SHALL name accountable owner, backup owner, role holders, escalation tiers and review cadence; CI SHALL validate fields, two reviewers on security-critical paths and staleness. | C009 | PARTIAL (B-OWN-01) |
| REQ-GOV-002 | SHALL | ADR-0001 SHALL be approved by named approvers. | C010 | PARTIAL (B-OWN-01) |
| REQ-GOV-003 | SHALL | Exceptions/waivers SHALL carry owner, approval and expiry; expired waivers SHALL fail the production gate. | C099 | IMPLEMENTED |
| REQ-GOV-004 | SHALL | Support, SLO/error budget, rollout, lifecycle/EOL, vulnerability SLA, reconstruction, runbooks, incident process and recurring reviews SHALL be documented. | C091, C092, C094, C095, C096, C097, C098 | IMPLEMENTED |
| REQ-GOV-005 | SHALL | Operational commitments (on-call, canary windows, EOL dates, review calendar) SHALL be accepted by the owning team. | C091, C092, C094, C097, C098 | BLOCKED (B-OWN-01) |
| REQ-GOV-006 | SHALL | Traceability SHALL be generated deterministically and CI SHALL fail on unmapped requirements, missing tests/symbols, orphan tests and VERIFIED claims without evidence. | C020 | IMPLEMENTED |
| REQ-GOV-007 | SHALL | The production exit gate SHALL evaluate every final-exit item and refuse GO while any blocker is open. | C100, C090 | IMPLEMENTED |
