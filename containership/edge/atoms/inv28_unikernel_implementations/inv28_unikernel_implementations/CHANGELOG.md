# Changelog - INV-28

## 4.3.0 - 2026-09-23

This release applies `docs/applied/INV28_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (MC-001 to MC-100) through the junkyard chop shop. Every item has an owner, a status and resolvable references in `ops/MC_STATUS.json`, rendered to `ops/MC_STATUS.md`.

The status counts are 77 `implemented_unreviewed`, 15 `partial`, 5 `decision_pending`, 3 `blocked_external` and **0 complete**. Nothing can be marked complete until an independent reviewer accepts it.

### Safety-relevant behaviour change (MC-094, ADR-0001 PROPOSED)
- **Production now admits only `mature` toolchains.** In v4.2.0 a `beta` toolchain could be selected in production. It is now refused with `TC_MATURITY_BELOW_POLICY` unless an approved, unexpired waiver scoped to that exact `name@version` covers it. `experimental` is never admitted in production.
- The deprecated v1 `ToolchainRegister.select` applies the same rule.
- See `docs/ADR-0001-production-maturity.md` and `config/policy.default.json`.

### Added
- **The PK_TOOLCHAIN/2 model** (`model.py`) adds a pinned version, runtimes, devices, features, hypervisors, providers and ABIs. It also carries a structured security response, UTC review provenance with a per-entry interval, structured limitations, lifecycle and EOL, an integrity identity and a catalog status.
- **Versioned policy and waivers** (`policy.py`). The production-rule floor cannot be weakened.
- **Typed request, result and refusal** (`selection.py`) with stable reason codes (`errors.py`). Every unmet constraint is reported for each candidate. The engine also enforces site capabilities and workload feature needs, applies deadline and cancellation, bounds its output, and keeps a cache that is invalidated on any change.
- **Register lifecycle** (`registry.py`): update, transition, remove, rollback and emergency disable. It adds per-capability authorisation, compare-and-swap (CAS) on revisions, signed and chained snapshots, and an atomic `FileStore` with reconstruct.
- **GAP-15 certificate consumption** (`certification.py`), **signed advisory feed** (`advisories.py`), **selection-to-build ticket plus the INV-27 verifier** (`binding.py`), and **canary/staged rollout with GAP-08 announcements** (`rollout.py`).
- **Observability** (`observability.py`, `service.py`, `explain.py`): metrics with a cardinality cap, pseudonymised structured logs, W3C trace context, a hash-chained decision ledger, health, readiness, status, an explain view, lineage and review scheduling.
- **Schemas** for every interface (`schemas/`), a stdlib schema checker, the example catalog (with OSv unregistered, per `docs/ADR-0002-osv-representation.md`), example documents and a CLI.
- **Vendored pk_core** (`_vendor/`), with digests pinned in `_vendor/PK_CORE_PROVENANCE.json`. The real W0-W9 workflow and gate now run. See `evidence/PK_GATE_RESULTS.json`: GO, 32 of the 100 findings exercised and the rest derived from declarations. These two counts are reported separately.
- **Documentation and operations files**: `docs/ARCHITECTURE.md`, `docs/THREAT_MODEL.md` (T-01 to T-15, each with a test), `docs/MIGRATION.md`, `ops/RUNBOOK.md`, `ops/SLA.md`, `ops/TECH_DEBT.md`, `ops/CAPACITY.json`, `ops/COMPATIBILITY_MATRIX.json`, `ops/alerts.json`, `ops/dashboards.json`, plus `SECURITY.md`, `CONTRIBUTING.md`, `DEVELOPMENT.md`, a placeholder `LICENSE` (decision D-004) and a generated `MASTER.md`.
- **Tooling and CI**: `tools/check_all.py` runs lint, SAST, the secret scan, the dependency check and SBOM, the MASTER.md check, tests under `python` and `python -O`, coverage, mutation, bench, soak, the pk_core gate, the MC-status check and review-due. `tools/release_gate.py` is the formal exit gate, with a falsifier test showing GO is reachable. The CI, release and review-freshness workflows, `pyproject.toml`, `requirements.lock` and the pre-commit configuration are included.

### Defects found by this pass and fixed
1. **Registry commits re-serialised the whole register on every mutation.** This made registration O(n²): building 1024 entries took **21.8 s**. Commits now hash a chained head over the per-record digests, and building 1024 entries including certificates takes about 1.2 s. See `evidence/BENCH_RESULTS.json`.
2. **GAP-15 certificate lookup scanned every certificate for every candidate.** A 1024-entry selection had a p50 of **182 ms**. An indexed lookup brought it to about 13 ms.
3. **Per-candidate locking in the certificate and advisory lookups** caused a lock convoy under the GIL. Throughput with 4 threads fell to **129/s**, below the single-thread rate. Indexes are now copy-on-write with lock-free reads, and the soak runs at about 430/s. See `evidence/SOAK_RESULTS.json`.
4. **The decision id included `id(registry)`**, so the same inputs gave a different id in each process. The decision id and the cache key are now separate.
5. **The metrics cardinality check scanned every series on each increment.** It now uses a per-metric set.
6. **Coverage counted lines executed at import time as missed.** This was a measurement error in the new tool, and it now measures function-body coverage. See `evidence/COVERAGE.json`.
7. **ruff and mypy** were available in the build container and both now pass clean (`evidence/OPTIONAL_LINTERS.json`). They flagged 60 lint findings and 31 typing findings, all of them typing or hygiene rather than behaviour. One variable was reused as both a list and a tuple in `selection.py`. Separately, `ruff --fix` stripped the test harness's re-exports as "unused"; the test suite caught that and the imports are now marked.
8. **Mutation testing left 34 survivors on its first full run.** `tests/test_boundaries.py` kills 31 of them. Two are documented as equivalent (unreachable). One survivor remains listed: `>` versus `>=` on a monotonic-clock deadline, which no test can observe. The final score is 298 of 299 non-equivalent mutants killed (99.7%). See `evidence/MUTATION.json`.

### Evidence
- `evidence/CHECK_ALL.json`, `evidence/TEST_RESULTS.json`, `evidence/COVERAGE.json`, `evidence/MUTATION.json`, `evidence/BENCH_RESULTS.json`, `evidence/SOAK_RESULTS.json`
- `evidence/SAST.json`, `evidence/SECRET_SCAN.json`, `evidence/DEPS.json`, `evidence/SBOM.cdx.json`, `evidence/PK_GATE_RESULTS.json`, `evidence/pk_evidence.jsonl`
- `evidence/MC_STATUS.json`, `evidence/GOVERNANCE_CHECK.json`, `evidence/RELEASE_EVIDENCE.json` (verdict **NO_GO**, with named blockers), `evidence/PROVENANCE.json`

### Still open (owner or environment)
- Name the role holders in `ops/OWNERS.json`, and accept or replace ADR-0001, ADR-0002 and ADR-0003, the licence (D-004) and the signing/KMS decision (D-005).
- Approve or reject waivers W-001 to W-003. Connect the real GAP-15, INV-27 and GAP-08.
- Run CI on the 3.10-3.13 × OS matrix. Only CPython 3.11 on Linux was executed here.
- Re-baseline performance on reference hardware (TD-9: p99 at 1024 entries is above the PROPOSED 25 ms).
- Have an independent reviewer accept the MC items.

## 4.2.0 - 2026-09-23

Repository audit, validation hardening, and deterministic-selection pass.

### Hardening

- Normalise language, architecture, maturity, and environment identifiers before matching.
- Reject empty capability sets, malformed tokens, invalid review clocks, and non-boolean security-contact flags.
- Make registry membership externally read-only and reject duplicate names case-insensitively.
- Make equal-maturity selection deterministic and independent of registration order.
- Validate logical time for stale-review checks and selection.
- Add an explicit `limitations` field to register entries so known limitations can be represented rather than only described in prose.
- Correct README inventory metadata: `MASTER.md` is referenced by the inherited documentation but is absent from the supplied archive.

### Verification

- Source compiles under CPython.
- Domain-level smoke tests cover normalisation, duplicate rejection, production safety gates, stale-review enforcement, and deterministic selection.
- The upstream `pk_core` conformance suite remains an external dependency and cannot be executed from this standalone archive.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Toolchain.__post_init__: languages/architectures given as a str made matching a substring test ("c" in "ocaml" selected MirageOS for C); empty name accepted -> require set/frozenset (TypeError), non-empty name (ValueError)
- component.py::ToolchainRegister.select: environment compared case-sensitively, so "Production" bypassed the experimental/security-contact/stale-review gates -> normalise strip().lower()
- component.py::ToolchainRegister.register: duplicate names accepted, leaving ambiguous entries (stale copy still selectable) -> ValueError on duplicate

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
