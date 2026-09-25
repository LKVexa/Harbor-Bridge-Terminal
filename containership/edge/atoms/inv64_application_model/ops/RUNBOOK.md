# INV-64 operator runbook — Day-0 / Day-1 / Day-2 (MC-33; C096)

Status: written against 4.3.0 tool syntax; **not yet exercised by an operator drill** (MC-33 blocker). Commands assume the package directory `inv64_application_model/` inside `$WORK`. Windows: use `tools\bootstrap.ps1` and `py -3` instead of `python3`.

Authorization: steps marked 🔒 need the named capability (ops/owners.json decision rights). Every risky step is audited by the tool itself.

## Day-0 — bootstrap

| Step | Command | Expected | If not |
|---|---|---|---|
| 1 prerequisites | Python 3.10–3.13; write access to `$WORK`; for certification: pinned `pk_core` at `$PK_CORE_PATH` | — | see compatibility.json |
| 2 verify artifact | `sha256sum -c SHA256SUMS` in the release dir; `python3 -m inv64_application_model.tools.release verify --release REL --dist DIST --trusted-key <pub> --trusted-kid <kid>` | `{"result": "PASS"}` | stop; do not install (SECURITY_RESPONSE.md) |
| 3 install | POSIX `sh inv64_application_model/tools/bootstrap.sh [--certification] [--wheelhouse DIR]` · Windows `powershell -File inv64_application_model\tools\bootstrap.ps1 [-Certification]` | venv created, `pip check` clean, preflight printed | read the failing preflight check |
| 4 trust roots 🔒 admin.trust | provision issuer keys in the host's `TrustSource`; sign the trust policy with the root key | `TrustStore.activate` succeeds; audit `trust.activate active` | wrong root key ⇒ `artifact.signature` |
| 5 authz policy 🔒 admin.policy | load `PK_APP_AUTHZ_POLICY/1`; `Authorizer.activate(doc)` | audit `policy.activate active`; status no longer `policy.missing` | PolicyError text names the rule |
| 6 baseline evidence | `python3 -m inv64_application_model.tools.run_evidence --out evidence/` | evidence files written; gate verdict printed | read `EXIT_GATE.json` blockers |

## Day-1 — deploy / change configuration

1. Build the effective config: `overlay.merge(base, overlays, Scope(...), authorize=...)`; review `overlay.diff` (dry run). Values redacted outside the owning tenant.
2. 🔒 config.activate — `rev = store.propose(effective, actor=..., release=VERSION, validator=validate)`.
3. Stage via `rollout.Rollout(...)` (ops/ROLLOUT_POLICY.json): `promote(None)` → observe window → `promote(signals)` per stage. Missing signals block promotion.
4. Each target: `store.activate(rev, expected_active=<current>, health_probe=...)`. Expected `{"result": "active"}`; `rolled_back` means the health probe failed and the candidate is quarantined.
5. Verify: `service.status()["state"] == "ready"`, `config.active == rev`.
6. Archive: `python3 -m inv64_application_model.tools.run_evidence --out evidence/`; keep with the change record.

Rollback at any point: see <a id="activation"></a>**activation** below.

## Day-2 — operate

| Routine | Cadence | How |
|---|---|---|
| health | continuous | orchestrator probes `status()`; `ready=false` removes the instance |
| SLO / error budget | weekly | dashboard rows "Golden signals" and alert INV64-A01 history |
| audit verification | daily | `python3 -m inv64_application_model.audit verify audit.jsonl --anchor anchor.json --key-env INV64_ANCHOR_KEY` → `"result": "PASS"` |
| key/cert rotation 🔒 admin.trust | per key policy (≤ 90 days) | SECURITY_ARCHITECTURE.md §2/§7 |
| dependency review | monthly | `python3 -m inv64_application_model.tools.review_collect dependency` |
| capacity review | quarterly | compare `evidence/PERF.json` capacity_model with dashboards |
| backups | after each commit | BACKUP_RESTORE.md |

### Status reason codes → sections

