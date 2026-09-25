# Configuration (C017, C032-C039)

Document `PK_SNAPSHOT_CONFIG/1`; defaults, bounds and semantic rules in `config.py`. Examples validated by
the runtime validator: `examples/config.production.json` (minimal production) and
`examples/config.restrictive.json` (maximally restrictive far-edge).

* **Secure defaults:** encryption, cross-boundary refusal, entropy ack and restore grants are `LOCKED` true;
  production forbids the reference adapter, memory storage, HS256 and debug logging; `auth.audience` and
  `kms.key_id` are required (no anonymous endpoints, key *aliases* only).
* **Units** are in the names (`_ms`, `_bytes`, `_mib`, `_per_s`); every numeric field has bounds.
* **Overlays:** `compose(("base", …), ("environment", …), ("site", …), ("emergency", …))` — fixed order,
  no environment-variable precedence, unknown keys refused, LOCKED keys cannot be weakened by any layer, and
  the emergency layer may only touch `admission`/`quotas`.
* **Validation (C034):** syntax, type, range, identifiers, adapter/profile compatibility, residency contains the
  node, timeout budget (`restore ≥ kms + storage/4 + entropy`), retry cap ≥ base, per-tenant ≤ in-flight,
  inline secrets. Errors carry field paths only (never values).
* **Activation (C037):** `ConfigStore.activate(doc, author, source, approval_ref, expect_revision)` —
  validate → fail-closed audit → one CAS transaction writing `config/active` and the immutable
  `config/rev/<n>` record. A crash leaves wholly old or wholly new (tested with a torn WAL tail and a crash
  after fsync). The service swaps its config reference atomically on `reload_config()`.
* **Provenance (C036):** revision, SHA-256 digest, author, source, approval ref, activation time (ms), scope,
  previous revision; every decision record and audit event carries the governing revision;
  `ConfigStore.governing(rev)` reconstructs it.
* **Rollback (C038):** `ConfigStore.rollback(to_revision, author, reason)` re-activates an old revision as a
  new revision (history is never rewritten). Drill evidence: `evidence/DRILLS.json`.
* **Artifacts vs state (C032):** the installed package is immutable and never written; mutable state lives only
  in `metadata.root`, `storage.root` and the service work dir (private tmpfs). Surviving restart: metadata +
  blobs. Ephemeral: work dir, admission counters, decision cache, breaker state.

## Quotas and fairness (C017)
Per tenant: `quotas.max_snapshots_per_tenant`, `max_bytes_per_tenant`, `max_memory_mib`, `max_devices` —
checked before any hypervisor/storage work. Admission: `max_inflight`, `max_queue`, `per_tenant` (fairness
cap on concurrent slots), per-tenant token bucket `tenant_rate_per_s`/`tenant_burst`. Rejections return
`SNAP_QUOTA_EXCEEDED` (policy, not retryable) or `SNAP_OVERLOADED` (retryable with `retry_after_s`).
There are no privileged bypass paths. KMS concurrency is bounded by admission (every KMS call happens inside
an admitted operation).
