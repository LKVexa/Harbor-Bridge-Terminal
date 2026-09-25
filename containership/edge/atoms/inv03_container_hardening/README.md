# INV-03 - Container hardening

**Version:** 4.3.0 (see `CHANGELOG.md`)  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`  
**Audit:** `AUDIT_REPORT.md`  
**Open gaps:** `MISSING_COMPONENTS.md`

INV-03 provides a fail-closed pre-admission hardening evaluator for container workload specifications. It refuses workloads that do not satisfy the baseline controls and can honor narrowly scoped, time-limited exceptions only when the exception record is well formed.

## Implemented baseline

The 4.2.0 evaluator enforces five controls:

1. `non-root` - a root/UID-0 or empty user is refused.
2. `read-only-root` - `readOnlyRootFilesystem` must be literal `true`.
3. `not-privileged` - `privileged` must be explicitly present and literal `false`; omission fails closed.
4. `drop-all-capabilities` - capabilities must be structured, must drop `ALL`, and must add none.
5. `seccomp` - profile must be `RuntimeDefault` or `Localhost`.

The policy registry is immutable at runtime, control order is deterministic, malformed top-level inputs are converted to denials rather than evaluator crashes, and results identify the schema and baseline version used.

## 4.3.0 at a glance

4.3.0 applies the 70-component *Professional Engineering Checklist* to this package. The 4.2.0 evaluator
(`policy.py`, `PK_HARDEN_EVAL/1`) is kept byte-identical as the legacy baseline. The new stdlib-only runtime
under `hardening/` evaluates a Kubernetes-shaped PodSpec against **16 controls** (`PK_HARDEN_EVAL/2`):
sandbox runtime class, non-root with UID-resolution proof, read-only root, not-privileged,
no-privilege-escalation, drop-ALL capabilities, seccomp (Localhost profiles digest-registered),
host namespaces, user namespaces, host devices, host mounts/sockets/propagation, kernel surface
(sysctls, procMount), AppArmor/SELinux, writable-volume allowlist, resource limits and
default-deny networking, applied to init, app and ephemeral containers.

Around it: HMAC-signed baselines with epoch-CAS activation, last-known-good cache and rollback;
tighten-only tenant/environment/site overlays; an exception authority rebuilt from a hash-chained,
sealed audit ledger (approver identity, separation of duties, TTL cap, renewal limit, sweep);
a trusted clock that fails closed; authentication and deny-by-default authorization; a Kubernetes
validating-webhook adapter (`failurePolicy: Fail`); runtime inventory with version floors and
downgrade refusal; drift reconciliation, quarantine plans and a deny-all emergency switch; metrics,
redacting structured logs, W3C trace context, and an explain object on every decision.

| Where | What |
|---|---|
| `hardening/` | runtime (controls, baseline, authority, engine, admission, runtime, integrations, telemetry, core) |
| `schemas/` | JSON Schema 2020-12 for EVAL/2, BASELINE/2, EXCEPTION/2 |
| `tests/test_h_*.py` | 72 tests: controls, integrity, engine/adapter, fuzz/concurrency/adversarial/perf/faults, schemas, gate |
| `fixtures/` | 13 valid/invalid PodSpecs with hand-declared expected results |
| `tools/` | `release_gate.py`, `mutation_probe.py` (10/10 planted defects killed), `recurring_review.py`, `build_status.py` |
| `docs/` | runbooks, incident playbook, ADR-0001 (PROPOSED), SLA, backup/restore, ownership (UNASSIGNED) |
| `CHECKLIST_STATUS.json` | per-component status, evidence and blockers for all 70 components |
| `RELEASE_GATE.json` | the last gate run — **NO_GO** |

### Honest status

**0 of 70 components complete.** 51 LOCAL_VERIFIED (built and tested here), 12 PARTIAL, 7 BLOCKED.
Completion needs cluster integration evidence and a named human approver, and neither exists in this
archive. Blocked: 35 Key-management integration (C047-C048); 46 Real `pk_core` dependency pin and full conformance run (C082, C090); 47 Orchestrator integration tests (C030, C083); 48 Runtime/architecture compatibility matrix tests (C084); 55 Named accountable owner and escalation path (C009, C097); 56 Approved architecture decision record (C010); 69 `MASTER.md` source artifact.

Run the gate: `python3 -B tools/release_gate.py` (exit 3 = NO_GO with evidence recorded).

## Evaluation result (legacy 4.2.0 evaluator, `policy.py`)

`evaluate(workload, spec, exceptions, today)` returns a dictionary containing:

- `schema` - `PK_HARDEN_EVAL/1`
- `baseline_version` - baseline/package version used for the decision
- `workload` - normalized workload identifier
- `admit` - `true` only when no control or interface error remains
- `failed` - failed, unexcepted control names
- `excepted` - failed controls covered by active exceptions
- `input_errors` - malformed interface inputs that force denial

## Exception rules

An exception is honored only when it is scoped to the exact workload/control, has a non-blank reason, has a real integer expiry strictly after evaluation time, and is not revoked. Boolean values are not accepted as integer timestamps. Legacy tuple-keyed exceptions are retained for compatibility, and JSON-safe nested, composite-key, and list encodings are also accepted.

## Responsibility

Own the container hardening baseline, fail-closed input validation, pre-admission evaluation, named findings, recorded expiring exceptions, and baseline versioning.

## Explicitly does not own

- Image content scanning
- Runtime intrusion detection
- Kernel configuration
- Image building
- Authorization policy implementation

Integration hooks to those systems are still required for a complete production platform; see `MISSING_COMPONENTS.md`.

## Interfaces

- `baseline` - `PK_HARDEN_BASELINE/1`
- `evaluate` - `PK_HARDEN_EVAL/1`
- `exception` - `PK_HARDEN_EXCEPTION/1`

## Testing

From the folder containing this package:

```text
python -m compileall -q inv03_container_hardening
python inv03_container_hardening/tests/test_policy.py
python -O inv03_container_hardening/tests/test_policy.py
python inv03_container_hardening/tests/test_component.py
```

`test_policy.py` has no `pk_core` dependency and tests the security-critical evaluator directly. `test_component.py` exercises framework conformance when `pk_core` is available; it intentionally skips rather than reporting a false pass when the dependency is absent.

## Current production-readiness boundary

*(4.2.0 text, kept for history — see "4.3.0 at a glance" and `CHECKLIST_STATUS.json` for the current state.)*

This archive was not yet a complete container-isolation platform. In particular, it does not yet enforce a gVisor/runsc runtime class, host namespace/device/mount restrictions, `allowPrivilegeEscalation=false`, signed baseline distribution, a persistent exception authority, live runtime drift detection, a real admission-controller adapter, or full observability/certification infrastructure. Those gaps are enumerated and prioritized in `MISSING_COMPONENTS.md`.

## Day-0 / day-1 / day-2

- **Day 0:** install/pin `pk_core`, run the dependency-free policy suite, validate the 100-item checklist, then run framework conformance.
- **Day 1:** integrate the evaluator with the orchestrator/admission layer and refuse deployment when the production gate is not satisfied.
- **Day 2:** re-run conformance on every baseline or implementation change, monitor policy decisions and exception expiry, and reconcile runtime state against admission state.

Rollback is to the previously approved baseline/package release. Emergency disable must be implemented in the surrounding orchestration layer; a production-grade mechanism is still listed as an open component.
