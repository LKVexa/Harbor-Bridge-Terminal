# INV-17 Streaming Primitive — v4.3.0 Missing-Component Implementation Report

**Date:** 2026-09-23 · **Input:** 4.2.0 hardened archive + 64-section implementation checklist · **Output:** 4.3.0
**Production Exit Gate:** **NO_GO** (`conformance/PRODUCTION_EXIT_GATE.json`) — 10 blockers, 7 conditions.

## Result

| Closure state | Components |
|---|---:|
| IMPLEMENTED_PENDING_HUMAN | 8 |
| IMPLEMENTED_VERIFIED | 50 |
| WAIVER_PROPOSED | 3 |
| NA_PROPOSED | 2 |
| MEASURED_FAILING | 1 |

Every automated check passes: compile, 141 tests under `python` and `python -O`, the pk_core W0–W9 workflow
(gate `GO`, ledger intact), coverage (line 99.9 %, decision-branch 97.8 %),
ruff, mypy, schema-manifest drift, SBOM re-verification and traceability (100/100 checklist IDs traced).
The verdict is NO_GO for reasons no code can close: owners are unassigned, the ADR and waivers are unapproved,
no human drill or hosted CI run has happened, artifacts are unsigned, and one SLO fails when measured.

## What changed the 4.2.0 disposition

- **`pk_core` is no longer missing.** The owner's `PK_Master_Applied_All_Batches.zip` (Desktop\New folder) holds four
  byte-identical copies of pk_core 4.0.0; one is vendored under `vendor/pk_core`. The 100-check conformance suite
  that 4.2.0 had to skip now runs: 3/3, gate GO.
- **The adjacent layers are real.** The five sibling contracts (INV-12/15/18/19/20) are vendored from the same estate and
  loaded by `tests/test_adapters.py`. Four reciprocate INV-17's declared relation. **INV-12 does not list INV-17 at all**
  (TD-001) — a sibling-side fix, recorded, not papered over.

## Measured, not claimed

- **SLO-3 (p99 element handoff < 1 µs) is NOT met**: p99 1204 ns, p50 669 ns,
  2.5 % of handoffs ≥ 1 µs against a 1 % budget (CPython 3.11.15,
  this host). The 4.2.0 runtime measured on the same host is also above 1 µs at p99 (823 ns), so the SLO was never met;
  it had simply never been measured.
- **4.3.0 costs ~29 % more at p50 than 4.2.0** (669 vs 518 ns) for the freeze,
  idempotency and bool-safe type checks (TD-006).
- **Registry-mediated writes cost ~14.5 µs/element**, because each write
  re-verifies an HMAC capability (TD-005). The recommended change is to authorise once per handle.
- Zero-copy handoff within an instance confirmed; 2 lock acquisitions per element; ~40 B/element buffer overhead.

## Defects this pass found in its own work and fixed

1. Idempotent-duplicate check ran before the type check, so a mistyped retry returned `False` (caught by the doc writer reading the code).
2. `enable()` lifted freezes it had not applied (caught the same way).
3. `emergency_disable()` overwrote the freeze reason of already-frozen streams, so `enable()` unfroze manual/quarantine freezes (caught by `test_enable_does_not_lift_unrelated_freezes`).
4. **Security:** the replay cache LRU-evicted live single-use nonces, re-opening the transfer replay window (caught while writing a coverage test); now fail-closed.
5. Single-use lived in verifier memory; now a signed `su` claim.
6. `HttpBody.receive_all` lost chunks already read when it hit `NOT_READY` (caught by `test_chunked_body_respects_credit`).
7. The fair scheduler existed but nothing called it; `StreamRegistry.rebalance` now does.
8. The rollout simulator could not fail — its workload ignored the candidate's overload settings; rebuilt so `--fail-at` really triggers rollback.
9. Tools and tests both used a helper named `_pkg`; the coverage run silently loaded 25 of the tests (renamed `_tools_pkg`).

## Component closure register

