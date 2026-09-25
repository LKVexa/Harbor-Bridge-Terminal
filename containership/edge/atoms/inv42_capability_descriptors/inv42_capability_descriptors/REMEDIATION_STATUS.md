# INV-42 v4.3.0: remediation status against the missing-component checklist

**Source checklist:** `inv42_capability_descriptors_v4.2.0_MISSING_COMPONENTS_DETAILED_CHECKLIST.md` (42 components)  
**Remediated version:** 4.3.0 (2026-09-22)  
**Production exit verdict:** `NOT_ELIGIBLE`. Re-run `tools/exit_gate.py` to reproduce it.

## Legend

| Status | Meaning |
|---|---|
| implemented | Code, tests and docs exist in this archive, and the exit criterion can be verified locally. |
| implemented-pending-external | Built and tested here. Closing it still needs CI-run or sibling-layer evidence. |
| implemented-blocked-external | Built and tested here. Closing it needs something only the owner or platform can supply. This is a BLOCKER waiver. |
| partial-waived | Partly done. The remainder is under a time-bounded waiver. |
| waived | Can't be done without fabricating content. The work is recorded under a waiver instead. |

## Components

| ID | Priority | Component | 4.3.0 status | Evidence | External / waiver |
|---|---|---|---|---|---|
| MC-001 | BLOCKER | pk_core dependency and executable suite-level release gate | implemented-blocked-external | tools/certify.py (dev/certification profiles, hard-fail, API+version probe, evidence); SPEC_MANIFEST.json pk_core contract; CI gate job | W-001: pk_core version/source/hash must be supplied by suite owner |
| MC-014 | BLOCKER | artifact integrity, provenance, SBOM, and release signing | implemented-blocked-external | tools/release.py (reproducible archive, CycloneDX SBOM, SLSA provenance, Ed25519 signed manifest, verify incl. rebuild), RELEASE.md, KEY_MANAGEMENT.md | W-004: HSM/KMS production key |
| MC-015 | BLOCKER | confidential authenticated transport profile | implemented-blocked-external | transport.py TLS1.3 mTLS profile, identity pin, bounded frames; TransportTest (round-trip, rogue CA, plain socket); ADR-0003 | W-005: deployment PKI |
| MC-041 | BLOCKER | machine-readable acceptance evidence and formal production exit result | implemented-blocked-external | tools/exit_gate.py -> evidence/PRODUCTION_EXIT.json (current verdict NOT_ELIGIBLE) | closes when W-001/W-004/W-005 close |
| MC-002 | HIGH | MASTER.md source/master prompt artifact | waived | NFR.md SHALL requirements stand in; not reconstructed (would be fabrication) | W-002 |
| MC-003 | HIGH | accountable owner and escalation metadata | partial-waived | OWNERS.yaml (accountable owner, escalation ladder, support hours) | W-003: on-call/secondary/security contact TBD |
| MC-004 | HIGH | requirements traceability matrix | implemented | tools/traceability.py + TRACEABILITY.json (100/100 mapped, evidence paths validated, CI --check, test_operations) | — |
| MC-005 | HIGH | adjacent-layer adapters and integration tests | implemented-pending-external | adapters.py (INV-41 source, INV-13 ABI boundary), tests/test_integration.py (process transfer, degraded control plane, schema conformance), wit/inv42-descriptor.wit | W-006: real sibling-layer builds |
| MC-006 | HIGH | pinned implementation/specification manifest | implemented-pending-external | SPEC_MANIFEST.json (protocols, runtime, adjacent layers, tooling) | W-001 for pk_core pin |
| MC-007 | HIGH | reproducible packaging and dependency metadata | implemented-pending-external | pyproject.toml (Python bounds, stdlib-only runtime, extras), requirements-release.txt hash policy | W-001; owner generates tooling hashes |
| MC-008 | HIGH | CI pipeline and mandatory release checks | implemented-pending-external | .github/workflows/ci.yml (matrix tests, -O, extended fuzz, traceability, coverage, perf, certification, release build/verify, exit gate) | needs first CI run (W-006) |
| MC-010 | HIGH | formal success/degraded/retryable/terminal failure taxonomy | implemented | outcomes.py TAXONOMY/classify/RETRY_POLICY; OutcomeTaxonomyTest | — |
| MC-016 | HIGH | external identity/attestation/policy/key/time outage behavior | implemented | key_provider fail-closed (KeyUnavailable), NFR.md External services, KeyProviderTest, degraded-control-plane test | — |
| MC-017 | HIGH | tamper-evident security audit event sink | implemented | audit.py hash chain + MAC + anchored head + allow-list; AuditTest (modify/delete/reorder/truncate/re-forge) | — |
| MC-019 | HIGH | fault-injection and recovery test suite | implemented | FaultInjectionTest (mint failure no partial commit - bug fixed, close failure, restart, child crash), observer-failure test | — |
| MC-027 | HIGH | parser/input fuzzing harness | implemented | FuzzTest seeded mutational fuzzing (20k default, 200k in CI with rotating seed) + regression corpus | — |
| MC-029 | HIGH | expanded threat-derived adversarial suite | implemented | THREAT_MODEL.md T1-T15; AdversarialTest (hostile subclasses - bug fixed, log safety, constant-time, key compromise, sustained exhaustion) | — |
| MC-030 | HIGH | benchmark, soak, burst, overload, and fleet-scale suite | implemented | tools/bench.py (latency, burst, overload, fleet, soak) | — |
| MC-031 | HIGH | cross-runtime/OS/CPU/provider compatibility matrix and CI | implemented-pending-external | CI matrix 4 OS/arch x Python 3.10-3.13 | W-006: run evidence |
| MC-033 | HIGH | performance thresholds and regression gate | implemented | PERF_THRESHOLDS.json p50/p95/p99, release-blocking in bench + CI | — |
| MC-035 | HIGH | measured SLO/error-budget and support commitment machinery | implemented | SLO.md + burn-rate alerts | — |
| MC-036 | HIGH | canary/staged rollout/rollback/emergency-disable automation | implemented | emergency_disable()/INV42_EMERGENCY_DISABLE, ROLLOUT.md, tools/rollout.py canary evaluator + tests | — |
| MC-037 | HIGH | vulnerability response, patching, EOL, and adjacent-version support policy | implemented | VULNERABILITY_POLICY.md | — |
| MC-038 | HIGH | incident response runbook | implemented | INCIDENT_RUNBOOK.md | — |
| MC-009 | MEDIUM | license and notice files | partial-waived | LICENSE (all-rights-reserved holding notice), NOTICE | W-008: owner licence choice |
| MC-011 | MEDIUM | deployment-context semantics | implemented | NFR.md deployment contexts, disconnected, precedence, unsupported | — |
| MC-012 | MEDIUM | quantitative non-functional requirements | implemented | NFR.md quantitative table, PERF_THRESHOLDS.json, SLO.md | — |
| MC-013 | MEDIUM | configuration applicability/provenance decision | implemented (N/A decision) | NFR.md Configuration: no mutable config; rules if introduced | — |
| MC-018 | MEDIUM | managed key lifecycle / protected-memory integration | partial-waived | key_provider injection, rotation-by-table-replacement, KEY_MANAGEMENT.md | W-007: no protected memory in CPython |
| MC-020 | MEDIUM | health/readiness adapter and stall thresholds | implemented | telemetry.health (ready/degraded/not_ready, saturation, stall) | — |
| MC-021 | MEDIUM | metrics exporter | implemented | telemetry.Metrics Prometheus exporter (ops by outcome/class, latency histograms, saturation, disable gauge) | — |
| MC-022 | MEDIUM | structured logging with privacy controls | implemented | telemetry.StructuredLogger + redact; leak tests | — |
| MC-023 | MEDIUM | distributed tracing propagation | implemented | telemetry.span/parse_traceparent/with_trace (W3C) | — |
| MC-024 | MEDIUM | operator explain view and release/infrastructure correlation | implemented-pending-external | telemetry.explain (decision view + release lineage) | live infra graph is a platform service |
| MC-025 | MEDIUM | telemetry retention/sampling/privacy/export policy | implemented | TELEMETRY_POLICY.md | — |
| MC-026 | MEDIUM | dashboards and alerts | implemented | dashboards/inv42_dashboard.json, alerts/inv42_alerts.yml (attack/policy/load/dependency/degradation classes) | — |
| MC-028 | MEDIUM | mixed-operation concurrency/race suite | implemented | ConcurrencyTest mixed open/resolve/close/status and destroy races | — |
| MC-032 | MEDIUM | coverage measurement and threshold gate | implemented | tools/coverage_gate.py (95% descriptors, 85% others; all runtime modules currently >= 85.7%) | — |
| MC-034 | MEDIUM | edge power/thermal measurement | implemented (N/A decision) | NFR.md Edge power | — |
| MC-039 | MEDIUM | recurring review automation/evidence | implemented | REVIEWS.json, tools/review_due.py, .github/workflows/review.yml | — |
| MC-040 | MEDIUM | exception/waiver/technical-debt registry | implemented | WAIVERS.json (owner/expiry/exit condition), enforced by traceability + exit gate | — |
| MC-042 | OPTIONAL | policy-controlled descriptor transfer/delegation between tables | implemented | delegation.py re-issuance (move/share, default deny, idempotent txn, atomic, audited), ADR-0002, DelegationTest | — |

