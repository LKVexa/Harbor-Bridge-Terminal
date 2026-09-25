# INV-69 operations runbook (C096 partial, C097, C095, C089, C093)

Owners and escalation: [`ops/OWNERS.md`](OWNERS.md) · [`ops/ESCALATION.json`](ESCALATION.json) ·
alert → runbook links: [`ops/alerts.json`](alerts.json). Severity model: SEV1–SEV4 in `ESCALATION.json`.

Roles during an incident: **incident commander** = first L2 responder (`inv69-service-owner` or delegate);
**communications** = `inv69-oncall` until handed over; **scribe** fills `ops/INCIDENT_TEMPLATE.md`.

## Containment commands (tested: `tests/test_v43.py::OpsTest`)

All containment goes through `GovernedRuntime.contain(action, operator=..., reason=...)` and is itself
recorded in the run-event chain.

| Action | Effect | Use when |
|---|---|---|
| `disable_new_runs` | `start_run` refuses with AGT-POL-001; in-flight runs continue | approval bypass suspected, bad release, corrupt state |
| `force_heavy_sandbox` | every tool routes to INV-71 regardless of risk class | fast-sandbox escape suspected |
| `release_containment` | clears both | after recovery sign-off |
| config emergency layer | `ConfigStore.activate([..., ("emergency", {...})])` — tighten-only (e.g. `budgets.max_steps: 1`) | runaway loops, cost blow-up |
| config rollback | `ConfigStore.rollback(gen, expected_generation=active)` | bad config generation |
| revoke tool capability | remove the tool from INV-59 policy (authorization layer) | tool misbehaving |

Evidence bundle (never destroys data): `backup.create_backup(runtime, key=<from key service>, actor=<you>)`
plus `runtime.status()` plus `runtime.config.export_provenance()` — store read-only; the bundle is HMAC-sealed.

## Scenario runbooks

<a id="rb-approval-bypass"></a>
### Approval bypass suspected (SEV1)
1. `contain("disable_new_runs")`. 2. Export evidence bundle. 3. Verify: `runtime.verify_events()` and each
`run.agent.verify_transcript()`; find `invocation` events with `outcome=ran` for side-effect tools without a
preceding `approval_recorded` for the same run (explain view: `python -m inv69_agentic_workload_layer.explain`).
4. Page `inv69-security-owner`. 5. Recovery only after root cause + regression test.

<a id="rb-audit-chain"></a>
### Audit-chain failure (SEV1)
`verify_events()`/`verify_transcript()` false or AGT-INT-001. Contain new runs; do **not** restart the
process (the in-memory head is the only local anchor until the remote anchor lands — W-004); export bundle;
compare head with the last externally anchored head.

<a id="rb-sandbox-escape"></a>
### Sandbox escape indicator (SEV1)
`force_heavy_sandbox`, then `disable_new_runs` if the indicator came from INV-71. Hand to INV-70/71 owners.

<a id="rb-leaked-credential"></a>
### Leaked credential (SEV1)
Rotate at the key service; config uses `secretref://` only, so no config change is needed unless the ref
itself changes. Artifacts signed with a compromised key: add digests to `revoked_digests` in the trust policy
and re-pin the policy digest.

<a id="rb-runaway"></a>
### Runaway agent / tool loop (SEV3)
Budgets already bound each run (AGT-CAP-001/002). If many runs loop: emergency layer tightening
`budgets.max_steps`; `cancel_run(run_id)` for specific runs (watchdog HLT-STALL-CRIT lists them).

<a id="rb-dependency"></a>
### Dependency outage (SEV2)
Check `status()["dependencies"]` and `blocked_capabilities`. Critical trust services fail closed by design
(`ops/SPEC.md` §C048); do not bypass. Non-critical (telemetry, topology, fast sandbox) degrade automatically.
On recovery, `set_offline(False)` returns deferred ops; they are re-evaluated with `trust.reconcile`.

<a id="rb-corrupt-state"></a>
### Corrupt state
Restore: `restore_to_staging(bundle, key=..., actor=...)` → inspect record → `activate_restore(staged, durable)`.
Approvals are never restored (re-approval required); committed effect keys are, so nothing replays.

<a id="rb-bad-release"></a>
### Bad release or configuration (SEV2)
Config: rollback generation. Code: redeploy previous line from `ops/EOL.json` (4.2 is security-fix-only).
Performance regression: `tools/release_gate.py` must have blocked it; if not, file a defect against the gate.

## Rolling upgrade (C027/C093)
Order: INV-57 → INV-59 → INV-70/71 → INV-69. INV-69 refuses peers failing `compat.handshake`
(protocol major or required capability missing) **before any side effect**. Rollback points after each step.

## Disaster / partition scenarios (C089)
Automated in `tests/test_v43.py::DisasterTest`: executor loss with failover (fencing), partition with offline
queue + reconnect reconciliation, control-plane (policy/identity) outage, storage corruption detected on restore,
long partition exceeding cache freshness. Reset: every scenario builds fresh adapters (`tests/harness.py::build`).
Objectives: RPO = last committed effect key (0 duplicate side effects); RTO target 60 s after lease expiry (PROPOSED).

## Post-incident
Template: `ops/INCIDENT_TEMPLATE.md`. Findings go to `ops/REVIEWS.json` register; exceptions to `ops/WAIVERS.json`.
