# Unikernel Containership — UC-2.2.0 Audit and Repair Report

**Release:** UC-2.1.3 → UC-2.2.0  
**Assessment date:** September 21, 2026 (America/Los_Angeles); execution evidence is timestamped September 22 UTC.  
**Disposition:** locally validated, ship-layer hardened development skeleton. **Not a production-isolated or native-bootable unikernel platform.**

## 1. Scope and preserved material

The supplied ZIP contains 7,341 files (56,226,825 expanded bytes). Its source SHA-256 is `0c110e435d1abd3d5b30e04bc02c641260c0414cf5ba328946f7cd39a4aae461`. The original upload was retained unchanged. The audit inspected the ship orchestration implementation, launchers, schemas and release inventory; parsed the outer and nested Python/JSON material; reproduced lifecycle flaws in disposable directories; built and exercised the native engines and hull; and added targeted negative tests. This is not a line-by-line security certification of every embedded C, VM or hull implementation.

UC-2.2.0 repairs the Python ship layer and root launchers, adds reusable safety helpers, diagnostics and tests, and refreshes release metadata/documentation. The original `hull/` (24 files), `hold/` (14 files) and six `berths/` trees (7,153 files) are preserved byte-for-byte. Historical conformance artifacts, including cargo `_fabric` paths, are retained. New live runtime state, compiled caches and audit-test backup generations are not delivery payloads. No license grant was invented: the original LICENSE and ownership terms are preserved.

The release has the short extraction root `UC220/`. It is a **fresh full-source package, not an in-place updater**. Extract beside, not over, an existing workspace to protect local edits. Embedded component version labels are intentionally unchanged; older conformance results are historical evidence, not newly executed claims.

## 2. What actually exists

The system provides a local Python management layer, four classical VM engines, script-to-slot sorting, six delivered project berths, a hull language-studio runtime, metadata/witness programs, checksums/seals and reversible TIFF-backed state. The repaired layer validates local inputs and handles ordinary failures more safely.

It does not contain a guest boot chain or a demonstrated library-OS-linked application image. It does not create a hypervisor security boundary, enforce `NETWORK=deny` at the OS, supply tenant authentication or turn the four local engines into separate distributed failure domains. `CARGO.pal` is a row-sequence witness derived from cargo metadata; successful execution of that witness is not translation or semantic execution of arbitrary Python, C or Java cargo. See `SECURITY.md` and `MISSING_COMPONENTS.md` before interpreting architectural names as implemented guarantees.

## 3. Observed validation

| Activity | Observed outcome |
|---|---|
| Original outer release checksums / inventory | Both pass; 7,340 checksummed files, 7,339 inventory entries, with explicit self-exclusions. |
| Outer source parse | 111 Python and 3,776 JSON files; zero parse errors. |
| Outer plus five nested hold ZIPs | 328 Python and 7,415 JSON parse instances; zero parse errors. Repeated packaged implementations are counted as instances, not unique sources. |
| Baseline build | All four engines, executable hull and six hull faces built successfully. |
| Baseline inherited verification | 19 ship-level PASS; recursive 83 PASS, 0 FAIL, 8 SKIPPED. |
| New regression suite | **128/128 PASS**, including negative and injected-failure tests. |
| Actual ZIP/load/native integration | **18/18 checks PASS**. |
| Candidate native build | **4/4 engines and 6/6 hull faces**, executable hull; no reported build problems. |
| Candidate inherited full verification | **19 ship-level PASS; recursive 83 PASS, 0 FAIL, 8 SKIPPED**. |
| Package qualification boundary | Final source re-seal, fresh archive extraction, doctor and regression checks are recorded separately in external handoff evidence. They do not constitute a second native verification run. |

The execution host was Linux x86-64, CPython 3.13.5, with Pillow 12.3.0 and the available C/make/Java toolchain. These installed versions describe the observed environment, not a vulnerability-clearance statement or recommended immutable production dependency set.

### Skips are not passes

