# Unikernel Containership UC-2.5.0 — TIFF/GIF integration report

**Date:** September 22, 2026. **Disposition:** integrated and locally tested candidate; **not Production GO**. Original uploads and existing user installations were not modified. This release is a separate, short-root source package.

## Applied change

The TIFF Nine-Phase Prompt/Workflow v1.6.0 was applied to the active TIFF pixel-state path in UC-2.4.0, not only appended as a document. Changes include bounded TIFF admission, exact state reconstruction, reversible GIF transport, a checked u64 pixel kernel, atomic history writes, generation/digest-checked live edits, checkpoints, local commands, read-only VWS integration and reproducible validation tools. The four native DF engines, sealed berths and supplied genesis images were preserved rather than relabeled as new engine implementations.

The native kernel still executes the supplied DF instruction sets. The new `pixel_kernel.py` is a deterministic CPU state-operation layer connected to those engines, not a new bootable OS, hypervisor or GPU kernel.

## Inputs and preservation

| Input | SHA-256 |
|---|---|
| UC-2.4.0 VWS candidate ZIP, 74,094,074 bytes | `3bc5ed219dccafbcec54f32baa827c127de6624849f690238e360557eb930d07` |
| TIFF workflow v1.6.0 ZIP, 16,792,991 bytes | `408cd5dfe526c876fca8f081413edcf7ed08a33a6368909a3a89f70e8cde7920` |

The original TIFF series is retained byte-for-byte in `tifflow/series.zip`. A comparison of **7,167 original hold and sealed-berth files**, including **30 genesis TIFFs**, found no changed or missing files. The earlier VWS workflow and its historical evidence remain separate; they were not silently promoted. Input pins and exact added/modified/removed file records are in `provenance/UC250_INPUTS.json` and `provenance/UC250_CHANGES.json`.

## Observed qualification

| Check | Observed result | Evidence |
|---|---|---|
| Complete Python regression | **378 tests passed**, no failures, 32.271 seconds | `evidence/tiff/logs/python_release.log` |
| New TIFF/GIF/kernel tests | **100 passed** (included in 378) | `evidence/tiff/logs/pixel_final.log` |
| New workflow integrity tests | **6 passed** (included in 378) | Complete Python log |
| Independent TIFF encoder matrix | **8 variants passed**: classic/BigTIFF × II/MM × strips/tiles | Pixel and P06 logs |
| Capacity checks | 512 TIFF pages and 512 GIF frames accepted; 513th-page append refused; counter preflight exercised | Pixel `CapacityTests` |
| Native engine/hull build | **4/4 native engines built; 6/6 hull faces succeeded** | `native_build.json`, retry and recovery logs |
| Complete Node/WebSocket suite | **146 passed, 6 skipped, 0 failed** across all 21 test files | `node_release/results.json` and TAP files |
| Native execution over authenticated WebSocket | Stale generation refused; pinned sealed witnesses agreed; **TICK_OK** | `node_release/ship-execution-observation.json` |
| Pixel-to-native execution | Edited 40 → tick result 41; edited 70 → R7 71 → TIFF cell 71 | `native_pixel_proof.json` |
| GIF and checkpoint | Exact logical GIF restoration; complete checkpoint archive preserved byte-for-byte | `native_pixel_proof.json` |
| Upstream data preservation | **7,167 original files unchanged**, including all 30 genesis TIFFs | `upstream_preservation.json` |
| Workflow local phase profile | Eight local test groups passed; P08 absent backend not run; nine full-source gates unpromoted | `tiff_profile_execution.json`, `phases/` |


Numbers represent distinct scopes, not a sum of independent test populations: the TIFF/GIF/kernel and workflow tests are included within the complete Python total. An independently generated fixture test covers eight storage/header combinations within one unittest case. Skips are not passes. The six skipped Node cases are the retained direct-Fabric adapter tests, whose expected standalone DF folder layout is absent; the containership-specific authenticated `ship` native-execution case did run and pass. The final fresh-extraction checks are reported separately in the companion `UC250_Release_Checks.zip`; no native build is claimed to ship with that extraction.

### Native pixel execution, not only codec round trips

The qualification script used the actual candidate CLI to set live DF_Small tile 0/word 0 to **40**, read it back, export it to GIF, restore a separate TIFF and verify exact logical state. Checkpoint preserved the entire old TIFF byte-for-byte and retained one unchanged live page. A real four-engine tick then returned **TICK_OK** and the edited cell became **41**.

A separate hull-native test set its actual TIFF-backed cell to **70**, executed the existing native VM, observed **R7 = 71**, and read **71** back from the resulting TIFF. The pre-test hull TIFF was restored in a `finally` block. This is concrete evidence that pixel edits reach native execution; it is not a general correctness proof for all VM programs. See `evidence/tiff/logs/native_pixel_proof.json` and the captured CLI logs.

### Bounded local workflow execution

The original workflow verifier passed: 325 components, 325,000 canonical tasks and 355 source files. All source task identities, full canonical rows, source prompts/workflows, component hashes and phase order are retained. Deep checking validates the original archive, every task-row binding, the execution ledger and all 325 component hashes.

The local phase-ordered execution profile ran tests in **P01–P07 and P09**, with zero local test failures. **P08 was not run** because COG/object-store/Zarr implementations are absent. P06's test is independent encoder interoperability, not a scientific production backend. P07's checks reject incompatible metadata; they do not implement Geo/OME/pyramids. Those distinctions are explicit in every phase's evidence and the component map.