## Global completion controls

- [x] Every MC is linked to its INV-42-Cxxx controls in `MISSING_COMPONENTS.json` and `TRACEABILITY.json`. All 100 requirements are mapped, and each evidence path is validated by `tools/traceability.py --check`.
- [x] New tests were added alongside every fix. They grew from 17 to 58, and CI makes them mandatory.
- [x] The threat model, ADRs, README, SECURITY, OPERATIONS, COMPATIBILITY and CHANGELOG were updated, and the SBOM and provenance tooling was added.
- [x] Each waiver is recorded with an owner, an expiry date and an exit condition. A waived control is never counted as met, and the exit gate blocks on it.
- [ ] Assign an issue or epic per MC. This needs the owner's tracker.
- [ ] Code review plus a security and architecture review by a human reviewer. The chop-shop audit is recorded in `REVIEWS.json` and is waiting for your countersignature.
- [ ] Re-run the exit gate on the exact artifact signed with the KMS key. This is blocked by W-004.

## Evidence captured in this pass

| Check | Result |
|---|---|
| Standalone, integration and operations suites | 58 run; 55 pass; 3 skipped (pk_core, by design); 0 failures; also passes under `python -O` |
| Certification profile | **FAIL**, as intended: pk_core is not pinned or present (W-001) |
| Fuzzing | 20,000 seeded mutants plus a 10-case regression corpus. No mutant was accepted. |
| Performance gate | pass. Resolve p50/p99 = 8.0/23.1 µs; soak ≈ 50,610 open+close/s |
| Coverage gate | pass. descriptors.py 100%; every other runtime module ≥ 85.7% (stdlib-trace line mode) |
| Traceability | met: 82, waived: 3, met-pending-external-evidence: 8, not-applicable: 7 |
| Release | Reproducible archive, SBOM, provenance and signature all verify. Channel is `dev-only` because the key is ephemeral (W-004). |