The eight nested skips are B8 on the two subsystem berths, which carry no runnable native sample in the gate's supported dialects, and B11 on all six berths, which carry no studio-container descriptor pair to mount as hull cargo. The ship's top-level 19/19 PASS does not erase these eight missing exercises. The independent hull runtime and all six generated hull faces were nevertheless built and exercised through their own gates. `verify --require-complete` now blocks any nested SKIPPED result; its conservative policy is covered by four direct result-contract tests. A richer required/optional/not-applicable qualification matrix remains backlog work.

### High-value negative evidence

In disposable baseline fixtures, `unload('../outside')` removed a sibling directory, and replacement using an invalid source removed the original berth. Both unsafe outcomes were reproduced before repair and covered by regression tests afterward.

The integration ZIP contained eight distinct logical files, including `A.py`/`a.py`, `AUX.py`, a long nested path, both `CARGO_MANIFEST.json` casing variants and `_Alias/keep.py`. All eight byte streams survived admission and aliasing, the new berth sums verified, its native witness ran, and its reference witness was then deliberately altered. Even after recomputing file checksums, sealed execution correctly refused the inconsistent reference with exit code 3. The fixture was unloaded and the six original active berths remained.

Unit tests use mocks where controlled failure injection is required; real multiprocess locking and actual Pillow round trips are also exercised. Native integration and full inherited verification are separate from those unit contracts. An early integration harness used `--no-studio` while requesting a gate requiring a hull face; that setup correctly failed B9. The harness was corrected to normal registration and rerun successfully. Earlier attempt logs are not relabeled as passing evidence.

## 4. Finding ledger and repairs

Severity is relative to a trusted-operator local development deployment, not a CVSS score or certification. FIXED means the named defect was addressed, not that the entire surrounding subsystem is production complete. PARTIAL identifies the exact remaining boundary.

### UC-A01 — Unscoped berth lifecycle paths

**HIGH · FIXED**  
**Locations:** `ship/unikernel/berth.py; cli.py`

**Finding:** Baseline unload with ../outside deleted an isolated sibling directory.

**Applied:** Validate names and resolve contained paths before berth operations. Reject links/reparse points and unsafe components.

**Evidence:** Traversal and reserved-name regression cases.

**Remaining boundary:** The host filesystem and cooperating operator remain trusted; not race-proof against a privileged concurrent writer.

### UC-A02 — Destructive replacement before admission

**HIGH · FIXED**  
**Locations:** `ship/unikernel/berth.py`

**Finding:** Baseline replacement with a nonexistent source removed the existing isolated berth.

**Applied:** Stage, verify and swap; retain the previous generation; attempt rollback on ordinary pre-commit failure.

**Evidence:** Missing-source, staged failure, swap failure and journal fault tests.

**Remaining boundary:** Cross-resource recovery spanning registry, seal, hull and TIFF state remains partial.

### UC-A03 — ZIP admission and cross-platform loss hazards

**HIGH · FIXED**  
**Locations:** `ship/unikernel/safety.py; berth.py; engines.py`

**Finding:** Archive extraction had no explicit count/expanded-size/ratio policy and no complete duplicate/special-entry admission. Ordinary extractall sanitization is not claimed universally vulnerable to traversal.

**Applied:** Preflight canonical members, limits, encryption, links, duplicates and file/directory conflicts; stream flat staged blobs before portable aliasing.

**Evidence:** Archive rejection suite and actual eight-file ZIP/native integration.

**Remaining boundary:** Native payloads are still trusted; the input budget is not a global storage or CPU quota.

### UC-A04 — Slot-run bypasses ledger identity and failure result

**HIGH · FIXED**  
**Locations:** `ship/unikernel/cli.py`

**Finding:** A supplied path could bypass intended cargo lookup; alias/wrong-slot and native failure handling were insufficient.

**Applied:** Require a unique ledger entry in the requested slot, contained path, matching size and digest; propagate failed native halts.

**Evidence:** Original-path and alias resolution, wrong-slot, untracked, modified-byte and failed-result tests.

**Remaining boundary:** A registered file is not proof its behavior is safe; real guest isolation remains absent.

### UC-A05 — Sealed result does not enforce its pinned witness

**HIGH · FIXED**  
**Locations:** `ship/unikernel/cli.py; tif_fabric.py`

