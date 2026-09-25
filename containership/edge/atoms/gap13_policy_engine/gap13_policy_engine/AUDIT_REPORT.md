# GAP-13 Policy Engine — Audit & Build Report

**Release:** 5.0.0 (from 4.2.0 hardened) · **Date:** 2026-09-22
**Work order:** apply *GAP13 Policy Engine Missing Components Professional Checklist v1.0.0* (sha256:5d26c7b0…8ad50) to the candidate `gap13_policy_engine_v4.2.0_hardened`.

## Executive result
All 51 work packages now have implementation, tests, and documentation in this package, plus contracts for EXT-01…05. The big change is that trust is now derived, not asserted. The 4.2.0 engine accepted a caller's `{"verified": True}`. 5.0.0 activates only a bundle whose Ed25519 signature a `BundleVerifier` has checked against a GAP-07 trust store, and only if the bundle clears the durable anti-rollback floor. The release also adds a control plane: stale-policy modes, rollback, freeze/deny-only/disable/quarantine, audited administration, and telemetry. On top of that sit certification tooling: benchmarks, an evidence manifest, and release gates.

**No component is marked DONE.** The checklist makes independent review and explicit acceptance a condition of DONE, and this build cannot grant that to itself. 47 components are `VERIFYING`. 4 are `BLOCKED` on inputs this package cannot supply.

| Blocked | Why |
|---|---|
| G13-MC-033 edge power/thermal | needs far-edge hardware + power meter (protocol ready: `docs/EDGE_POWER_BENCH.md`) |
| G13-MC-038 adjacent integration | real GAP-07/GAP-04/PLN-01/06/07 builds absent; contract tests pass against reference adapters |
| G13-MC-041 named owners | roles/escalation defined; names must come from the organisation, not be invented |
| G13-MC-042 ADR approval | ADR-001 written, status *Proposed*, approver unassigned |

## Verification performed
* `python -m unittest discover` — **146 tests: 143 pass, 0 fail, 0 error, 3 skip**. The 3 skips are the pk_core conformance tests: pk_core is not in the archive (waiver W-003, pending approval). The same result holds under `python -O`.
* `component.py` (the pk_core adapter) was smoke-tested against a pk_core interface stub. Its behavioural findings still fire through the real signed-bundle path.
* Requirement coverage: all **56 SHALL requirements** in `docs/REQUIREMENTS.md` have passing evidence (`docs/TRACEABILITY.json`).
* Full benchmark (reference sandbox, CPython 3.11):

| Rules | Load (verify+parse+activate) | Engine p99 | Service p99 | Linear-scan p50 (4.2.0 algorithm) | Throughput |
|---|---|---|---|---|---|
| 100 | 19 ms | 0.044 ms | 0.32 ms | 0.074 ms | ~34 k/s |
| 1 000 | 177 ms | 0.047 ms | 0.26 ms | 0.67 ms | ~34 k/s |
| 10 000 | 2.1 s | 0.052 ms | 0.27 ms | 6.8 ms | ~27 k/s |

  Overload probe (32 threads, max_concurrency 4): 739 of 800 shed with retryable `G13-E310`, 0 hung threads.
* Evidence: `evidence/5.0.0/manifest.json`. It is content-addressed and covers every artifact digest, per-test result, benchmark, requirement coverage, component status, waivers and source digests. Check it with `python -m gap13_policy_engine.certify --verify evidence/5.0.0/manifest.json`.

## Gate results
* **rc (engineering regression) gate: NO_GO — single blocker:** the pk_core conformance tests are skipped, and the waiver covering them (W-003) is `PENDING_APPROVAL`. Every other rc check passes: tests, requirements, performance ceilings and baseline, overload, golden fixtures, version consistency, evidence integrity and secret scan. The gate becomes GO when W-003 is approved or the conformance suite is run with pk_core present.
* **production-exit gate: NO_GO** — 51 components not yet accepted, owners unassigned, ADR not accepted. This is the correct state for an unreviewed build.

## Defects in the 4.2.0 baseline fixed by this release
1. Trust was caller-asserted (`{"verified": True}`), so any code path could activate an unsigned permissive bundle. It is now cryptographically derived (MC-001).
2. Match semantics were not type-strict, so `True` matched a rule written for `1` (attribute type confusion). Matching is now type-strict.
3. Staleness was reported but not enforced; a stale bundle still allowed. Hard expiry is now enforced (MC-007).
4. There was no anti-rollback floor, so an old valid bundle could be replayed (MC-008).
5. Every evaluation did an O(n) scan of all rules. The compiled index makes evaluation near-constant (MC-029).
6. Tenant, identity and classification could be supplied by the caller. They now come only from the trusted provider (MC-005/006).

## Residual limitations
The HMAC admin-token format is a reference implementation; bind it to the production IdP (EXT-03). The stdlib random fuzzer is not coverage-guided. Only Linux has been exercised; Windows and macOS are declared supported but unverified (W-004). Loading 10 000 rules takes about 2.1 s. That meets the 3 s SLO ceiling, but the tenant/estate scope check is quadratic in tenant allows × estate denies.
