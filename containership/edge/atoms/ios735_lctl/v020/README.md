# iOS735 → LCTL v0.2.0

The iOS735 skeleton (the Swift L3 of the iOS735_VEC1 stack) translated into LCTL, using the two corpora you supplied:

- **LCTL 1.6.1-RC1 (LCTL-C 1.0)** is the source language. Every unit is written in the 8-column form and lowered by its compiler.
- **LCTL 1.6.0-RC1** independently verifies each lowered canonical unit, and its causal-DAG, parallel-plan and provenance tools ran on every unit.

## v0.2.0 missing-components closure

This release executes the v0.1.1 missing-components checklist (M01–M09). The payload is unchanged. What is new, and what is still waiting on the owner, is tracked in [`CLOSURE_STATUS.md`](CLOSURE_STATUS.md); run `python tools/release.py preflight` for the live gate state.

- **Toolchain trust (M01/M04):** `toolchains/LOCK.json` pins both LCTL JARs and the Java policy. `tools/verify.py` authenticates them **before** any execution. The pins are `PENDING_OWNER_APPROVAL`, so the full verifier currently refuses to run; this is by design. See [`docs/TOOLCHAIN_PROVISIONING.md`](docs/TOOLCHAIN_PROVISIONING.md).
- **Evidence acceptance (M02):** `tools/evidence_check.py` decides whether a `VERIFY/2` run is acceptable release evidence.
- **CI (M03):** `owner-toolchain-verify.yml` is a privileged full-verifier workflow for protected branches, tags and manual runs.
- **SBOM, signing, provenance (M07/M08):** `tools/sbom.py` and `tools/release.py`. See [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md).
- **Schemas (M09):** [`schemas/`](schemas/README.md) contains the map, `VERIFY/2` and lock schemas, plus a stdlib validator in `tools/schema_check.py`.
- **Owner decisions (M05/M06 and inputs for M01/M03/M04/M08):** [`docs/OWNER_DECISIONS.md`](docs/OWNER_DECISIONS.md).

## License

No license has been granted yet. The owner has not chosen one (M05), so no reuse, modification or redistribution rights are stated. The external LCTL toolchains and the Java runtime are governed by their own terms.

## v0.1.1 hardening

This release hardens the translator and verification harness without changing the generated LCTL-C, canonical LCTL, or translation-map payload bytes from v0.1.0. That preserves the bundled owner-toolchain verification evidence while making future regeneration and verification stricter.

- `tools/translate.py` now validates the exact project shape and Swift/runtime parity before writing, writes atomically, and supports `--out` for isolated deterministic regeneration.
- `tools/check_translation.py` validates the entire canonical unit set and `TRANSLATION_MAP.json`, plus emitted metadata that the original checker did not cover. `--falsify` now exercises nine independent corruption cases.
- `tools/verify.py` now stages canonical/evidence outputs transactionally and requires compile, canonical verification, causal-DAG, parallel-plan, provenance, column-stats, and the independent translation check to pass before committing generated outputs.
- `tests/test_offline_integrity.py` and `.github/workflows/offline-integrity.yml` provide dependency-free regression coverage on Windows and Linux without requiring the external LCTL toolchains.
- `MANIFEST.sha256` plus `tools/manifest.py` provide deterministic SHA-256 integrity coverage for every release file.

The repository release version is recorded in `VERSION`. The embedded `proof=ios735-lctl:0.1` tag inside generated LCTL is retained as a payload compatibility/provenance tag; changing it would require regenerating canonical output with the owner LCTL compiler.

## What is here

| Path | Contents |
|---|---|
| `source/P01_…lctlc` … `P43_…lctlc` | 43 phase modules. Each component is one `@frame`, chained by `tick`/`prev` in boot order |
| `source/IOS735_APP.lctlc` | The application unit: 43 phase frames, the P01→P43 boot chain, and a SHA-256 seal of each phase module |
| `canonical/*.lctl` | The sealed canonical LCTL/1.3 the 1.6.1 compiler lowered (17,481 rows, 822 frames) |
| `map/TRANSLATION_MAP.json` | Per component: unit, row prefix, contract hash, family, and all 25 controls with status and text hash |
| `evidence/VERIFY.json`, `evidence/lctl160/` | Per-unit gate results and the 1.6.0 causal-DAG / parallel-plan / provenance output |
| `tools/translate.py` | Swift skeleton → LCTL-C (deterministic) |
| `tools/verify.py` | Runs both LCTL toolchains over every unit, then the round-trip check |
| `tools/check_translation.py` | Reads canonical LCTL and the translation map back and compares them with the Swift sources/control ledger |
| `tests/test_offline_integrity.py` | Dependency-free regression tests for round-trip integrity, falsifiers, repository shape, and byte determinism |
| `input/iOS735_Skeleton/` | The parts of the skeleton the translation and checker read |
| `MANIFEST.sha256` | SHA-256 digest inventory for all release files (self-entry excluded) |
| `AUDIT_REPORT.md` | Post-update audit findings and remaining external/release gaps |
| `CLOSURE_STATUS.md` | Item-by-item M01–M09 closure status |
| `toolchains/LOCK.json` | Owner toolchain trust lock (pins pending) |
| `schemas/` | JSON Schemas for the map, `VERIFY/2` and the lock |
| `sbom/` | SPDX 2.3 SBOM (DRAFT until pins and license exist) |
| `tools/toolchain_trust.py`, `evidence_check.py`, `schema_check.py`, `sbom.py`, `release.py` | Trust, evidence acceptance, schema validation, SBOM, release/provenance/signing |
| `tests/test_release_hardening.py`, `tests/fixtures/simtoolchain/` | 44 closure tests. The simulator is test-only |
| `docs/` | Provisioning, release process, owner decisions |