| # | Component | Pri | Status | Open item |
|---:|---|---|---|---|
| 1 | Accountable owner and escalation record | P0 | IMPLEMENTED_PENDING_HUMAN | owner, deputy, paging target and review dates must be filled by a human; gate fails until then |
| 2 | Approved architecture decision record | P0 | IMPLEMENTED_PENDING_HUMAN | ADR status is Proposed; approval is a human act |
| 3 | SHALL-level requirements specification | P0 | IMPLEMENTED_VERIFIED | — |
| 4 | Lifecycle/state-machine specification | P0 | IMPLEMENTED_VERIFIED | — |
| 5 | Requirements traceability matrix | P0 | IMPLEMENTED_VERIFIED | — |
| 6 | External schema/WIT artifacts | P0 | IMPLEMENTED_VERIFIED | — |
| 7 | Boundary authentication specification | P0 | IMPLEMENTED_VERIFIED | — |
| 8 | Capability/authorization policy | P0 | IMPLEMENTED_VERIFIED | — |
| 9 | Timeout/cancellation/retry/idempotency contract | P0 | IMPLEMENTED_VERIFIED | — |
| 10 | Cross-version compatibility protocol | P0 | IMPLEMENTED_VERIFIED | — |
| 11 | Tenant/workload fairness policy | P0 | IMPLEMENTED_VERIFIED | — |
| 12 | Cloud/datacenter/near-edge/far-edge applicability profile | P1 | IMPLEMENTED_VERIFIED | — |
| 13 | Declarative configuration loader/schema | P0 | IMPLEMENTED_VERIFIED | — |
| 14 | Configuration provenance record | P0 | IMPLEMENTED_VERIFIED | — |
| 15 | Atomic configuration activation/rollback mechanism | P0 | IMPLEMENTED_VERIFIED | — |
| 16 | Deterministic bootstrap/package manifest | P0 | IMPLEMENTED_VERIFIED | — |
| 17 | Adjacent-layer integration adapters | P0 | IMPLEMENTED_VERIFIED | INV-12 reciprocity gap recorded as TD-001 (sibling-side fix) |
| 18 | pk_core integration dependency | P0 | IMPLEMENTED_VERIFIED | — |
| 19 | Dedicated threat-model artifact | P0 | IMPLEMENTED_VERIFIED | — |
| 20 | Artifact integrity/provenance/SBOM pipeline | P0 | WAIVER_PROPOSED | digests + SBOM + unsigned attestation produced; signing needs a release key (WVR-003) |
| 21 | Tenant/workload isolation verification | P0 | IMPLEMENTED_VERIFIED | — |
| 22 | Data classification/encryption/residency policy | P0 | IMPLEMENTED_VERIFIED | — |
| 23 | Trust-service outage behavior | P1 | IMPLEMENTED_VERIFIED | — |
| 24 | Tamper-evident security audit events | P1 | IMPLEMENTED_VERIFIED | truncation detection requires an externally stored anchor (documented residual) |
| 25 | Adversarial/resource-exhaustion security suite | P0 | IMPLEMENTED_VERIFIED | — |
| 26 | Automated health and stall thresholds | P1 | IMPLEMENTED_VERIFIED | — |
| 27 | Load shedding/circuit-breaker policy | P1 | IMPLEMENTED_VERIFIED | — |
| 28 | Failover/distributed disposition | P1 | NA_PROPOSED | N/A disposition drafted; approver must sign off |
| 29 | Crash/restart/resume/replay semantics | P0 | IMPLEMENTED_VERIFIED | — |
| 30 | Quarantine/freeze/emergency-disable control | P0 | IMPLEMENTED_VERIFIED | — |
| 31 | Fault-injection suite | P0 | IMPLEMENTED_VERIFIED | — |
| 32 | Reproducible benchmark harness | P0 | IMPLEMENTED_VERIFIED | — |
| 33 | Percentile and worst-case SLO measurement | P0 | MEASURED_FAILING | SLO-3 (p99 < 1us) measured and NOT met on the reference host; needs SLO revision or a native fast path |
| 34 | Per-tenant/per-workload overhead benchmark | P1 | IMPLEMENTED_VERIFIED | — |
| 35 | Copy/context-switch/serialization profiling | P1 | IMPLEMENTED_VERIFIED | — |
| 36 | Power/thermal measurement | P2 | WAIVER_PROPOSED | not measured: no edge hardware (WVR-001) |
| 37 | Capacity/saturation model | P1 | IMPLEMENTED_VERIFIED | — |
| 38 | Performance regression release gate | P0 | IMPLEMENTED_VERIFIED | — |
| 39 | Health/readiness/version/capability endpoint | P1 | IMPLEMENTED_VERIFIED | — |
| 40 | Metrics exporter | P1 | IMPLEMENTED_VERIFIED | — |
| 41 | Structured logging | P1 | IMPLEMENTED_VERIFIED | — |
| 42 | Trace propagation | P1 | IMPLEMENTED_VERIFIED | — |
| 43 | High-cardinality diagnostics/privacy guard | P1 | IMPLEMENTED_VERIFIED | — |
| 44 | Decision-reason/explainability surface | P1 | IMPLEMENTED_VERIFIED | — |
| 45 | Release-lineage/infrastructure correlation | P1 | IMPLEMENTED_VERIFIED | — |
| 46 | Telemetry retention/sampling/export policy | P1 | IMPLEMENTED_PENDING_HUMAN | sampling implemented; retention values PROPOSED and need approval |
| 47 | Dashboards and alert rules | P1 | IMPLEMENTED_PENDING_HUMAN | definitions validated against exported metric names; not yet loaded into a live Prometheus/Grafana |
| 48 | Exhaustive public-interface contract tests | P0 | IMPLEMENTED_VERIFIED | — |
| 49 | Platform/runtime compatibility matrix/tests | P0 | IMPLEMENTED_PENDING_HUMAN | matrix defined in CI; only CPython 3.11/Linux executed in this build |
| 50 | Fuzz/property-based tests | P0 | IMPLEMENTED_VERIFIED | — |
| 51 | Deep race/soak concurrency suite | P0 | IMPLEMENTED_VERIFIED | — |
| 52 | Benchmark/soak/burst/fleet-scale suite | P0 | WAIVER_PROPOSED | per-instance soak/burst run; fleet-scale not exercised (WVR-002) |
| 53 | Disaster/partition/reconnect suite | P1 | IMPLEMENTED_VERIFIED | — |
| 54 | Machine-readable release evidence bundle | P0 | IMPLEMENTED_VERIFIED | — |
| 55 | Canary/staged rollout/rollback implementation | P0 | IMPLEMENTED_VERIFIED | simulation over in-process instances; no real fleet |
| 56 | Vulnerability response / patch / EOL policy | P0 | IMPLEMENTED_PENDING_HUMAN | target SLAs PROPOSED; need owner approval |
| 57 | State backup/restore applicability record | P1 | NA_PROPOSED | N/A disposition drafted; approver must sign off |
| 58 | Full operational runbook | P0 | IMPLEMENTED_PENDING_HUMAN | simulated tabletop generated; a human-attended drill is still required |
| 59 | Recurring governance review process | P1 | IMPLEMENTED_PENDING_HUMAN | no review has been held yet |
| 60 | Exceptions/waivers/technical-debt register | P0 | IMPLEMENTED_VERIFIED | — |
| 61 | Formal production exit-gate artifact | P0 | IMPLEMENTED_VERIFIED | the gate exists and runs; its verdict is NOT GO |
| 62 | Continuous integration workflow | P0 | IMPLEMENTED_VERIFIED | workflow authored; not yet executed on a hosted runner |
| 63 | Static typing/linting policy | P1 | IMPLEMENTED_VERIFIED | — |
| 64 | Coverage report and minimum threshold | P0 | IMPLEMENTED_VERIFIED | — |

