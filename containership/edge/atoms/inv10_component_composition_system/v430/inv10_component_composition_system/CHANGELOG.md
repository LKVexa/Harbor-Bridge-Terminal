# Changelog - INV-10

## 4.3.0 - 2026-09-22

Closes the 50 residual components listed in `MISSING_COMPONENTS.md` (disposition: `DISPOSITION_4.3.0.md`).

### Identity guarantee
- `composition.py` is **byte-identical** to 4.2.0 (sha256 `794caa37…4b2a`). Every 4.2.0 composition id is unchanged.
  New capabilities are layers that wrap `compose()`; rewrites (aliases, dead-export elimination, nesting) are applied
  before linking and recorded in additive fields (`extension_digest`, `tree_digest`).

### Added
- Packaging: `pyproject.toml`, `requirements.lock`, `inv10` CLI, fail-closed `pk_core` gate (`pkcore_compat.py`).
- Contracts: JSON Schemas for PK_COMPONENT/1, PK_COMPOSITION/1, PK_COMPOSITION_MANIFEST/1; `docs/IDENTITY_PROFILE.md`; conformance vectors.
- Integration: WIT world parser (`wit.py`); INV-09/INV-11/INV-12/PLN-02 ports with reference adapters (`adapters.py`).
- Governance: tenant/workload/environment/site context, default-deny link policy, provenance verification, external-environment resolver (`governance.py`).
- Security: key provider with rotation, token authentication and roles, hash-chained audit trail (`security.py`).
- Operations: metrics (Prometheus), structured logs with trace context, health, explain (`observability.py`).
- Control plane: registry, content-addressed store, atomic activation/rollback, config ledger, admission control, idempotent/replay-safe service, quarantine/freeze (`controlplane.py`).
- Optional capabilities: incremental linking, import aliasing, dead-export elimination, nested compositions, diff/impact, 4.1.0 migration (`features.py`).
- Verification: 54 new tests (71 total) (integration, property/fuzz, scale/soak/burst, fault injection, concurrency, vectors), benchmark, evidence/gate generator, SBOM, release signing, CI workflow, generated API reference.

### Not claimed
- Overall gate verdict is **CONDITIONAL_GO**: pk_core conformance, the real adjacent services, and owner sign-off (ADR / OWNERSHIP / SECURITY) remain BLOCKED.

## 4.2.0 - 2026-09-22

Audit, correctness, hardening, and verification pass.

### Correctness fixes

- Fixed self-cycle bypass: a component importing an interface that it also exports now retains the self-edge and is refused as `COMPOSITION_CYCLE`.
- Replaced the incomplete 4.1.0 identity material with a canonical manifest containing every unit name, import, export, resolved binding, and used external import.
- Replaced the 24-hex-character (96-bit) truncated digest with the full SHA-256 digest.
- Added `PK_COMPOSITION_ID/2` so callers can distinguish the corrected identity semantics while the additive response remains `PK_COMPOSITION/1`.

### Hardening

- Added strict string/shape validation, NFC checks, control/format-character rejection, whitespace checks, identifier-length bounds, and duplicate-input detection.
- Added bounded `CompositionLimits` for components, per-component interfaces, external imports, total interface references, and identifier length.
- Added structured `CompositionError` subclasses with stable machine-readable error codes/details.
- Added deterministic provider and per-import binding metadata to successful compositions.
- Split the pure linker into `composition.py` and moved element metadata to dependency-free `metadata.py`.
- Made the `pk_core` checklist adapter lazy-loaded so linker-only consumers can import and test the package without `pk_core`.

### Verification

- Added 12 standalone stdlib linker tests covering determinism, graph-sensitive identity, self-cycles, multi-node cycles, unsatisfied imports, ambiguous exports, duplicate component identities, explicit externals, identifier hardening, resource ceilings, empty composition determinism, and linker-only package import.
- Verified the linker under normal and `python -O` execution.
- Ran a deterministic 1,000-case randomized DAG property pass checking input-order-independent IDs and topological provider-before-consumer order.
- `tests/test_component.py` compiles, but its three `pk_core` conformance tests are skipped in the standalone archive because `pk_core` is not bundled. No fresh 100/100 production certification is claimed by this release.

### Audit artifacts

- Added `AUDIT_REPORT.md`, `MISSING_COMPONENTS.md`, and `MANIFEST.sha256`.

### Compatibility note

- Composition IDs intentionally change from 4.1.0 because the old digest did not encode the complete composition graph. Recompute persisted IDs before comparing across identity profiles.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::compose: duplicate/empty component names silently overwrote each other's dependency edges -> refused with AmbiguousExport

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
