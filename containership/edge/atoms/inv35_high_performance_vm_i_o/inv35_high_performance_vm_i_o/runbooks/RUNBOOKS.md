# INV-35 Operational runbooks — day 0 / day 1 / day 2 (C096)

All commands use `tools/inv35ctl.py` (reference CLI over the runtime API) or the
equivalent control-plane calls. Every action is audited. Approval: **PENDING**.

## Day 0 — install / bootstrap
<a id="rb-00-install"></a>
1. Verify artifact: `python verify.py` on the release tree; confirm `tree_digest` matches the change ticket.
2. Select profile (`config/defaults/<profile>.json`) and write a site override (`config/examples/*`).
3. `python tools/inv35ctl.py config-check <site.json>` — must print `CONFIG=OK digest=…`.
4. Provision KMS key handle and trusted time; confirm `status` shows `key_service: ok`, `time_service: ok`.
5. Register a smoke queue with synthetic regions; run `python tools/inv35ctl.py smoke` (submits every `fixtures/valid` case, expects every `fixtures/invalid|adversarial` code).

## Day 1 — first traffic
<a id="rb-01-first-traffic"></a>
1. Enable one tenant; watch `inv35_queue_depth`, `inv35_saturation`, refusal codes on the dashboard.
2. Confirm zero E1xx from well-behaved guests; any E105 from a production guest ⇒ RB-03.
3. Record baseline latency from `inv35_submit_latency_us`.

## Day 2 — steady state
<a id="rb-02-routine"></a>
* Weekly: `status` + `explain` spot check; audit chain verify on SIEM ingest.
* Monthly: key rotation (`KeyRing.rotate` → wait max TTL → `retire`), dependency review (REV-DEPS).
* Quarterly: access/policy review (REV-ACCESS/REV-POLICY), offline-policy drill on one far-edge site.

## Alert runbooks

### RB-03 Bounds violations <a id="rb-03-bounds-violations"></a>
Meaning: a guest posted descriptors outside its memory (hostile or buggy driver).
1. `inv35ctl explain --queue Q` → identify queue/tenant and codes. 2. If sustained or security-relevant: `transition QUARANTINED` (SEV2). 3. Export audit + journal. 4. Notify tenant owner. Do **not** raise limits.

### RB-04 Stalled queue <a id="rb-04-stalled-queue"></a>
1. Check `pending`, `idle_s` in status. 2. Enter `DEGRADED` mode `no_notification_suppression`. 3. If still stalled: backend health (breaker state), then guest. 4. Exit mode after root cause.

### RB-05 Authentication/authorisation failures <a id="rb-05-auth-failures"></a>
1. Group `inv35_security_refusals_total` by code. E301 spike ⇒ key mismatch or forgery (check rotation timeline); E304 ⇒ replay (SEV2 security); E305 ⇒ cross-tenant attempt (SEV2). 2. If forgery suspected: rotate + retire keys (SEV1 path).

### RB-06 Not ready <a id="rb-06-not-ready"></a>
Check `dependencies`: key_service/time_service unavailable ⇒ restore service (component is failing closed by design); stalled queues ⇒ RB-04; queues FROZEN after restart ⇒ owning controller resumes with a new epoch.

### RB-07 Saturation <a id="rb-07-saturation"></a>
1. Identify top tenants by queue depth. 2. Temporary: site override lowering `tenant_share`/`submit_rate_per_s` (tighten-only safe). 3. Capacity: add hosts / move guests (INV-24).

### RB-08 Latency regression <a id="rb-08-latency"></a>
Compare with release baseline; check facade overhead ratio in the latest perf evidence; roll back artifact if regression tracks a release.

### RB-09 Degraded too long <a id="rb-09-degraded"></a>
Find the mode (`inv35_queue_mode`); control_plane_unreachable ⇒ network/controller; others ⇒ operator decision to exit or escalate.

### RB-10 Config rollback <a id="rb-10-config-rollback"></a>
`ControlPlane.rollback_config(token, tenant=…, queue=…, to_generation=N)`; confirm new generation and digest in status.

### RB-11 Crash recovery <a id="rb-11-crash"></a>
Process restarts with journal → queues FROZEN → controller `claim(epoch+1)` → `transition SERVING`. Verify reservations match guest ring state.
