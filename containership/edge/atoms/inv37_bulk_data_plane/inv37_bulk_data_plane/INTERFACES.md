# INV-37 Bulk data plane — interface inventory

**Version:** 4.3.0 · Covers INV-37-C021, C025, C027, C028. `tests/test_docs.py` fails if a public `BulkDataPlane` method or a registered error code is missing from this file. Reviewed on every release and whenever a transport, storage or auth integration changes (owner: architecture_approver).

## 1. Boundary inventory

| # | Boundary | Producer → Consumer | Direction / sync | Trust | Authn | Authz (capability) | Version | Limits | Failure modes | Data class |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | Python API `BulkDataPlane.*` | embedding service → INV-37 | in-proc, sync | untrusted caller | capability token v1 (HMAC) | per method, see §2 | package semver | all of §4 | registry codes | metadata + payload |
| B2 | `PK_BULK_MANIFEST/1` (JSON) | control plane (INV-36/GAP-14) → INV-37 | in, sync | untrusted | via B1 token | `create-transfer` | schema id | size/chunk/count | `invalid_manifest` | metadata |
| B3 | `PK_BULK_CHUNK/1` payloads | producer → INV-37 | in, sync per chunk | untrusted | via B1 | `write-chunk` | schema id | chunk bytes | `digest_mismatch` | payload (tenant data) |
| B4 | `PK_BULK_RESUME/1` (legacy, read-only) and `/2` (MAC-bound) | INV-37 ↔ peer | both | untrusted | `/2`: HMAC | `read-progress`, `resume` | schema id; negotiation | 1000 listed indices per response | `resume_conflict`, `stale_owner`, `authentication_failed` | metadata |
| B5 | Shared-memory descriptor `INV37_SHM_DESCRIPTOR/1` + region | INV-37 (owner) → producer (attacher) | out, then producer writes | producer untrusted | HMAC binding | `attach-buffer` | ABI id | `max_mapped_bytes` | `authorization_denied`, `transfer_closed`, `unsupported_capability` | payload |
| B6 | Config files `INV37_CONFIG/1` | operator → INV-37 | in at activation | operator-trusted, validated | file permissions | n/a (deployment) | schema id | — | `invalid_config` | config (no secrets) |
| B7 | Key ring file | secret manager → INV-37 | in at start | trusted, mode 0600 | filesystem | n/a | JSON {keys, active, revoked} | ≥32-byte keys | `invalid_config` | **secret** |
| B8 | Checkpoint store `INV37_CHECKPOINT/1`, `INV37_LEASE/1`, `data.bin` | INV-37 ↔ local filesystem | both | semi-trusted disk | seal HMAC | n/a | schema id | `checkpoint.max_bytes`, retention | `checkpoint_corrupt`, `stale_owner`, `quota_exceeded` | payload + metadata |
| B9 | Audit log (hash-chained JSONL) | INV-37 → SIEM | out | append-only | chain MAC | `inspect` to read via ops | `INV37_AUDIT_CHAIN/1` | — | verify failure refuses start | security metadata |
| B10 | Structured logs (JSONL) | INV-37 → log pipeline | out, best-effort | — | — | — | fields in OBSERVABILITY.md | ring 2000 in memory | export errors degrade health | pseudonymised metadata |
| B11 | Metrics (`snapshot()`, Prometheus text) | INV-37 → scraper | out, pull | — | embedding service | — | metric names | reservoir 4096 | — | aggregate |
| B12 | Trace context (W3C `traceparent`) | caller ↔ INV-37 | both | untrusted, validated | — | — | W3C v00 | — | malformed → new trace | ids |
| B13 | Health / diagnostics / explain | INV-37 → operator | out, sync | — | token | `read-progress` / `inspect` | fields | — | — | metadata; tenant pseudonymised unless `inspect` |
| B14 | Optional `pk_core` governance adapter | INV-37 → pk_core | out | trusted code | — | — | **unpinned** (optional) | — | tests NOT_EXECUTED if absent | none |
| B15 | Production-gate evidence (`artifacts/`, `governance/`) | CI/owners → gate | in | reviewed | HMAC signature | owners | schema ids | — | BLOCKED | release metadata |
| B16 | Policy precedence `INV37_PRECEDENCE/1` | architecture owner → INV-37 | in | reviewed | file review | — | version + digest | — | `invalid_config` | policy |

External dependencies: **required** — CPython ≥3.10 stdlib, local filesystem for checkpoints (prod/stage/edge); **optional** — shared memory (fallback: copy path, degraded), pk_core (tests not executed), log export (degraded); **unsupported** — host/guest shared memory, network transport, remote KMS, encryption provider (fail closed when required).

Memory/handle ownership (B5): only the creating data plane unlinks a region; attachers may close their mapping only; the descriptor is invalid after `cancel`/`close`/`quarantine`/`revoke`. Checkpoint file handles are opened per write and closed before returning.

## 2. Python API and required capability