**Finding:** Sealed success did not consistently require matches_pinned or a valid pre-execution reference contract.

**Applied:** Validate parsed program seal, row count and witness before execution; require the pinned match in the final result.

**Evidence:** Actual successful native run, then deliberately changed reference plus recomputed file sums is refused with exit 3.

**Remaining boundary:** These checks cover the executed witness program, not arbitrary cargo-language semantics.

### UC-A06 — Incomplete pin and checksum admission

**HIGH · FIXED**  
**Locations:** `ship/unikernel/engines.py; ucmanifest.py; gates.py`

**Finding:** Missing hold pins and malformed checksum records could be accepted or confused with host limitations.

**Applied:** Require all five hold pins, reject malformed/duplicate/escaping checksum records and preserve parser failures as failures.

**Evidence:** Missing-pin, invalid digest, duplicate, traversal and strict parser tests; full rebuild and native gates.

**Remaining boundary:** A local hash is not an independently authenticated publisher signature; mutable caches remain a trust boundary.

### UC-A07 — Hull reassembly paths and mount ownership

**HIGH · PARTIAL**  
**Locations:** `ship/unikernel/hullmount.py`

**Finding:** Reassembly and mount names lacked consistent path confinement and ownership protections; corrupt registry could silently appear empty.

**Applied:** Constrain paths/names, verify cargo bytes, reject unowned replacement and unreadable registry; write ownership atomically.

**Evidence:** Mount ownership and registry corruption regression tests; full hull and face integration.

**Remaining boundary:** Carried-key enrollment is operator trust, not external release authorization; full transactional mount rollback is not implemented.

### UC-A08 — Tick success overstates executed agreement

**HIGH · FIXED**  
**Locations:** `ship/unikernel/tif_fabric.py`

**Finding:** Success could overlook required hull/replay/mount/native outcomes.

**Applied:** Require participating engine, fabric, requested hull and requested mount execution, pinned agreement and replay success for TICK_OK.

**Evidence:** Native B10 differential, chained, painted-tick and painted-declaration cases across all six delivered berths.

**Remaining boundary:** Agreement is local deterministic execution, not fault-independent consensus or workload correctness.

### UC-A09 — Manifest inventory inconsistencies

**MEDIUM · FIXED**  
**Locations:** `ship/unikernel/ucmanifest.py`

**Finding:** Inventory verification did not comprehensively enforce duplicate entries, counts and aggregate bytes.

**Applied:** Validate entry identity, size/hash, file count, total bytes and absence of extra included files; reject included nonregular filesystem objects.

**Evidence:** Manifest duplicate/count/total/escape and FIFO/link cases.

**Remaining boundary:** Duplicate-key-safe JSON and complete canonical schema migrations are still roadmap work.

### UC-A10 — Stale berth inventory after final unload

**MEDIUM · FIXED**  
**Locations:** `ship/unikernel/ucmanifest.py; registry.py`

**Finding:** Empty berth lists could leave old manifest berth metadata in place.

**Applied:** Always rewrite berth list, even when empty, and current release identity on reseal.

**Evidence:** Last-berth reseal regression; final package inventory verification.

**Remaining boundary:** Historical seal lineage is preserved and intentionally retains older release evidence.

### UC-A11 — Checksum self-reference in new berth metadata

**MEDIUM · FIXED_FOR_NEW_LOADS**  
**Locations:** `ship/unikernel/berth.py`

**Finding:** BERTH.json attempted to retain a digest of the sums file that subsequently binds BERTH.json.

**Applied:** Omit this circular field in newly generated BERTH.json; bind current sums externally in the bill of lading.

**Evidence:** New-load integration verifies no self-reference and valid berth sums.

**Remaining boundary:** Historical delivered berth artifacts are retained byte-for-byte, not silently rewritten.

### UC-A12 — Concurrent mutation and truncated writes

**MEDIUM · PARTIAL**  
**Locations:** `ship/unikernel/safety.py; registry.py; ucmanifest.py; tif_fabric.py`

**Finding:** Independent writers and direct metadata/image replacement risk interleaving or truncating state.

**Applied:** Serialize cooperating commands with an OS-released lock and use same-directory fsync/replace for core metadata and ship TIFF updates.

