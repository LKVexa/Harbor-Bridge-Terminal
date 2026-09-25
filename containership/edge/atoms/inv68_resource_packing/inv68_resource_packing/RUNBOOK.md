# INV-68 operator runbook 4.3.0 (MC-38; C096, C097)

Commands run from the directory *containing* `inv68_resource_packing`. Every step
lists the expected output and the exit criterion. Escalation: ops/owners.json
(on-call route UNASSIGNED — see §10).

## 1. Day 0 — preflight and bootstrap
| Step | Command | Expect | Exit criterion |
|---|---|---|---|
| 1.1 | `sh inv68_resource_packing/tools/bootstrap.sh --state-dir /var/lib/inv68` (Windows: `tools\bootstrap.ps1 -StateDir ...`) | `INV-68 bootstrap: ready`, exit 0 | exit 0; exit 1 = preflight/test failure, 2 = Python < 3.10, 3 = digest/install failure |
| 1.2 | `python -m inv68_resource_packing.tools.preflight --certification` | P01–P08 `ok` | P08 fails until pk_core is supplied (MC-02) |
| 1.3 | Seed trust roots from the secret store (token kids, audit MAC key, anchor key) | keys in process env/secret mounts only | nothing written under the state dir |
| 1.4 | Activate the site configuration (controller token): `compose(defaults, ("environment:<env>", ...), ("site:<site>", ...))` → `activate_config` | journal entry, `config.activate` committed audit record | `status().state == "ok"` |

## 2. Day 1 — deploy and verify
| Step | Command | Expect |
|---|---|---|
| 2.1 | Verify release: `python -m inv68_resource_packing.tools.release verify --release <dir> --trusted-key <hex> --trusted-kid <kid>` | `result: PASS` (managed signer) |
| 2.2 | Run gate: `python -m inv68_resource_packing.release_gate --pk-gate PK_GATE_RESULTS.json --approval APPROVAL.json` | exit 0 GO (2 CONDITIONAL_GO needs recorded conditions; 3 NO_GO blocks) |
| 2.3 | Canary per `ops/ROLLOUT_POLICY.json` (1 % → 10 % → 50 % → 100 %), `rollout.RolloutController.step(candidate, baseline)` each bake | `promote` at each stage |
| 2.4 | Smoke: pack `examples/service_request.json`; check explain + status | `outcome: partial` (the example whale is unplaced by design) |

## 3. Rollback
Config: `PackingService.rollback_config(controller_token)` → previous snapshot, audited
(`config.rollback`). Code: reinstall the previous wheel verified against its
`SHA256SUMS`; configuration stays compatible within a minor. Automated rollback:
`RolloutController.abort` (drill: evidence/ROLLBACK_DRILL.json).

## 4. Overload / latency (alerts INV68-A05, A07)
1. `status()["admission"]` — in_flight at `max_concurrency` and shed_total rising = load.
2. If one tenant dominates `inv68_requests_total{tenant}` → lower its quota (overlay) and activate.
3. If p99 > 100 ms with low load → efficiency/algorithm regression: compare with
   `bench/PERF_BASELINE.json` via `tools/bench.py`; roll back the release.
4. Raise `max_concurrency` only if CPU headroom exists on the INV-68 host.

## 5. Capacity-source outage (A03)
`status()["dependencies"]["capacity_source"]` = `open` → upstream down. INV-68 refuses
rather than guessing. Options: fix the source; or, for urgent batches, callers pass
explicit `host_capacity` from known-good data (documented degraded mode §8 of the spec).

## 6. Emergency disable (A02, any unsafe placement)
1. `PackingService.freeze(operator_token, "<incident id + reason>")` — audited; persists across restarts.
2. Verify `status().state == "frozen"`; new packs return `FROZEN`; config and audit are untouched.
3. Preserve evidence: copy `audit.jsonl`, anchor, `cfg/` and the last structured logs (§9).
4. Fix → staged activation while frozen → `unfreeze(operator_token, reason)` → watch A02/A08 for one bake period.
Drill: evidence/EMERGENCY_DISABLE.json.

## 7. Software defect (A01 — any `INTERNAL`)
Collect correlation ids from logs (`event: pack.internal`), reproduce with the request
digest from the audit record, add the input to `tests/fixtures/fuzz_regressions.json`,
fix, run `tools/run_evidence.py`. Freeze if placements may be wrong.

## 8. Policy rejections (A06)
Spike in `FORBIDDEN` → token scope drift (check principal tenants/capabilities);
`QUOTA_EXCEEDED` → fairness working as designed or quota mis-sized; confirm with the
tenant before changing overlays.

## 9. Efficiency regression (A08)
Compare `inv68_efficiency_ratio` with PERF efficiency; check workload mix change
(new large workloads), headroom/overcommit changes in the journal; roll back config
if a change correlates.

## 10. Escalation, severity, paging
| Sev | Definition | Page | Escalate |
|---|---|---|---|
| SEV1 | memory overcommit observed, cross-tenant exposure, audit tampering | immediately | security_owner + accountable_owner within 30 min |
| SEV2 | packing unavailable/frozen > 15 min, INTERNAL errors | yes | service_owner within 15 min |
| SEV3 | degraded (breaker open, efficiency/latency regression) | ticket | next business day |

Routes are UNASSIGNED until owners are named — this runbook is not production-ready
until §10 has names and a paging tool (MC-03/MC-38 governance).

## 11. Day 2 routine
Daily: check SLO/error-budget burn (SPECIFICATION §4 SLI table) on the dashboard. Weekly: review security anomalies (UNAUTHENTICATED/FORBIDDEN/REPLAY_DETECTED rates; unexpected `config.*`/`control.*` actors in the audit ledger) and dependency health (`status().dependencies`); confirm the last backup exists and restores (BACKUP_RESTORE.md); `inv68-audit verify` with anchor; review `inv68_audit_dropped_total`. Monthly:
dependency/SBOM review, config review. Quarterly: rollback, emergency-disable and
restore drills (`tools/drills.py`), access review, threat-model delta.
