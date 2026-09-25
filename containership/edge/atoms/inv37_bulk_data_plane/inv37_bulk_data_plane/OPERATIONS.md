# INV-37 operations: SLOs, rollout, vulnerability/EOL, backup/restore, incidents, reviews

**Version:** 4.3.0 · Covers INV-37-C091–C099. All numeric commitments are **proposed** until accepted by the roles in `governance/OWNERS.json` (recorded in `governance/APPROVALS.json`).

## SLOs, error budgets, support (C091)
| SLO | Target (28-day) | Error budget | SLI |
|---|---|---|---|
| Integrity | 0 objects returned without end-to-end verification | none — any breach is SEV1 | `digest_failures_total{level=object}` + audit |
| Transfer success | ≥ 99.9 % of admitted transfers reach VERIFIED (excl. caller cancel, policy rejection) | 0.1 % | `transfers_verified_total / transfers_created_total` |
| Resume efficiency | ≤ 1 % of bytes re-sent after interruption beyond unacknowledged chunks | 1 % | `bytes_resent_total / bytes_verified_total` |
| Chunk latency | p99 within PERF_THRESHOLDS for profile | 1 % of 5-min windows | `chunk_accept_seconds` |

Budget policy: > 50 % burned → freeze feature releases; 100 % → only reliability fixes, service_owner approval for any change. Support: prod — 24×7 on-call, SEV1 ack 5 min; edge — business hours; dev — best effort.

## Canary, staged rollout, rollback, emergency disable (C092)
1. Gate: `tools/production_gate.py --run --config-digest <digest>` must be PASS (currently NO_GO).
2. Canary 1 node / 1 % of transfers for 24 h; abort if any SEV1/SEV2 alert, error rate > 2× baseline, or p99 > threshold.
3. Stages 10 % → 50 % → 100 % with 24 h soak each; config digest pinned per stage.
4. **Rollback**: `freeze(admin, True)` → drain (`sweep`) → reinstall previous wheel → `ConfigManager.rollback()` if config changed → `recover()` (checkpoint format `INV37_CHECKPOINT/1` unchanged within 4.x) → unfreeze.
5. **Emergency disable**: `freeze(admin, True)` stops admission immediately (waiters receive `admission_frozen`); `quarantine_tenant` isolates one tenant; both audited.

## Vulnerability response and EOL (C094)
| Severity (CVSS) | Triage | Fix / mitigation available | Deployed to prod |
|---|---|---|---|
| Critical ≥ 9.0 | 24 h | 72 h | 7 d |
| High 7.0–8.9 | 3 d | 14 d | 30 d |
| Medium | 7 d | 60 d | next release |
| Low | 30 d | best effort | next release |

Intake via security_owner; zero runtime dependencies means scanning covers CPython and the package itself (SBOM `artifacts/certification/sbom.cdx.json`). Support window: each minor release supported 12 months after the next minor; EOL announced ≥ 6 months ahead; deprecations tracked in `governance/DEPRECATIONS.json` (min 180-day window).

## Backup, restore, migration (C095)
- **Back up**: `checkpoint.directory` (transfers/*, quarantine/*), `config-history.json`, audit log. Key ring is backed up only by the secret manager. Backups must be filesystem-consistent snapshots (checkpoints rely on atomic rename).
- **Restore**: stop process → restore directory → start → `recover()`; chunks whose bytes fail re-hash are dropped automatically and re-requested; broken seals are quarantined. Restores older than the key ring's active key require the old key id kept as verification-only.
- **Reconstruction**: if checkpoints are lost, re-transfer from the authoritative source manifest (the manifest digest is the source of truth).
- **Migration**: 4.2 → 4.3 has no persistent state to migrate (4.2 was in-memory). Future checkpoint schema changes require a reader for N-1 and a migration tool before removal.
- Restore drill evidence is gate criterion `restore_drill` (not yet run).

## Incident severity, paging, containment, recovery (C097)
| Sev | Examples | Page | Containment |
|---|---|---|---|
| SEV1 | object integrity failure delivered/near-delivered; cross-tenant exposure; key compromise | sre + security immediately | freeze admission; quarantine tenant(s); rotate + revoke keys; preserve checkpoints/audit |
| SEV2 | auth-failure burst; repeated quarantines; recovery failures | sre (15 min) | quarantine affected transfers; consider freeze |
| SEV3 | stalls, latency SLO burn, degraded dependency | sre (60 min) | scale / fix dependency |
| SEV4 | single-tenant quota pressure | ticket | adjust quota via config activation |

Escalation ladder: `governance/OWNERS.json#escalation`. Recovery requires `verify_audit` PASS, integrity path re-validated (conformance run), and service_owner sign-off before unfreeze. Post-incident review within 5 business days; action items tracked with owner/expiry.

## Recurring reviews (C098)
| Review | Cadence | Owner | Tooling |
|---|---|---|---|
| Access / capability grants, key rotation | quarterly | security_owner | key ring `revoked`, audit log |
| Policy precedence & residency | semi-annual | architecture_approver | `policy/precedence.json` digest |
| Dependencies / pins / SBOM | each release + monthly | service_owner | `tools/check_pins.py` |
| Configuration drift | monthly | sre_owner | `config-history.json`, digest in health |
| Architecture / ADRs / threat model | each release | architecture_approver | ADR-0001, THREAT_MODEL.md |
| Owners metadata | `review_by` date (6 months) | service_owner | `tools/check_governance.py` blocks when overdue |

## Exceptions, waivers, debt (C099)
Waivers: `governance/WAIVERS.json` (≤ 90 days, named approver role + person, compensating controls; validated by `tools/check_governance.py`; the gate honours only active approved waivers). Debt: `TECHNICAL_DEBT.md` (owner role + gate). Deprecations: `governance/DEPRECATIONS.json`.
