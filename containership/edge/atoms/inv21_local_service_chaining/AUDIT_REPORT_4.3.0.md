# INV-21 Local Service Chaining — Remediation Report 4.3.0

**Input:** `inv21_local_service_chaining-4.2.0-hardened.zip` + `INV21_MISSING_COMPONENTS_COMPREHENSIVE_CHECKLIST_4.2.0.md` (42 gaps)
**Date:** 2026-09-23 · **Result:** **NO_GO** (`evidence/gate_result.json`). This is the correct verdict; see §4.

## 1. What was done

* The 4.2 runtime was split into stdlib-only modules (`chain`, `context`, `policy`, `residency`, `admission`, `transport`, `errors`, `audit`, `telemetry`, `config`, `lifecycle`, `rollout`, `schema`). pk_core is now needed only by the conformance adapter (`component.py`, `contract.py`). Its absence **fails** the suite; it no longer skips.
* 9 versioned JSON schemas, golden fixtures and a breaking-change detector were added.
* Added 16 test modules (plus the unchanged 4.2 `test_runtime.py`), 128 tests in total. They cover identity, schema/errors, policy/residency, admission/lifecycle/config, audit/telemetry, async/HTTP transport, semantic equivalence (loopback and real sockets), adversarial T1–T12, fuzz/property (5 000 iterations at the gate), races, fault injection, adjacent-contract stand-ins, packaging, rollout, governance and second-pass regressions.
* Packaging uses PEP 517 with `setuptools==79.0.1` pinned by hash. The wheel is byte-reproducible (`SOURCE_DATE_EPOCH`), and a clean isolated install passes its smoke test. Generated alongside: SBOM (CycloneDX 1.5), unsigned in-toto provenance, benchmark harness plus baseline, the traceability matrix (C001–C100 and GAP-001..042), the release gate, and the CI workflow.
* Added docs (design, threat model, operations, incident response, capacity, compatibility, semantic equivalence, privacy, patching/EOL, reviews), five ADRs, Prometheus alert rules and a Grafana dashboard. Governance registers were added for owners, waivers, reviews and approvals.

## 2. Verification performed (clean extraction, by the release gate)

| Check | Result |
|---|---|
| compile (all modules, incl. tools) | PASS |
| full suite, zero-skip rule | **FAIL**: 128 ran; the only failure is `test_pk_core_importable`, plus 3 dependent skips |
| same suite under `python -O` | PASS |
| fuzz 5 000 iterations | PASS |
| CPython 3.10 / 3.11 / 3.12 / 3.13, Linux x86_64 | PASS (aarch64, macOS and Windows untested) |
| schema compatibility vs v1 snapshot | PASS |
| reproducible wheel + sdist | PASS (digests in `evidence/gate_result.json` → `artifacts`, built copies in `evidence/dist/`) |
| clean install + smoke from the built artifact | PASS |
| SBOM / provenance | generated; **unsigned** |
| signature | **FAIL**: no signing identity or verifier |
| vulnerability scan | **FAIL / NOT_RUN**: no scanner or index reachable (0 third-party runtime dependencies) |
| benchmark regression vs baseline | PASS |
| contract SLO: p99 local dispatch < 20 µs | **FAIL**: measured ≈124 µs (production path, cached, fully audited) and ≈58 µs (4.x path) |
| pk_core pinned | **FAIL**: source, version and hash are UNRESOLVED |
| licence | **FAIL**: owner decision pending |
| waivers approved | **FAIL**: 5 unapproved |
| independent review record | **FAIL**: none |
| traceability | **FAIL**: 3 gaps blocked, 15 partial, 24 implemented but unverified, 0 verified (`evidence/traceability.json`) |

## 3. Independent second-pass audit

A separate agent audited a clean extraction of the first 4.3.0 build adversarially. It found 10 reproducible defects and 7 overclaimed statuses. Fixes were made and regression tests added in `tests/test_second_pass_findings.py`, which reproduces the auditor's probes. The same auditor then re-ran its probes against the fixed build (§3.1).

