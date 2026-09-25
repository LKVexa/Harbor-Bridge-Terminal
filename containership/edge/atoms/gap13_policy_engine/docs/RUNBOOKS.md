# GAP-13 runbooks — day-0/1/2, emergency controls, incidents (G13-MC-020/028/047)

All commands assume the package's parent directory is on `PYTHONPATH` and a service object `svc` (or the `/v1` API with a bearer token). Every privileged call needs the capability named in brackets.

## Deployment {#deployment}
Prerequisites: Python ≥3.10, `cryptography`, a writable per-host `state_dir`, a GAP-07 trust store, an IdP issuing `PK_POLICY_TOKEN/1`, a TLS sidecar.
1. Validate: `python -m unittest discover -s gap13_policy_engine/tests` → 0 failures.
2. Configure (see *Configuration*), start `rpc.serve(svc, authenticator, host="127.0.0.1")`, put TLS in front.
3. Validate: `GET /v1/health` → 200; `GET /v1/ready` → 503 `no active bundle` (expected before day-1).
Failure path: import error for `cryptography` → install it; every bundle otherwise fails closed.

## Day 0 — bootstrap
1. Record baseline evidence: `python -m gap13_policy_engine.certify --out evidence/` → archive the manifest.
2. `python -m gap13_policy_engine.release_gate --profile rc` → must be `GO`.

## Day 1 — first policy {#distribution}
1. Publisher (EXT-01/GAP-07) signs bundle generation N.
2. Policy admin A: `POST /v1/bundles/stage` [policy.bundle.stage] → note `digest`, `replay: new`.
3. Policy admin B (≠ A, MFA ≤ 5 min): `POST /v1/bundles/activate {digest}` [policy.bundle.activate].
4. Validate: `/v1/ready` 200; `/v1/status.active.generation == N`; spot-check `/v1/explain`.
Failure paths: `G13-E120` verification → check key id/trust store/clock; `G13-E130` → generation not above floor (see *issuer sequence reset*); `G13-E141` → updates frozen.
Automated: `DistributionController(svc, HttpsFetcher(url, token_fn), principal, mode="stage")` then human activation.

## Day 2 — operation
* Watch `g13_bundle_age_seconds`, `g13_stale_refusals_total`, `/v1/ready`.
* Every config change: `svc.reconfigure(principal, cfg, source=<git sha>, version=<tag>)` [policy.config.change]; confirm `status.config_provenance.previous_digest` chains.
* Every release: re-run certify + release gate; evidence must reference the new artifact digests (never reuse).

## Configuration {#configuration}
`EngineConfig.from_mapping({...})` — keys: environment, site, staleness_warning_seconds (default 240), staleness_hard_seconds (300, max 7 d), stale_mode (FAIL_CLOSED | DENY_ONLY | FREEZE_LAST_KNOWN_GOOD), clock_skew_tolerance_seconds, default_deadline_ms, unknown_attribute_policy, limits{max_bundle_bytes, max_rules, max_match_attributes, max_string_length, max_nesting_depth, max_request_attributes, max_request_bytes, max_explanation_matches, max_concurrency, max_queue_depth, audit_buffer_records}. Unknown keys are refused.

## Stale policy {#stale-policy}
Symptoms: `stale.warning` audit event / degraded health, then `G13-E300` refusals (FAIL_CLOSED).
1. Check distribution: `svc.status()["dependencies"]`, controller `history`.
2. Restore connectivity and push a newer generation (Day 1 steps).
3. If connectivity cannot be restored and the site must keep serving: an **approved waiver** is required to switch `stale_mode` to `FREEZE_LAST_KNOWN_GOOD` via `reconfigure` (max 24 h, record change id). `DENY_ONLY` is always permissible.

## Restart {#restart}
`svc.restore_from_cache()` → True when the newest non-quarantined cached envelope re-verifies. Age carries over. False → corrupt cache or revoked key: ready stays 503 until a fresh bundle is activated. Never hand-edit `cache.json`, `antireplay.json`, `control.json`.

## Rollback {#rollback}
`POST /v1/rollback {"reason": "INC-123 ...", "digest": optional}` [policy.bundle.rollback]. Validate `status.active.digest` and a known request via `/v1/explain`. Rollback does not lower the anti-rollback floor; to re-publish the old content as *new*, the publisher issues it with a higher generation.

## Emergency controls {#emergency-controls}
Decision tree:
1. Bad policy suspected, service healthy → `DENY_ONLY` [policy.control.deny_only] (safe, reversible), then rollback.
2. Known-bad bundle → `quarantine(digest=…)` [policy.control.quarantine]: auto-rolls back to non-quarantined LKG, else `DENY_ONLY`.
3. Untrusted distribution channel → `UPDATE_FROZEN` [policy.control.freeze].
4. Engine misbehaving (wrong verdicts) → `EVALUATION_DISABLED` [policy.control.disable] — callers fail closed per EXT-02; never auto-expires.
5. Recover → `NORMAL` [policy.control.clear], reason + change id mandatory.
Every transition requires `reason` and `change_id`; `expires_at` allowed only for UPDATE_FROZEN/DENY_ONLY. State survives restart and reconfiguration. Validate with `/v1/status.control`.

## Break-glass {#break-glass}
A `kind: breakglass` token (issued by the IdP under dual control, lifetime ≤ 1 h) bypasses step-up and SoD but not capabilities or audit. Every break-glass action is audited with `breakglass=true`; post-event review within 2 business days is mandatory.

## Issuer sequence reset {#issuer-sequence-reset}
DR/key-rotation that restarts generations requires a **new `policy_id` namespace** (e.g. `estate-2027`) — the old floor is never reset. Publish the new namespace, activate, then retire the old one.

## Incident response {#incident-response}
| Sev | Definition | Response |
|---|---|---|
| SEV1 | Wrong allow in production, or evaluation unavailable estate-wide | Page oncall + security; DENY_ONLY or quarantine within 15 min; rollback |
| SEV2 | Hard-stale at a site, verification failures on all new bundles, audit sink down | Page oncall; restore distribution / trust store; consider waiver |
| SEV3 | Warning-stale, elevated auth denials, overload sheds | Ticket; investigate within business day |
| SEV4 | Cosmetic / docs | Backlog |
Containment → eradicate (rollback/quarantine/revoke key) → recover (NORMAL) → evidence: export audit (`svc.audit.export()`), verify chain, attach to the post-incident review.
Alert → runbook mapping is in `ops/alerts/gap13_alerts.yaml` (`runbook` annotation).
