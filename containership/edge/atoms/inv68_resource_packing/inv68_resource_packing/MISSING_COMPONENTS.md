# INV-68 — Complete post-update missing-component inventory

**Version audited:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** concrete repository artifacts/capabilities still absent or incomplete after the hardening pass.

This inventory groups the 88 checklist items that remain `PARTIAL` or `MISSING`
in `POST_UPDATE_AUDIT.md` into implementable production components. It also
records repository-integrity gaps discovered outside the 100-item checklist.
A component is retained here until its requirement is backed by executable,
testable, repository-local evidence or a formally approved N/A rationale.

## Missing / incomplete production components

### MC-01 — Authoritative master-source artifact
- **Priority:** P1
- **Checklist linkage:** repository integrity / provenance; not a numbered checklist item.
- **Missing:** `MASTER.md`, which the supplied 4.1.0 README claimed was carried verbatim.
- **Required completion:** recover the authoritative master prompt/workflow source from its origin; checksum it; record provenance; do not synthesize a substitute and call it authoritative.

### MC-02 — Reproducible `pk_core` dependency and integration environment
- **Priority:** P0
- **Checklist:** C030, C040, C090, C100.
- **Missing:** vendored/locked/reproducibly installable `pk_core`, dependency manifest, supported version pin, and an automated way to run the 100-item integration gate from a clean environment.
- **Required completion:** pin an approved `pk_core` revision/version, define installation/bootstrap, verify hashes, and make the conformance gate runnable in CI and offline build environments as required.

### MC-03 — Ownership, support, and escalation metadata
- **Priority:** P0
- **Checklist:** C009, C091, C097.
- **Missing:** accountable owner, service owner, security owner, support boundary, on-call route, and escalation chain.
- **Required completion:** add CODEOWNERS/OWNERS metadata plus incident and operational escalation contacts/roles.

### MC-04 — Approved architecture decision record
- **Priority:** P1
- **Checklist:** C010.
- **Missing:** ADR covering the choice of Wasm-oriented resource packing/hyper-density, first-fit-decreasing behavior, CPU overcommit, memory policy, headroom model, alternatives, consequences, and approval state.
- **Required completion:** create and approve an ADR with decision date, status, reviewers, alternatives, constraints, and supersession rules.

### MC-05 — Formal requirements, context profiles, lifecycle, and traceability package
- **Priority:** P0
- **Checklist:** C005, C011–C020.
- **Missing:** technology-specific assumptions; SHALL-level requirements; cloud/datacenter/near-edge/far-edge applicability; complete NFRs; success/degraded/failure semantics; lifecycle/state transitions; compatibility policy; quotas/fairness; disconnected operation; conflict precedence; requirements traceability matrix.
- **Required completion:** create a versioned requirements specification and RTM mapping every requirement to code, tests, schemas, evidence, and owner.

### MC-06 — Boundary authentication, authorization, and capability model
- **Priority:** P0
- **Checklist:** C023, C024, C042–C044, C046.
- **Missing:** authenticated principal model, authorization rules, least-privilege capabilities, node/peer/control-plane identity, and enforceable tenant/workload boundary controls.
- **Required completion:** define identities and trust roots, capability grants, policy evaluation points, denial semantics, and isolation tests.

### MC-07 — Interface transport and failure-semantics contract
- **Priority:** P0
- **Checklist:** C025–C028.
- **Missing:** timeout, cancellation, retry, idempotency, backpressure, structured error codes/details, mixed-version behavior, payload/concurrency/queue/connection limits.
- **Required completion:** extend the interface contract with normative transport semantics and machine-readable error/limit schemas plus conformance tests.

### MC-08 — Adjacent-layer integration harness
- **Priority:** P0
- **Checklist:** C030, C083.
- **Missing:** executable integration fixtures for scheduler, Kubernetes integration mechanism, power/thermal scheduler, accelerator peer, and supported execution tiers.
- **Required completion:** build hermetic integration tests with success/refusal/failure/degraded paths and versioned fixtures.

