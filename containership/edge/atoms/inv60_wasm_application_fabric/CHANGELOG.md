# Changelog - INV-60

## 4.3.0 - 2026-09-22

Missing-components pass against `INV60_WASM_APPLICATION_FABRIC_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` (M01–M86).

### Added
- `fabric/` hardened control plane (16 stdlib-only modules) around the unchanged `runtime.Lattice`.
- Real WebAssembly execution tier through V8 (`NodeWasmBackend`): import-free, memory ceiling, wall-clock kill; `WasmCloudBackend` seam fails closed.
- WIT package `inv60:lattice@1.0.0`, JSON schemas for PK_LATTICE_START/LINK/CALL and the result envelope, 47 golden fixtures + a Node validator.
- Vendored `pk_core` beside the package (M76): the 100-item conformance suite now runs instead of skipping.
- `MASTER.md` restored verbatim from the owner's series (M01).
- Governance: ADR-0001, 30 SHALL/SHOULD/MAY requirements, 16-threat STRIDE model, SLOs, six runbooks, ownership/waiver/review registers, support matrix, alerts/dashboard.
- Tooling: `tools/ci.py` (strict), bench with baseline + regression gate, SBOM (CycloneDX), traceability, acceptance evidence, exit gate, bootstrap, config promotion diff, seal/verify.
- Tests: 7 → 194 (security, semantics, resilience, config/observability, fuzz, governance), all passing under `python` and `python -O`.

### Fixed (defects found by this pass's own tests)
- Token base64 was malleable: a flipped padding-bit character decoded to the same credential; decoding is now strict and canonical (found by fuzzing).
- `negotiation.parse` crashed with `TypeError` on non-string versions instead of refusing (found by fuzzing).
- Nonce GC iterated an unlocked dict (`RuntimeError` → `INTERNAL` under concurrent calls), and the replay check-then-record was not atomic (found by the `-O` concurrency run).
- Audit-ledger append was not atomic under concurrency (chain could fork).

### Measured, not claimed
- Authenticated call p99 ≈ 6 ms on this container — **misses** the 3 ms routing-overhead target because verification is pure-Python Ed25519; capability-checked call p99 ≈ 0.004 ms meets it (`release/BENCHMARK.json`).

## 4.2.0 - 2026-09-22

Second audit, repair and hardening pass.

### Runtime hardening

- Split the dependency-free lattice model into `runtime.py` so its safety properties can be tested without `pk_core`.
- Validate host names, component names, link names, unique membership, instance-to-host consistency, and non-negative failover state.
- Copy bytes-like artifacts to immutable `bytes` on ingest; reject non-bytes-like payloads.
- Reject duplicate component starts instead of silently overwriting placement.
- Require a running component and callable provider before granting a runtime link.
- Add explicit `add_host`, `stop`, and `unlink` lifecycle operations; stopping a component revokes its runtime links.
- Refuse calls for instances assigned to unavailable hosts.
- Make host loss transactional: all refusal conditions are checked before membership or placement mutation.

### Verification and audit correctness

- Added `tests/test_runtime.py` with dependency-free tests for integrity, membership/failover atomicity, lifecycle authority revocation, and configuration validation.
- Corrected the README: `MASTER.md` is referenced by the source-series description but is absent from the supplied archive.
- Added `AUDIT_REPORT.md` with verified fixes, verification limits, and the post-update missing-component inventory.
- The `pk_core`-dependent 100-item suite remains externally dependent and is reported as unverified when `pk_core` is unavailable rather than counted as a local pass.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::Lattice.start: unknown ref raised bare KeyError, empty host list raised ZeroDivisionError -> new UnknownArtifact(LookupError) / LookupError before any mutation
- component.py::Lattice.lose_host: unknown host raised ValueError from list.remove; losing the last host with instances removed it then crashed with ZeroDivisionError leaving state corrupt -> LookupError checked before mutation

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
