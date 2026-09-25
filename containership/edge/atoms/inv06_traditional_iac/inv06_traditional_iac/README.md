# INV-06 - Traditional IaC

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Package-local schemas:** `schemas/PK_IAC_PLAN_1.schema.json`, `schemas/PK_IAC_STATE_1.schema.json`, and `schemas/PK_IAC_DRIFT_1.schema.json`

INV-06 models traditional infrastructure-as-code as a serial-bound plan/apply state machine. A plan is computed from authoritative state, sealed with a deterministic SHA-256 integrity digest, and may be applied only to the exact state serial against which it was generated. Protected-resource policy changes also advance the serial, stale or structurally invalid plans fail closed, and apply replaces state atomically after full validation.

## 4.3.0 production-component layer

The 72 missing components from the 4.2.0 audit were worked through with the Professional-Grade Missing-Component Checklists. Package-local references now exist for 48 of them, as standard-library modules with tests:

| Module | Components |
|---|---|
| `durable.py` | MC-010 durable state, MC-012 WAL/recovery, MC-013 rollback, MC-014 backup/restore/migration |
| `locking.py` | MC-011 lease + fencing |
| `graph.py`, `config.py` | MC-016 parser/compiler, MC-017 graph, MC-024 overlays, MC-025 provenance |
| `policy.py` | MC-009 precedence, MC-022 GAP-13 gate, MC-023 INV-01/07/08 handoffs |
| `security.py` | MC-033 authn, MC-034 authz, MC-036 signing/verification, MC-037 tenancy, MC-039 outage policy, MC-040 signed audit, MC-041 redaction |
| `resilience.py` | MC-021 offline queue, MC-026 retry/idempotency, MC-027 admission/breaker, MC-028 degraded, MC-029 failover, MC-030 freeze, MC-031 watchdog |
| `observability.py` | MC-043 – MC-048 |
| `execution.py` | MC-015 engine runner, MC-018 provider pins, MC-019 provider contract, MC-035 sandbox, MC-064 platform check |
| `release.py` | MC-051 – MC-054, MC-062, MC-063, MC-069 |
| `service.py` | `ControlPlane`, the single wired change path |

Run everything and regenerate evidence:

```text
python inv06_traditional_iac/tests/test_production.py
python inv06_traditional_iac/tools/build_status.py path/to/PROFESSIONAL_COMPONENT_CHECKLISTS.md
```

Current gate verdict: **NO_GO**. See `evidence/PRODUCTION_GATE.json` and `EXECUTION_REPORT.md`. The package does not claim production readiness. Its durable backend and lock are single-host. Real cloud and datacenter adapters, KMS, the CI test farm, edge power measurement, and owner sign-offs are still outstanding.

## Responsibility

Own the reference semantics for plan computation, state serials, in-process locking, stale-plan refusal, drift detection, destroy protection, structured failure reporting, and package-local conformance behavior.

## Owns

- Plan computation and structural validation
- State serials and in-process synchronization
- Stale-plan refusal
- Protected-resource policy and serial invalidation
- Atomic in-memory apply
- Drift detection with explicit present/missing semantics
- Deterministic plan integrity digests
- Structured error codes/details
- In-memory metrics and tamper-evident audit chaining

## Explicitly does not own

- Cloud/provider API calls
- Terraform/HCL parsing or execution
- Durable or distributed state storage
- Distributed locks/leases or consensus
- Identity, authorization, secrets, KMS, or certificate infrastructure
- CI/CD and GitOps synchronization

Those production components are tracked in `MISSING_COMPONENTS.md`.

## State-engine safety properties

- `resources` returns a detached copy; callers cannot bypass the serial by mutating the authoritative dictionary.
- `protected` is exposed as a `frozenset`; protection changes go through `protect()`/`unprotect()` and advance the serial.
- Resource values must be JSON-compatible and finite, enabling deterministic validation and hashing.
- Plans carry `schema`, `serial`, create/update/delete operations, and an integrity digest.
- Plan schemas are validated fail-closed, including unknown/missing fields, operation overlap, duplicate deletes, invalid identifiers, unsupported schema versions, and digest mismatch.
- Apply holds an `RLock` across serial validation, state matching, next-state construction, commit, serial advancement, metrics, and audit recording.
- Drift distinguishes a missing resource from a resource whose legitimate value is JSON `null`.
- Audit events contain operation metadata rather than resource values and are chained by SHA-256 digests. This is an in-memory integrity mechanism, not a durable signed audit service.

## Running standalone tests

From the directory containing `inv06_traditional_iac`:

```text
python inv06_traditional_iac/tests/test_component.py
```

The state-engine tests have no third-party dependency. If `pk_core` is not importable, only the two parent-framework conformance tests are skipped and the standalone tests still execute.

## Running the parent `pk_core` gate

When this package is placed in the full Post-Kubernetes workspace and `pk_core` is importable:

```text
python -m pk_core list
python -m pk_core run INV-06 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-06 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

The isolated archive does **not** bundle `pk_core`, so a 100/100 parent-framework certification cannot be independently reproduced from this ZIP alone. `AUDIT_REPORT.md` records that limitation.

## Day-0 / day-1 / day-2

- **Day 0:** import the package, run the standalone unit suite, provide the approved `pk_core` dependency, and establish the first parent-framework evidence ledger.
- **Day 1:** run the parent gate before deployment; preserve the resulting evidence and the exact component/dependency versions used.
- **Day 2:** re-run standalone and parent gates on every implementation/contract change and verify evidence continuity.

## Source-package note

The prior README referred to a `MASTER.md` file containing the per-item master prompts/workflows, but that file is not present in the supplied archive. The documentation no longer claims it is bundled; restoration of the authoritative source document is tracked as `MC-001` in `MISSING_COMPONENTS.md`.
