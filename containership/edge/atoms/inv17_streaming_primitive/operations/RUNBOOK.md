# INV-17 Operational Runbook

**Controls:** C096, C097 (checklist §58); references C048, C052, C054, C059, C071, C076.

No drill has been executed against this runbook yet (tools/drill.py is planned). Treat steps as untested until a drill record exists.

## 0. Diagnostic surfaces

`observability.serve_status(registry, host="127.0.0.1", port)` returns a loopback `ThreadingHTTPServer` (caller must `serve_forever()`):

| Path | Code | Content |
|------|------|---------|
| `/healthz` | 200 (always live while process serves) | `status()` document |
| `/readyz` | 200 if health `healthy`/`degraded`, else 503 | `status()` incl. `health`, `reasons[:20]` |
| `/version` | 200 | version + interface versions |
| `/metrics` | 200 | Prometheus text (`inv17_streams_open`, `inv17_credit_stalls_total`, `inv17_elements_buffered`, `inv17_load_shed_total`, `inv17_breaker_open`, `inv17_disabled`, `inv17_elements_dropped_total`, `inv17_duplicate_writes_total`, `inv17_audit_events_total{kind}`, `inv17_health_status{status}`, …) |
| `/explain` | 200 | policy (disabled, frozen scopes, breaker, budget, default quota), topology, last 50 redacted decisions |

In-process equivalents: `registry.health()`, `explain(registry, stream_id)`, `stream.stats()`.

## 1. Credit stall

**Signal:** `health` reason `"<sid>: credit stalled for Ns"` or `"stall ratio X"`; `inv17_credit_stalls_total` rising.
1. `explain(registry, sid)`; `stats()` on the stream: `credit == 0`, `credit_stalls` rising → reader is not granting.
2. Check reader process liveness. If the reader is gone but not dropped, the stream will stay stalled — call `drop_reader()` on it (writer then gets `EndDropped`).
3. If reader is alive but slow: capacity issue; consider quarantining the workload (§8).
4. Not a fix: raising `max_credit` does not help when credit is 0.

## 2. Buffer ceiling

**Signal:** `BufferLimitExceeded`, reason `"<sid>: buffer n/max"` (≥ 90 %).
1. Reader granted credit but is not reading. Check reader.
2. Tenant-wide: `registry.buffered_total(tenant)` vs `TenantQuota.max_buffered`.
3. Reduce grant sizes in the reader, or drop the stuck reader.

## 3. Drop storms

**Signal:** `inv17_elements_dropped_total` / `inv17_dropped_end_streams` jump.
1. Identify affected tenant/workload in `/metrics` labels and `/explain`.
2. Correlate with deploys (release lineage labels) → roll back (§7, rollout.md).
3. If a single workload is crash-looping, `quarantine(scope="workload")`.

## 4. Load shed / breaker open

**Signal:** `LoadShed`, `inv17_load_shed_total`, `inv17_breaker_open`=1, `CircuitOpen` on opens.
1. `registry.buffered_total()` vs `global_buffer_budget`. Find top tenants by buffer.
2. Quarantine the offending tenant if one dominates.
3. Breaker half-opens after `breaker_cooldown_s` (default 5 s) and closes on the next successful write. It reopens on any failure while half-open.
4. Raising `overload.global_buffer_budget` is a config change (§7) — only with memory headroom evidence.

## 5. Authentication / authorization failures

**Signal:** audit kinds `auth.denied`, `auth.replay`, `authz.denied` (also `inv17_audit_events_total{kind=...}`).
1. Export `audit.export_jsonl()`; group by tenant and `error` code.
2. Expired tokens → client clock/TTL (`max_ttl` 300 s). Unknown `kid` → key rotation mismatch (`KeyRing.rotate`/`retire`); re-add the old key until clients refresh.
3. `auth.replay` bursts or cross-tenant `authz.denied` → treat as security incident (Sev0/1), revoke via `CapabilityAuthority.revoke(token)`.

## 6. Trust-service outage

**Signal:** audit `trust.unavailable`; ops fail with `TrustServiceUnavailable` (`dependency` = `keys`, `time`, or `replay-cache`).

`replay-cache` means the single-use nonce cache is full (`replay_cache` capacity of live, unexpired single-use nonces); only single-use tokens (e.g. `transfer`) are refused. It clears as nonces expire (≤ `max_ttl`); if persistent, reduce single-use issuance/TTL or raise `replay_cache`.
1. Behaviour is fail-closed by design; do not bypass.
2. Restore key service / trusted time. Existing `Stream` objects already held by clients keep working (auth is checked at registry calls only).
3. After recovery, confirm new opens succeed.

## 7. Configuration rollback

1. `ConfigManager.activate(...)` auto-rolls back when `health_probe` fails (`ActivationFailed`, audit `config.rollback` auto).
2. Manual: `ConfigManager.rollback(author=..., reason=...)` restores previous (history 16). Verify `provenance.digest`.
3. Note: new stream limits apply only to streams opened after activation.

## 8. Emergency disable / quarantine

See operations/emergency-disable.md. Summary: `registry.emergency_disable("sre-oncall", reason)` freezes all streams and refuses registry ops (`ComponentDisabled`); `registry.quarantine("sre-oncall", scope="tenant"|"workload", value=..., reason=...)` freezes a scope.

## 9. Post-incident

Record `audit.anchor()`, run `audit.verify()`, file incident record, update this runbook.
