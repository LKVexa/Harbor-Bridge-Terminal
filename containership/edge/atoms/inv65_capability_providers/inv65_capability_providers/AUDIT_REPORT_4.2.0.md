# INV-65 Capability Providers — Audit and Missing-Component Report

**Audited input version:** 4.1.0  
**Updated version:** 4.2.0  
**Audit date:** 2026-09-22  
**Scope:** files physically present in the supplied `inv65_capability_providers` archive. Adjacent INV repositories and an external `pk_core` installation were not present, so this report does not claim that components absent here are absent from the wider system.

## Result

The archive was parseable and syntactically valid, but 4.1.0 contained a material interface/model mismatch and several reference-model hardening gaps. Version 4.2.0 fixes the defects that can be corrected locally without inventing unavailable external systems or source material. The updated archive compiles and its standalone behavior tests pass under normal and optimized Python. The shared 100-item conformance suite remains unexecutable in this isolated archive because `pk_core` is neither bundled nor installed; those tests skip explicitly rather than producing a false pass.

## Fixed in 4.2.0

1. **Named-link contract mismatch fixed.** `PK_PROVIDER_LINK/1` says a link contains component + link name + config, but 4.1.0 keyed state only by component. 4.2.0 supports multiple isolated named links per component and keeps `default` as a backwards-compatible implicit link.
2. **Durable revocation added.** `unlink()` removes a link from both active and restart state, preventing a revoked link from reappearing after restart.
3. **Raw configuration exposure removed.** The public `links` dictionary is gone. Only link names are queryable; stored configuration stays private to the provider model.
4. **Configuration validation hardened.** Link configuration is restricted to bounded plain-data shapes, identifiers and operations are fail-closed validated, non-finite floats are rejected, and common inline secret fields are rejected in favor of secret references.
5. **Concurrent state transitions hardened.** Link activation, revocation, checkpoint, restart, health, and counters are protected by an `RLock` so restart cannot observe a half-applied update.
6. **Stable error taxonomy added.** No-link, invalid-link, and backend-unavailable failures now expose stable machine-readable error codes.
7. **Backend health gating preserved and made explicit.** An unhealthy backend refuses calls with `PK_PROVIDER_UNAVAILABLE`.
8. **Pure reference model split from `pk_core`.** `provider.py` can be unit-tested without the shared framework, avoiding all-or-nothing skipped testing.
9. **Standalone tests expanded.** Added tests for named-link isolation, backwards-compatible default link behavior, durable unlink, secret hygiene, invalid inputs, health gating, defensive copies/private state, and concurrent updates.
10. **Documentation corrected.** The README no longer falsely says `MASTER.md` is present and now accurately distinguishes the hardened reference model from missing production components.

## Verification performed

- ZIP path/symlink safety check before extraction: **PASS**.
- Python bytecode compilation (`compileall`): **PASS**.
- `CHECKLIST.json` parse/count/uniqueness: **PASS** — 100 declared, 100 present, 100 unique IDs.
- Standalone reference-model unit tests: **PASS** — 8/8.
- Same standalone tests under `python -O`: **PASS** — 8/8.
- Static AST scan for executable `assert`, `eval`, and `exec` in production/test Python: **PASS** after update.
- Full `pk_core` 100-item conformance execution: **NOT RUN** — `pk_core` unavailable in the supplied archive/environment; 3 conformance tests skip explicitly.

## Missing components after the 4.2.0 update

The following are still missing **from this archive**. “Missing” means no implementation, schema, test harness, executable artifact, or dedicated operational document sufficient to satisfy the corresponding capability was found here.

