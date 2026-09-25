# PLN-02 - Application plane

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 02_Synthesis_Planes  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

> **Source-archive note:** the v4.1.0 README said that `MASTER.md` was carried in
> the package. The supplied archive did not contain that file. v4.2.0 removes
> the false presence claim and records `MASTER.md` as a post-audit missing
> artifact in `MISSING_COMPONENTS.md` rather than reconstructing source text that
> was not supplied.

The application plane describes an application as a composition of portable
components and the capabilities they require. It resolves a declared
composition against an environment provider catalogue and refuses to publish a
revision when required capabilities or imported interfaces cannot be satisfied.

## v4.3 production controls (missing-components work order)

v4.3.0 executes `PLN02_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md` against this package. The
resolver's v4.2 semantics and revision identity are unchanged; new controls wrap it.

| Module | Closes | What it does |
|---|---|---|
| `service.py` | wiring | `ApplicationPlaneService.submit()` / `.admin()` — the fail-closed request pipeline |
| `errors.py` | MC-14 | stable error registry, `PK_ERROR/1` public documents, redaction |
| `context.py` | MC-13, MC-26 | tenant/env/site context, deadlines, cancellation, idempotency, bounded safe retry |
| `versioning.py` | MC-04 | supported-major windows, negotiation, adjacent-layer matrix |
| `admission.py` | MC-05 | payload bound, token-bucket quotas, fair concurrency, shedding, circuit breaker |
| `trust.py` | MC-11, MC-18, MC-21 | key ring (HMAC-SHA256 / optional Ed25519), rotation, bearer tokens, artifact attestations |
| `secret_refs.py` | MC-18 | `secret://` references, inline-secret refusal, redaction, fail-closed secret store |
| `catalogue.py` | MC-27, MC-06 | signed `PK_SIGNED_CATALOGUE/1` client, freshness, rollback refusal, leased offline cache |
| `policy.py` | MC-07, MC-12, MC-28 | entitlements, fixed constraint precedence, explainable deterministic selection |
| `store.py` | MC-25, MC-24 | atomic fenced revision store, supersession, rollback, freeze/disable/quarantine, backup/restore |
| `audit.py` | MC-22 | hash-chained, MAC'd append-only audit ledger |
| `config.py` | MC-17 | `PK_PLANE_CONFIG/1`, overlays, provenance digest, atomic activation, last-known-good rollback |
| `oam.py` / `wit.py` | MC-09 / MC-10 | OAM v1beta1 subset adapter; WIT subset parser + structural compatibility checker |
| `observability.py` | MC-23, MC-30 | metrics (cardinality-capped), JSON logs, W3C trace context, health/readiness, stall watchdog |
| `tools/gate.py`, `tools/traceability.py`, `tools/bench.py` | MC-08, MC-36, MC-29/35 | fail-closed release gate, traceability matrix, perf/soak harness |

Status of all 39 items (`TRACEABILITY.json`, verified by the gate): **17 IMPLEMENTED · 15 PARTIAL ·
4 BLOCKED_OWNER · 3 BLOCKED_EXTERNAL.** Gate verdict: **NO_GO**, by design, until the owner decisions
(MASTER.md source, ADR approval and named owners, governance evidence, licence) and external evidence
(deployment isolation, CI matrix, fleet environment, live peers) exist. See `docs/OVERHAUL_REPORT.md`.

```text
python -m unittest discover -s pln02_application_plane/tests -p "test_*.py"        # 88 tests, 3 pk_core skips
python -m pln02_application_plane.tools.gate --tier local --out pln02_application_plane/evidence/gate_local.json
python -m pln02_application_plane.tools.bench --soak 60 --out pln02_application_plane/evidence/perf_baseline.json
```

## Responsibility

Own the application model: resolve a declared composition of components and
required capabilities into a satisfiable, versioned application revision, or
reject it with a typed refusal that identifies the unsatisfied condition.

## Owns

