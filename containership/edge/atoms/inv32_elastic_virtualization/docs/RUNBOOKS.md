# INV-32 Runbooks (v4.3.0)

Conventions: every step lists **Action → Expected → Branch → Rollback → Escalate**. Commands are read-only
unless marked ⚠ (mutating: display scope and require typed confirmation). Escalation role names resolve via
GOVERNANCE.md (owners currently **unassigned — BLOCKED**). `$PKG = python -m inv32_elastic_virtualization`.
These runbooks have **not yet been exercised in a game day** (BLOCKED: needs a real environment); first
exercise must update this file.

## Day-0 bootstrap
| # | Action | Expected | Branch / rollback | Escalate |
|---|---|---|---|---|
| 1 | Verify hardware/OS/hypervisor against `compat_matrix.json` | row status `supported` | otherwise stop | platform |
| 2 | Verify network, DNS, NTP/NTS (skew < 1 s) | `chronyc tracking` offset < 1 s | fix time before continuing (authn ±30 s) | platform |
| 3 | Provision identity: node cert, credential issuer, audience `inv32` | certs valid ≥ 30 d | re-issue | security |
| 4 | Create encrypted volume for state dir; mount at `state_dir` | `cryptsetup status` active | abort; nothing written yet | platform |
| 5 | Verify artifacts: `pip download` wheel, compare SHA-256 with evidence manifest; `$PKG.release verify-evidence` | exit 0 | stop; do not install | security |
| 6 | Write site/env/node config; `$PKG.bootstrap --check --layer site=site.json …` | exit 0, JSON `ok: true` | fix per `checks[].code`; exit 2/3/4/5 meanings in bootstrap docstring | service owner |
| 7 | Provider capability preflight: adapter `capabilities()` vs matrix | versions allowlisted | stop (fail-closed adapter) | provider team |
| 8 | Initialise lease: start controller; audit shows `ownership_acquired` epoch=1 | one owner | if `not_owner`, find other controller first | on-call |
| 9 | Readiness: health `ready: true`, all checks true | — | read `checks` for false item | on-call |
| 10 | ⚠ Safe test adjustment on a **disposable** guest: grow +1 block, revert | outcomes success/success; audit 2 events | revert manually; quarantine guest | on-call |
| 11 | Abort/cleanup: stop service; keep state dir (evidence); `bootstrap --check` for diagnosis | — | — | service owner |

## Day-1 deployment / rollout
1. Canary = 1 host per hardware class, lowest tenant count, not hosting SEV-sensitive tenants.
2. Pre-deploy: `DurableStore.backup()` + `anchor()`; record digests in change ticket.
3. Order: lease/state schema (none in 4.3.0) → controllers → adapters. One host at a time.
4. Observe 30 min per stage: error ratio, `inv32_refusals_total{reason="audit_integrity_error"}` = 0, p99 < SLO.
5. Success: all health checks true, no invariant alerts. Auto-rollback: any `ProviderInvariantViolation`,
   `store_integrity_error`, or p99 > 2× baseline.
6. Expansion: 1 → 5% → 25% → 100% of host groups.
7. Emergency disable: ⚠ `set_quarantine(token,"global",None, reason, ticket, owner)` or config emergency layer
   `{"emergency_disable": true}` — no restart needed (tested).
8. Rollback: previous wheel (digest from previous evidence manifest); `ConfigManager.rollback(revision)`.
9. Post-deploy: `release.py evidence` for the rollout; attach to ticket.

## Day-2 operations
Routine health (hourly probe) · capacity review (weekly, PERFORMANCE.md model) · audit/anchor verification
(`DurableStore.verify()` + `verify_against_external(anchors)`, daily) · key rotation (`Keyring.rotate`, retire
old after max TTL 1 h + skew) · dependency/provider upgrade (matrix first, then Day-1 flow) · config change
(`stage` → `activate(health_gate=…)`; rollback by revision) · quarantine/clear (operator credential, reason,
ticket, owner, TTL) · drain/restart (`controller.drain()` then stop; start runs `recover()`) · backup drill
(weekly: `backup` → `restore` into clean dir → compare `audit_head`) · retention cleanup
(`prune_idempotency(retention)`; verify non-terminal kept).

## Incident runbooks
| Incident | First action (containment) | Diagnosis | Recovery validation |
|---|---|---|---|
| Reserve/invariant threat | ⚠ host quarantine | `host_snapshot`, explain for recent ops | free ≥ 0; invariants alert clear |
| Cross-tenant authz anomaly | ⚠ revoke principal (`revoke_principal`) + tenant quarantine | audit `rejected`/`authz_*` fields | policy review sign-off |
| Audit-chain corruption | controller not ready (automatic); preserve state dir copy | `verify()`, anchors | restore + anchors match |
| State-store corruption/outage | automatic not-ready; ⚠ stop service | load error code | restore; `recover()` report clean |
| Provider outage | circuit open (automatic) | provider health | circuit closed, probe success |
| Stuck mutation | watchdog incident; ⚠ guest quarantine | explain + provider request id | `recover()` verdict applied/not_applied |
| Split brain / stale controller | ⚠ stop both; fencing rejects stale writes | lease file epoch | single owner, `recover()` on new owner |
| Credential/key compromise | ⚠ rotate keyring, revoke principals, emergency disable | audit by principal | new kid only accepted |
| Overload / retry storm | shed LOW priority (automatic) | refusals by reason | inflight < limit |
| Telemetry outage | none (degraded) | sink | metrics resume |
| Site/network partition | FROZEN_WRITE (automatic) | lease store reachability | lease re-acquired, reconcile |
| Unfreeze | require: all health checks true, incident owner approval, audit note | — | `quarantine_clear` audited |

## Quality gate
Destructive steps are marked ⚠ and require typed confirmation of scope; commands default to `--check`/read-only;
runbook changes after each game day (BLOCKED until first exercise).
