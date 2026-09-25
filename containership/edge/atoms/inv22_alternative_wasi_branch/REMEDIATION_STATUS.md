# INV-22 v4.3.0 — Remediation status

Generated from `data/remediation.json` against `docs/REMEDIATION_CHECKLIST.md` (64 work packages, controls C001–C100).

**Production exit gate: NO_GO.** 3 skipped tests (full conformance requires zero skips); preflight pk_core not ok; preflight adjacent not ok; preflight baselines not ok; 47 of 64 work packages not complete; 100 of 100 controls lack complete evidence.

Tests: 115 run, 0 failed, 3 skipped (the 3 skips are the pk_core conformance tests).

| Status | Work packages |
|---|---|
| ✅ implemented | 17 |
| 🟡 partial | 36 |
| ⛔ blocked (external) | 7 |
| 👤 owner decision | 4 |

Control-level view (worst status across each control's packages): blocked_external 46, legacy_v4.2.0 1, owner_decision 30, partial 23. Full row-by-row linkage: `evidence/traceability.json`.

| MC | Priority | Work package | Status | Implementation | Remaining gap |
|---|---|---|---|---|---|
| MC-01 | P0 | `pk_core` runtime/framework dependency | ⛔ blocked (external) | `preflight.py`, `__init__.py` | pk_core is not in the archive; preflight reports it, imports no longer break without it, release mode forbids PK_CORE_PATH |
| MC-02 | P0 | Adjacent architecture dependencies | ⛔ blocked (external) | `dependencies/adjacent.json`, `preflight.py` | INV-13/11/12/10 and GAP-14 not supplied; manifest + fail-closed policy + status check in place, pins empty |
| MC-03 | P0 | Package/build metadata | ✅ implemented | `pyproject.toml`, `VERSION`, `__init__.py` | wheel+sdist build twice, identical manifests, clean-install smoke test |
| MC-04 | P0 | Dependency lock/provenance | 🟡 partial | `requirements.lock` | runtime lock with hashes for the crypto dependency; test/lint toolchain lock and registry policy still owner-side |
| MC-05 | P0 | Actual WASIX/WASI implementation pin | ⛔ blocked (external) | `baselines/manifest.json`, `matrix.py::check_baselines` | owner must supply approved WASI and WASIX repos, commit SHAs, digests and feature profile |
| MC-06 | P0 | Machine-readable branch matrix schema (`PK_BRANCH_MATRIX/1`) | ✅ implemented | `schemas/pk_branch_matrix.v1.schema.json`, `matrix.py`, `canonical.py` | — |
| MC-07 | P0 | Machine-readable shim contract (`PK_BRANCH_SHIM/1`) | ✅ implemented | `schemas/pk_branch_shim.v1.schema.json`, `shim.py` | — |
| MC-08 | P0 | Machine-readable certification contract (`PK_BRANCH_CERT/1`) | ✅ implemented | `schemas/pk_branch_cert.v1.schema.json`, `cert.py` | — |
| MC-09 | P0 | Persistent certification store | 🟡 partial | `store.py` | SQLite reference backend done (restart, races, corruption, backup); at-rest encryption and multi-node backend not done |
| MC-10 | P0 | Cryptographic certification integrity | 🟡 partial | `cert.py` | Ed25519 profile, trust store, rotation, compromise, skew, stale revocation done; KMS/HSM signer adapter and second-library interop not done |
| MC-11 | P0 | Complete interface inventory discovery | 🟡 partial | `wit.py`, `matrix.py::completeness` | inventory + completeness gate over a WIT subset; runtime capability cross-check and real baselines outstanding |
| MC-12 | P1 | Automatic matrix generation/diffing | 🟡 partial | `wit.py`, `reference.py`, `data/overrides.json` | structural diff, needs_review, reviewed overrides, --check drift gate; full WIT grammar (resources/async/streams semantics) not covered |
| MC-13 | P0 | Semantic compatibility proof mechanism | 🟡 partial | `proofs/fs-open-flags.json` | proof record + exhaustive/mutation evidence; status pending_review (needs 2 reviewers) and not bound to pinned baselines |
| MC-14 | P0 | Real bidirectional translators | 🟡 partial | `shim.py` | real bidirectional reference translator for filesystem open-flags/rights; remaining shimmable surfaces need pinned WIT |
| MC-15 | P0 | Shim round-trip validation | ✅ implemented | `shim.py` | finite domain proven exhaustively both directions; 5 mutants killed; applies to every registered translator today |
| MC-16 | P0 | Structured production error model | ✅ implemented | `errors.py`, `schemas/pk_branch_error.v1.schema.json` | — |
| MC-17 | P1 | Timeout/cancellation/backpressure semantics | 🟡 partial | `shim.py` | deadline/cancel/overload on translation; store busy timeout; no generic retry/backoff helper or streaming backpressure |
| MC-18 | P0 | Authentication boundary implementation | 🟡 partial | `auth.py`, `ops.py` | signed identity tokens with iss/aud/exp/nbf/replay checks; transport (mTLS) and IdP integration are deployment-side |
| MC-19 | P0 | Authorization/capability enforcement | 🟡 partial | `auth.py`, `ops.py` | default-deny scoped grants, SoD, break-glass at the ops boundary; ShimService itself is not yet wrapped by authz |
| MC-20 | P1 | Configuration subsystem | ✅ implemented | `config.py` | — |
| MC-21 | P0 | Configuration validation and atomic activation | ✅ implemented | `store.py::activate_config`, `config.py` | — |
| MC-22 | P0 | Secrets handling integration | 🟡 partial | `config.py`, `telemetry.py`, `errors.py` | secret references + redaction + repo secret scan; provider integration and rotation drill not done |
| MC-23 | P0 | Runtime/site branch-selection control | 🟡 partial | `store.py`, `governance.py`, `ops.py` | durable site branch with fencing, impact plan, admission, freeze; INV-10 link-time enforcement is external |
| MC-24 | P1 | Lifecycle/state machine | ✅ implemented | `lifecycle.py`, `store.py` | — |
| MC-25 | P0 | Compatibility/version negotiation | ✅ implemented | `canonical.py` | — |
| MC-26 | P1 | Resource and quota enforcement | 🟡 partial | `canonical.py`, `shim.py`, `config.py` | payload/depth/items/concurrency/matrix limits; CPU/storage/connection quotas not applicable until a server exists |
| MC-27 | P1 | Offline/intermittent-connectivity behavior | 🟡 partial | `cert.py`, `config.py` | revocation freshness bound and fail-closed offline; reconnect reconciliation not implemented |
| MC-28 | P1 | Conflict/precedence policy engine | ✅ implemented | `governance.py` | — |
| MC-29 | P0 | Requirements traceability artifact | ✅ implemented | `evidence.py`, `data/remediation.json` | generated per run from CHECKLIST.json + this ledger |
| MC-30 | P0 | Integration test suite | ⛔ blocked (external) | — | needs pk_core, adjacent elements and approved runtimes |
| MC-31 | P0 | Reference/conformance fixtures | ✅ implemented | `fixtures/`, `fixtures_gen.py` | — |
| MC-32 | P0 | Differential runtime test harness | ⛔ blocked (external) | — | needs approved standards-WASI and WASIX runtimes |
| MC-33 | P1 | Cross-platform/architecture testing | 🟡 partial | `.github/workflows/inv22-ci.yml` | CI matrix declared (3 OS x 3 Python); not executed here |
| MC-34 | P1 | Fuzzing/property-based testing | 🟡 partial | — | seeded mutation fuzzing of matrix JSON, WIT and translator inputs; continuous coverage-guided fuzzing not set up |
| MC-35 | P0 | Security test suite | 🟡 partial | `docs/THREAT_MODEL.md` | tamper/replay/escalation/SoD/resource tests; side-channel and supply-chain tests outstanding |
| MC-36 | P1 | Performance/benchmark suite | 🟡 partial | — | latency budget smoke benchmarks; no stored baseline comparison |
| MC-37 | P1 | Capacity/load/stress tests | 🟡 partial | — | overload rejection and recovery only |
| MC-38 | P1 | Failure-injection/chaos tests | 🟡 partial | — | activation fault injection, restart, corruption, race tests; process/network chaos outstanding |
| MC-39 | P0 | Telemetry backend/exporter | 🟡 partial | `telemetry.py` | bounded metrics + redacting JSONL exporter; no tracing/OTel exporter |
| MC-40 | P0 | Health/readiness endpoint | 🟡 partial | `telemetry.py::health` | readiness model; no network endpoint |
| MC-41 | P0 | Audit/event log | ✅ implemented | `store.py` | — |
| MC-42 | P1 | Alerting/SLO automation | 🟡 partial | `telemetry.py` | zero-budget SLO evaluation with actions; no alert routing/dashboards |
| MC-43 | P1 | Drift history persistence | ✅ implemented | `store.py::record_drift` | — |
| MC-44 | P1 | Drift threshold/policy action | ✅ implemented | `governance.py::drift_findings` | — |
| MC-45 | P1 | Operator CLI/API | 🟡 partial | `cli.py`, `ops.py` | read-only CLI + authenticated ops API; mutations not yet on the CLI |
| MC-46 | P1 | Deployment artifacts | 👤 owner decision | — | target execution environment (container/VM/edge) not specified |
| MC-47 | P0 | Bootstrap automation | 🟡 partial | `docs/RUNBOOKS.md` | documented bootstrap; not automated |
| MC-48 | P0 | Rollback implementation | 🟡 partial | `store.py::rollback_config` | config rollback tested; code/store rollback documented only |
| MC-49 | P1 | Migration tooling | 🟡 partial | `store.py::migrate` | versioned resumable migration framework at v1; newer-store refusal tested |
| MC-50 | P0 | Release automation/CI | 🟡 partial | `.github/workflows/inv22-ci.yml` | pipeline written, never run |
| MC-51 | P1 | Static analysis/type checking configuration | 🟡 partial | `pyproject.toml` | ruff/mypy config pinned; pyflakes-clean gate run in tests |
| MC-52 | P1 | Coverage measurement/gate | 🟡 partial | `pyproject.toml` | coverage threshold configured in CI; measured locally in the evidence bundle when coverage is installed |
| MC-53 | P1 | Software bill of materials (SBOM) | 🟡 partial | `evidence.py` | file/dependency inventory bound to digests; not CycloneDX-validated |
| MC-54 | P0 | Vulnerability scanning | ⛔ blocked (external) | — | vulnerability database access required (pip-audit/OSV) in CI |
| MC-55 | P0 | Artifact signing/attestation | 👤 owner decision | — | release signing identity/key must be provisioned by owner |
| MC-56 | P1 | License/NOTICE files | 👤 owner decision | — | licence for this repository not stated anywhere; owner must choose |
| MC-57 | P0 | Security policy | 🟡 partial | `SECURITY.md` | policy written; intake contact is a placeholder for owner |
| MC-58 | P1 | Contribution/ownership metadata | 👤 owner decision | `CODEOWNERS` | template only; owners must be named |
| MC-59 | P0 | Operational runbooks | 🟡 partial | `docs/RUNBOOKS.md` | runbooks written; not drilled |
| MC-60 | P0 | Disaster-recovery/backup plan | 🟡 partial | `store.py::backup`, `docs/RUNBOOKS.md` | verified backup/restore; RPO/RTO not approved |
| MC-61 | P1 | Data retention/privacy/residency controls | 🟡 partial | `config.py`, `docs/DATA_POLICY.md` | inventory and retention settings; deletion job not implemented |
| MC-62 | P1 | Deprecation lifecycle | 🟡 partial | `matrix.py`, `lifecycle.py` | end-of-support enforced on matrix entries; translator/baseline deprecation registry not built |
| MC-63 | P0 | Formal governance/waiver mechanism | ✅ implemented | `governance.py` | — |
| MC-64 | P0 | Full local conformance evidence | ⛔ blocked (external) | `evidence.py` | bundle generated but cannot be complete while MC-01 blocks the 100-control run |

## What the owner needs to supply to move the gate

1. **pk_core** at a pinned version with `API_LEVEL = 1` (MC-01) — unblocks the 3 skipped conformance tests and MC-64.
2. **Adjacent elements** INV-13, INV-11, INV-12, INV-10, GAP-14: commit SHAs + contract schema digests into `dependencies/adjacent.json` (MC-02).
3. **WASI / WASIX baselines**: repositories, commit SHAs, content digests and enabled feature profile into `baselines/manifest.json` (MC-05); then regenerate the matrix and re-review `data/overrides.json`.
4. **Decisions**: repository licence (MC-56), named CODEOWNERS (MC-58), release-signing identity (MC-55), deployment target (MC-46), security intake contact (MC-57).
5. **Two reviewers** for `proofs/fs-open-flags.json` (MC-13).
6. **CI with index access** to generate hashed locks, run pip-audit, coverage and the 3×3 platform matrix (MC-04, MC-33, MC-50, MC-52, MC-54).