## How a component translates

| iOS735 (Swift) | LCTL row(s) |
|---|---|
| Component contract | `REG` region: type, phase, layer, family, visibility, `owner=UNASSIGNED`, 25 controls, `complete=0`, control-status counts; the contract SHA-256 goes in the PROOF cell (the same hash the VEC1 Photons bind) |
| `LifecycleState` (9 states) | 9 `EVENT` rows |
| `Lifecycle.transitions` | 1 `DEP` row, 21 edges (the 1.6.0 causal DAG consumes them) |
| `CompositionRoot` boot order | `FUTURE` awaits: each component waits on the previous one's `.active`; phases chain in the app unit |
| Data ownership | `MEMORY_DOMAIN`, owner UNASSIGNED, source of truth left as a product decision |
| `ComponentError.classify` | `FAILURE_DOMAIN`: 10 codes → domain / disposition |
| `QualityBudget` | `CAPACITY`, `approval=proposed` |
| Declared capabilities | `DEVICE`, gated "declared and justified before request" |
| Required hardware + fallback | `DEVICE`, with the fallback |
| Family clauses x.21–x.25 | 5 rows on a family-specific op (e.g. wire contract → `CLASSICAL_CHANNEL`, sync merge → `CONSISTENCY_SCOPE`, background mode → `TIMEOUT`, reproducible build → `SCHEDULE_SEAL`), each carrying its evidence need and the checklist text's hash |

## Results

- **LCTL 1.6.1** `column-verify`: 44/44 PASS. `column-compile`: 44/44.
- **LCTL 1.6.0** `verify` of the lowered canonical units: 44/44 PASS (`execution_class=SYMBOLIC`, `physical_qpu=false`, `quantum_boundary=NOT_CROSSED`).
- **Round trip:** 735/735 components read back from canonical LCTL and `TRANSLATION_MAP.json` match the Swift skeleton. That covers contract hash (also equal to the stack's `Golden.swift`), region/status metadata, lifecycle edges/events, error map, state domains, budgets, capability gates, hardware/fallbacks, family clause operators/evidence hashes, completion counts, boot order, phase composition, and source seals.
- **Falsifiers:** all 9 caught — a dropped lifecycle edge, swapped disposition, claimed completion, deleted component, reordered boot, approved budget, weakened capability gate, corrupted family metadata, and corrupted translation-map contract hash. Separately, editing one canonical row made the 1.6.0 verifier fail with `FRAME_SEAL: mismatch`.
- **Size:** LCTL-C is 2.63 MB against 5.19 MB lowered, 49.4 % smaller, in line with the 1.6.1 corpus's own 52 %.
- **Determinism:** re-running the translator produces byte-identical sources.

Offline integrity check (no external LCTL toolchain required):
`python -m unittest discover -s tests -v`

Full owner-toolchain re-verification:
`python tools/verify.py --lctl161 <LCTL_1.6.1 folder> --lctl160 <LCTL_1.6.0 folder>`. It needs Java 21, Python 3.10+ and **approved pins in `toolchains/LOCK.json`**. Then run `python tools/evidence_check.py`.

## Limits of the translation

- **It is structural, not behavioural.** LCTL is a quantum/classical execution language. Its executable ops are quantum gates and measurements, and it has no classical arithmetic on bit registers (the verifier refuses `X` on `c[0]`). So the iOS components become LCTL regions, events, dependencies, domains and capacities, which the verifier seals and the causal DAG analyses. There is no executable work: 1.6.0 reports `work=0 span=0`. Nothing was forced into quantum gates to fake behaviour.
- **One inert qubit per unit.** LCTL refuses any unit without a quantum register, so each unit declares `q[1]`, tagged `p=ios735:inert-anchor` and never used.
- **Checklist text is referenced, not carried.** LCTL-C has no comments, and its argument grammar forbids `;` and `=` inside values. The 25 controls of each component are therefore carried as counts, as 5 hashed clause rows, and in full in `map/TRANSLATION_MAP.json`.
- **LCTL checks less than it looks like.** Probing both runtimes showed the verifier does **not** reject cyclic `DEPENDENCY` edges or `FUTURE`s that await a nonexistent event. That is why `check_translation.py` exists: the translation's semantics are checked there, not by LCTL alone.
- **Family carrier ops are my choice.** Only about 99 metadata ops are verifier-accepted without an explicit face, and none were designed for app requirements. The mapping is in `translate.py` (`FAMILY_OP`).
- **Nothing moved toward completion.** 0 of 18,375 controls are complete, as in the skeleton.
