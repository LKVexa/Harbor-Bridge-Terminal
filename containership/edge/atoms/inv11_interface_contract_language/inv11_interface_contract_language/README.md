# INV-11 - Interface contract language

**Version:** 4.3.0 (see `CHANGELOG.md`)
**Group:** 01_Source_Inventory
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

The interface contract language is WIT: the typed vocabulary that says what crosses a component boundary. It is the only thing standing between two components written in different languages and a memory-safety incident, so compatibility here is structural and checked, never assumed from a version number.

## Responsibility

Own interface type definitions and compatibility: decide whether two versions of an interface can be linked by comparing their structure, and classify every change as compatible, breaking, or additive.

## Owns

- Interface type definitions and their structure
- Structural compatibility checking
- Change classification (additive, compatible, breaking)
- Version semantics for interfaces
- Refusal to link structurally incompatible interfaces

## Explicitly does not own

- Bindings generation
- Component linking
- Runtime marshalling
- Language-specific type mapping
- Placement

## Non-goals

- Generating language bindings
- Linking components
- Marshalling values at run time
- Inferring compatibility from a version string

## Interfaces

- `compare` - PK_INTERFACE_DIFF/1 - change class between two interface versions
- `define` - PK_INTERFACE/1 - a typed interface definition

## Service-level objectives

- **compatibility soundness** - zero links permitted between structurally incompatible interfaces (error budget: no budget)
- **classification accuracy** - every change classified before publication (error budget: no budget)
- **comparison latency** - p99 under 5ms per interface pair (error budget: 1% may exceed)

## Running it

The structural compatibility model is dependency-free. The production component
and contract require the external `pk_core` estate package.

```text
# Standalone structural unit tests (no pk_core required)
python -m unittest inv11_interface_contract_language.tests.test_model -v

# Full component conformance (requires pk_core; fails preflight with exit 2 if absent)
python inv11_interface_contract_language/tests/test_component.py

# Estate-level commands
python -m pk_core list
python -m pk_core run INV-11 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-11 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

Set `PK_CORE_PATH` when `pk_core` is installed outside the import path. See
`AUDIT_REPORT.md` for the 4.2.0 validation record and `MISSING_COMPONENTS.md`
for implementation gaps that remain beyond this reference model.

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-11`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-11`; a `NO_GO` verdict blocks the rollout, `CONDITIONAL_GO` requires the listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every change to the contract or implementation and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of
the component from the registry package, which the gate reports as a reduced
element count rather than a silent pass.

## 4.3.0 — WIT front end and production-completion workstreams

4.3.0 applies the 40-component production-completion checklist
(`conformance/COMPONENT_CHECKLISTS.md`) to this package. The 4.2.0 reference
model (`interface_model.py`, `component.py`, `contract.py`) is unchanged;
everything new lives in `wit/` (stdlib only):

| Layer | Module |
|---|---|
| source loader, lexer, parser, AST | `wit/source.py`, `wit/lexer.py`, `wit/parser.py`, `wit/ast.py` |
| identity + use/include/import resolver | `wit/resolve.py` |
| diagnostics, limits | `wit/diagnostics.py`, `wit/limits.py` |
| normalization, fingerprints, type graph | `wit/normalize.py`, `wit/typegraph.py` |
| compatibility policy + link check | `wit/compat.py` (`INV11-COMPAT-POLICY/1`) |
| schemas | `wit/schema.py`, `schemas/*.json` |
| differential testing vs wasm-tools 1.219.1 | `wit/differential.py`, `conformance/DIVERGENCES.json` |
| provenance, matrix, telemetry, audit, ownership | `wit/ops.py` |
| semver, deprecation, waivers, adapters, diff renderer | `wit/lifecycle.py` |
| release: reproducible zip, SBOM, provenance, signing | `wit/release.py` |
| benchmarks, soak, capacity fit | `wit/perf.py` |
| evidence bundle + verifier | `tools/evidence.py`, `tools/verify_evidence.py` |

```text
python -m inv11_interface_contract_language.wit check  path/to/package
python -m inv11_interface_contract_language.wit diff   old/ new/ --expanded
python -m inv11_interface_contract_language.wit export path/to/package    # PK_INTERFACE/1
cd inv11_interface_contract_language && python -B -m unittest discover -s tests -p "test_wit_*.py"
INV11_WASM_TOOLS=/path/wasm-tools python -B tools/evidence.py --out evidence
```

**Status of the checklist (builder's run, INV11-4.3.0-20260923T012827Z):** 1044 component items —
PASS 548, PARTIAL 159, DRAFTED 155, OPEN 72, BLOCKED 110.
All 40 component gates are BLOCKED (each needs an independent code/security
review record) and the production decision is **NO_GO** until the owner
reviews. `LEDGER.md` in the evidence directory lists every item with its reason.

Still owned elsewhere (unchanged): binding generation, component linking,
runtime marshalling, language-specific type mapping, placement.