### MC-09 — Pinned implementation/specification, dependency lock, SBOM, and artifact provenance
- **Priority:** P0
- **Checklist:** C031, C045.
- **Missing:** approved Wasm packing implementation/spec pins, dependency lock, SBOM, signatures/digests, provenance verification, and approved-version policy.
- **Required completion:** lock exact revisions, generate SBOM, verify signed artifacts/digests, and fail closed on unapproved provenance.

### MC-10 — Declarative configuration and transactional configuration lifecycle
- **Priority:** P0
- **Checklist:** C032–C038.
- **Missing:** versioned config schema, secure defaults, site/environment overlays, provenance metadata, atomic activation, rollback, and clear mutable-state separation.
- **Required completion:** move policy such as overcommit/headroom defaults into a validated config object with immutable snapshots and transactional activate/rollback semantics.

### MC-11 — Secret-handling and diagnostic-redaction policy
- **Priority:** P1
- **Checklist:** C039, C075.
- **Missing:** explicit prohibition/location for credentials, redaction rules, secret references, and diagnostics handling.
- **Required completion:** document and test a no-secret-in-config/logs policy; use references to managed secret stores where integration requires secrets.

### MC-12 — Deterministic clean-environment bootstrap
- **Priority:** P1
- **Checklist:** C040.
- **Missing:** one-command/bootstrap script or build manifest that turns an empty supported environment into a healthy component with verified dependencies.
- **Required completion:** provide offline-aware bootstrap, dependency verification, preflight, exit codes, and post-install self-test.

### MC-13 — Full threat model
- **Priority:** P0
- **Checklist:** C041.
- **Missing:** attacker model, assets, trust boundaries, abuse cases, STRIDE-equivalent analysis, mitigations, residual risk, owners, and review cadence.
- **Required completion:** turn the current three threat bullets into an approved threat model tied directly to controls and tests.

### MC-14 — Cryptographic transport/storage and security-service outage behavior
- **Priority:** P0
- **Checklist:** C047, C048.
- **Missing:** encryption requirements, key rotation, identity/attestation/policy/key/time outage behavior, and fail-open/fail-closed decisions.
- **Required completion:** define cryptographic profiles and deterministic outage semantics for every trusted dependency.

### MC-15 — Tamper-evident security audit event pipeline
- **Priority:** P0
- **Checklist:** C049.
- **Missing:** signed/chained audit records for security-sensitive operations and policy changes.
- **Required completion:** define event schema, append-only integrity mechanism, actor/correlation fields, retention, verification tooling, and tests.

### MC-16 — Adversarial and threat-derived security test suite
- **Priority:** P0
- **Checklist:** C050, C087.
- **Missing:** privilege escalation, injection, replay, spoofing, escape, side-channel, resource-exhaustion, and threat-control regression tests.
- **Required completion:** derive tests directly from MC-13 and make failures release-blocking.

### MC-17 — Failure taxonomy, health model, and stall detection
- **Priority:** P0
- **Checklist:** C051, C052.
- **Missing:** complete component/process/VM/node/site/network/provider/control-plane failure taxonomy plus liveness/readiness/stall thresholds.
- **Required completion:** define health states, detection windows, false-positive budget, ownership, and machine-readable health outputs.

### MC-18 — Retry, admission control, load shedding, and circuit breaking
- **Priority:** P0
- **Checklist:** C053, C054.
- **Missing:** safe-to-retry classification, bounded exponential backoff/jitter, admission budgets, overload refusal, circuit state, and recovery policy.
- **Required completion:** implement only where applicable; otherwise record an approved N/A with evidence that the synchronous pure algorithm does not own those boundaries.

### MC-19 — Failover, degraded operation, restart/replay, and distributed-safety semantics
- **Priority:** P0
- **Checklist:** C055–C058.
- **Missing:** failover constraints, noncritical dependency degradation, crash/restart semantics, and stale-controller/split-brain/duplicate ownership protection or formal N/A determinations.
- **Required completion:** specify control-plane state ownership and recovery protocol, then add deterministic tests.

