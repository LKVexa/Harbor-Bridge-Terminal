# Changelog - INV-02

## 5.0.0 - 2026-09-22

Checklist execution pass over the 78 missing production components (MC01–MC78). Backwards compatible: `registry.Registry` and the `pk_core` adapter are unchanged.

### Added
- `oci.py` (MC01, MC14), `store.py` (MC03, MC15, MC30, MC34–MC38, MC52), `distribution.py` (MC02, MC16, MC17, MC36, MC39, MC40), `rootfs.py` (MC04, MC09, MC13), `runtime.py` (MC05–MC12, MC22–MC28, MC33), `trust.py` (MC18–MC21, MC55), `policy.py` (MC29, MC32, MC49, MC77), `audit.py` (MC31), `observability.py` (MC45–MC48), `resilience.py` (MC41–MC43), `timeutil.py` (MC44), `config.py` (MC54), `migrations.py` (MC53, MC76).
- Test suites: OCI, store, trust/policy, distribution against a local HTTP registry, rootfs/adversarial layers, runtime, ops, seeded fuzzing, thread + multi-process races, fault injection, and real `runc` integration (MC57–MC64).
- Tooling: `tools/release_evidence.py` (MC67, MC70), `tools/bench.py` (MC65).
- Governance: `MASTER.md` restored (MC68, E-01), `pyproject.toml` (MC69), `NOTICE` + `LICENSE-STATUS.md` (MC71), ADR-0001 (MC72), `OWNERS.yaml` (MC73), `COMPATIBILITY.md` (MC66, MC74), CI workflow (MC75), `waivers/waivers.json` (MC77), `SECURITY.md` (MC78), operations guide + alert rules (MC50, MC51, MC53, MC55, MC56), `COMPONENT_STATUS.json`, annotated checklist.

### Changed
- Package version 5.0.0; README documents the new modules and validation commands.
- `MISSING_COMPONENTS.md` is superseded by `COMPONENT_STATUS.json` (kept for history).

### Owner actions (cannot be closed by engineering)
- Choose and add a licence (MC71); name owners (MC73, G-01); approve SLA/EOL defaults (MC78).

## 4.2.0 - 2026-09-22

Audit, parse, fix, hardening, and residual-gap inventory pass.

### Hardening and correctness

- Added `registry.py` as a stdlib-only integrity model so core checks can run without `pk_core`.
- Normalized and validated environment names; protected both `prod` and `production`, closing case/alias/padding mutable-tag bypasses.
- Added strict image-name, tag, digest, environment, and reference parsing including registry-port-safe tag parsing.
- Digest resolution now requires a known, non-quarantined manifest.
- Added configurable ceilings for layer count/size, total image bytes, manifest size, reference length, and history size.
- Added deterministic schema-versioned manifests with media type and layer sizes; retained v4.1.0 legacy manifest read compatibility.
- Hardened manifest decoding/schema/descriptor failure handling to fail closed with `IntegrityError`.
- Added thread synchronization around compound registry operations.
- Added bounded tag-movement provenance records.
- Added manifest/layer quarantine and release controls.
- Added explicit registry statistics rather than classifying manifests by content prefix.
- Made `pk_core`-dependent package exports lazy so the reference model can be imported in partial checkouts.

### Tests and auditability

- Added `tests/test_registry.py` covering digest identity, de-duplication, mutable-tag policy, unknown digests, reference parsing, tag movement, corruption, malformed manifests, legacy compatibility, limits, quarantine, custom policies, package import, and concurrency.
- Added `AUDIT_REPORT.md` with fixed findings, validation status, compatibility notes, and residual risk.
- Added `MISSING_COMPONENTS.md` with the production-gap inventory.
- Corrected the README claim that `MASTER.md` was bundled; it is absent and now tracked as a missing artifact.

### Validation limitation

- The uploaded archive does not include `pk_core`; estate-wide conformance tests are therefore skipped in the isolated package and require rerun in the complete checkout.


## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Registry.resolve: contract mandates "record which digest a tag resolved to" but nothing was recorded -> append (ref, env, digest) to a new Registry.resolutions list
- component.py::Registry.resolve: unknown tag raised bare KeyError and a malformed "@sha256:..." reference was returned unchecked -> raise UnknownReference (new LookupError subclass) for both
- component.py::Registry.pull: unknown manifest / missing layer raised bare KeyError -> UnknownReference / IntegrityError
- component.py::Registry.push: setdefault kept an already-corrupted blob under its digest forever, so re-pushing good bytes could not heal it -> replace the stored blob when it no longer matches its digest

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
