# INV-41 4.3.0 — remediation report

**Input:** `inv41_capability_security_v4.2.0_MISSING_COMPONENT_CHECKLIST.md` (24 sections, 85 non-verified audit IDs) applied to `inv41_capability_security_v4.2.0_hardened.zip`.
**Output:** version 4.3.0 of the same package. The 4.2.0 files are kept, extended in place, and `POST_UPDATE_AUDIT.*` stays as the historical 4.2.0 baseline.
**Environment:** cloud container, CPython 3.10.20 / 3.11.15 / 3.12.3 / 3.13.13, Linux x86_64, 2 vCPU, no network, no pk_core.

## Verdict

| | |
|---|---|
| Development gate (`tools/run_ci.py --mutation`) | **PASS**: 8 suites, 107 tests (3 pk_core conformance tests skip and are recorded as BLOCKED, never counted as passes), plus 10 tools |
| Production exit gate (`tools/release_gate.py`) | **NO_GO**: 2 PASS, 8 BLOCKED, 1 FAIL (production governance, because owners are unassigned) |
| 85 non-verified 4.2.0 audit IDs | **59** implemented with local evidence · **25** partial, with a named blocker · **1** fully blocked (C068 edge power) |
| Requirements | 85 normative requirements: 70 IMPLEMENTED, 3 PARTIAL, 12 BLOCKED. None self-reports VERIFIED, because VERIFIED needs an independent reviewer. |
| Security-control mutants | **20/20 killed** (`evidence/mutation.json`) |
| Compatibility | 4/4 available cells PASS (Py 3.10–3.13 Linux x86_64); 20 cells NOT_RUN (Windows/macOS/aarch64) |
| Release build | deterministic: two builds gave identical bytes (archive hash and file list in `dist/RELEASE_MANIFEST.json`); SBOM, manifest, provenance; **development** signature only |

"Implemented with local evidence" means the code, test or document exists and the automated checks pass in this environment. Governance and operations documents are checked for structure and cross-references only. **No human has reviewed or approved them.**

## Section-by-section

| § | Component | What was built | State |
|---|---|---|---|
| 1 | Ownership | OWNERS.json/md, CODEOWNERS (two reviewers on critical paths), escalation tiers, decision authority, `governance_check.py` (fields, humans, two reviewers, staleness) | PARTIAL: only you are named (as proposed owner); every other role is UNASSIGNED (B-OWN-01) |
| 2 | ADR | ADR-0001: decision, properties, trust boundary, rationale, 4 alternatives, invariant→test table, change rule | PARTIAL: status PROPOSED, not approved |
| 3 | Requirements/semantics | 85 SHALL/SHOULD requirements, assumptions table, `preflight.py` (fails closed), 5 profiles with secure defaults, outcome model, broker lifecycle, concurrency contract, capacity, disconnected mode, precedence | implemented |
| 4 | Traceability | `traceability.py`: deterministic, hashed snapshot; fails on unmapped, missing symbol/test, orphan test, VERIFIED without evidence | implemented; 0 errors |
| 5 | Interface contracts | `contracts/INTERFACES.json` (21 boundaries), `errors.py` INV41-ERR/1, hard limits, retry/idempotency rules, golden vectors | implemented |
| 6 | Estate integration | `estate_gate.py` gives an explicit PASS/FAIL/BLOCKED with hash-chained records; production profile exits 2; pin file | gate built; **BLOCKED**, because pk_core was not supplied (B-EST-01) |
| 7 | Pinning/provenance | stdlib-only rule enforced, spec hashes, manifest, SLSA-style provenance, signed/versioned config | signing identity **BLOCKED** (B-SIGN-01) |
| 8 | Config lifecycle | `config.py`: schema, canonical digest, HMAC signature, key revocation, monotonic versions, atomic swap, crash-at-every-phase, rollback that never resurrects, migration /0→/1 | implemented |
| 9 | Threat model | THREAT_MODEL.md + threats.json (19 threats → requirements → tests → mutants), mutation harness | implemented; T-INTROSPECT/T-ESCAPE stay open (WVR-001) |
| 10 | Isolation | `isolation.py`: separate `-I -S -B` process, empty env, rlimits, wall-clock kill, opaque-handle bridge with session revocation | process tier implemented; namespaces/seccomp/Wasm **BLOCKED** (B-ISO-01) |
| 11 | Identity | `identity.py`: adapter protocol, HMAC reference adapter (iss/aud/nbf/exp/type/revocation/replay), principal binder (random-id domains; authentication ≠ authorization) | production mechanisms **BLOCKED** (B-IDN-01) |
| 12 | Data protection | DATA_PROTECTION.md matrix; redaction enforced in every output path | KMS/TLS **BLOCKED** (B-KEY-01) |
| 13 | Audit | `audit.py`: hash chain + seq + monotonic + HMAC, forbidden-field refusal, bounded buffer, mandatory audit denies, segment anchoring, offline verifier | implemented; external anchor BLOCKED |
| 14 | Resilience | failure taxonomy, retry + budget, breaker with hysteresis, admission + priority lane, degraded mode, quarantine, fault injection (never fails open) | implemented |
| 15 | Performance | `bench.py` (fingerprint, 5 rounds, percentiles, memory/object, contention) + regression gate + slo.json | SLOs PROPOSED, need approval; edge power BLOCKED |
| 16 | Health/metrics/logs/traces | `telemetry.py` + `Broker.health` | implemented; backends BLOCKED (B-DEPLOY-01) |
| 17 | Diagnostics/explain/lineage/alerts | reason ledger, `Broker.explain`, lineage fields, telemetry policy, 10 alerts with runbook anchors, dashboard spec | defined; not wired to a backend |
| 18 | Contract tests | test_contracts.py (16), golden vectors for 3 schemas, `-O` equivalence | implemented |
| 19 | Compatibility | SUPPORT_MATRIX.json, `compat.py`, CI workflow matrix | 4 cells PASS, 20 NOT_RUN (B-COMPAT-01) |
| 20 | Fuzz/property | seeded property + model-based state-machine fuzzing, pinned regressions; nightly tier run once (20,000 iterations) | implemented |
| 21 | Races | 7 barrier/preemption-forced race tests; nightly tier run once (400 rounds) | implemented |
| 22 | Scale/soak/disaster | `scale_soak.py`: scale limits, soak (nightly: 120 s, 514,939 ops, 0.1 B/1k-op), burst with priority revocation, 7-dependency partition/reconnect, restart | release tier and fleet **BLOCKED** (B-SOAK-01, B-FLEET-01) |
| 23 | Operations governance | OPERATIONS.md (support/error budget, rollout, lifecycle, vuln SLA, reconstruction, day-0/1/2 runbooks, incidents, reviews), waiver ledger with expiry enforcement | written; team acceptance BLOCKED |
| 24 | Supply chain | deterministic double-build, CycloneDX SBOM, manifest + verify, provenance, NOTICE, pinned-SHA CI workflow | licence and signing BLOCKED (B-LIC-01, B-SIGN-01) |

