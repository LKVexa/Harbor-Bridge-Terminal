# INV-71 Heavy Agent Sandbox - audit, fixes, hardening, and version bump

## Executive summary

The uploaded repository was version **4.1.0** and contained a compact Python reference model plus a 100-control checklist integration. It compiled, but its three conformance tests all skipped because `pk_core` was not included or otherwise importable. The repository also overstated its inventory (`README.md` claimed `MASTER.md` was bundled when it was absent) and could be read as stronger production proof than the code actually provided.

The hardened repository is **4.2.0**. The reference model was separated into dependency-free `sandbox.py`, tested without `pk_core`, and hardened around clean-snapshot integrity, path handling, egress canonicalization, resource bounds, lifecycle closure, teardown, and audit integrity. Production-readiness claims were narrowed: the README now explicitly distinguishes executable reference semantics from a real microVM sandbox.

## First-pass defects found and corrected

| Finding | Risk | v4.2.0 correction |
|---|---|---|
| Filesystem digest serialization used `path + NUL + data` with no record/data length boundary. Two different maps could produce the same pre-hash byte stream. | Integrity checks could report the same digest for structurally different filesystem maps without a SHA-256 collision. | `digest()` now length-prefixes both paths and payloads before hashing; regression test added. |
| Guest writes accepted relative paths and traversal aliases such as `../escape`. | The reference semantics did not actually model a confined guest namespace. | Only canonical absolute non-root POSIX paths are accepted; dot, dot-dot, duplicate separator, backslash, NUL, and overlong paths fail closed. |
| Global `BASE` was a mutable dictionary. | External mutation could alter future session starting state or cause digest mismatch/denial of service. | Base snapshot is exposed as an immutable mapping; every session starts from an exact copy and validates the base digest. |
| Empty/invalid session identifiers were accepted. | Weak identity semantics and ambiguous audit records. | Session IDs are validated for non-empty bounded canonical syntax. |
| Egress matching used raw strings only. | Case/trailing-dot mismatches and URL/host:port ambiguity weakened the allowlist model. | DNS names/IP literals are canonicalized; URLs, host:port, whitespace, and malformed DNS fail closed. |
| Teardown reported `verified` after clearing filesystem/connections but retained denied-host history and the egress allowlist. | “Verified empty” overstated the amount of guest/capability state actually cleared. | Teardown clears filesystem, connections, denials, and egress capability data, moves the session to `CLOSED`, and returns audit-chain verification. |
| No explicit post-teardown lifecycle type. | Closed-session operations were conflated with quota/egress errors. | Added `SessionState` and `SessionClosed`; write/delete/connect after teardown are refused consistently. |
| Connection/denial histories could grow without bound. | Long-lived reference sessions could accumulate unbounded metadata. | Histories are bounded; audit history is also bounded while retaining a chain anchor. |
| No tamper-evident security-decision record. | Reference security outcomes were not integrity-linked. | Added a SHA-256 hash-chained audit event model and tamper-detection tests. This remains local/unsigned and is not a substitute for durable production audit infrastructure. |
| Package import eagerly required `pk_core`. | The security-sensitive reference model could not be tested when the external integration package was absent. | `pk_core` integration is now lazy; dependency-free model/tests run standalone while legacy conformance tests still require `pk_core`. |
| README claimed `MASTER.md` existed although it was absent. | Artifact inventory was inaccurate. | Claim removed and discrepancy documented; no replacement content was fabricated. |

## Hardening added

Version 4.2.0 adds a dependency-free `sandbox.py`; immutable clean-base data; unambiguous filesystem hashing; canonical path and host validation; disk/file/log/audit bounds; atomic copy-then-commit write checks; method-level locking; explicit lifecycle closure; deletion semantics; hash-chained audit events; JSON Schemas for session/egress/teardown records; a proposed ADR; a repository threat model; a reproducible stdlib audit tool; dependency-free adversarial tests; a 100-control machine-readable audit matrix; and a complete production-gap inventory.

## Validation performed after changes