## Human actions that move the gate

1. Fill `governance/OWNERS.json` (owner, deputy, paging target, review dates).
2. Approve or amend `governance/ADR-0001-stream-design.md`, `governance/support-policy.md`, the telemetry retention values, and the N/A dispositions (#28, #57).
3. Approve or reject waivers WVR-001..003; provide a release signing key for #20.
4. Decide SLO-3: restate it as a measured CPython target, or fund a native fast path.
5. Run `.github/workflows/ci.yml` on hosted runners (platform matrix #49) and hold a staffed Sev-1 drill (#58).
6. Add `conformance/APPROVAL.json`, then re-run `tools/evidence_bundle.py`.

---

# INV-17 Streaming Primitive — v4.2.0 Audit / Hardening / Missing-Component Report

**Audit date:** 2026-09-23  
**Input version:** 4.1.0  
**Updated version:** 4.2.0  
**Scope:** source archive supplied for INV-17 only. No claims are made about sibling repositories or an external `pk_core` installation.

## Executive result

The runtime primitive was materially hardened and its independently testable core was separated from the `pk_core` assessment adapter. The updated runtime passes its standalone unit/contract suite under ordinary Python and `python -O`. The existing repository-level 100-check conformance suite cannot be executed from this archive because `pk_core` is neither bundled nor importable in the supplied environment; therefore the repository is **not independently certifiable as Production GO from this archive alone**.

## Defects corrected in 4.2.0

1. **O(n) FIFO read path** — `list.pop(0)` was replaced with `collections.deque.popleft()` for O(1) head removal.
2. **No hard outstanding-credit ceiling** — immutable `StreamConfig.max_credit` now fail-closes excessive grants without mutating state.
3. **No independent in-flight buffer ceiling** — `StreamConfig.max_buffer` now provides a second fail-closed resource guard.
4. **Shared mutable state was unsynchronized** — lifecycle, credit, queue, counters, and snapshots are protected by `RLock`.
5. **Runtime implementation was coupled to the certification framework** — the stream now lives in dependency-light `stream.py`; `component.py` re-exports it for compatibility.
6. **Errors lacked stable machine-readable identity** — all stream runtime errors now derive from `StreamError` and expose stable `PK_STREAM_*` codes plus immutable details.
7. **Termination left stale credit** — graceful end and abrupt writer drop now revoke outstanding credit.
8. **Reader drop retained undeliverable buffered objects** — dropping the reader now reclaims the buffer immediately and records `dropped_items`.
9. **Lifecycle invalid operations were underspecified in code** — post-end grants/writes and operations against dropped ends now reject explicitly.
10. **No atomic runtime diagnostics snapshot** — `Stream.stats()` exposes consistent state, credit, backlog, stalls, transfer/read counts, and dropped-element counts.
11. **No standalone data-plane tests** — `tests/test_stream.py` now tests resource ceilings, FIFO/backpressure, type confusion, graceful EOF, endpoint drops, stable errors, diagnostics, and concurrent mutation without requiring `pk_core`.

## Verification performed

- `python -m py_compile` for runtime, adapter, contract, package init, and tests: **PASS**.
- `python tests/test_stream.py -v`: **PASS (10/10)**.
- `python -O tests/test_stream.py -v`: **PASS (10/10)**.
- Existing `tests/test_component.py`: **SKIPPED (3/3)** because `pk_core` is not importable from this archive/environment.
- Static scan for common high-risk constructs (`eval`, `exec`, `shell=True`, pickle, TODO/FIXME): no runtime hits. The only broad `except Exception` is a failure-capture branch in a test thread.

## Remaining missing or incomplete production components

The following inventory is the complete set of gaps discovered in this archive during the second audit. A checklist item can map to more than one engineering artifact; conversely, one missing artifact can satisfy several checklist items when implemented.

| # | Missing / incomplete component | Checklist mapping | Current evidence / gap |
|---:|---|---|---|
| 1 | Accountable owner and escalation record | C009, C097 | No owner, on-call target, escalation ladder, or severity matrix exists in the archive. |
| 2 | Approved architecture decision record | C010 | `MASTER.md` contains workflow prompts, but no signed/approved ADR records the selected stream design and tradeoffs. |
| 3 | SHALL-level requirements specification | C011-C019 | Contract prose exists, but there is no standalone normative requirements/state/failure document covering all listed semantics and precedence rules. |
| 4 | Lifecycle/state-machine specification | C014-C015 | Runtime exposes states, but no formal transition table/diagram defines legal and illegal transitions and terminal semantics. |
| 5 | Requirements traceability matrix | C020 | No machine-readable mapping from all 100 checklist IDs to concrete code/test/evidence artifacts is shipped. |
| 6 | External schema/WIT artifacts | C021-C022 | Interface names such as `PK_STREAM/1` are declared, but their actual typed schema/WIT files are absent. |
| 7 | Boundary authentication specification | C023, C044 | No identity/authentication mechanism is specified for transfers or adjacent-layer integration. |
| 8 | Capability/authorization policy | C024, C042-C043 | Capability expectations are described conceptually, but there is no executable policy or capability-token contract. |
| 9 | Timeout/cancellation/retry/idempotency contract | C025 | Non-blocking backpressure exists, but full cancellation, timeout, retry, and idempotency semantics are not specified/tested. |
| 10 | Cross-version compatibility protocol | C016, C027, C093 | No supported-version matrix, negotiation rules, downgrade behavior, or compatibility fixtures exist. |
| 11 | Tenant/workload fairness policy | C017, C028 | Per-stream ceilings now exist, but there is no multi-stream tenant quota, fairness scheduler, or anti-starvation policy. |
| 12 | Cloud/datacenter/near-edge/far-edge applicability profile | C012, C018 | The contract says handles are instance-local; disconnected/network-tier behavior is not formally dispositioned per deployment tier. |
| 13 | Declarative configuration loader/schema | C032-C035 | `StreamConfig` is immutable, but no external validated configuration schema/loader or site/environment overlay mechanism exists. |
| 14 | Configuration provenance record | C036 | No author, source revision, activation timestamp, or provenance envelope is recorded for effective configuration. |
| 15 | Atomic configuration activation/rollback mechanism | C037-C038 | Per-object config is immutable, but there is no runtime configuration transaction, rollout, or rollback controller. |
| 16 | Deterministic bootstrap/package manifest | C031, C040 | No `pyproject.toml`, lockfile, install manifest, or pinned `pk_core` dependency is present. |
| 17 | Adjacent-layer integration adapters | C030, C083 | No executable adapters/fixtures for INV-15, INV-12, INV-18, INV-19, or INV-20 are included. |
| 18 | `pk_core` integration dependency | C030, C090 | The repository conformance adapter imports `pk_core`, but that dependency is absent/unpinned; its 100-check suite therefore cannot be executed here. |
| 19 | Dedicated threat-model artifact | C041 | Threat strings exist in `contract.py`, but no attacker model, trust boundaries, abuse cases, or mitigations matrix exists. |
| 20 | Artifact integrity/provenance/SBOM pipeline | C045 | No signing, digest policy, SBOM, provenance attestation, or approved-build verification pipeline exists. |
| 21 | Tenant/workload isolation verification | C046 | The primitive is in-process and has no tests demonstrating cross-tenant/workload isolation or transfer authorization. |
| 22 | Data classification/encryption/residency policy | C047 | Payload semantics are intentionally out of scope, but no boundary rule specifies when stream payloads require encryption or residency controls. |
| 23 | Trust-service outage behavior | C048 | Identity, attestation, policy, key, and time service outage behavior is not dispositioned as applicable/N/A with rationale. |
| 24 | Tamper-evident security audit events | C049 | Runtime counters exist, but no security event ledger, chaining, signing, or export interface is implemented. |
| 25 | Adversarial/resource-exhaustion security suite | C050, C087 | Basic bounds are tested; fuzzed exhaustion, spoof/replay, hostile object behavior, and abuse-case tests are absent. |
| 26 | Automated health and stall thresholds | C052 | `credit_stalls` is counted, but no threshold, health-state transition, timer, or alert policy is implemented. |
| 27 | Load shedding/circuit-breaker policy | C054 | Backpressure and ceilings provide local admission control, but there is no cross-stream overload/load-shedding or circuit-breaking mechanism. |
| 28 | Failover/distributed disposition | C055, C058 | Instance-local scope suggests some distributed concerns are N/A, but the repository lacks an explicit applicability decision and proof. |
| 29 | Crash/restart/resume/replay semantics | C057 | In-memory stream state has no persistence/reconstruction/replay contract or explicit loss semantics after process failure. |
| 30 | Quarantine/freeze/emergency-disable control | C059 | README mentions registry removal, but no executable disable/quarantine control is included. |
| 31 | Fault-injection suite | C060 | No forced endpoint/process/dependency failure harness verifies recovery objectives. |
| 32 | Reproducible benchmark harness | C061-C063 | The assessment adapter checks buffer size only; there is no latency/throughput/startup/CPU/memory benchmark with reproducible methodology. |
| 33 | Percentile and worst-case SLO measurement | C062 | The `<1us p99` SLO is declared but not measured or enforced by supplied evidence. |
| 34 | Per-tenant/per-workload overhead benchmark | C064 | No multi-tenant/workload benchmark or accounting model exists. |
| 35 | Copy/context-switch/serialization profiling | C065-C066 | Deque removes one avoidable cost, but no profiler evidence quantifies copies, scheduler transitions, or zero-copy opportunities. |
| 36 | Power/thermal measurement | C068 | No constrained-edge power or thermal benchmark exists. |
| 37 | Capacity/saturation model | C069 | Ceilings exist, but no predictive capacity model relates credit/backlog/stalls to sizing or scale decisions. |
| 38 | Performance regression release gate | C070 | No CI benchmark thresholds block regressions in throughput/tail latency/density/startup. |
| 39 | Health/readiness/version/capability endpoint | C071 | `stats()` is local diagnostics only; no standard operator-facing health/readiness/capability surface exists. |
| 40 | Metrics exporter | C072 | Counters/snapshot exist, but no Prometheus/OpenTelemetry/other structured metrics adapter is included. |
| 41 | Structured logging | C073 | No stable operation/workload/tenant identifiers or structured log events are emitted. |
| 42 | Trace propagation | C074 | No trace-context field/adapter exists at stream boundaries. |
| 43 | High-cardinality diagnostics/privacy guard | C075 | Snapshot fields are bounded, but there is no policy/redaction layer for richer diagnostics. |
| 44 | Decision-reason/explainability surface | C076-C077 | Error details help refusals, but no complete explain view ties decisions to config/policy/topology constraints. |
| 45 | Release-lineage/infrastructure correlation | C078 | No build/release/infrastructure graph identifiers are attached to events or diagnostics. |
| 46 | Telemetry retention/sampling/export policy | C079 | No retention, sampling, privacy, or export specification exists. |
| 47 | Dashboards and alert rules | C080 | No dashboards or alerts distinguish load, dependency failure, attacks, policy rejection, or software defects. |
| 48 | Exhaustive public-interface contract tests | C082 | Standalone tests cover core behavior, but not every externally declared `PK_STREAM/1`, `PK_STREAM_CREDIT/1`, and `PK_STREAM_CLOSE/1` schema because schemas are absent. |
| 49 | Platform/runtime compatibility matrix/tests | C084 | No CI matrix across supported Python/runtime/CPU/OS targets exists. |
| 50 | Fuzz/property-based tests | C085 | No fuzzing/property tests target type handling, state sequences, credit arithmetic, or schema boundaries. |
| 51 | Deep race/soak concurrency suite | C086 | Two deterministic thread-safety tests exist, but no randomized race detector, long soak, or mixed concurrent read/write/drop/grant state fuzzing exists. |
| 52 | Benchmark/soak/burst/fleet-scale suite | C088 | No sustained, burst, overload, long-duration, or fleet-scale load harness exists. |
| 53 | Disaster/partition/reconnect suite | C089 | Network behavior is mostly outside this instance-local primitive, but applicability and adjacent-layer partition/reconnect tests are absent. |
| 54 | Machine-readable release evidence bundle | C090 | Expected `pk_core` evidence/gate outputs are not present in the archive and cannot be generated without the dependency. |
| 55 | Canary/staged rollout/rollback implementation | C092 | Procedures are described at a high level only; no rollout automation or rollback artifact is included. |
| 56 | Vulnerability response / patch / EOL policy | C094 | No support window, patch SLA, vulnerability intake, or EOL schedule exists. |
| 57 | State backup/restore applicability record | C095 | The stream is ephemeral, but the repository does not formally record whether backup/restore is N/A and how reconstruction is handled. |
| 58 | Full operational runbook | C096-C097 | README has Day-0/1/2 notes, but no detailed incident, containment, recovery, paging, or operator runbook exists. |
| 59 | Recurring governance review process | C098 | No cadence, reviewer set, review evidence template, or automation is defined. |
| 60 | Exceptions/waivers/technical-debt register | C099 | No owner/expiry-based waiver and debt ledger exists. |
| 61 | Formal production exit-gate artifact | C100 | Gate commands are documented but no current signed/machine-verifiable exit-gate result ships with the repository. |
| 62 | Continuous integration workflow | C070, C081-C090 | No CI definition runs compile, runtime tests, optimized tests, conformance, static checks, or benchmarks on change. |
| 63 | Static typing/linting policy | C031, C081 | Type hints exist, but no configured type checker/linter or clean report is included. |
| 64 | Coverage report and minimum threshold | C081-C087 | No branch/line coverage evidence or release threshold is provided. |

## Release disposition

**Runtime core:** hardened and locally verified.  
**Repository certification:** **PARTIAL** — cannot independently run the `pk_core` conformance/evidence gate, and the production/governance/integration artifacts above remain missing or incomplete.  
**Recommended next gate:** provide/pin `pk_core`, add real interface schemas plus adjacent-layer fixtures, execute the 100-check evidence pipeline, then close the security/performance/operations artifacts before treating INV-17 as independently Production GO.