### MC-20 — Quarantine/freeze/disable control
- **Priority:** P0
- **Checklist:** C059.
- **Missing:** operator or automated mechanism to stop unsafe packing decisions without destroying evidence/state.
- **Required completion:** add disable/freeze state, authorization, audit event, clear health status, and recovery procedure.

### MC-21 — Fault-injection and disaster/partition recovery suite
- **Priority:** P0
- **Checklist:** C060, C089.
- **Missing:** fault injection for dependency loss, stale capacity, node loss, partitions, reconnect, and degraded control plane.
- **Required completion:** create repeatable chaos/fault fixtures with objective recovery assertions and evidence output.

### MC-22 — Reproducible performance benchmark and load-profile suite
- **Priority:** P0
- **Checklist:** C061–C064.
- **Missing:** latency/throughput/startup/CPU/memory/storage/network/power baselines; p50/p95/worst-case thresholds; steady/burst/overload/scale/recovery profiles; per-workload/per-tenant overhead.
- **Required completion:** add benchmark datasets, warmup methodology, machine/OS metadata, percentile calculations, reproducibility tolerances, and stored baselines.

### MC-23 — Efficiency analysis, bounded resources, and edge power/thermal evidence
- **Priority:** P1
- **Checklist:** C065–C068.
- **Missing:** measured copy/serialization/context-switch/hop analysis, optimization evidence/N/A rationale, explicit queue/concurrency/fan-out limits, and edge power/thermal measurements.
- **Required completion:** profile and document hot paths, set hard bounds, and capture constrained-node measurements.

### MC-24 — Production saturation model and performance-regression release gate
- **Priority:** P0
- **Checklist:** C069, C070.
- **Missing:** telemetry-backed saturation thresholds and automated release block on density/startup/throughput/tail-latency regression.
- **Required completion:** connect capacity primitives to live metrics and establish versioned baseline envelopes with CI gating.

### MC-25 — Health/readiness/configuration/dependency/capability status surface
- **Priority:** P0
- **Checklist:** C071.
- **Missing:** machine-readable health and readiness endpoint/object containing version, active config identity, dependency state, and active capabilities.
- **Required completion:** implement a stable status schema and readiness rules.

### MC-26 — Metrics, structured logs, traces, and safe diagnostic detail
- **Priority:** P0
- **Checklist:** C072–C075.
- **Missing:** emitted rate/error/latency/saturation/backlog/resource metrics, structured logs, trace propagation, safe high-cardinality diagnostics, correlation IDs.
- **Required completion:** instrument public operations and establish cardinality/redaction limits.

### MC-27 — Operator explain view and release/infrastructure lineage correlation
- **Priority:** P1
- **Checklist:** C077, C078.
- **Missing:** operator-readable decision explanation tying placement to resource state/policy/topology and correlation to application release + infrastructure graph.
- **Required completion:** render `PackingResult.decisions` with effective limits, rejected constraints, config version, workload lineage, and host/topology identifiers.

### MC-28 — Telemetry governance, dashboards, and alerts
- **Priority:** P1
- **Checklist:** C079, C080.
- **Missing:** retention/sampling/privacy/export policy plus dashboards/alerts distinguishing load, degradation, policy rejection, dependency failure, attack, and software defect.
- **Required completion:** version monitoring assets and test alert conditions against synthetic telemetry.

### MC-29 — Complete contract/integration/compatibility certification tests
- **Priority:** P0
- **Checklist:** C082–C084.
- **Missing:** transport-level contract tests, all-adjacent-layer integration tests, CPU architecture/runtime/hypervisor/provider/protocol compatibility tests.
- **Required completion:** establish a supported matrix and execute it in CI/release qualification.

