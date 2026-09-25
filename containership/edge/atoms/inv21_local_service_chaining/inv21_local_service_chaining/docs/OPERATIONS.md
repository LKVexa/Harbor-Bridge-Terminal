# INV-21 Operations Runbook (day-0 / day-1 / day-2)

## Day-0 bootstrap (empty node → healthy)
1. Install the wheel by digest: `pip install --no-index --require-hashes inv21_local_service_chaining-4.3.0-py3-none-any.whl` (digest in `evidence/release_manifest.json`).
2. Provision secrets **outside** configuration: identity key(s) (≥32 bytes, per key id), audit MAC key (≥32 bytes). Never place them in `PK_CHAIN_CONFIG/1` documents or logs.
3. Write the config document (`schemas/chain_config.schema.json`); validate: `python -c "import json,inv21_local_service_chaining.config as c; c.ChainConfig.from_mapping(json.load(open('chain.json')), environment='prod', site='eu-1')"`.
4. Construct `Chainer(config=..., policy=GuardedProvider(<INV-13 provider>), transport=HttpJsonTransport('https://peer'), audit=AuditLog(key, path='/var/log/inv21/audit.jsonl', lineage={...}), trusted_issuers={...})`. Production mode refuses to start without every one of these (`PK_CHAIN_INVALID_REQUEST field=wiring`).
5. Residency: start empty or `restore()` a snapshot, then `reconcile(INV-10 feed)` before `ready`.
6. Readiness: `GET /readyz` returns 200 only when policy is authoritative, transport present and audit healthy.

## Day-1 deployment
Stage via `rollout.py` (1% → 10% → 50% → 100%). Promotion requires ≥500 requests per stage and no breach of `Criteria` (error-rate Δ ≤ 0.5 pp, p99 ≤ 1.25× baseline, refusal Δ ≤ 1 pp, zero `PK_CHAIN_INTERNAL`). A breach returns `rollback`; for configuration rollouts `apply_verdict` performs `ConfigStore.rollback()` automatically.

## Day-2 operation
* **Config change**: `ConfigStore.activate(cfg, author=, source=)`; atomic across appliers; audited as `config_activated` with digest.
* **Rollback**: `store.rollback(author=)`; binary rollback = redeploy previous digest.
* **Emergency disable**: `chainer.quarantine(reason=, actor=)` → every call refused with `PK_CHAIN_QUARANTINED`; `release()` to resume. Both audited.
* **Stalled handler**: handlers exceeding `handler_stall_s` are marked unhealthy and stop receiving local traffic; re-enable with `residency.set_health(name, True)` after fixing.
* **Audit integrity**: export `audit.head()` to the SIEM at least every minute; verify with `audit.verify(read_jsonl(path), key, expected_head=<exported>)` (full file from genesis) or, for the in-memory ring, `anchor, recs = log.window(); verify(recs, key, anchor=anchor, expected_head=<exported>)`. Every routing decision (grants included) is audited. A mismatch is a SEV-1 (see INCIDENT_RESPONSE.md).
* **Reconstruction after crash**: residency is memory-only by design. On restart: `restore(last_snapshot, handlers)` → entries are unverified (not served) → `reconcile(INV-10 feed)`. Anything not confirmed is evicted. Invariant tested in `test_policy_residency.test_restart_restore_requires_reconcile`.

## Troubleshooting
| Symptom | Check | Likely cause |
|---|---|---|
| all calls `PROVIDER_UNAVAILABLE` | `/readyz` → dependencies.policy | INV-13 down or timeout too tight (`policy_timeout_s`) |
| calls go remote unexpectedly | `inv21_residency_stale_hits` | lease renewals stopped (control plane) |
| `CIRCUIT_OPEN` | `/readyz` → open_circuits | peer partition; recovers after `breaker_reset_s` |
| `OVERLOADED` | `inv21_saturation_ratio` | capacity: see CAPACITY_MODEL.md |
| explain a decision | `chainer.explain(trace_id)` | — |