- The application model and component composition graph
- Capability requirement resolution against providers
- Deterministic, content-addressed application revision identity
- Interface compatibility checks between composed components
- Rejection of unsatisfiable, ambiguous, or malformed compositions

## Explicitly does not own

- Where a component runs
- The runtime that executes a component
- Capability provider implementations
- Network transport between components
- Desired state of the estate

## Interfaces

- `PK_APPLICATION/1` - versioned application declaration
- `PK_PROVIDER_CATALOGUE/1` - versioned provider catalogue
- `PK_APPLICATION_REVISION/1` - immutable-by-publication resolved revision

JSON Schemas are in `schemas/`. Reference request fixtures are in
`tests/fixtures/`.

## Resolver API

The low-level Python API remains compatible with v4.1 callers:

```python
from pln02_application_plane import resolve, verify_revision

revision = resolve(components, edges, catalogue)
verify_revision(revision)
```

For externally visible versioned contracts, use `resolve_document`:

```python
from pln02_application_plane import resolve_document

revision = resolve_document(application_document, provider_catalogue_document)
```

`resolver.py` has no `pk_core` dependency. The `pk_core` conformance adapter in
`component.py` and contract builder in `contract.py` are loaded only when those
integration surfaces are requested.

## v4.2 resolver hardening

- Strict input validation and fail-closed rejection of unsupported fields
- Duplicate component and duplicate edge rejection
- Every declared import must have exactly one producer
- Unknown edge endpoints and interface mismatches return typed failures
- Capability requirement flags must be boolean
- Provider identifiers and all identifiers are bounded and validated
- Component names exclude the `:` binding-key delimiter to prevent namespace collisions
- Composition limits: 200 components, 4,096 edges, 4,096 catalogue entries,
  128 capabilities per component, and 128 imports/exports per component
- Canonical JSON encoding rejects non-finite/non-canonical values
- Full SHA-256 revision addresses (64 hex characters)
- Revision identity now covers normalized component capability/interface
  specifications, closing the v4.1 interface-version collision class
- Provider binding digest is recorded in the revision
- `verify_revision()` detects post-resolution mutation
- Structured Python errors expose stable error codes and machine-readable detail
- The resolver does not mutate caller-owned input objects

The returned Python revision is a dictionary for compatibility. Immutability is
therefore a publication/storage responsibility; `verify_revision()` provides an
integrity check before execution or persistence.

## Running tests

From the directory containing `pln02_application_plane`:

```text
python -m unittest discover -s pln02_application_plane/tests -p "test_*.py" -v
python -O pln02_application_plane/tests/test_resolver.py
```

The resolver suite is stdlib-only except for one optional JSON Schema
conformance test. `tests/test_component.py` additionally requires the external
`pk_core` package. In the supplied standalone archive, those `pk_core` tests
skip rather than pretending integration conformance has been proven.

## pk_core gate commands

When the compatible `pk_core` estate is available:

```text
python -m pk_core list
python -m pk_core run PLN-02 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate PLN-02 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

W0 refuses to lock context on an incomplete contract; W4 refuses to integrate an
interface without a schema reference; W7 refuses to certify while any
requirement is blocked; W9 refuses to close out unless the evidence chain is
intact and all 100 requirements have been answered.

## Day-0 / day-1 / day-2

- **Day 0:** import the package, run the standalone resolver tests, then run
  `pk_core run PLN-02` in the full estate and archive the evidence ledger.
- **Day 1:** run `pk_core gate PLN-02`; do not roll out a `NO_GO`. Record and own
  every condition associated with a conditional gate.
- **Day 2:** re-run tests and the gate on each contract or implementation change;
  verify the evidence ledger chains to the expected previous head.

v4.3 adds a reference revision store, catalogue client, policy engine and governance documents. What still
needs owner decisions or external evidence is listed per item in `TRACEABILITY.json` and `docs/OVERHAUL_REPORT.md`.