## Defects found and fixed during remediation

1. **`open()` partial commit.** The number was consumed and the entry inserted before the tag was minted. If minting failed, an orphaned live entry was left behind. This was found by MC-019 fault injection.
2. **Hostile `dict`/`str`/`int` subclasses were accepted by `from_wire()`.** This was found by the MC-029 adversarial work.
3. **Unbounded attacker text was echoed in error messages** (log-injection surface). This was found by MC-029.
4. **The package root could not be imported without `pk_core`.** This blocked every non-certification consumer. It was found while building MC-005 adapters.

## What the owner must supply to reach PRODUCTION_APPROVED

1. **W-001:** the `pk_core` version, source URL and sha256. Fill in `SPEC_MANIFEST.json` and run `tools/certify.py --profile certification` in clean CI.
2. **W-004:** a KMS- or HSM-backed Ed25519 release key. Rebuild the release and confirm `release.py verify` reports `production_eligible: true`.
3. **W-005:** the deployment CA and certificate issuance for `transport.py`.
4. **High-priority waivers W-002, W-003 and W-006:**
   - W-002: recover the original `MASTER.md`.
   - W-003: staff on-call and name a security contact.
   - W-006: get a green CI matrix run and integrate against real sibling layers.
5. **W-008:** choose the outbound licence.