**Evidence:** Multiprocess lock contention; atomic write failures preserve prior bytes.

**Remaining boundary:** No all-resource commit protocol or arbitrary host-writer protection; some diagnostic output files remain direct writes.

### UC-A13 — Invalid numeric inputs and weak CLI error contracts

**MEDIUM · FIXED**  
**Locations:** `ship/unikernel/cli.py`

**Finding:** Negative, enormous or non-finite inputs and inconsistent errors could produce misleading behavior.

**Applied:** Bound ticks/scale/interval/steps; restrict program names; emit stable nonzero error categories with diagnostic logs and preserve interrupts.

**Evidence:** NaN/infinity/zero/range/program/error/interrupt tests and wrapper inspection.

**Remaining boundary:** No externally versioned management API, full subprocess supervision or universal deadline contract yet.

### UC-A14 — Windows path and generated-namespace collisions

**MEDIUM · FIXED**  
**Locations:** `ship/unikernel/berth.py; root CMD launchers`

**Finding:** Case/normalization differences, Windows device names, long paths and cargo metadata names could overwrite or obstruct generated content.

**Applied:** Preserve logical names in a ledger; alias portable collisions and generated namespaces; quote Windows launch paths and retain exit status.

**Evidence:** Case-pair, AUX, long-path, CARGO_MANIFEST case-pair and _Alias integration with all original bytes intact; static package path checks.

**Remaining boundary:** Native Windows and macOS execution has not been observed; runtime toolchains and root path length still matter.

### UC-A15 — Unbounded TIFF history and partial writes

**MEDIUM · PARTIAL**  
**Locations:** `ship/unikernel/tif_fabric.py`

**Finding:** Append/read operations lacked explicit ship-level byte/page/geometry/sidecar budgets.

**Applied:** Enforce 8 MiB, 512 pages, fixed raster and bounded sidecar on ship-managed state; atomically replace files and close frames.

**Evidence:** Real Pillow codec append/read/limit/error-preservation tests and native B9/B10.

**Remaining boundary:** Embedded hull decoder entry points, initial allocation, rollover, global disk quotas and multi-picture atomicity remain incomplete.

### UC-A16 — Top-level PASS can hide nested skipped coverage

**MEDIUM · PARTIAL**  
**Locations:** `ship/unikernel/cli.py`

**Finding:** The inherited ship summary can show no skips while nested berth gates are skipped for absent sample types.

**Applied:** Add --require-complete, recursively refusing any SKIPPED gate, with failure taking precedence.

**Evidence:** Four result-policy tests; actual full verification preserves all nested skip evidence.

**Remaining boundary:** This is deliberately conservative, not a required/optional/not-applicable production qualification classifier.

### UC-A17 — Missing real unikernel execution and independent trust boundary

**RELEASE_BLOCKER · OPEN**  
**Locations:** `Architecture; guest backend; host runtime; release process`

**Finding:** No bootable guest, hypervisor isolation, OS-enforced deny-network, multi-tenant identity, external release authentication or multi-host consensus was identified.

**Applied:** Document actual capability limits in doctor, SECURITY.md and the 96-item theory-derived roadmap. No simulated completion claims.

**Evidence:** Local capability report explicitly reports these features false.

**Remaining boundary:** Requires new guest/build/isolation/lifecycle/security components; UC-2.2.0 remains a trusted local skeleton.

## 5. Compatibility and operating changes

Use `DOCTOR.cmd`, `SELFTEST.cmd`, `BUILD.cmd`, `VERIFY.cmd` and `RUN.cmd` from an already-open Command Prompt. Their exit status is preserved rather than swallowed; paths are quoted and UTF-8 is explicit. Set `PYTHON` to a usable interpreter path when `python` resolves only to a Store alias. The Windows Launcher equivalents are documented in README_START_HERE.md. No execution-policy, registry, administrator or automatic external package-install change is introduced.

Name validation is stricter. Ambiguous or unsafe input is refused rather than silently normalized. ZIP aliases preserve logical cargo identity instead of relying on case-sensitive disk behavior. Unload is intentionally recoverable: old cargo goes to `_runs/backups/` and therefore continues consuming space. Failed staged operations retain useful journals instead of fabricating success. `doctor` reports pending transaction journals.

