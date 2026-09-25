# INV-12 - Language interoperability

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions, in `CHECKLIST.json`  
**Master prompts:** `MASTER.md` (the 100 per-item master prompt + workflow documents, carried verbatim for audit)

Language interoperability is the promise that components written in different guest languages can call each other without learning or aliasing one another's memory layout. Values are validated, lowered into an isolated canonical snapshot, and lifted into a detached receiver-owned value. Mappings that would lose information fail closed.

## Responsibility

Own canonical lifting and lowering across the language boundary: map interface types to guest-language representations, refuse lossy mappings, enforce explicit ownership transfer, and guarantee that mutable memory is not shared between components.

## Owns

- Canonical ABI lifting and lowering reference behavior
- Per-language exact-representation allowlists
- Refusal of lossy mappings
- Isolated canonical snapshots for data-only values
- Atomic single-transfer ownership semantics
- UTF-8 validity checks for strings and record keys
- Depth, item-count, node-count, and string-size guards for canonical payloads
- The no-shared-mutable-memory guarantee between components

## Explicitly does not own

- Compilers and toolchains
- Interface definitions / WIT authoring
- Composition linking
- Host function implementations
- Placement

## Canonical interop engine (new in 4.3.0)

`canon/` is a stdlib-only engine that closes the semantic core of the missing-components checklist
(MC-001 … MC-018) and the operational controls around it. It needs no `pk_core`:

```python
from inv12_language_interoperability.canon import load_interface, parse_type, encode, decode, Some, Ok
iface = load_interface(open("inv12_language_interoperability/fixtures/corpus/corpus.wit").read())
t = parse_type("list<option<result<string, color>>>", iface)
value = [None, Some(Ok("h\u00e9llo")), Some(Ok("x"))]
image, root = encode(value, t)          # validated, canonical-ABI memory image
decode(image, root, t)                  # bounds/alignment/UTF-8/discriminant checked lift
```

| Area | Module |
|---|---|
| Schema loader + type AST (WIT subset, s8…u64, char, tuple, enum, flags, own/borrow, future/stream) | `canon/types.py` |
| Recursive validator, schema-derived limits | `canon/validate.py`, `canon/limits.py` |
| Registry, numeric policy `exact/1`, Unicode policy | `canon/registry.py`, `canon/numeric.py`, `canon/text.py` |
| Canonical layout, flattening, variant wire model | `canon/layout.py` |
| Guest memory, checked realloc, post-return lifecycle | `canon/memory.py` |
| Resource handles, own/borrow, call scopes | `canon/resources.py` |
| Error envelope `PK_INTEROP_ERROR/1` + redaction | `canon/errors.py` |
| Negotiation + evolution | `canon/negotiation.py` |
| Futures / streams | `canon/async_model.py` |
| Metrics, traces, audit chain, health, capacity | `canon/observability.py` |
| Config schema + transactions + provenance, artifact policy + SBOM, capability gate + outage policy | `canon/config.py`, `canon/provenance.py`, `canon/trust.py` |
| End-to-end boundary (reference runtime adapter + Python binding) | `canon/boundary.py` |

Cross-language evidence: Rust, Go and JavaScript fixtures (`fixtures/`) reproduce every golden image
byte-for-byte and interoperate 16/16 producer→consumer pairs; a Go→`wasip1` guest runs in V8 and
exchanges values with the host through real linear memory (`tools/wasm_host.mjs`).

One command runs every gate: `python inv12_language_interoperability/tools/ci.py` (see `docs/OPERATIONS.md`).
Checklist execution record: `CHECKLIST_MC_STATUS.md`; traceability: `docs/TRACEABILITY.md`.

## Hardened boundary behavior (legacy API, since 4.2.0)

- `lower()` snapshots nested mutable values instead of retaining aliases.
- `lift()` produces a detached value and consumes canonical ownership exactly once.
- Ownership transfer is lock-protected, preventing a concurrent double-lift race.
- Custom Python objects are rejected rather than invoking arbitrary `__deepcopy__` hooks.
- Cyclic, over-deep, over-large, and invalid UTF-8 payloads are refused.
- Python `bool` cannot masquerade as an integer wire type.
- Declared `f32` values must already be exactly representable as IEEE-754 binary32; silent f64-to-f32 rounding is rejected.
- The JavaScript profile admits `s64`/`u64` as exact BigInt-backed mappings rather than Number-backed conversions.
- Public mapping tables are read-only.

Default reference limits are defined in `component.py`:

- nesting depth: 64
- items per container: 100,000
- total canonical nodes: 200,000
- UTF-8 bytes per string/key: 16 MiB
- UTF-8 bytes per owner identifier: 256

These are reference-model safety ceilings, not a substitute for schema-derived production limits.

## Interfaces

- `lift` - `PK_CANONICAL_LIFT/1` - canonical value lifted into a guest representation
- `lower` - `PK_CANONICAL_LOWER/1` - guest value lowered into canonical storage
- `mapping` - `PK_TYPE_MAPPING/1` - per-language representation of an interface type

## Service-level objectives

- **no loss** - zero values silently truncated or re-encoded lossily (error budget: no budget)
- **no sharing** - zero bytes of mutable linear memory shared between components (error budget: no budget)
- **boundary cost** - p99 lowering+lifting under 2us for scalar values (error budget: 1% may exceed)

The latency SLO now has a reproducible harness (`tools/bench.py`, `evidence/bench.json`). Native Rust/Go fixtures meet it (scalar p99 well under 2 µs); the Python reference does not, and the production runtime path is not yet measurable here, so the SLO is certified only as a native proxy. See `MISSING_COMPONENTS.md`.

## Running it

```text
python inv12_language_interoperability/tools/ci.py                # all engine gates, evidence/ci_run.json
python -m unittest inv12_language_interoperability.tests.test_canon
python inv12_language_interoperability/tests/test_component.py   # set PK_CORE_PATH if pk_core is elsewhere
python -m pk_core list
python -m pk_core run INV-12 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-12 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an interface without a schema reference; W7 refuses to certify while any requirement is blocked; W9 refuses to close out unless the evidence chain is intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0 (bootstrap):** import the package, run `pk_core run INV-12`, and archive the emitted evidence ledger as the baseline.
- **Day 1 (deployment):** run `pk_core gate INV-12`; a `NO_GO` verdict blocks rollout, while `CONDITIONAL_GO` requires listed conditions to be accepted and recorded.
- **Day 2 (operation):** re-run the gate on every contract or implementation change and verify the ledger chains onto the previous head.

Rollback is the previous sealed evidence head; emergency disable is removal of the component from the registry package, which the gate reports as a reduced element count rather than a silent pass.

## Audit artifacts

- `AUDIT.md` - findings, repairs, validation, and residual risk (4.2.0 and 4.3.0 passes).
- `MISSING_COMPONENTS.md` - per-component status after the 4.3.0 pass.
- `CHECKLIST_MC_STATUS.md` - the 3,550-item professional checklist, executed and annotated.
- `docs/` - SPEC, ADR, threat model, traceability, compatibility matrix, runbook, incident playbook, operations.
- `evidence/` - machine-readable gate results and the sealed `RELEASE_EVIDENCE.json`.
