# INV-18 Completion Primitive — v4.3.0 Remediation Audit

**Audited version:** 4.3.0 (from 4.2.0-hardened)
**Date:** 2026-09-23
**Work order:** apply `INV18_v4.2.0_missing_components_checklist.md` (88 missing items) to the candidate
**Method:** junkyard chop-shop, candidate-only (no yard donors were pulled; everything is stdlib and first-party)
**Gate verdict:** **NO_GO** (exit 20) — `conformance/RELEASE_EVIDENCE.json`, sealed by SHA-256

## Executive result

All 88 missing components now exist in version control **with executed evidence**:
193 tests (185 pass, 0 fail, 8 skipped), identical on CPython 3.10, 3.11, 3.12 and 3.13;
15/15 wire fixtures; 9/9 fault-injection scenarios; 20/20 threat-model threats mapped to
passing tests; benchmark thresholds met; the RTM links all 136 requirements (36 SHALL + 100
checklist items) to tests with zero untested requirements, zero untagged tests and zero
orphan modules.

Of the 88 items: **71 satisfied, 13 partial, 4 blocked.** Every partial/blocked item is
held by something this pass cannot honestly supply — a missing dependency, a human
approval, or hardware/platforms not available here. The gate refuses to turn any of them
into a pass, which is the behaviour C100 asks for.

## What still stops a GO

| Blocks | Items | What clears it |
|---|---|---|
| **pk_core absent** (BLOCKED) | C031, C093, C100 (3 pk_core tests skip) | vendor pk_core at a pinned commit, record its sha256 in `requirements.lock.json` |
| **real adjacent components absent** (BLOCKED) | C030, C083 (5 real-tier tests skip) | set `INV18_REAL_COMPONENTS` to the INV-12/15/16/17/20 packages and run the gate |
| **owners vacant** (BLOCKED) | C009 | name backup, security and operational owners in `governance/OWNERS.json`; replace `-TBD` CODEOWNERS handles |
| **ADR not approved** (BLOCKED) | C010 | approving authority sets ADR-001 status to `ACCEPTED` |
| human approvals (CONDITION) | C041/C087 threat model, C062/C091 thresholds + revised SLO, C063 DEBT-PERF-01, C068 power N/A, C098 review countersign, C097 tabletop | sign the record, or accept the condition in `governance/ACCEPTED_CONDITIONS.json` |
| evidence signing (CONDITION) | C045 | provide `INV18_RELEASE_KEY` to the gate |
| platforms (CONDITION) | C084 | run `.github/workflows/ci.yml` on Windows, macOS arm64 and Linux arm64 |

When only CONDITIONs remain and each is accepted, the verdict becomes `CONDITIONAL_GO`; with none, `GO`.

## Measured findings you should know

1. **The source SLO is not achievable in CPython.** "p99 resolution under 1 µs" measures
   at ≈ 2.7 µs p99 (bare resolve p50 ≈ 1.1 µs). Revised thresholds are PROPOSED (W-C062).
2. **Lock convoy in the governed runtime.** One thread: ≈ 16–24k create→resolve→take
   cycles/s. At 2–16 threads the combined rate drops to ≈ 5–6k/s. Correctness holds; the
   capacity model sets ≤ 3 threads per Runtime. Recorded as DEBT-PERF-01.
3. Memory: 1.2 KB per bare future, 2.9 KB per governed future; the bounded tombstone ring
   adds at most about 10 MB. Soak shows no leak once every bounded ring is full.

## Defects found and fixed by this pass's own tests

1. `ErrorRecord.from_dict` accepted `details: []` (property/fuzz test) and echoed a malformed
   peer `original_code` into an invalid record (error-record fuzz).
2. After registry release, a second receiver got `PERMISSION_DENIED` instead of
   `FUTURE_ALREADY_TAKEN`, and a producer resolving a cancelled future got
   `ALREADY_RESOLVED` instead of `FUTURE_CANCELLED`. Fixed with a bounded tombstone ring
   that stores the terminal state.
3. Wire `fence` (failover) did not check tenant ownership, so a cross-tenant failover
   takeover was possible.
4. The wire endpoint kept every future forever (an unbounded registry).
5. Type-mismatch rejections were never logged (found by the fault suite).
6. The config env prefix `INV18_` collided with operational variables. `INV18_CONTEXT`
   and `INV18_RELEASE_KEY` made the CLI refuse to start (found by the multi-Python
   compatibility run). The prefix is now `INV18_CFG_`.
7. `adapters.py` used `__import__` dynamically (found by the ambient-authority inventory).
8. `__init__` imported pk_core eagerly, so the primitive could not load without it. It now loads lazily.
9. My own example config set a soft limit above its hard limit (found by the config-layer test).
10. The fault harness's invariant checker treated telemetry counters as state. It now
    separates state invariants from telemetry consistency (a crash-at-boundary test caught this).

## Item-by-item status (the 88 remediated items)

Legend: ✅ satisfied (artifact + executed passing tests) · ◐ partial (implemented and tested, human/infra blocker open) · ⛔ blocked (mandatory test cannot execute here)

