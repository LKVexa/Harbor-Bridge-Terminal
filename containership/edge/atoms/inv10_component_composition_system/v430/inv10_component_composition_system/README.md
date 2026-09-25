# INV-10 — Component composition system

**Version:** 4.3.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Master prompts:** `MASTER.md` retains the 100 per-item master prompt + workflow documents for audit.

INV-10 links application units by matching declared imports to exactly one declared export, or to an explicitly declared external interface. A successful composition is internally closed, deterministically ordered, and content-addressed from the complete normalized composition graph.

## Responsibility

Own component linking: satisfy every import from a declared export or refuse the composition, detect dependency cycles, expose external imports explicitly, and produce a deterministic content-addressed composition identity.

### Owns

- Component import/export declarations at the linker boundary.
- Link resolution across one composition.
- Duplicate-provider refusal.
- Dependency-cycle detection, including self-cycles.
- Closure computation and external-import reporting.
- Canonical composition identity generation.
- Deterministic provider and binding metadata.

### Explicitly does not own

- Wasm/module validation.
- Deep interface type compatibility checking.
- Runtime instantiation.
- Host-function implementations.
- Placement/scheduling.
- Artifact signature or provenance verification.

## 4.2.0 hardening changes

The linker implementation is now isolated in dependency-free `composition.py`. The `pk_core` checklist adapter remains in `component.py` and is lazy-loaded by the package.

The 4.2.0 linker:

- rejects self-dependency cycles instead of silently deleting the self-edge;
- hashes the full canonical unit/import/export/binding graph rather than only component names, order, external imports, and export names;
- uses the full SHA-256 digest instead of a 96-bit truncation;
- labels the new digest semantics as `PK_COMPOSITION_ID/2` while retaining the additive `PK_COMPOSITION/1` response schema;
- validates names and interface identifiers for type, emptiness, surrounding whitespace, Unicode NFC normalization, control/format characters, and length;
- enforces bounded component/interface/resource counts before graph construction;
- emits structured, machine-readable composition errors;
- returns explicit `providers` and `bindings` metadata;
- keeps deterministic ordering independent of input sequence;
- can be imported for linker-only use without `pk_core` installed.

> **Identity migration note:** composition IDs produced by 4.2.0 intentionally differ from 4.1.0 because the old digest omitted material graph state. Persisted 4.1.0 IDs should be treated as legacy identifiers and recomputed before cross-version equality checks.

## Core API

```python
from inv10_component_composition_system import Unit, compose

units = [
    Unit("store", frozenset(), frozenset({"wasi:kv/store"})),
    Unit("api", frozenset({"wasi:kv/store"}), frozenset({"wasi:http/handler"})),
]

result = compose(units)
```

A successful result contains the compatibility fields `components`, `order`, `external_imports`, `exports`, `composition`, `schema`, and `closed`, plus the additive hardening fields `providers`, `bindings`, `digest_algorithm`, and `identity_profile`.

### Structured failures

All linker failures derive from `CompositionError` / `ValueError` and expose `as_dict()` with a stable code, message, and details:

- `INVALID_COMPOSITION`
- `UNSATISFIED_IMPORT`
- `AMBIGUOUS_EXPORT`
- `COMPOSITION_CYCLE`
- `RESOURCE_LIMIT_EXCEEDED`

### Resource ceilings

`CompositionLimits` defaults to bounded ceilings for component count, per-component interface count, declared external imports, total interface references, and identifier length. Callers may supply a stricter immutable `CompositionLimits` instance.

## Interfaces

- `component` — `PK_COMPONENT/1` — a component with typed imports and exports.
- `compose` — `PK_COMPOSITION/1` — an internally closed composition with explicit external imports.
- composition identity profile — `PK_COMPOSITION_ID/2` — canonical SHA-256 over normalized unit and binding state.

## Service-level objectives from the contract

- **closure** — zero compositions published with an unsatisfied internal import (no error budget).
- **determinism** — identical component graphs produce an identical composition ID (no error budget).
- **link latency** — p99 under 200 ms for 200-component compositions (1% error budget).

The archive does not yet contain the benchmark/evidence package required to certify the latency objective; see `MISSING_COMPONENTS.md`.

## Validation

Linker-only tests require only the Python standard library:

```text
python tests/test_linker.py
python -O tests/test_linker.py
```

The checklist/evidence conformance test requires the sibling `pk_core` package:

```text
python tests/test_component.py
```

If `pk_core` lives elsewhere, set `PK_CORE_PATH` before running it. In the standalone archive used for this audit, `pk_core` is not bundled, so the three `pk_core` conformance tests skip rather than producing false certification evidence.

## pk_core workflow

When this package is placed beside a compatible `pk_core` installation:

```text
python -m pk_core list
python -m pk_core run INV-10 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-10 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an interface without a schema reference; W7 refuses to certify while any requirement is blocked; W9 refuses to close out unless the evidence chain is intact and all checklist requirements have been answered.

## Day 0 / Day 1 / Day 2

- **Day 0:** import/test the package, run the linker unit suite, then run `pk_core run INV-10` in the full repository and archive the evidence ledger.
- **Day 1:** run `pk_core gate INV-10`; do not roll out on `NO_GO`, and record explicit conditions for any `CONDITIONAL_GO` result.
- **Day 2:** re-run linker tests and the gate on every contract or implementation change; verify evidence-chain continuity before promotion.

Rollback for the checklist/evidence layer is the previous sealed evidence head. Application-level rollback, registry rollback, and persisted composition-ID migration are not implemented in this standalone archive and remain listed as missing components.

## Audit artifacts

- `AUDIT_REPORT.md` — findings, fixes, validation performed, and residual risk.
- `MISSING_COMPONENTS.md` — prioritized inventory of production components not present after this hardening pass.
- `MANIFEST.sha256` — SHA-256 hashes for archive contents (excluding the manifest itself).

## 4.3.0 layout

| Module | Covers |
|---|---|
| `composition.py` | pure linker (unchanged from 4.2.0) |
| `schemas.py`, `schemas/` | PK_COMPONENT/1, PK_COMPOSITION/1, manifest schemas |
| `manifest.py` | declarative manifest loader |
| `wit.py` | WIT worlds -> units |
| `adapters.py` | INV-09 / INV-11 / INV-12 / PLN-02 ports |
| `governance.py` | context, link policy, provenance, external resolver |
| `security.py` | keys, authentication, audit trail |
| `observability.py` | metrics, logs/tracing, health, explain |
| `controlplane.py` | registry, store, activation, config ledger, admission, service, quarantine |
| `features.py` | incremental, aliasing, dead-export elimination, nesting, diff, migration |
| `cli.py` | `inv10 compose|explain|diff|migrate|wit|schema-check|version` |

Run everything: `python -m unittest discover -s inv10_component_composition_system/tests -t inv10_component_composition_system/tests`
Gate evidence: `python tools/gen_evidence.py` · Benchmark: `python tools/bench.py`