| ID | Priority | Missing component | Why it remains missing / relevant checklist areas |
|---|---|---|---|
| M01 | P1 | `MASTER.md` master prompt/workflow corpus | README 4.1.0 claimed it existed; the source archive did not contain it. It cannot be recreated verbatim without the original source. |
| M02 | P0 | Resolvable/pinned `pk_core` dependency | Tests and runtime import `pk_core`, but there is no bundled copy, dependency manifest, lock, or install metadata that makes the required version reproducible. C031, C040, C084, C093. |
| M03 | P0 | Versioned machine-readable interface schemas | `PK_PROVIDER_CONTRACT/1`, `PK_PROVIDER_HEALTH/1`, and `PK_PROVIDER_LINK/1` exist only as descriptive strings; no JSON Schema, protobuf, WIT, OpenAPI, or equivalent schema is shipped. C021-C022, C026-C029, C082. |
| M04 | P0 | Production provider host / transport boundary | No long-lived service/process exposes provider operations over WIT/RPC/HTTP or any other production boundary. `provider.py` is in-memory only. C012, C021, C025, C030, C040. |
| M05 | P0 | Durable persistent link-state store | Restart continuity is modeled only with an in-memory snapshot. There is no crash-safe durable store, WAL, transactional database, reconstruction source, or persistence adapter. C032, C037-C038, C057, C095. |
| M06 | P0 | Tenant/environment/site/workload identity binding | The contract declares those boundaries, but the reference key is component + link name only. No trusted caller identity context binds a link to tenant/site/environment/workload. C006, C023-C024, C042-C046. |
| M07 | P0 | Authentication integration | No mTLS, workload identity, signed token, attestation, SPIFFE-like identity, or other authentication mechanism is implemented at a provider boundary. C023, C044, C048. |
| M08 | P0 | Authorization/capability enforcement integration | Policy ownership is correctly external, but this archive has no hook that consumes an authorization decision/capability and binds it to a link/call. C024, C042-C046. |
| M09 | P0 | INV-55 secret resolver integration and rotation semantics | 4.2.0 rejects obvious inline secrets and allows references, but nothing resolves, caches, rotates, revokes, scopes, or zeroizes referenced credentials. C039, C047-C048. |
| M10 | P1 | Configuration provenance/version/author/activation model | No provenance record, monotonic config version, author identity, activation timestamp, staged activation, transactional multi-link update, or operator rollback artifact exists. C033-C038. |
| M11 | P1 | Explicit provider/link lifecycle state machine | No declared states/transitions for starting, ready, degraded, draining, disabled, failed, relinking, or revoked links. C014-C016, C051-C059. |
| M12 | P1 | Provider registry, discovery, and contract/version negotiation | Contract identity is a string only; there is no registration/discovery index, supported-version advertisement, compatibility negotiation, or duplicate-owner protection. C016, C027, C058, C071, C093. |
| M13 | P1 | Wire-level structured error schema | Python exceptions have stable codes, but no serialized failure envelope with retryability, details, correlation ID, schema version, or compatibility rules is defined. C026-C027. |
| M14 | P0 | Timeout, cancellation, retry, idempotency, and backpressure layer | None of these distributed-call semantics is implemented around `call()`. C025, C053-C054. |
| M15 | P0 | Admission control, quotas, fairness, rate limits, and circuit breaking | No per-link/tenant concurrency cap, queue bound, request budget, load shedding, fairness scheduler, or circuit breaker exists. C017, C028, C054, C067, C069. |
| M16 | P1 | Production health/readiness/stall/dependency model | `health()` is only a Boolean backend projection; there are no readiness states, thresholds, dependency detail, liveness/stall detection, reason codes, or active-capability report. C052, C071. |
| M17 | P0 | Failover/degraded-mode/split-brain controls | No failover policy, residency-aware target selection, degraded capability set, fencing/lease, duplicate-owner prevention, or stale-controller handling is present. C055-C059. |
| M18 | P0 | Tamper-evident security audit events | Link create/update/revoke, secret-reference use, health changes, restart, and refused calls emit no security audit record or evidence-chain event. C049, C073, C076, C090. |
| M19 | P0 | Transport/state encryption and key-rotation integration | No TLS/mTLS transport configuration, at-rest encryption, managed key integration, rotation, or unavailable-key behavior is implemented. C047-C048. |
| M20 | P1 | Provider artifact trust, SBOM, provenance, and implementation pinning | No executable-provider allowlist, digest/signature verification, SBOM, provenance policy, pinned provider implementation/version catalog, or supply-chain verification exists. C031, C041, C045, C094. |
| M21 | P1 | Metrics, structured logging, tracing, and explainability pipeline | Signals are named in the contract but no metric exporter, latency/error/saturation measurement, structured log schema, trace propagation, safe high-cardinality diagnostics, explain view, or lineage correlation exists. C061-C069, C071-C079. |
| M22 | P2 | Dashboards and alert definitions | No dashboards, alert rules, SLO burn alerts, dependency/attack/software-defect classifiers, or on-call routing artifacts are shipped. C080, C091, C097. |
| M23 | P0 | Adjacent-layer integration tests | No executable tests integrate with INV-60 Wasm application fabric, INV-55 Secrets integration, INV-64 Application model, or INV-61 Distributed WIT RPC. C003, C030, C083. |
| M24 | P1 | Public contract fixtures and protocol compatibility tests | No golden request/response fixtures, schema compatibility corpus, mixed-version tests, or migration fixtures exist for the declared provider interfaces. C027, C029, C082, C084. |
| M25 | P0 | Fuzzing and adversarial security test suite | No fuzz harness or tests for injection, spoofing, replay, privilege escalation, link-confusion, resource exhaustion, malicious nested input, or side-channel behavior. C041, C050, C085, C087. |
| M26 | P0 | Fault-injection/disaster/partition/reconnect test suite | No process-kill, store-corruption, network-partition, site-loss, secret-service-loss, control-plane-loss, reconnect, or recovery objective tests exist. C051-C060, C089. |
| M27 | P1 | Benchmark/soak/burst/fleet-scale harness and release performance gates | The p99 <1 ms SLO is declared but not measured. No reproducible latency/throughput/startup/CPU/memory/storage/network/power baseline or regression gate is shipped. C061-C070, C088, C091. |
| M28 | P1 | Architecture/runtime compatibility matrix and test matrix | No supported Python/runtime/OS/CPU/provider/protocol matrix or automated cross-matrix tests exists. C084, C093. |
| M29 | P1 | CI/build/release automation | No CI workflow, deterministic build job, test matrix, security scan, packaging job, release gate, or artifact publication pipeline is present. C070, C090, C092, C100. |
| M30 | P0 | Machine-readable conformance/evidence artifacts | README names `evidence/pk_evidence.jsonl` and `conformance/PK_GATE_RESULTS.json`, but neither directory/artifact exists in this archive. C020, C090, C100. |
| M31 | P1 | Requirements traceability matrix | `CHECKLIST.json` has requirements, but there is no static artifact mapping every C001-C100 item to implementation locations, tests, evidence IDs, status, owner, and waiver/expiry. C020, C090, C099-C100. |
| M32 | P1 | Architecture/security/operations governance documents | No ADR, accountable owner/escalation record, detailed threat model, incident severity/paging procedure, or formal day-0/day-1/day-2 runbook set exists beyond the brief README notes. C009-C010, C041, C096-C098. |
| M33 | P1 | Staged rollout, canary, rollback, drain, and emergency-disable implementation | README describes registry removal conceptually, but there is no executable rollout/drain/rollback procedure, state migration plan, or safe emergency-disable control. C038, C059, C092. |
| M34 | P2 | Vulnerability/EOL/review/waiver governance artifacts | No vulnerability-response SLA, patch cadence, EOL policy, recurring review schedule, exception/waiver register, debt owner, or expiry tracking. C094, C098-C099. |
| M35 | P1 | Backup/restore/migration/reconstruction tooling | Once durable state exists, no backup, point-in-time restore, schema migration, cross-site restore, or reconstruction verifier is present. C057, C095. |
| M36 | P1 | Installable package/dependency metadata and reproducible lock | No `pyproject.toml`, wheel/sdist configuration, dependency declaration, constraints/lock file, Python-version declaration, or reproducible installation recipe exists. C031, C040, C084, C093. |
| M37 | P2 | Distribution license/notice metadata | No `LICENSE`, `NOTICE`, or equivalent distribution terms are included in this archive. This is a repository governance/distribution gap rather than a runtime defect. |
| M38 | P1 | Concrete provider/adaptor conformance fixtures | No reference key-value/HTTP/message-broker provider adaptor or fake transport fixture proves the contract against representative capability classes without implementing the backing services themselves. C029-C031, C083. |
| M39 | P1 | SLO/error-budget measurement and enforcement | Isolation/restart/latency objectives are declarations only; there is no measurement window, burn calculation, breach policy, support commitment, or release-blocking evidence. C013, C061-C070, C091. |
| M40 | P1 | Data-residency/locality/failover constraint engine | Site/environment boundaries are declared, but no routing/residency metadata or constraint enforcement prevents a link from being restored or failed over to a forbidden site. C006, C019, C035, C055, C069. |

## Important distinction

The following items are **not** counted as missing ownership inside INV-65 because the contract explicitly places them outside this component: component business logic, backing-service implementations, ownership of link authorization policy, artifact-signing authority, and provider scheduling. What is missing here are the provider-side **integration/enforcement hooks** needed to consume those adjacent capabilities safely.

## Post-update disposition

Version 4.2.0 is a materially stronger and internally testable **reference/conformance component**, not a production-complete capability-provider subsystem. The P0 items above are the principal blockers to treating this archive by itself as production-ready: external framework reproducibility, typed schemas/transport, durable state, trusted identity and authorization binding, secret resolution, distributed-call controls, failover/fencing, audit/encryption, adjacent integration testing, security/fault testing, and machine-readable release evidence.