| Item | Status | Principal evidence |
|---|---|---|
| C009 owner & escalation | ◐ OWNERS_VACANT | governance/OWNERS.json, CODEOWNERS, OWNERS_HISTORY.json; GovernanceTest |
| C010 ADR | ◐ ADR_NOT_APPROVED | docs/adr/ADR-001 (PROPOSED); gate refuses until ACCEPTED |
| C011 SHALL requirements | ✅ | REQUIREMENTS.json (36 SHALL, stable IDs, classes, verification) |
| C012 context matrix | ✅ | ARCHITECTURE §1, config/site-far-edge.json, ApplicabilityTest, test env labels |
| C013 NFRs | ✅ | ARCHITECTURE §2 + methodology per NFR |
| C014 outcome semantics | ✅ | errors.CODES, OutcomeMatrixTest (exhaustive state×op) |
| C016 versioning | ✅ | ARCHITECTURE §4, tools/api_snapshot.py + undeclared-break test |
| C017 capacity/quotas/fairness | ✅ | runtime limits, LimitsTest, no-starvation test |
| C018 network absence | ✅ | ARCHITECTURE §6, runtime sandbox (no network), partition/reconnect tests |
| C019 precedence | ✅ | policy INV18-PREC/1, errors.precedence, PrecedenceTest |
| C020 RTM | ✅ | certify.build_rtm → conformance/RTM.json/.md, gap-detection tests |
| C022 schemas | ✅ | wire.SCHEMAS → schemas/*.json, validator, drift test |
| C023 auth boundaries | ✅ | INTERFACES §2 matrix, AuthnTest negatives |
| C024 capabilities | ✅ | resolver/receiver/observer/admin caps, CapabilityTest, confused-deputy tests |
| C025 timeout/cancel/retry/idempotency/backpressure | ✅ | wait/take_wait/cancel, idempotency keys, race tests |
| C026 structured errors | ✅ | errors.py, PK_FUTURE_ERROR/1, round-trip + unknown-code tests |
| C027 cross-version | ✅ | wire.negotiate, other-major refusal, ext forward-compat |
| C028 interface limits | ✅ | size-before-parse, boundary/boundary+1 tests |
| C029 fixtures | ✅ | fixtures/v1 (15), fixtures_runner, examples/producer_consumer.py executed |
| C030 adjacent integration | ⛔ REAL_TIER_NOT_RUN | adjacent.py doubles all pass; real tier skipped |
| C031 pinned dependencies | ⛔ PK_CORE_MISSING | pyproject.toml, requirements.lock.json; pk_core tests skip |
| C032 artifact/config/state separation | ✅ | ARCHITECTURE §9, read-only install bootstrap test |
| C033 config schema & secure defaults | ✅ | config.SCHEMA/DEFAULTS, ValidationTest |
| C034 fail-closed activation | ✅ | whole-document validation, fuzz, no partial activation |
| C035 site/env config | ✅ | layering, INV18_CFG_ allow-list, same-artifact test |
| C036 provenance | ✅ | config.Revision, ProvenanceTest |
| C037 atomic updates | ✅ | single-reference swap, concurrent-reader + crash-between-stage-and-commit tests |
| C038 rollback | ✅ | ConfigStore.rollback / activate_or_rollback, drill rollback |
| C039 secrets | ✅ | secret:// refs only, redaction, sentinel-leak tests |
| C040 bootstrap | ✅ | bootstrap.py, clean read-only idempotent bootstrap test |
| C041 threat model | ◐ THREAT_MODEL_NOT_APPROVED | conformance/THREAT_MODEL.json (20 threats → tests) |
| C042 least privilege | ✅ | SECURITY §2 matrix, capability tests |
| C043 ambient authority | ✅ | AST inventory + runtime sandbox |
| C044 authentication | ✅ | auth.py, forged/expired/replayed/wrong-aud tests |
| C045 artifact integrity | ◐ UNSIGNED_EVIDENCE | SHA256SUMS, SBOM, verify tooling, tamper tests; no signing key here |
| C046 isolation | ✅ | tenant-bound caps, anti-enumeration, quotas |
| C047 encryption/rotation | ✅ | at-rest N/A statement, key rotation overlap/revocation tests |
| C048 security-service outage | ✅ | fail-closed outage tests (single + simultaneous) |
| C049 tamper-evident audit | ✅ | AuditChain (+HMAC), mutation/deletion/reorder detection |
| C050 adversarial suite | ✅ | tests/test_security.py (20 tests) |
| C051 failure matrix | ✅ | RESILIENCE §1 FMEA with tests / justified N/A |
| C052 health/stall | ✅ | health(), threshold tests, single-slow-producer no-flap test |
| C053 bounded retry | ✅ | retry.RetryPolicy, jitter/deadline/cancel tests |
| C054 admission/circuit | ✅ | admission limits, CircuitBreaker with hysteresis |
| C055 failover | ✅ | epoch fencing, stale-owner test |
| C056 degraded operation | ✅ | telemetry-sink failure keeps core correct, DEGRADED status |
| C057 crash/restart | ✅ | SIGKILL restart test, crash-at-boundary test |
| C058 split brain | ✅ | epochs, simultaneous owners, delayed duplicates |
| C059 quarantine | ✅ | disable drain/freeze, unauthorized refusal, disable under load |
| C060 fault injection | ✅ | fault.py 9 scenarios, invariant checks |
| C061 baselines | ✅ | bench.py, conformance/BENCH_BASELINE.json |
| C062 percentile thresholds | ◐ THRESHOLDS_PROPOSED | PERFORMANCE_THRESHOLDS.json (baseline passes) |
| C063 load regimes | ◐ DEBT-PERF-01 | steady/burst/overload/recovery/concurrency measured |
| C064 per-workload overhead | ✅ | scaling curve, tenant quota test |
| C065 copy/hop analysis | ✅ | profile_ops: zero copies, 0 hops |
| C066 optimisations | ✅ | OPT-1 adopted and measured; rejected options documented |
| C067 resource bounds | ✅ | bounded rings, overload memory test, soak no-leak |
| C068 power/thermal | ◐ W-C068 | N/A determination awaiting approval |
| C069 capacity model | ✅ | bench.capacity_model; 20k-future prediction within 25 % |
| C070 regression gate | ✅ | bench.compare + injected-regression test; enforced by certify |
| C071 status | ✅ | PK_FUTURE_STATUS/1, schema test |
| C072 metrics | ✅ | declared metric contract, bounded cardinality |
| C073 structured logs | ✅ | PK_FUTURE_LOG/1, redaction, rate limit |
| C074 trace context | ✅ | W3C traceparent, continuity across INV-16/20/wire |
| C075 safe diagnostics | ✅ | hashed tenants, sentinel tests |
| C076 decision records | ✅ | DecisionLog, every-branch test |
| C077 explain view | ✅ | `explain`, predefined-incident diagnosis test |
| C078 lineage | ✅ | conformance/LINEAGE.json, event→release chain test |
| C079 telemetry policy | ✅ | OBSERVABILITY TP/1 mapped to config |
| C080 dashboards/alerts | ✅ | dashboards/*.json, alerts.py, synthetic alert tests |
| C082 contract tests | ✅ | test_contract.py incl. installed-copy test |
| C083 tier integration | ⛔ REAL_TIER_NOT_RUN | local + wire tiers pass; real tier skipped |
| C084 platform compat | ◐ PLATFORMS_NOT_RUN | CPython 3.10–3.13 on linux-x86_64 all green; CI matrix declared |
| C085 fuzz/property | ✅ | test_property.py, fixtures/fuzz_corpus.json |
| C087 threat-derived tests | ◐ THREAT_MODEL_NOT_APPROVED | every high/critical threat → passing test |
| C088 bench/soak/burst | ✅ | bench.run, soak with leak detection |
| C089 disaster/partition | ✅ | partition/reconnect, restart, outage, degraded tests |
| C090 release evidence | ✅ | certify.py → sealed RELEASE_EVIDENCE.json, verify() |
| C091 SLO policy | ◐ THRESHOLDS_PROPOSED | OPERATIONS SLO policy, slo-report |
| C092 rollout/disable | ✅ | drills canary/rollback/disable executed by runbook test |
| C093 compat matrix | ◐ PK_CORE_MISSING | conformance/COMPAT_MATRIX.json + COMPAT_RESULTS.json |
| C094 maintenance SLAs | ✅ | OPERATIONS maintenance policy |
| C095 backup/restore | ✅ | non-durable classification, restore = bootstrap |
| C096 runbooks | ✅ | every `sh runbook` block executed in CI |
| C097 incident mgmt | ◐ TABLETOP_PENDING | SEV table, INC-1..4, alerts linked to runbooks |
| C098 recurring reviews | ◐ REVIEW_NOT_COUNTERSIGNED | governance/REVIEWS.json; overdue critical review blocks gate |
| C099 waiver register | ✅ | governance/WAIVERS.json; expired-waiver test |
| C100 exit gate | ⛔ | certify.py implemented and tested; verdict NO_GO due to the blockers above |

## Honest limits of this pass

- The real-tier integration tests only check that the real packages import and expose
  `COMPONENT`. Once the real INV-12/15/16/17/20 APIs are available, the scenarios in
  `tests/test_integration.py` should be ported to them.
- The wire adapter is a transport-agnostic endpoint with a simulated link. It does not
  include a real mTLS server; the host has to provide one (residual risk in the threat model).
- Signing uses HMAC with a key from the environment. No asymmetric signatures or
  Sigstore-style provenance are included.
- Human records (ADR approval, threat-model approval, reviews, tabletop, owner
  assignments) are prepared but deliberately left unsigned. A tool cannot approve its own work.

## Reproduce

```
python inv18_completion_primitive/tools/run_tests.py
python inv18_completion_primitive/tools/compat_matrix.py
python -m inv18_completion_primitive gate          # exit 20 today
python inv18_completion_primitive/tools/verify.py inv18_completion_primitive
```