### MC-30 — Fuzz/property and concurrency/race testing
- **Priority:** P0
- **Checklist:** C085, C086.
- **Missing:** fuzz/property-based hostile input testing and race/concurrency certification or formal N/A for the pure stateless engine.
- **Required completion:** add deterministic seeds/corpus minimization and shared-state stress tests where integration introduces concurrency.

### MC-31 — Benchmark, soak, burst, and fleet-scale certification suite
- **Priority:** P0
- **Checklist:** C088.
- **Missing:** long-running soak, burst, fleet cardinality, allocation churn, and large-batch scalability tests.
- **Required completion:** create representative workload distributions and failure thresholds with archived results.

### MC-32 — Machine-readable release acceptance evidence
- **Priority:** P0
- **Checklist:** C090.
- **Missing:** signed/hashed release evidence manifest proving required tests, benchmarks, security checks, schemas, versions, and approvals ran for a specific build.
- **Required completion:** generate an immutable release evidence JSON/JSONL document and verify it before certification.

### MC-33 — Measured SLO compliance and support commitments
- **Priority:** P0
- **Checklist:** C091.
- **Missing:** measured compliance with declared SLOs, support hours/response targets, error-budget policy, and escalation behavior.
- **Required completion:** bind telemetry and benchmark evidence to SLO calculations and operational support commitments.

### MC-34 — Canary/staged rollout, rollback, and emergency-disable implementation
- **Priority:** P0
- **Checklist:** C092.
- **Missing:** progressive delivery strategy, automated rollback triggers, rollback artifacts/config, emergency-disable procedure, and rehearsal evidence.
- **Required completion:** codify rollout stages, acceptance checks, abort thresholds, and rollback drills.

### MC-35 — Supported-version compatibility matrix
- **Priority:** P1
- **Checklist:** C093.
- **Missing:** supported INV-68, schema, `pk_core`, scheduler, Kubernetes integration, runtime, and protocol version combinations.
- **Required completion:** publish matrix with test status, support window, deprecated combinations, and CI jobs.

### MC-36 — Patching, vulnerability-response, and end-of-life SLA
- **Priority:** P1
- **Checklist:** C094.
- **Missing:** severity-to-remediation timelines, CVE intake/triage, patch release process, EOL notice/support policy.
- **Required completion:** define policy and ownership; link it to dependency/SBOM monitoring.

### MC-37 — Backup/restore/migration/reconstruction semantics
- **Priority:** P1
- **Checklist:** C095.
- **Missing:** procedure for any control-plane configuration/evidence/state, or an explicit approved statement that runtime packing state is fully reconstructible/stateless.
- **Required completion:** identify authoritative state and recovery point/recovery time expectations, then test restoration/reconstruction.

### MC-38 — Production-grade day-0/day-1/day-2 and incident runbooks
- **Priority:** P0
- **Checklist:** C096, C097.
- **Missing:** preflight, bootstrap, deploy, verify, rollback, troubleshooting, severity classification, paging, containment, recovery, and evidence-preservation steps.
- **Required completion:** convert README notes into executable operator runbooks with commands, expected outputs, exit criteria, and escalation points.

### MC-39 — Recurring review process and exception/technical-debt registry
- **Priority:** P1
- **Checklist:** C098, C099.
- **Missing:** scheduled access/policy/dependency/config/architecture reviews; waiver/debt/deprecation records with owners, rationale, risk, and expiry.
- **Required completion:** add review cadence and machine-readable exception register; expired exceptions must fail the release gate.

### MC-40 — Formal production exit gate
- **Priority:** P0
- **Checklist:** C100.
- **Missing:** repository-local executable gate that proves architecture, requirements, interfaces, implementation, security, resilience, performance, observability, testing, rollback, and ownership readiness from concrete evidence.
- **Required completion:** implement gate policy over MC-02/MC-32 evidence and make a non-passing result release-blocking.

## Supplementary repository-level gaps

### MC-41 — Continuous integration pipeline
- **Priority:** P0
- **Missing:** CI workflow that compiles, runs standalone tests, runs `pk_core` tests when available, validates schemas, executes security/static checks, benchmarks, and produces release evidence.