| Method | Capability | Idempotency / sync | Cancellation / timeout |
|---|---|---|---|
| `create_transfer(token, manifest, transfer_id=…)` | `create-transfer` | idempotent for same (id, object, tenant); `resume_conflict` otherwise | admission waits ≤ `timeouts.admission` |
| `region_view(token, tid)` | `attach-buffer` | read-only accessor | — |
| `accept_chunk(token, tid, index, payload=None)` | `write-chunk` | duplicate chunk = no-op | idle → `DISCONNECTED` via `sweep`; checkpoint I/O → retryable `timeout` |
| `resume_token(token, tid)` | `read-progress` | pure | — |
| `reconcile(token, tid, peer_token)` | `resume` | pure except DISCONNECTED→RECEIVING | token `max_age` |
| `finalize(token, tid)` | `finalize` | idempotent after VERIFIED | `timeouts.final_verification` (advisory) |
| `cancel(token, tid)` | `cancel` | idempotent | releases slot, region, checkpoint |
| `close(token, tid)` | `finalize` | idempotent | releases resources |
| `quarantine(admin, tid, reason)` / `quarantine_tenant(admin, tenant, on)` / `release(admin, tid)` | `quarantine` / `release` | idempotent | — |
| `freeze(admin, on)` | `freeze` | idempotent | wakes waiters with `admission_frozen` |
| `recover()` | (startup, operator) | re-entrant per checkpoint | — |
| `sweep(now)` | (scheduler) | idempotent | enforces idle and total timeouts |
| `health()` | none (local) | pure | — |
| `diagnostics(token, tid)` | `read-progress` or `inspect` | pure | — |
| `explain(admin, tid=None)` | `inspect` | pure | — |
| `negotiate(offer)` (module) | n/a | pure | — |

Timeout classes (`timeouts.*`): admission, idle_chunk, total_transfer, final_verification, checkpoint_flush, shutdown. Retry classes come from `outcomes.ERROR_CODES` and are applied by `retry.RetryPolicy` (full-jitter exponential backoff, attempt cap, retry budget). Integrity and security failures are never retried. Backpressure: saturation → `admission_rejected`/`quota_exceeded` with `reason`; memory/mapping pressure → `quota_exceeded`; storage pressure → `quota_exceeded` from the checkpoint store.

## 3. Version negotiation (C027)

`negotiate(offer)` picks the highest mutually supported version for each surface in `SUPPORTED` (manifest, chunk, resume, transport, auth). Refusals (`version_incompatible`): no mutual version; peer omits manifest/chunk; peer omits auth while auth is required (**no silent downgrade**); unknown mandatory features. `encryption` as a mandatory feature → `encryption_unavailable` until a provider is approved. Unknown optional surfaces are ignored. Rolling upgrade: 4.3 peers speak RESUME/2 with 4.3 and RESUME/1 with 4.2 (fixture `negotiate.v1_peer`).

## 4. Authoritative limits table (C028)

| Limit | Key | Default (prod) | Kind | Error when exceeded | Validation order |
|---|---|---|---|---|---|
| Object bytes | `limits.max_object_bytes` | 1 GiB | config-time | `invalid_manifest` | 1 (manifest) |
| Chunk bytes | `limits.max_chunk_bytes` | 16 MiB | config-time | `invalid_manifest` | 2 |
| Chunk count | `limits.max_chunks` | 262,144 | compile/default-only (not overridable) | `invalid_manifest` | 3 |
| Active transfers (global) | `limits.max_concurrent_transfers` | 8 | config-time | `admission_rejected` | 5 |
| Pending transfers | `limits.max_pending_transfers` | 32 | config-time | `admission_rejected` | 4 |
| Bytes in flight (global) | `limits.host_memory_budget` | 8 GiB | config-time | `admission_rejected` | 5 |
| Per-tenant active / bytes | `tenancy.*` | 2 / 2 GiB | config-time | `quota_exceeded` | 5 |
| Mapped bytes per region | `limits.max_mapped_bytes` | 4 GiB | config-time | `quota_exceeded` | 6 |
| Checkpoint storage | `checkpoint.max_bytes` | 64 GiB | config-time | `quota_exceeded` | 6 |
| Retry attempts | `retry.max_attempts` (∩ registry) | 5 | config-time | original error | — |
| Replay cache | `Authenticator(replay_cache)` | 100,000 nonces | code | oldest evicted | — |
| Resume response indices | code | 1000 | code | truncated with `missing_count` | — |
| Open connections / fan-out | n/a — INV-37 has no network listener; owned by INV-36/INV-38 | — | externally imposed | — | — |

Preflight rejects unsafe combinations (worst-case memory, mapped > budget, inverted retry). Current limits and utilization are exposed by `health()`. The limits schema is part of `INV37_CONFIG/1` and its digest is in configuration provenance.

## 5. Error codes

All codes are listed with outcome/retry semantics in SEMANTICS.md §7: `invalid_manifest`, `digest_mismatch`, `object_digest_mismatch`, `transfer_incomplete`, `admission_rejected`, `quota_exceeded`, `transfer_closed`, `illegal_transition`, `cancelled`, `timeout`, `quarantined`, `admission_frozen`, `authentication_failed`, `authorization_denied`, `replay_detected`, `security_service_unavailable`, `unsupported_capability`, `version_incompatible`, `invalid_config`, `checkpoint_corrupt`, `stale_owner`, `resume_conflict`, `encryption_unavailable`, `residency_violation`, `bulk_data_plane_error`.