| Reason / alert | Section |
|---|---|
| `dependency.unhealthy`, `dependency.stale`, A03 | [dependency outage](#dependency-outage) |
| `policy.missing` | [policy](#policy) |
| `config.activation_in_progress`, `config.none_active`, A08 | [activation](#activation) |
| any `degraded` reason | [degraded](#degraded) |
| any `blocked` reason incl. `emergency.disabled` | [blocked](#blocked) |
| A01 | [slo burn](#slo-burn) · A02 [overload](#overload) · A04 [rejection spike](#rejection-spike) · A06 [defect](#defect) · A09 [telemetry](#telemetry) |
| A05, A07, A10 | ops/INCIDENT_RESPONSE.md |

<a id="dependency-outage"></a>
### Dependency outage
1. `status()["dependencies"]` names it. Required ⇒ blocked, optional ⇒ degraded.
2. Identity/trust source: existing tokens keep working ≤ 300 s, then `auth.trust_unavailable`; do **not** raise the cache TTL in production without security approval.
3. Adjacent INV layer: page its owner (INV-10/63/65/66); INV-64 needs no action (no partial activation).
4. Close when the dependency is healthy for 10 min.

<a id="policy"></a>
### Policy missing or rejected
Every request is denied (fail closed). Re-activate the last good policy: `authorizer.rollback()` 🔒 admin.policy, or activate a fixed one. Never activate an unsigned/unreviewed policy to "get traffic flowing".

<a id="activation"></a>
### Activation, rollback, quarantine
- Stuck `pending`: restart the process; recovery aborts an interrupted PREPARE or rolls forward a COMMIT (check `status()["config"]["recovery"]`).
- Operator rollback 🔒 config.rollback: `store.rollback(actor=..., reason=...)` → `{"result": "rolled_back", "active": <known-good>}`; again ⇒ `noop`.
- Auto-rollback happened (A08): candidate is quarantined; investigate; lift only with `store.reapprove(digest, approver=<someone else>)`.
- No known-good revision: `activation.no_known_good` — use [emergency disable](#blocked).

<a id="degraded"></a>
### Degraded
Service keeps serving. Fix the named optional dependency; if `audit.events_dropped` appears treat it as SEV1 (ops/INCIDENT_RESPONSE.md#audit).

<a id="blocked"></a>
### Blocked / emergency disable
Emergency disable 🔒 breakglass or owner: `service.emergency_disable(actor=..., reason=...)` — every request returns `service.disabled`; audited. Re-enable with `emergency_enable` after the cause is fixed and status shows no other blocked reasons.

<a id="slo-burn"></a>
### SLO burn
Check the dominating class on the dashboard: overload → [overload](#overload); dependency → [dependency outage](#dependency-outage); `internal` → [defect](#defect). If a rollout is in progress, abort it (`Rollout.abort`).

<a id="overload"></a>
### Overload
`admission.*` rejections are expected under burst; clients back off. Persistent saturation (inflight ≥ 80% of limit for 15 min) ⇒ add instances (capacity model in evidence/PERF.json); do not raise per-tenant limits without the owner.

<a id="rejection-spike"></a>
### Rejection spike
Group by code in logs (`code` field). One tenant with `manifest.*`/`secret.*` codes = bad client change — contact the tenant; many tenants = possible bad schema/policy rollout — roll back the last policy/config change.

<a id="defect"></a>
### Defect (`internal`)
Collect the correlation IDs from logs (redacted by construction), `explain` records and the exception type; open a SEV2; roll back the last release if it started after a deploy.

<a id="telemetry"></a>
### Telemetry self-health
Log drops / sink errors: the exporter is down or too slow; the service is unaffected (bounded ring). Absent series: the instance may be dead — check liveness.

## Diagnostics collection
`service.log.records(tenant=<tenant or None>)`, `explain.explain(decisions, viewer_tenant=...)`, `service.status(viewer=principal)` — all redacted and tenant-scoped; never attach raw manifests to tickets.

## Upgrade
1. Read CHANGELOG + COMPATIBILITY.md migration notes. 2. Back up (BACKUP_RESTORE.md). 3. Preflight with the new version. 4. Roll out via `rollout.py`. 5. Rollback = previous package version + restore if the state format changed (none in 4.x).

## Day-2 restore
Stop the instance → `backup_restore restore --into NEW --tenant T` → PASS → swap directories → start → `status()` ready → `audit verify` PASS.

## Decommission
1. 🔒 config.rollback/owner: emergency-disable. 2. Final backup + audit seal (`AuditLog.seal`). 3. Ship ledger + anchor to WORM retention (≥ 3 years). 4. Remove trust material from the host. 5. Record in ops/REVIEWS.json history.