### MC-42 — Packaging, dependency, license, and distribution metadata
- **Priority:** P1
- **Missing:** top-level build/package manifest for standalone distribution, dependency lock, declared license file, supported Python/runtime matrix, and release artifact manifest. These may exist in a parent monorepo, but they are absent from this isolated archive and therefore cannot be verified here.

<!-- STATUS-4.3.0:BEGIN (generated by tools/build_ledger.py) -->
## 4.3.0 status

No component is COMPLETE (reviewer sign-off is required and no reviewer exists). Item counts are DONE / PARTIAL / OPEN_EXTERNAL / OPEN_GOVERNANCE from `evidence/ITEM_LEDGER.json`.

| MC | Priority | 4.3.0 status | Items D/P/X/G | What remains |
|---|---|---|---|---|
| MC-01 | P1 | BLOCKED_EXTERNAL | 0/10/13/7 | MASTER.md not supplied; provenance record + digest enforcement ready; not synthesized |
| MC-02 | P0 | BLOCKED_EXTERNAL | 0/9/32/0 | pk_core not supplied; PK_CORE_PATH bootstrap, certification preflight and CI conformance job defined |
| MC-03 | P0 | GOVERNANCE_PENDING | 0/9/0/23 | roles, support boundary, escalation chain and CODEOWNERS defined; no named people |
| MC-04 | P1 | GOVERNANCE_PENDING | 20/0/0/9 | ADR-0001 written, status PROPOSED |
| MC-05 | P0 | IMPLEMENTED_LOCAL | 61/3/2/2 | SPECIFICATION.md + RTM; sign-off pending |
| MC-06 | P0 | IMPLEMENTED_LOCAL | 32/11/1/2 | HMAC tokens, capability ceilings, tenant scope, replay; production mTLS/OIDC is DEBT-001 |
| MC-07 | P0 | IMPLEMENTED_LOCAL | 47/1/0/0 | INTERFACES.md, errors registry, deadlines, idempotency, limits, negotiation |
| MC-08 | P0 | PARTIAL | 27/6/10/0 | hermetic emulators for all four neighbours; real components not available |
| MC-09 | P0 | PARTIAL | 8/18/10/2 | SBOM, SHA256SUMS, DSSE provenance, verify tooling; managed signer, lock hashes, external spec pin missing |
| MC-10 | P0 | IMPLEMENTED_LOCAL | 48/1/1/1 | PK_PACK_CONFIG/1, overlays, CAS+epoch+lock activation, rollback, crash recovery |
| MC-11 | P1 | IMPLEMENTED_LOCAL | 29/4/0/2 | secretref-only config, central redaction, repo scan; rotation ownership pending |
| MC-12 | P1 | IMPLEMENTED_LOCAL | 27/8/4/0 | bootstrap.sh/.ps1, preflight P01-P08, fresh-venv install check; lock hashes and pk_core outstanding |
| MC-13 | P0 | GOVERNANCE_PENDING | 35/5/0/8 | THREAT_MODEL.md T1-T18 mapped to controls/tests; approval and owners pending |
| MC-14 | P0 | PARTIAL | 17/17/1/4 | crypto profile + outage matrix implemented for shipped paths; no network transport shipped; rotation automation absent |
| MC-15 | P0 | IMPLEMENTED_LOCAL | 24/14/0/1 | hash-chained PK_PACK_AUDIT/1, anchor, loss markers, verify CLI; retention unconfirmed |
| MC-16 | P0 | IMPLEMENTED_LOCAL | 26/17/0/1 | threat-derived tests + fuzz; escape testing limited to static scan; CI gating defined not executed |
| MC-17 | P0 | IMPLEMENTED_LOCAL | 40/2/0/0 | FAILURE_MODEL.md, status, stall |
| MC-18 | P0 | IMPLEMENTED_LOCAL | 36/0/0/2 | admission, shedding, breaker, retry classification at the service boundary |
| MC-19 | P0 | IMPLEMENTED_LOCAL | 29/10/0/0 | epoch fence, CAS, lock, crash recovery; standby failover is a documented procedure |
| MC-20 | P0 | IMPLEMENTED_LOCAL | 32/0/0/1 | audited, persisted freeze/unfreeze |
| MC-21 | P0 | IMPLEMENTED_LOCAL | 32/9/0/0 | 14 fault scenarios; multi-site disaster exercise needs real sites |
| MC-22 | P0 | IMPLEMENTED_LOCAL | 34/17/0/1 | 6 profiles, baseline, regression gate; 4.2.0 perf defect fixed (311 ms -> 5.6 ms p50) |
| MC-23 | P1 | PARTIAL | 27/4/12/0 | hot path optimized with differential proof; edge power/thermal needs hardware |
| MC-24 | P0 | PARTIAL | 13/11/8/2 | baseline envelope + gate; production saturation needs live telemetry |
| MC-25 | P0 | IMPLEMENTED_LOCAL | 28/7/0/0 | PK_PACK_STATUS/1 via library call; no network endpoint adapter |
| MC-26 | P0 | IMPLEMENTED_LOCAL | 39/10/0/0 | metrics, logs, traceparent, cardinality caps; OTLP exporter is an adapter concern |
| MC-27 | P1 | IMPLEMENTED_LOCAL | 34/5/1/0 | PK_PACK_EXPLAIN/1 + text render |
| MC-28 | P1 | IMPLEMENTED_LOCAL | 32/14/1/2 | 9 alert rules validated synthetically; retention unconfirmed |
| MC-29 | P0 | PARTIAL | 11/19/15/1 | contract tests + 4.2.0 compatibility; platform matrix defined, one platform executed |
| MC-30 | P0 | IMPLEMENTED_LOCAL | 40/5/0/0 | property/fuzz/differential + 7 race scenarios incl. cross-process; 2 fuzz defects found and fixed |
| MC-31 | P0 | PARTIAL | 33/11/0/1 | burst/fleet/churn done; soak ran below the 1 h certification threshold |
| MC-32 | P0 | IMPLEMENTED_LOCAL | 25/9/1/3 | machine-readable evidence + gate + digests; signature ephemeral |
| MC-33 | P0 | PARTIAL | 6/16/3/12 | lab-measured SLOs; production SLIs and support owner missing |
| MC-34 | P0 | IMPLEMENTED_LOCAL | 37/4/0/0 | staged rollout controller, auto rollback, rehearsed; production rehearsal pending |
| MC-35 | P1 | IMPLEMENTED_LOCAL | 27/7/2/4 | compatibility.json + negotiation |
| MC-36 | P1 | GOVERNANCE_PENDING | 30/0/0/17 | policy written; intake contact unassigned |
| MC-37 | P1 | IMPLEMENTED_LOCAL | 28/9/0/2 | state inventory, RPO/RTO, export/restore, tamper refusal, drill |
| MC-38 | P0 | GOVERNANCE_PENDING | 46/11/2/9 | RUNBOOK + INCIDENT_RESPONSE executable; paging routes unassigned |
| MC-39 | P1 | GOVERNANCE_PENDING | 20/5/0/11 | cadence + register + expiry enforcement; never performed |
| MC-40 | P0 | IMPLEMENTED_LOCAL | 61/2/2/4 | release_gate.py evaluates all dimensions from evidence; current verdict NO_GO |
| MC-41 | P0 | PARTIAL | 0/49/5/3 | ci.yml defined (actions to be SHA-pinned); not executed |
| MC-42 | P1 | PARTIAL | 14/15/2/28 | pyproject, wheel/sdist, SBOM, notices; license undecided |
<!-- STATUS-4.3.0:END -->

## Closure rule

A gap is closed only when the corresponding implementation/documentation exists,
its automated verification passes, and the evidence is tied to the exact release
version. A generic checklist assertion or prose declaration alone is not enough
for production certification.
