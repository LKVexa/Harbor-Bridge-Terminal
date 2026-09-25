## UC-2.8.0 — edge-component atoms combined (2026-09-23)

- Combined the 99 supplied edge-component archives (`Edge Components in`) with UC-2.7.0. The archives are kept byte-for-byte under `edge/source/` (91 distinct; 8 byte-identical duplicates recorded as aliases).
- Extracted one canonical atom per element (86: GAP-01..15, 62 INV elements, PLN-01..07, SCH-01, iOS735 LCTL) under `edge/atoms/`. Four distinct alternative builds (INV-30, INV-55, INV-61, INV-66) are kept under `edge/variants/`, and each canonical choice is recorded with its reason. The GAP-04 release-evidence archive sits beside its atom.
- Added `pk/PK_ATOM_BINDINGS.json`, which binds 85 atoms to their PK elements and records the supplied `pk_core` 4.0.0 tree hash for owner pinning. The generated `pk_components/`, checklists and PK gate are unchanged.
- Added `ship/unikernel/edge_atoms.py`, `uc edge status|list|check [--deep]|show|test`, the `EDGE.cmd`/`EDGE` launchers and an `edge_atoms` block in `uc platform status`. Atom suites run as child interpreters in disposable copies under `_runs/edge/work/` with an isolated import path, so atom writes never reach the sealed tree.
- Recorded evidence (`edge/evidence/EDGE_TEST_RESULTS.json`): 9,833 passed / 41 failed / 0 errors / 46 skipped across 86 suites (59 green, 27 red). Every failure is classified: stale in-atom version pins, pk_core-presence expectations, absent wasm-tools, host performance ceilings, and 4 atom-internal assertions. No atom was edited.
- Added `tests/test_edge_atoms.py`, which covers inventory counts, shallow and deep integrity, tamper, stray-file and corruption detection, runner isolation and the CLI.
- Moved the release label to UC-2.8.0, the folder to `UC280`, and the PK ownership, routing and PHOTON host paths to the new location. Resealed `MANIFEST.json`/`SHA256SUMS.txt`, which also binds the PHOTON and `pk/` files that UC-2.7.0 had added after its last seal.
- The existing boundaries still hold: no atom is wired into berths, hull, VWS control, the TIFF path or the 1-bit fabric; no PASS promotion; not Production GO.

## UC-2.7.0 — 375K master-series application and bounded platform services (2026-09-22)

- Preserved all 15 attached master-series volumes byte-for-byte and verified 150 components / 375,000 unique task IDs.
- Added `master-workflow` status/check/show/execute surfaces and `MASTER_FLOW` launchers.
- Added conservative per-component/task disposition ledgers; zero source tasks are auto-promoted PASS.
- Added bounded local event bus, hash-chained audit ledger, metrics, tracing, structured log records, priority/backpressure queue, idempotency keys, quota/feature/retention validators, capacity planning, hardware facts and compatibility reporting.
- Added explicit pixel-kernel ABI/capability descriptor and conformance tests.
- Added current threat, supply-chain, tenant-isolation, local protocol and pixel-state specifications.
- Extended authenticated VWS read-only policy with `ship master-workflow status` and `ship platform ...` inspection.
- Retains hard boundaries: no bootable unikernel guest, hypervisor isolation, multi-host consensus, production signing authority or public deployment claim.

## UC-2.6.0 — bounded 1-bit communication fabric (2026-09-22)

Applied the ten retained JYRM 1BNCF v3.1.0 phase archives to UC-2.5.0 as a fail-closed communication adaptation. Added UC1B/UCFP wire formats, canonical LSB-first packing, CRC/order/address validation, FP32 warmup/fallback, residual feedback, adaptive scaling, recovery/checkpoint/replay, local routing/reduction, bounded memory transport, TIFF carrier integration, source-preserving 275,000-ID traceability, read-only VWS inspection, tests and operator tooling. This is **1-bit communication, not 1-bit cognition**. No source task or phase is promoted by local test success.

External JYRM model semantics, NCCL/GPU, public TCP transport, Windows named-pipe qualification and JA21/QAM/FXSpot/Junkyard adapters remain absent or blocked.

## UC-2.5.0 — TIFF/GIF and pixel-state integration (2026-09-22)

Applied the retained TIFF Nine-Phase Prompt/Workflow v1.6.0 to UC-2.4.0's active state path. Added strict bounded classic/BigTIFF admission, a raster-only decoding adapter, verified atomic history writes, reversible UC/FABRIC_GIF/1 transport, checked u64 pixel-cell operations, local inspection/export/edit/checkpoint commands, read-only VWS pixel inspection, and full source-task integrity/disposition tracking. Native engines and sealed genesis content remain unchanged.

See `docs/tiff/START.md`, `docs/tiff/CONTRACT.md`, `docs/tiff/VALIDATION.md`, `docs/tiff/WORKFLOW_APPLICATION.md` and `provenance/UC250_CHANGES.json`. Passing local tests are not full source-task completion or production approval. Native Windows, browser UI, scientific/cloud backends, GPU/SIMD and native-child resource quotas remain unqualified or absent as explicitly documented.

# UC-2.4.0 — VWS terminal integration