- Python compilation: **PASS** for all repository Python files.
- Dependency-free unit/adversarial suite: **PASS** (12 executable tests).
- Legacy `pk_core` conformance suite: **NOT EXECUTED / SKIPPED** (3 tests) because the external `pk_core` package is not supplied in or beside this repository.
- JSON parseability: `CHECKLIST.json` and all added JSON Schemas parse successfully.
- Version coherence: `VERSION` and `__version__` are both **4.2.0**.

The repository audit tool records the exact repeatable result in `REPO_AUDIT_RESULTS.json`.

## Second audit: production completeness

The second audit does **not** accept the older statement that “all 100 requirements are satisfied” as repository evidence. Checklist inheritance/default findings from an external framework are not equivalent to a production implementation. `AUDIT_AFTER.json` evaluates each of the 100 controls against artifacts actually present here.

The remaining gaps are enumerated one-for-one in `MISSING_COMPONENTS.md`. The highest-impact missing systems are a real Firecracker/jailer runtime and hardened host boundary; pinned/signed kernel/rootfs/snapshot supply chain; production control-plane authn/authz/attestation; network namespace/firewall/DNS-destination enforcement; CPU/memory/pids/I/O/network cgroup-style controls and admission; durable external audit/metrics/logs/traces; integration/compatibility/fuzz/escape/fault/performance/soak testing; CI/release provenance and regression gates; canary/rollback/incident/patch/EOL operations; and accountable ownership/approval/exception governance.

## Scope and residual risk

The upgraded Python code is intentionally a **reference model**, not a secure sandbox for hostile code. Python process memory, dictionaries, locks, and hash chains cannot create the isolation properties of a microVM or prove host memory/block-device erasure. Production certification remains blocked until the missing components are implemented and independently exercised at the real isolation boundary.

---

## v4.3.0 production remediation pass (2026-09-23)

**Input:** v4.2.0 (20 files, zip sha256 `f23a04ad…0c08`) and `INV71_v4.2.0_PRODUCTION_REMEDIATION_MASTER_CHECKLIST.md` (sha256 `73c27b3d…c2cc`, 1,730 checklist lines). The checklist is kept under `governance/`.

**Method:** everything that can be built and tested without real infrastructure was built as a stdlib-only reference control layer, with tests, governance data and a reproducible evidence bundle. Every checklist line was then given a status in `governance/checklist_status.py`. `tools/build_evidence.py` checks those claims: every cited path must exist, every cited test must exist and pass, and a line marked implemented is downgraded to PARTIAL if its tagged tests fail. An adversarial subagent reviewed the result, and its findings were fixed or reflected in downgraded statuses before release.

**Results:** see `MISSING_COMPONENTS.md` (generated), `evidence/traceability.json` and `evidence/gate-result.json`. No control became EVIDENCED. No line is DONE. The production gate is NO_GO.

**Defects found and fixed** (each has a regression test):
1. IPv6 zone IDs were accepted by `canonicalize_host` (found by the fuzz harness).
2. A session was acknowledged before its audit record was durable.
3. The audit spool bound was off by one record.
4. The lease table grew without bound because epochs were numbered per sid.
5. Expired idempotency and replay entries were kept until capacity was reached.
6. A full replay cache evicted live nonces, which allowed replay (found by the adversarial review).
7. Config approvals were recorded but never enforced, and participants were never told to commit or abort (found by the adversarial review).
8. An egress capability could outlive its DNS answer by up to 29 s (found by the adversarial review).
9. Waivers could pass with the same approver listed twice (found by the adversarial review).
10. The first evidence build was sealed before `REPO_AUDIT_RESULTS.json` was rewritten, so a fresh copy failed the integrity check (found by the adversarial review). The build order is now fixed.

**Reclassified after review:** the per-dimension DES lines had first been scored as if they were identical across controls. They are not; each dimension has its own four DES lines, and all of them were rescored. GATE-04 is now PARTIAL: the gate checks that evidence is present and not failing, but has no per-control staleness or revocation check. C015-IMP-04, C024-IMP-03 and C036-IMP-02 are now PARTIAL.
