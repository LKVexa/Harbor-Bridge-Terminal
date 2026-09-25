# Changelog - INV-23

## 5.0.0 - 2026-09-23

Remediation of all 14 missing-component work packages (MC-01…MC-14) from
`INV23_Missing_Components_Remediation_Checklist.md`. Breaking: new interface majors.

### Added
- **MC-01** `pkcore_compat.py`: single documented pk_core resolution precedence (PK_CORE_PATH >
  installed > SHA-256-pinned `vendor/pk_core` 4.0.0 > dev-only sibling), API + version
  checks, shadowing detection, `INV23_CONFORMANCE=release` hard-fail mode. pk_core 4.0.0
  vendored unmodified from the owner's `PK_Master_Applied_All_Batches.zip`.
- **MC-02** `MASTER.md` restored verbatim from the same archive; `MASTER_PROVENANCE.json`.
- **MC-03** `backends/` (Linux KVM: cpuinfo + `/dev/kvm` open + `KVM_GET_API_VERSION`;
  Windows: `IsProcessorFeaturePresent` + `WHvGetCapability`; macOS: `kern.hv_support`),
  `probe.Prober` (backend selection, timeout, TTL cache, invalidation), `indeterminate`
  state, 14 stable reason codes, unknown nesting depth never fabricated.
- **MC-04/05** `ownership/`: memory, POSIX `flock`, Windows `msvcrt` providers; 256-bit
  tokens (hash-only at rest), fencing generations, leases, PID+start-time+boot-id liveness,
  stale-owner takeover with history, fail-closed corruption, `repair()`; `claim.ClaimManager`.
- **MC-06** `schemas/` (PK_VIRT_PRIMITIVE/1+/2, PK_VIRT_CLAIM/1+/2, PK_VIRT_OWNERSHIP/1,
  PK_GATE_RESULTS/1), stdlib validator + semantic invariants, versioning rules.
- **MC-07** `telemetry.py`: metrics, events (INV23-E001…E009), spans, bounded labels,
  redaction, exporter isolation, optional OpenTelemetry sink.
- **MC-08** `benchmarks/benchmark_probe.py`: p99 < 50 ms gate, baselines, regression, waivers.
- **MC-09** `compatibility.json` → generated `COMPATIBILITY.md` (18 rows, status-tracked).
- **MC-10** property/fuzz suite (seeded stdlib generator; Hypothesis layer when installed).
- **MC-11** multi-process contention (12 procs × 25 rounds), SIGKILL recovery + fencing,
  restart, tampering, fault injection, adjacent-layer admission contract (`admission.py`).
- **MC-12** `pyproject.toml`, `cli.py` (`inv23-probe`), CI/hardware/release workflows,
  ruff + mypy gates, version-consistency check, CycloneDX SBOM, SLSA-style provenance.
- **MC-13** SECURITY.md, THREAT_MODEL.md (20 threats), SUPPORT.md, CODEOWNERS,
  incident runbook, waiver ledger + validator, LICENSE-STATUS.md (license undetermined).
- **MC-14** `tools/gate.py` + `tools/verify_evidence.py`: hash-chained, checksummed gate evidence.

### Changed
- Primitive model moved to `model.py` (pk_core-free); package `__init__` loads `COMPONENT` lazily.
- Contract interfaces now reference the /2 schemas; exclusivity is described as a project
  slot, since the KVM, WHPX and HVF APIs are not exclusive.

### Deprecated
- `PK_VIRT_PRIMITIVE/1` and `PK_VIRT_CLAIM/1` (in-process `VirtPrimitive`) are frozen and kept
  for the pk_core reference assessment and for decoding historical evidence.

## 4.2.0 - 2026-09-23

Audit, parse, hardening and validation pass.

- Added thread-safe claim/release/report snapshots with `RLock`.
- Removed anonymous release of an active claim; holder identity is now required.
- Hardened host/boolean/nesting/holder/max-nesting validation, including explicit rejection of booleans as integer depths.
- Added standalone stdlib behavioural and concurrent-claim tests that run without `pk_core`.
- Corrected README provenance text for the absent `MASTER.md`.
- Added `AUDIT_REPORT.md` with post-update validation and remaining component gaps.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::VirtPrimitive.report: bare_metal flipped to False as soon as the primitive was claimed, contradicting claim()'s own bare_metal=True -> treat CLAIMED like USABLE for bare_metal
- component.py::VirtPrimitive.claim: accepted empty holder and negative max_nesting -> ValueError
- component.py::VirtPrimitive.__post_init__: negative/non-int nesting_depth accepted (would read as "better than bare metal") -> ValueError
- component.py::VirtPrimitive.release: any caller could drop another hypervisor's exclusive claim -> optional holder arg; mismatched holder raises PrimitiveUnavailable

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