**Full-source engineering disposition remains 325,000 BLOCKED; zero PASS/FAIL/reviewer-approved NOT_APPLICABLE. All nine full-source phase gates remain BLOCKED.** Seventy-four component mappings contain partial local implementation evidence; this is not 74 completed components. Individual task-specific qualification, acknowledged ownership and independent review were not fabricated. The source's broad cloud, scientific, SIMD and image-processing program is not claimed complete. See `tifflow/APPLICATION.json`, `tifflow/COMPONENTS.json`, `tifflow/ledger.jsonl.gz`, and `docs/tiff/WORKFLOW_APPLICATION.md`.

## Important implemented boundaries

The codec admits only the lossless RGBA8 PA21FABTIF/1 state profile. Classic TIFF/BigTIFF, both byte orders and strip/tile storage are checked within an **8 MiB file / 512-page** budget. BigTIFF header support does not mean multi-gigabyte processing. Inputs with malformed offsets, conflicting state metadata, duplicate/cyclic tags, unsupported pixel formats or excessive resource demands are refused before normal state reconstruction.

A minimal validated raster-only TIFF adapter resolves the tested Pillow big-endian BigTIFF limitation without patching the installed dependency. All emitted history pages are decoded and verified before same-directory replacement. Writers reject stale expected-file hashes. Full-history and counter exhaustion are preflighted before native ticks. Explicit checkpoints preserve complete old files rather than silently trimming history.

The native payload limit is **464 bytes / 58 u64 words per tile**, not the full 512 raster bytes. Pixel operations reject booleans, invalid addresses, over-capacity writes and implicit overflow. Multi-cell operations use a private copy. GIF frames encode exact logical state bytes, keep identical consecutive frames and restore to new offline TIFFs. GIF is not the live format; BRO1 framing is normalized to the guest-visible logical state, not preserved as arbitrary wrapper bytes.

Only read-only pixel inspection is available through VWS. Local write commands retain the existing workspace lock, generation fence, managed transaction and digest guard. Binary admission and hashes do not sandbox native codecs or authenticate hostile rewrites. Standalone optimistic file checks do not defeat malicious filesystem races. Rename is the commit point, and a post-rename synchronization failure can be reported after replacement. Native external side effects are not all rollback-able. Native-child CPU/memory quotas remain unenforced.

## Unsuccessful attempts retained in the evidence

The report does not present only successful final runs. `evidence/tiff/logs` retains the initial codec/CLI and interop failures that were fixed, as well as interrupted or improperly orchestrated qualification attempts.

1. Initial integration tests exposed validation ordering/import assumptions in temporary workspaces. The checks were fixed without weakening the original tests; the full original regression suite subsequently passed.
2. The first independent fixture run failed for both big-endian BigTIFF storage variants in the installed Pillow decoder. The raster-only adapter fixed that issue; all eight independent variants subsequently passed.
3. The first native build exceeded the execution environment's limit. The managed transaction was explicitly rolled back (`c314edd1f913498cb6687ca10a847669`). Retained, nontransactional compiled caches were reused on the successful retry; the retry was not represented as a clean-from-scratch rebuild. All four engines and six hull faces then succeeded. Logs and recovery evidence are retained.
4. An early full Node run was incorrectly launched concurrently with native execution in the same workspace. Two read-only e2e tests received the expected busy-lock refusal. That test orchestration was corrected; workspace protection was not removed. Explicit native-execution full-suite mode now serializes files. The final serial run's results supersede that failed attempt.
5. Another Node runner was externally interrupted after 20 of 21 file records. Its `complete:false` record is not counted as a complete suite, even though the remaining child later finished. A subsequent complete run supplies the final result.

There is no new all-berth long verification claim. UC-2.4.0's historical all-berth timeout remains historical, not an observed UC-2.5.0 pass. No public deployment or browser UI test was attempted as part of this patch.

## Performance observations, not a speedup claim

A deterministic 693-byte logical-state fixture produced a 982-byte Deflate TIFF and 1,505-byte reversible GIF. On the qualification host, 500 TIFF reads and 100 verified atomic writes per compression were measured. Deflate read median was approximately 0.499 ms and verified write median 1.077 ms. These are single-host microbenchmarks, not comparisons against UC-2.4.0 or throughput/service-level guarantees. Validating every history page adds work as history grows. The benchmark script and raw JSON are included; do not infer SIMD/GPU acceleration from these numbers.

## Reproduce and limits

Start with `docs/tiff/START.md`. `VERIFY_TIFF.cmd --deep` checks source integrity and the 100 pixel tests. `python -B -m unittest discover -s tests -v` runs the Python regression suite. `node vws/tools/test.js` runs the Node suite, with optional cases skipped unless explicitly enabled. A previously built native workspace and `UC_EXECUTION_TESTS=1` enable the native execution case; this mode now runs test files serially. Do not run these commands concurrently with another operation on the same workspace.

Qualification was on Linux, CPython 3.13.5, Pillow 12.3.0 and Node 22.16.0. Optional test-only encoders were NumPy 2.3.5 and tifffile 2026.5.15. Accepted runtime version ranges are not per-version certification. Windows launchers are supplied and text/path checked, but native Windows execution and actual browser interaction were not observed. The inherited nested DF_Xtra_Large engine archive reports a case-collision during build inspection; the source archive is preserved unchanged, so the main release's path scan must not be read as qualification of every nested payload on a case-insensitive filesystem.

No general GeoTIFF/OME, COG/Zarr/cloud/distributed backend, SIMD/GPU implementation, hostile-tenant isolation, quota enforcement, new universal TIFF editor, signing authority or production release approval is claimed. The original licenses, including the terminal's restrictive supplied notice, are retained; integration does not relicense them. All runtime credentials, build products and mutable test state are excluded from the release package.