- Integrate supplied HERMIT RAMWS as vws/ (integration revision 2.0.1-uc.1).
- Add authenticated loopback launcher, fixed-root/Python bridge, typed ship messages and virtual ship command.
- Separate inspection from explicit control; enforce generation fencing, bounded output/deadlines, global concurrency and disconnect cancellation.
- Fix contradictory volatile-launch snapshot configuration and exact-credential revocation.
- Correct the launcher integration test to exchange its bearer for an Origin-bound cookie, and replace an invalid inherited stress workload with explicit capture-limit checks on both worker backends. These checks do not certify native process memory limits.
- Add bounded array validation and omit new capabilities on legacy non-ship hello packets.
- Add complete 6,360-record source-preserving workflow reapplication and fail-closed traceability checks.
- Add portable Node test discovery, new Python/Node tests, operations/security/runbooks and actual qualification evidence.
- Preserve original licenses and hull/hold bytes; do not claim source-task completion, native Windows qualification, browser acceptance or public deployment.

---

# Changelog

## UC-2.3.0 — September 22, 2026

Application type: tested local-foundation implementation pass over the attached nested to-do series. Not a complete unikernel implementation or a production promotion.

### Added

- Strict bounded duplicate-safe JSON readers; integer-only canonical encoding for new contracts, without rewriting legacy formats.
- Versioned control-request validation, truthful backend/assurance capability output, and no-fallback isolation admission.
- SQLite local identities, monotonic generations, legal transition model, operation outcome records, and generation inspection.
- Verified managed-file snapshots, a durable transaction journal, pre-mutation capacity checks, and explicit pending rollback with displaced-data retention.
- Typed artifact DAG validation, cycle/missing-edge refusal and exact affected-descendant queries; bounded content-addressed local blobs with read-time integrity verification.
- Bounded ship helper process output, deadlines and POSIX process-group cleanup; a best-effort untested Windows tree-kill branch.
- Read-only exact-source workflow import and 96,000-record application ledger; current acceptance blockers retained.
- Regression, seeded transition, actual process-crash, disk/write-failure and negative-input fixtures; two new top-level qualification gates.

### Fixed

Unload can no longer ignore a failed hull unmount or failed studio-registration cleanup. Load failure propagation includes mount results. JSON emission no longer breaks while reporting a NaN/infinity input refusal. Expected generation and required isolation are checked before the protected mutation path. Successful console output is withheld until its managed transaction commits. Explicit output reports are staged and published only after the transaction decision, and cannot overwrite managed source/control files.

### Compatibility and limits

The hold, hull and six original berth payloads are preserved. Historical metadata retains its original release/version context. New ship metadata is intentionally resealed after the documented source changes; no seal is used to waive an unexplained native failure. Per-command snapshots increase storage demand and can refuse large workspaces at conservative limits. Old backups and new journals are never automatically pruned. Native execution inside untouched imported adapters is not globally supervised. See the recovery and trust-boundary documents for explicit exclusions.

## UC-2.2.0 — September 21, 2026 (America/Los_Angeles)

Release type: backward-oriented minor hardening release; stricter invalid-input handling and additional diagnostics commands. The source baseline is UC-2.1.3. The original outer archive is not modified.

### Fixed

* Centralized berth/container identity and contained-path validation, including unload and execution paths.
* Staged loads/replacements, retained backups, error rollback attempts and visible transaction journals.
* Bounded ZIP admission and flat staging that preserves logical case-distinct names before Windows-safe aliasing.
* Protection of Windows device names, path-component collisions and generated cargo metadata/alias names.
* Required hold pins, strict checksum records, strict inventory totals and empty-berth reseal behavior.
* Pre-execution bundle/reference checks, cargo ledger/hash checks and nonzero failure propagation.
* TIFF tick verdict checks and bounded atomic ship-managed TIFF rewrites.
* Cooperative writer locking, atomic metadata replacement, UTF-8 subprocess decoding, explicit root CMD exit propagation and invalid numeric argument refusal.
* Mount ownership/path validation and refusal to silently discard an unreadable mount registry.

### Added

`uc.py --version`, `uc.py doctor`, `uc.py self-test`, `verify --require-complete`, DOCTOR/SELFTEST wrappers, a regression suite, a source-level audit ledger, security boundary documentation and a 96-component theory-to-implementation roadmap with 12 phase files and machine-readable dependencies.

### Compatibility and preserved content

The six delivered berths remain the original sealed workload examples. Their metadata's historical load-time release fields, declarations and old checksum self-reference fields are not retroactively rewritten; new loads omit the invalid self-reference. The current release identity comes from `ship/unikernel/__init__.py`, `VERSION`, the rebuilt bill of lading and the current manifest. `hull/` and `hold/` bytes and existing license notices are preserved. Old `conformance/` and capability reports remain historical evidence; use the audit evidence associated with UC-2.2.0 for the current test results.

Names that previously accepted traversal, terminal newlines, device names or ambiguous Windows storage are now refused/aliased. Invalid limits return 3 (blocked/refused); malformed CLI syntax returns 2. Native failures return 1; interruption returns 130. Successful unload/replacement consumes backup space instead of irreversibly deleting the previous berth. No automatic backup pruning is enabled.

### Not implemented

This is not a native bootable unikernel, a guest/hypervisor integration, a multi-tenant service, an authenticated distributed scheduler or a production isolation certification. See `SECURITY.md` and `docs/MISSING_COMPONENTS.md`.
