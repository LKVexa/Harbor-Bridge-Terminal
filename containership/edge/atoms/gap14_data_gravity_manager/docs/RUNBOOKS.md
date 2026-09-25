# GAP-14 v4.3.0 — Release, Incident and Lifecycle Runbooks (G14-P2-40)

Roles are named by function; the people filling them are recorded in `../OWNERS.md` (currently **unassigned** — assigning them is a certification prerequisite, not something this package can do).

| Role | Responsibility |
|---|---|
| Service owner (SO) | GAP-14 correctness, releases, config authority requests |
| Security reviewer (SR) | trust store, key rotation, incident classification |
| Operations owner (OO) | on-call, probes, dashboards, game days |
| Release approver (RA) | signs the certification decision |

## Severity

| Sev | Definition | Page | Examples |
|---|---|---|---|
| SEV-1 | possible illegal placement or audit loss/tamper | SO + SR + OO immediately | `G14_AUDIT_CHAIN_BROKEN`; a handoff executed without a matching `decision.issued` |
| SEV-2 | decision path down or fail-closed for most tenants | OO, SO within 15 min | readiness failing; breaker open on GAP-13 |
| SEV-3 | degraded latency / drift | OO next business hours | SLO burn; drift alarm |

## RB-01 Decision path not ready
1. `health()` → read `checks` and `dependencies`. 2. Config false → activate last known-good revision (`rollback`). 3. Breaker open → check the named dependency's health; do **not** lower TTLs or disable verification to recover. 4. Success check: `ready: true`, refusals rate back to baseline.

## RB-02 Audit unavailable / chain broken (SEV-1 if broken)
1. Stop traffic (no decisions are returned without audit, so this is containment of availability only). 2. Preserve the audit file read-only; copy with hash. 3. `python -m gap14_data_gravity_manager verify-audit <file> --keys <keys>` → note `at_seq`. 4. Broken chain: SR opens incident; compare with PLN-06 received handoffs for the affected sequence range. 5. Restore: start a new audit file whose first record references the last verified head (`verify_chain(..., start_head, start_seq)`), record the gap in the incident. Success check: verify passes on both segments.

## RB-03 Fail-closed surge (security / stale-data)
1. Group `gap14_refusals_total` by code. 2. `G14_SIGNATURE_INVALID`/`G14_UNKNOWN_ISSUER` → key rotation mismatch or tampering: SR verifies trust store vs producer keys. 3. `G14_STALE_INPUT`/`G14_CLOCK_SKEW` → producer lag or NTP. 4. `G14_VERSION_ROLLBACK` → producer restored from backup; only the producer owner may confirm, then restart GAP-14 to reset watermarks (watermarks are per-process memory). Success: code rate returns to baseline.

## RB-04 Latency SLO burn
1. Compare `gap14_dependency_latency_seconds` by dependency vs `gap14_decision_latency_seconds`. 2. If GAP-14 CPU-bound: check threads-per-process (DESIGN R-2); scale processes. 3. Re-run `tools/bench.py` on the node type. Success: p99 < 50 ms for 1 h.

## RB-05 Rollback (game day: quarterly)
1. Config: `rollback(prev_revision, now, actor)`; confirm `config.rolled_back` in audit. 2. Code: redeploy previous artifact; verify `MANIFEST.sha256`. 3. Run `verify-audit` across the boundary. Success: decisions resume; chain verifies end-to-end.

## RB-06 Drift / calibration
1. `record_outcome` report → which dimension alarmed. 2. Ship a candidate model as `shadow_model`; watch `gap14_shadow_divergence_total`. 3. Canary 5 % → 25 % → 100 % over ≥ 3 days; residency cannot be affected by any model (I2). Success: drift alarm clears on new model revision.

## RB-07 Restore evidence from backup
1. Restore audit file(s) and `release_evidence.json`. 2. Verify file hashes against the backup manifest. 3. `verify-audit`. 4. Record restore in incident. Exercise: semi-annual.

## Deprecation and EOL
* Schema versions: announce deprecation ≥ 2 minor releases ahead; emit warning logs for deprecated schema tags; reject only after measured usage of the old version is **zero for 30 days** (usage from `gap14_refusals_total` / request logs) — the migration gate.
* Package EOL: 12 months after the successor's GA; security fixes only in the final 6.

## Exercise record

| Exercise | Cadence | Last run | Evidence |
|---|---|---|---|
| Tabletop: illegal placement / audit loss (E01) | semi-annual | **not yet run** | — |
| Game day: rollback (E02) | quarterly | **not yet run** | — |
| Restore evidence (E03) | semi-annual | **not yet run** | — |
| Deprecation staged exercise (E04) | per deprecation | **not yet run** | — |

Automated equivalents exist (`test_rollback_then_forward_needs_newer_than_highest`, `test_file_sink_resumes_and_verifies`, `test_audit_loss_mid_stream`) but do not substitute for human exercises.
