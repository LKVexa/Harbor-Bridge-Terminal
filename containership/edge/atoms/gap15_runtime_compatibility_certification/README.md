# GAP-15 - Runtime compatibility certification

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 04_Gap_Subsystems  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

Runtime compatibility certification answers a heterogeneous edge-estate question: will this exact artifact run on this exact runtime and node profile? The component certifies only from recorded evidence and returns **untested** rather than inferring support from a similar runtime or profile.

## Responsibility

Own the runtime compatibility matrix: certify an artifact against a runtime and node profile from tested evidence only, distinguish incompatible from untested, expire positive certifications, and enforce runtime lifecycle state.

## Owns

- Compatibility matrix state and matrix revision
- Certification verdicts and evidence timestamps
- The distinction between incompatible, untested, expired, and end-of-life
- Positive-certification expiry
- Runtime deprecation and end-of-life state
- Deterministic `PK_COMPATIBILITY_MATRIX/1` and `PK_RUNTIME_LIFECYCLE/1` views

## Explicitly does not own

- Running compatibility tests
- Building artifacts
- Rollout sequencing
- Node capability probing
- Runtime implementations

## Core interfaces

- `CompatibilityMatrix.certify()` -> `PK_CERTIFICATION/1`
- `CompatibilityMatrix.matrix_view()` -> `PK_COMPATIBILITY_MATRIX/1`
- `CompatibilityMatrix.lifecycle_view()` -> `PK_RUNTIME_LIFECYCLE/1`

Every certification verdict includes the environment, matrix revision, legacy string triple, and typed artifact/runtime/profile coordinates. A positive certification also includes `tested_at`, `expires_at`, and `age`.

## Security and integrity behavior

- Exact triples only; profile similarity is never treated as evidence.
- Future-dated evidence fails closed as `untested`, whether the recorded result is compatible or incompatible.
- Older test evidence cannot overwrite newer evidence.
- Contradictory evidence at the same timestamp is rejected.
- Exact same-timestamp/same-result replay is idempotent and does not advance matrix revision.
- Lifecycle regression (for example `end-of-life -> supported`) requires explicit `allow_reactivation=True`.
- Invalid identifiers, control characters, boolean timestamps, negative timestamps, malformed stored records, and unknown lifecycle states fail closed.
- Requested coverage is calculated over unique triples so duplicate requests cannot distort the metric.

## Service-level objectives

- **no inference** - zero certified verdicts without a recorded test result (error budget: no budget)
- **expiry** - zero expired positive certifications treated as current (error budget: no budget)
- **eol enforcement** - zero rollouts certified onto an end-of-life runtime (error budget: no budget)

`CERTIFICATION_TTL_SECONDS` is currently `500`; the older `CERTIFICATION_TTL` name is retained as a compatibility alias.

## Running the checks

From the parent directory containing this package and `pk_core`:

```text
python gap15_runtime_compatibility_certification/tests/test_component.py
python -O gap15_runtime_compatibility_certification/tests/test_component.py
python -m pk_core list
python -m pk_core run GAP-15 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate GAP-15 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

Set `PK_CORE_PATH` if `pk_core` is stored elsewhere. The package's tests intentionally skip the `pk_core`-dependent suite when that dependency is not importable rather than fabricating a pass.

## Day-0 / day-1 / day-2

- **Day 0:** load the package, establish the initial matrix/lifecycle revision, run the GAP-15 gate, and archive the evidence ledger.
- **Day 1:** require a deployable `PK_CERTIFICATION/1` verdict for the exact artifact/runtime/profile triple before rollout admission.
- **Day 2:** re-run the gate on contract or implementation changes, re-test expired certifications, review lifecycle transitions, and verify the evidence ledger chain.

Rollback is the previous sealed evidence head. Emergency disable is removal of the component from the registry package, which the gate should report as a reduced element count rather than a silent pass.

## Source-material note

The v4.1.0 README claimed a bundled `MASTER.md`, but that file was not present in the supplied archive. v4.2.0 removes that inaccurate claim. `CHECKLIST.json` is the only bundled 100-item source checklist. The absent source master document is tracked in `MISSING_COMPONENTS.md` rather than being reconstructed and represented as verbatim source material.

## Audit artifacts

- `AUDIT_REPORT.md` - findings, fixes, verification, and residual risk
- `MISSING_COMPONENTS.md` - components not present in this archive that are still needed for production-grade runtime compatibility certification
- `MANIFEST.sha256` - deterministic SHA-256 checksums for the shipped files (integrity aid only; not a cryptographic signature)

## Production layer (v4.3.0)

v4.3.0 executes the *Missing Components — Professional Engineering Checklist v1.0.0* against this
package. The v4.2.0 reference model is unchanged; `production/` adds a stdlib-only certification
service built around one pure verdict function (`production/state.py::certify`) fed by an append-only,
hash-chained ledger in a durable SQLite store.

```text
python -B gap15_runtime_compatibility_certification/tools/run_checklist.py      # run all tests + execute the checklist
python -m gap15_runtime_compatibility_certification.production.cli verify --db data/gap15.db
python -m gap15_runtime_compatibility_certification.production.serve --config cfg.json --development
```

Status of the 1,040 controls is in `evidence/CHECKLIST_EXECUTION.md` (per control, with evidence or a
named blocker) and the 100-row traceability matrix in `evidence/RTM.md`. Headline: 541 controls
locally verified by passing tests, 294 blocked on things this build cannot supply (HSM/KMS, real GAP-02/GAP-07/
GAP-08 services, replication, a fleet, CI, named owners, independent review, the original MASTER.md),
exit gate **NO_GO**. A production start without a KMS/HSM key provider is refused by design.
