# Runbooks — Day 0 / Day 1 / Day 2 / Incident (component 23)
Runbook version 1.0 (4.3.0) · last tested: **never by an independent operator**.

## Day 0 — bootstrap
1. Prereqs: Python 3.11–3.13; `setuptools==68.1.2`, `wheel==0.42.0` (pinned in pyproject).
2. `python -m inv20_http_component_worlds.tools.release --out dist/` → verify `dist/SHA256SUMS`,
   `build_manifest.json.ok == true` (includes clean-room install + tests on the installed wheel).
3. Install pk_core in the approved range (`pip install .[conformance]`) and verify its digest against
   `evidence/dependencies/pk_core.json`. *(Blocked until WI-INV20-01 resolves.)*
4. `python -m inv20_http_component_worlds.witgen --check`.
5. Configuration: start from `config/defaults.json`; validate with `config.validate`; stage with an
   approver when `outgoing_enabled` is true.
6. Identity: provision capability-signing key into the secret store; mint workload capabilities.
7. `python VERIFY.py`; archive `evidence/` as the baseline.

## Day 1 — deploy
Pre-deploy: VERIFY exit code 0 (GO) for the artifact digest. Canary per RELEASE_AND_ROLLBACK.md.
Activate config with `ConfigStore.activate(readiness=...)` (auto-rollback on failed readiness).
Expected signals: `requests_handled{2xx}` rising, `egress_denials` flat, phase=`ready`.
Rollback: `ConfigStore.rollback`, redeploy previous digest. Capture post-deploy evidence.

## Day 2 — operate
- Health: read `HealthMonitor.snapshot()` — `phase`, `reason` codes (`config_invalid`,
  `dependency_unavailable:*`, `request_stalled`, `queue_saturated`, `drain_stuck`).
- Policy denial triage: `egress_denials{reason}` → reason tells which layer (not_allowlisted,
  private/loopback/metadata = rebinding, mixed_answer, cname_denied, capability_scope).
- Upstream failures: breaker state, `retries{code}`; never raise retry limits beyond schema bounds.
- DNS/egress: re-run `DestinationPolicy.authorize` for the authority; check resolver answers.
- Saturation: `saturation{queue}`, `E_OVERLOADED` reasons (`tenant_limit` ⇒ noisy neighbour).
- Leaks: `len(world.live)` and `admission.active` must return to 0 when idle.
- Cert/identity issues: hand off to the TLS/identity owner (UNASSIGNED).
- Drift: compare active `provenance.digest` with the approved revision.

## Incident
Severity: SEV1 policy bypass / cross-tenant exposure; SEV2 outage; SEV3 degradation.
1. Preserve evidence: export audit stream + anchor, metrics, config provenance.
2. Contain: `revoke_all()` (egress kill switch) and/or `quarantine(tenant)`.
3. Roll back artifact/config. 4. Validate recovery (VERIFY + canary). 5. Post-incident review →
add a regression test (and fuzz corpus entry for parser bugs).
Pager/escalation contacts: **UNASSIGNED** (see governance/OWNERSHIP.md).

## Validation still required
Empty-environment bootstrap by a non-author, tabletop exercises, one rollback drill, one
quarantine/security drill.
