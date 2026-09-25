# Changelog - INV-69

## 4.3.0 - 2026-09-23

This release remediates the 49 controls that the v4.2.0 post-hardening audit marked as `missing`
(`INV69_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md`).

### Added (stdlib-only)
- `governed.py`: `GovernedRuntime`, the integrated service layer. See ADR-0002.
- Core modules:
  - `errors.py`: stable error-code registry
  - `lifecycle.py`: typed state machines
  - `context.py`: deadlines, cancellation, W3C trace context and bounded admission
  - `retry.py`: the shared retry engine (full jitter, retry budget)
- `config.py` and `config/`: declarative configuration and deployment profiles.
  - Covers four profiles: cloud, datacenter, near_edge and far_edge.
  - Adds overlays with locked fields, generations switched by compare-and-swap, and a
    provenance chain.
- `precedence.py`: a versioned constraint-precedence policy with decision traces and waivers.
- `trust.py`: dependency criticality and freshness, connectivity state, the offline queue,
  reconciliation and degraded modes.
- `artifacts.py`: the artifact trust verifier.
- `compat.py`: peer handshake, migrators and deprecation warnings.
- `sandbox.py`: contract-faithful adapters for INV-57, INV-59, INV-70 and INV-71. Also fault
  plans, fencing and failover target selection.
- `health.py`, `telemetry.py`, `explain.py` and `backup.py`: status and watchdog, the telemetry
  policy with lineage, the explain view, and backup/restore.
- Schemas: `PK_AGENT_RUN_EVENT/1`, `PK_AGENT_ERROR/1`, `PK_AGENT_CONFIG/1` and `PK_AGENT_STATUS/1`.
- Tools:
  - `gen_spec` (SPEC.md generated from code)
  - `rtm` (100-control traceability matrix and audit rerun)
  - `governance_check`, `deps_check` (with SBOM), `perf_gate`, `release_gate`,
    `capacity_model` and `alert_eval`
- Tests (133, stdlib-only apart from the jsonschema lane):
  - `tests/test_v43.py` (21 classes)
  - `tests/test_fuzz.py`: property and mutation fuzzing, plus a resource-limited isolated campaign
- `bench/perf_suite.py`.
- Ops artifacts:
  - `ops/`: owners, escalation, runbook, incident template, reviews, waivers, alerts, dashboards,
    approved technology list, EOL table, compatibility matrix, performance thresholds
  - `.github/CODEOWNERS` and CI
  - `requirements.lock` and `pyproject.toml`

### Fixed: kernel defects present in v4.2.0 (found by this pass's fuzzing)
- A deeply nested tool argument raised `RecursionError` out of `Agent.step`. Such arguments are now
  refused with AGT-VAL-002.
- `_arg_shape` echoed secret-looking dict **keys** into the transcript. They are now redacted.

### Fixed: defects in this pass's own new code, caught by its own tests
- `status()` readiness disagreed with the admission gate. A critical dependency could be down but
  still inside its cache window, and status would say "ready" while `start_run` refused. Readiness
  now uses the same matrix through `TrustMonitor.would_pass`.
- Redaction missed hyphenated key formats such as `sk-live-...`.
- A non-string `schema_version` crashed configuration validation with `TypeError`.
- Soak testing showed unbounded retention, about 16 KB per completed run. `GovernedRuntime.archive`
  now gives bounded retention while keeping the chain continuous.

### Performance (C065/C066, measured before and after in `evidence/OPTIMIZATION_REPORT.json`)
- `collections.abc.Mapping` replaced `typing.Mapping` in hot `isinstance` checks.
- The kernel makes one bounds traversal per step instead of two.
- The retry RNG is created once instead of on every call.
- Lineage is cached per configuration generation and topology snapshot.
- Redaction regexes are combined.

### Not done (named blockers; see `ops/WAIVERS.json` and `ops/RTM.md`)
- No owners are named.
- pk_core is absent and unpinned.
- The real adjacent peers are absent.
- Signatures use HMAC only.
- Chains have no external anchor.
- Only one platform was executed.
- Power was not measured.
- Thresholds and ADR-0002 are still PROPOSED.
- Release gate: **NO_GO**.

## 4.2.0 - 2026-09-22

Second audit, corrective hardening and repository-evidence pass.

### Runtime correctness and security

- Extracted the safety-critical policy kernel to `runtime.py`, which has no
  `pk_core` dependency and can be tested standalone.
- Added immutable `ToolSpec` metadata and a read-only tool registry.
- Added construction-time rejection of unknown allowlist entries.
- Added a real cost budget alongside the existing step budget.
- Changed step accounting so rejected tool-call attempts consume the bounded
  invocation budget instead of permitting unlimited hostile refusals for free.
- Added bounded transcript capacity and fail-closed sealing when audit capacity
  is exhausted.
- Replaced raw `(tool, arg)` set membership with exact-argument HMAC binding, so
  dict/list payloads can be approved without `TypeError` and approval references
  do not expose raw payloads.
- Made approvals one-use, exact-argument-bound, non-self, allowlist-aware and
  side-effect-only.
- Made approval recording transactional: if the audit event cannot be committed,
  the approval is rolled back.
- Added rollback of cost/approval state if a would-be successful step cannot
  commit its audit record.
- Added per-agent locking to close budget/approval races across concurrent callers.
- Added secret-safe argument shape metadata rather than raw argument persistence.
- Added local event hash chaining plus `verify_transcript()` and versioned
  transcript export.
- Hardened canonicalization for cyclic containers, non-finite floats, mixed key
  types and arbitrary objects.
- Invalid/non-string tool names now fail closed rather than raising membership
  errors.

### Contracts, documentation and tests

- Added versioned JSON Schemas for `PK_AGENT_STEP/1`,
  `PK_AGENT_APPROVAL/1`, and `PK_AGENT_TRANSCRIPT/1`.
- Added `docs/ADR-0001-agent-execution-governance.md`.
- Added `docs/SECURITY.md` with trust boundaries, implemented controls and
  residual external-control requirements.
- Added 15 standard-library runtime tests, including concurrency, tamper
  detection, replay resistance, hostile input handling and audit-capacity
  exhaustion. The suite passes in normal and optimized (`python -O`) mode.
- Made package imports lazy so the standalone runtime remains usable when
  `pk_core` is unavailable.
- Corrected the README's false claim that `MASTER.md` was present.
- Added a post-hardening repository gap audit and machine-readable audit report.

### Verification note

The standalone runtime suite passes locally. The existing `pk_core` conformance
suite is not executable in this uploaded archive because `pk_core` is absent;
those tests skip by design and are not counted as production certification.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Agent.step: an approval for (tool, arg) was a standing grant, letting a side-effectful action run unlimited times after one approval -> approval consumed on run
- component.py::Agent.approve: empty approver or the agent approving itself accepted -> PermissionError

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