Core atomic replacement protects an individual file or berth generation; the registry, ship seal, mounted hull and multiple live pictures are not a single transaction. Do not delete unexplained journals, use `seal` to hide a failure, or reset TIFF history to conceal disagreement. Back up the complete workspace before manual generation recovery.

Local admission bounds are 50,000 entries, 64 MiB per file, 1 GiB per admitted archive/eligible directory cargo and a large-member compression ratio of 1,000:1. Ship TIFF handling is bounded to 8 MiB and 512 pages at its guarded entry points. These are refusal bounds, not a comprehensive resource manager. Automatic history rollover, aggregate storage quota, backup retention, hard native CPU/memory limits and log quotas are not implemented.

## 6. Completion roadmap and architectural basis

`MISSING_COMPONENTS.md` and its JSON companion define **96 gaps in 12 workstreams**, with stable IDs, priority, missing/partial status, dependencies, a concrete implementation target and an acceptance test. `phases/P01.md` through `P12.md` provide the same workstream content as individual files. The dependency graph has 96 unique nodes, no missing dependency targets and no cycles.

The first release target should be one real guest: a chosen workload plus one engine linked with selected OS functionality, built for one defined guest target, booted under an actual isolation backend, tested by its application output, stopped and checkpointed/restored. Keep the ship outside as the management plane. Unikraft's library-OS architecture and Solo5's separation of guest ABI from host runtime support that distinction; Firecracker's production host guidance explains why merely selecting a VMM is not a complete isolation policy. OCI is an optional artifact/runtime interoperability choice, not proof that current berths are OCI containers. SLSA and TUF provide supply-chain and update-trust design references, not certifications earned by a checksum file. Primary source URLs, source IDs and access date are retained in THEORY_SOURCES.json and the roadmap.

The milestones are A: reliable local control plane; B: a genuine bootable guest; C: isolated, operable single-host containership; D: independently qualified optional multi-host federation. An offline single-guest release does not need to wait for optional network services, an OCI registry or distributed consensus. Conversely, a multi-host claim must not be made from same-process or same-host replicas.

## 7. Residual risks and unobserved tests

Production isolation is not established. Runtime cache and engine imports/native binaries remain trusted local code. Carried hull keys do not establish an external publisher identity. Complete fail-safe transaction recovery, race-free hostile filesystem access, duplicate-key-safe canonical JSON, all-resource quotas, authenticated management, real guest boot, isolation, supervision, semantic workload certification and independent release/update trust remain open.

No native Windows/macOS execution, hypervisor boot, hostile multi-tenant deployment, full power-loss campaign, comprehensive C memory-safety review, coverage-guided parser fuzzing, current dependency CVE clearance or multi-host failure/partition campaign was performed. Filename portability tests and Linux execution are not substitutes for those tests. Formal proofs, production GO and certification are not asserted.

## 8. Evidence and reproducibility

Run `python -X utf8 -B uc.py self-test` for the new ship regression suite. Run `BUILD` and then `VERIFY` for native construction and the inherited full gate battery. `doctor` is a local prerequisite/integrity check and must not be substituted for those native gates. The native integration result files identify the commands used; the bounded fixture experiment was performed in the audit workspace, not against the user's live installation.

`reports/audit-2.2.0/` includes native build/full-verification JSON, new integration JSON, the unit-test log, source parse evidence, reproduced baseline failures and the consolidated test summary. `SOURCE_CHANGES.patch` is the human-reviewable ship implementation diff; `AUDIT_FINDINGS.json` is the machine-readable finding ledger. An external evidence bundle contains baseline and candidate logs, final source comparison and clean-package checks. Its package SHA-256 lives outside the archive to avoid a self-referential package digest. Local hashes detect byte changes but are not externally authenticated signatures.

**Release decision:** UC-2.2.0 is an improved, locally tested continuation of the supplied skeleton. Use it as a trusted development foundation and implementation baseline for the explicitly incomplete roadmap, not as a ready multi-tenant unikernel host.
