# Runbooks (v4.3.0)

All commands run from the directory that contains the package. Nothing here has been rehearsed by an operator in a real environment yet (INV-58-C092/C096 PARTIAL).

## Day 0
1. `python -B inv58_existing_service_mesh_layer/tools/bootstrap.py --config site.json` — preflight: Python ≥3.10, package import, optional `jsonschema`, `pk_core` presence (reported, BLOCKED if absent), config validation, secret references resolvable, end-to-end health check.
2. Host constructs `MeshLayerService(resolver=SecretResolver({"kms": <provider>}), node=..., site=..., lineage=ReleaseLineage(version, source_digest, build_id))` and calls `bootstrap(config, author=..., source=...)`. Any failure leaves lifecycle `failed` and nothing active.
3. Record `status()["config"]["digest"]` and `status()["audit"]["head"]` as the day-0 baseline.

## Day 1 — canary and staged rollout
| Stage | Scope | Promote when (all for ≥ 30 min) |
|---|---|---|
| 0 canary | 1 site, 1 low-risk tenant | 0 bounded-attempt violations; readiness 100 %; no new `E_INTERNAL`; p99 within gate |
| 1 | 10 % of sites | same + `inv58_admission_shed_total` flat |
| 2 | 50 % | same |
| 3 | 100 % | same; release acceptance record GO |
Abort at any stage → Rollback.

## Rollback
- **Config rollback:** `svc.rollback_config(operator_token)` (or `to_digest=`); verify `status().config.digest` equals the previous digest and `audit` shows `config.rolled_back`.
- **Automatic rollback:** a config whose post-activation probe fails (e.g. unresolvable key reference) is never left active.
- **Code rollback:** redeploy previous artifact; restore last sealed snapshot with `svc.restore(operator_token, snapshot)`; fencing prevents stale controllers overwriting newer policy.

## Emergency disable
1. A second operator arms the window: `svc.arm_break_glass(operator_token, seconds≤3600, reason=...)` (the armer can never invoke it).
2. `svc.break_glass(break_glass_token, reason=...)` → mutations frozen, lifecycle `frozen`; data plane keeps last-known-good policy.
3. Or scoped: `svc.quarantine(operator_token, tenant, route=..., reason=...)`.
4. Verify: `status().controls.frozen` / quarantined count; audit has `control.break_glass` / `control.quarantine`.

## Day 2
- Every change: regenerate RTM (`tools/rtm.py`), run `tools/release_gate.py`; a NO_GO blocks rollout.
- Daily: export audit (`audit_export`) and store head externally; check `inv58_saturation_ratio` < 0.7.
- Key rotation: publish new key under the same `secretref://`, export+seal audit segment, activate config, verify.

## Decision tree — "attempts look multiplied"
1. `explain(tenant, route)` → which layer owns retries and why?
2. owner=app but mesh VirtualService still retries → mesh config drift; quarantine route, fix mesh config, re-migrate.
3. effective_attempts > budget → invariant breach → SEV1, break-glass freeze.