| ID | Sev | Defect found | Fix |
|---|---|---|---|
| SP-01 | CRITICAL | In production, a hand-built `Principal` (no credential) ran a handler for another tenant | the chainer re-derives the principal from the carried credential with its own `IdentityVerifier` and refuses any mismatch |
| SP-02 | HIGH | Caller-supplied `ctx.path` set the policy `caller` | `caller` comes only from chainer-sealed child contexts (HMAC seal bound to an active root call) |
| SP-03 | HIGH | Any `path` made a call "nested", which bypassed admission | same seal; unsealed calls are always admitted as root calls |
| SP-04 | HIGH | `apply_config` could switch to production without the wiring checks and left the legacy checker active | shared `_wiring_problems()`; admission and breaker are built on apply |
| SP-05 | MEDIUM | Granted decisions were never audited | every routing decision is audited |
| SP-06 | MEDIUM | A revoked grant was still served from the policy cache | a cache hit checks the provider's live `revision` |
| SP-07 | MEDIUM | Restored or reconciled placements had infinite leases | the lease is re-applied on restore and on reconcile |
| SP-08 | LOW | A wrapped audit ring was unverifiable, and `verify([])` passed | `window()` anchor; empty input and a missing genesis record fail |
| SP-09 | LOW | The schema validator ignored keywords next to `anyOf`, schema-valued `additionalProperties`, unvisited unknown keywords, and `True == 1` | all four fixed. The follow-up found `validate()` did not itself reject unknown keywords in ad-hoc schemas; now fixed |
| SP-10 | LOW | Bearer-token replay at the peer | **Not fixed, only bounded.** `max_token_age_s` (default 300 s) caps the window. Request de-duplication was tried and removed: the request body is unsigned, so anyone holding the token can mint fresh requests, and de-duplication only broke legitimate repeated calls. Real protection needs mTLS, channel binding or request signing (ADR-005). |

### 3.1 Follow-up re-audit of the fixed build

The auditor confirmed SP-01 to SP-08 fixed and SP-09 partly fixed (completed afterwards). SP-10 still reproduces, as described above. It also found:

* **MEDIUM (residual, not fixable in-process):** handler code running in the same interpreter can mint a hop seal by calling the chainer's private `_seal_child`, and so spoof the policy `caller`. In-process handlers are inside the trust boundary; isolating them needs the INV-20 component sandbox. GAP-040 and GAP-027 are downgraded to `partial` for this reason.
* **LOW (residual):** a handler can leak a sealed child context to another thread and skip admission, but only while its own root call is active, and only for the same principal and tenant.
* **HIGH (fixed):** the gate's signature check would run any command, e.g. `true`. It now accepts only allow-listed signature tools, and the key or trust material is still external.
* **MEDIUM (fixed):** the independent-review check could never pass, because the approvals file was part of the digest it had to match. It is now excluded from the source-tree digest.

The auditor also showed that the gate's governance checks could be flipped by editing a file. They were tightened:

* An approval must name a non-implementer reviewer bound to the current `source_tree_sha256`.
* A waiver needs an approver, a date and an unexpired expiry.
* A `.sig` file counts only if a configured verifier accepts it.
* The pk_core pin must be a semver plus sha256, and the conformance tests must actually run.
* The licence must be real, not the placeholder.
* A failing test module now lowers the traceability status of every gap that cites it.

These checks are procedural, not cryptographic: someone with write access can still forge governance files. Real enforcement needs signing infrastructure (GAP-017).

The first pass's own tests also found and fixed six defects before the audit:

* The production API silently stripped whitespace from callee names.
* A JSON recursion bomb was misreported as a transport failure.
* `iat` rounding made fresh credentials intermittently "not yet valid".
* Ledger retention only evicted from the head.
* The pseudonymisation key was a published constant.
* A socket-scenario p99 made the benchmark gate flap.

## 4. Why the verdict is NO_GO, and what closes it

Each open item needs something this repository cannot supply on its own:

1. **GAP-001 (CRITICAL):** a pinned pk_core source, version and sha256. The conformance suite must then run with zero skips.
2. **GAP-028 (CRITICAL):** real interoperability tests with INV-20, INV-10, INV-16, INV-13 and SCH-01 in the assembled estate. Only contract stand-ins exist here.
3. **GAP-004 / GAP-005 (CRITICAL, partial):** the real INV-13 provider wired in, KMS key distribution, and a decision on workload attestation.
4. **GAP-017 / GAP-037 (CRITICAL, partial):** a signing identity plus verifier, and a vulnerability scan in CI.
5. **GAP-022:** the owner must decide on the 20 µs SLO (WAIVER-003). Soak/fleet-scale and power/thermal runs are still needed.
6. **GAP-039:** licence choice. **GAP-014/034/035/036:** confirm owner and contacts, approve the policies, run the first review.
7. **GAP-029 / GAP-038:** run the CI matrix on aarch64, macOS and Windows.
8. A new independent re-audit of this exact build by a reviewer outside this session, recorded in `governance/approvals.json` against the current `source_tree_sha256`. The follow-up check in §3.1 was done by an agent of the same session, so it does not count as an independent review record.

Nothing is marked `verified`. The remaining `implemented_unverified` gaps are ceilings asserted by the implementer. They close only after an independent second-pass audit, as the checklist requires.
