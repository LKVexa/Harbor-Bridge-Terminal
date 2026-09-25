# INV-13 Ownership, Incident and Escalation Package (MC-028)

> **Status: TEMPLATE WITH PLACEHOLDERS.** Named people, rotations and paging endpoints cannot be supplied by the build and must be filled in by the accountable organisation. Until then MC-028 remains **OPEN**.

| Role | Holder | Backup |
|---|---|---|
| Accountable owner (INV-13) | `<<NAME — LinearFinance.org Research Division>>` | `<<NAME>>` |
| Security reviewer (world/WIT changes) | `<<NAME>>` | `<<NAME>>` |
| On-call rotation | `<<rotation id / pager>>` | — |
| Release authority | `<<NAME>>` | — |

## Severity model
| Sev | Definition | Response | Example |
|---|---|---|---|
| S1 | Confirmed authority escape (guest reached undeclared capability/path/tenant) | page now; quarantine within 15 min | fs escape, SSRF to metadata |
| S2 | Control bypass without confirmed escape; audit chain verification failure | page, 1 h | verifier reports chain break |
| S3 | Degraded enforcement dependency (identity/attestation/policy store down → fail-closed outage) | business hours, 4 h | CONFIG_STALE spikes |
| S4 | Defect without security impact | ticket | metric misclassification |

## Runbooks
1. **Suspected escape (S1):** `ControlPlane.quarantine(<operator token>, <workload>, reason)` → revokes all root descriptors of the workload; `emergency_disable(<capability>)` if the vector is a provider; `freeze()` to stop policy mutation; export and verify the audit log (`audit_sink verify`); preserve `evidence/`.
2. **Bad policy/config release:** `ControlPlane.rollback_config(...)` (CAS re-point to previous digest); confirm `ConfigStore.active()`; open post-incident review.
3. **Audit verification failure (S2):** stop appends (sink refuses automatically), snapshot file, compare against last sealed checkpoint, rotate checkpoint key.
4. **Dependency outage (S3):** confirm the host is failing closed (denials classified `dependency`), restore the dependency, no manual bypass.

## Reviews and exceptions
* Access review of operator key holders: quarterly (`<<owner>>`).
* Policy/world review: on every change to `wit/` or policy bundles (gate: `APPROVED_SURFACE.json`).
* Exceptions/waivers: recorded in `EXCEPTIONS.json` with `id, item, approver, compensating_control, expires`; the release gate fails on any expired entry.