## Defects this pass found and fixed

In the 4.2.0 candidate:
1. NUL, newline and other control characters were accepted in identifiers, and there was no length bound. Found by the fuzzer; pinned as REG-001 and REG-002.
2. `Authority` and `Holder` refused pickling only by accident, because an internal `mappingproxy` cannot be pickled. That is now explicit on all four capability types.
3. Operation elements were hashed before they were type-checked, so a hostile `__hash__` ran inside `frozenset()`.
4. There was no bound on the size of an operation set, a policy or a holder, or on membrane depth.

In this pass's own work (caught by its own tests, gates or review, then fixed):
5. The preflight HMAC known-answer check had a wrong expected value. Preflight caught it on the first run. It now uses RFC 4231 case 2.
6. The audit token-pattern check rejected its own genesis digest. It now has an allowlist for public digest keys.
7. The circuit breaker treated `Unavailable` as a terminal denial and never opened on dependency outages. This was caught in code review before its test (RS003) ran.
8. Three first-run mutants survived. M14 exposed a vacuous config test: a forged MAC under a trusted key id was never tried, and it is now. M12 and M09 showed the controls are layered, so a test was added that isolates the prev-link check (AU006) and M09 was rewritten to strip all the guards.
9. The soak harness reported a 16–21 KB/1k-op "leak" that came from its own boxed-int latency lists and retained probes. The fix was an `array('q')` buffer and taking probes before the baseline snapshot. The library itself showed no growth under tracemalloc.
10. The benchmark regression gate failed from scheduler noise alone, because a single-round baseline moved from 7.6 to 12.6 µs. It now uses 5 rounds and gates on the best-round p50, and GV010 proves the gate still trips on a real 2× regression.
11. The traceability checker found 5 orphan tests and 5 unmapped audit IDs (C013, C021, C022, C051, C082). Requirements were added for them.

## What is needed to move to GO

See `BLOCKERS.json`. In order of leverage:
* **B-OWN-01:** name the owners and approvers, and approve ADR-0001 and the SLOs.
* **B-LIC-01:** choose a licence.
* **B-SIGN-01 / B-KEY-01:** provide a signing identity and KMS.
* **B-EST-01:** supply the pinned pk_core baseline.
* **B-ISO-01:** provide a hostile-code isolation runtime.
* **B-COMPAT-01 / B-SOAK-01 / B-FLEET-01 / B-DEPLOY-01:** CI runners, a release soak run, a fleet, and a deployment with a canary.
