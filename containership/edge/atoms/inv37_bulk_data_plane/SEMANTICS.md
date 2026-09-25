# INV-37 Bulk data plane — semantics, lifecycle and non-functional objectives

**Version:** 4.3.0 · **Status:** normative for the repository; production numbers marked *proposed* need accountable-role approval (see `governance/APPROVALS.json`).

Covers INV-37-C012, C013, C014, C015, C017, C018. The tables between the markers are generated from code by `tools/render_semantics.py`; `tests/test_docs.py` fails if they drift.

## 1. Outcome classes (C014)

| Class | Meaning | Payload/state reuse |
|---|---|---|
| success | Object verified end to end (`VERIFIED`) | Object may be consumed |
| partial_success | Some chunks verified; transfer resumable | Verified chunks kept; object must not be consumed |
| degraded_success | Verified via an approved fallback (copy transport when shm unavailable; recorded in `transport_select` decision) | As success; health reports `degraded` |
| retryable_failure | Transient (admission, timeout, checkpoint I/O, security service outage) | Progress kept; retry per registry |
| terminal_failure | Contract violation, cancellation, incompatible version | Start a new transfer where registry says so |
| policy_rejection | Quota, freeze, residency, encryption-required | Nothing allocated |
| security_rejection | Authn/authz/replay/quarantine/corrupt checkpoint | Nothing reused; quarantined state is frozen |

Caller obligations after: **cancellation** — discard handles, do not reuse id; **timeout** — call `resume_token`/`reconcile`, re-send `missing`; **peer disconnect** — transfer moves to `DISCONNECTED` after `timeouts.idle_chunk`, resume by sending chunks; **local crash** — on restart `recover()` reloads sealed checkpoints into `DISCONNECTED`, peers reconcile; **final verification failure** — transfer is `QUARANTINED`, treat as integrity incident (RUNBOOK §Incident).

Embedding-service reaction examples:

```python
try:
    dp.accept_chunk(tok, tid, i, payload)
except BulkDataPlaneError as e:
    c = classify(e)
    if c["outcome"] == "retryable_failure":   RetryPolicy().run(lambda: dp.accept_chunk(tok, tid, i, payload))
    elif e.code == "digest_mismatch":         refetch_chunk_from_source(i)          # never resend same bytes
    elif c["outcome"] == "security_rejection": page_security(e.code); stop()
    else:                                     abandon(tid, new_id=c["new_transfer_id_required"])
```

## 2. Consistency semantics (C013, C015)

- A chunk is **visible** (counted in `verified`, included in resume tokens) only after its digest verified and — on the durable path — after data fsync *and* the sealed state record was atomically replaced. Chunk acceptance and lifecycle updates occur under the per-transfer lock, so readers never see a verified count ahead of durable state.
- Duplicate delivery of an already-verified chunk is a no-op (`new: false`, `duplicate_chunks_total`), including after completion.
- `finalize` is idempotent once `VERIFIED`; concurrent `finalize` calls serialize on the transfer lock.
- Resume authority is the **receiver**: on reconnect, peer-claimed indices that the receiver has not verified are reported as `peer_overclaimed` and re-requested (`resume_conflict` if the token names another object/transfer).
- Fencing: every durable write checks the lease epoch; a superseded owner receives `stale_owner` and cannot write (split-brain protection).

## 3. Non-functional objectives (C013, C062, C091) — *proposed*

Numbers below are proposed for approval. "Measured" values come from `artifacts/benchmarks/baseline.json` (audit sandbox, 64 MiB object, 1 MiB chunks, CPython 3.11); they are *not* production baselines.

| Objective | Proposed threshold | Measured (sandbox) | Metric |
|---|---|---|---|
| Manifest validation latency (≤262,144 chunks) | p99 ≤ 250 ms | n/a (unit-scale) | `manifest_validate_seconds` |
| Chunk acceptance, shm path, 1 MiB | p50 ≤ 5 ms, p99 ≤ 10 ms, max ≤ 50 ms | p50 2.5 ms / p99 2.7 ms | `chunk_accept_seconds` |
| Chunk acceptance, durable fsync, 64 KiB | p99 ≤ 20 ms on SSD | see baseline | `chunk_accept_seconds` |
| Final assembly/verification, 1 GiB | p99 ≤ 8 s | scales linearly with hash rate | `finalize_seconds` |
| Resume-state generation | p99 ≤ 5 ms per 10k chunks | — | `resume_token_seconds` |
| Data-plane copies, shm path | **0** (hard) | 0; peak alloc 0.03% of object | `CopyCounter`, tracemalloc |
| Availability (successful transfers / attempted, excl. caller cancellations & policy rejections) | ≥ 99.9 % per 28-day window | — | `transfers_verified_total / transfers_created_total` |
| Acknowledged-progress loss on crash (durable path) | 0 acknowledged chunks (RPO = 0 for acked chunks) | crash tests pass | `test_checkpoint.test_crash_during_write_sequence` |
| Restart recovery (RTO) | ≤ 30 s for 10k transfers | see baseline `restart_recovery_s` | `transfers_recovered_total` |
| Cross-tenant memory exposure | 0 bytes | descriptor binding tests | security tests |
| Noisy neighbour | one tenant ≤ its quota; others admitted by fair share | contention tests | `admission_rejected_total{reason}` |
| Determinism | same inputs → same digests, error codes, transitions, effective config digest on all certified runtimes | conformance fixtures | conformance report |

Resource budgets by profile are in `config/profiles/*.json`; preflight rejects any combination whose worst case (`max_concurrent_transfers × max_object_bytes`, `max_mapped_bytes`) exceeds `host_memory_budget`.

## 4. Deployment contexts (C012)

| Context | Support | Topology | Transport | Durability | Limits profile | Conformance profile |
|---|---|---|---|---|---|---|
| Cloud / datacenter, same host producer+receiver | **Supported** | processes on one host | shm (zero-copy) or copy | checkpoint dir on local SSD | `prod.json` | full suite |
| Cloud / datacenter, cross-host | **Conditionally supported** — copy path only; network transport belongs to INV-36/INV-38 | embedding service moves chunks | copy | checkpoint | `prod.json` | full suite minus shm |
| Host ↔ guest VM | **Unsupported** (fails closed: `unsupported_capability`) | — | virtio/vhost not implemented | — | — | gate criterion `host_guest_zero_copy` |
| Near-edge | **Conditionally supported** | single node | shm if available else copy | checkpoint, shorter retention | `edge.json` | full suite on target hardware (not yet run) |
| Far-edge, intermittent connectivity | **Conditionally supported** | single constrained node | copy | checkpoint mandatory; offline resume via sealed state | `edge.json` (reduced concurrency 2, 1 GiB budget) | power/thermal unmeasured → gate BLOCKED |

Multi-zone: each site runs its own instance; cross-zone moves must pass `security.allowed_regions` and tenant `regions` (residency is evaluated before admission and cannot be overridden). New contexts are added by (1) a profile file, (2) a conformance run on that hardware stored as external evidence, (3) architecture approval.

## 5. Disconnected operation (C018)

- New transfers may start while offline **only** if authentication can be performed locally (key ring file present, clock readable). If the time source fails, authentication fails closed (`security_service_unavailable`).
- Idle transfers become `DISCONNECTED` after `timeouts.idle_chunk`; verified progress remains durable. Abandoned transfers are garbage-collected after `checkpoint.retention`; storage is bounded by `checkpoint.max_bytes` (`quota_exceeded` beyond it).
- Reconnect handshake: `reconcile(token, tid, PK_BULK_RESUME/2)` validates MAC, age (`max_age`), fencing epoch and object identity; stale or foreign tokens are rejected; the receiver's verified set wins.
- Source changes: a changed source produces a different manifest object digest, which is rejected as `resume_conflict` for the old transfer id.
- Operators inspect stranded state with `CheckpointStore.export_inventory()` (no payload bytes) and delete via `delete`/`gc`, or quarantine via `quarantine`.

## 6. Quotas and fairness (C017)

Hard safety ceilings (global active transfers, global bytes in flight = `host_memory_budget`, pending queue) are never exceeded. Per-tenant soft quotas (`max_active_transfers`, `max_bytes_in_flight`, `weight`) come from configuration. Waiters are admitted by lowest `active/weight`, ties by arrival — a tenant below its quota cannot be starved by a tenant at its quota. Tenant identity is the authenticated token's tenant; labels supplied by callers are ignored. Saturation and throttle reasons are exported (`admission.metrics()`). Capacity formula: `bytes_needed ≈ Σ_tenants min(quota_bytes, active × p95_object_size)`; `max_concurrent_transfers ≤ host_memory_budget / max_object_bytes`.

## 7. Generated tables

<!-- BEGIN GENERATED -->
### Outcome and error-code registry (from `outcomes.ERROR_CODES`)

| Code | Outcome class | Retryable | Max attempts | New transfer id | Progress | Caller obligation |
|---|---|---|---|---|---|---|
| `admission_frozen` | policy_rejection | yes | 3 | no | none | Operator freeze/emergency disable is active. |
| `admission_rejected` | retryable_failure | yes | 5 | no | none | Back off with jitter (see retry.RetryPolicy) and retry. |
| `authentication_failed` | security_rejection | no | 0 | no | none | Obtain a fresh credential; details intentionally minimal. |
| `authorization_denied` | security_rejection | no | 0 | no | none | Principal lacks the capability for this action/scope. |
| `bulk_data_plane_error` | terminal_failure | no | 0 | no | none | Generic; should not be raised by production paths. |
| `cancelled` | terminal_failure | no | 0 | yes | discard | Transfer was cancelled by caller or operator. |
| `checkpoint_corrupt` | security_rejection | no | 0 | yes | quarantine | Checkpoint failed its seal; quarantined file retained for investigation. |
| `digest_mismatch` | terminal_failure | no | 0 | no | keep | Re-send the offending chunk from source; never re-send the same bytes blindly. |
| `encryption_unavailable` | policy_rejection | no | 0 | no | none | Policy requires encryption and no approved provider is configured. |
| `illegal_transition` | terminal_failure | no | 0 | no | keep | Caller bug: operation not legal in current lifecycle state. |
| `invalid_config` | terminal_failure | no | 0 | no | none | Fix configuration; admission stays disabled. |
| `invalid_manifest` | terminal_failure | no | 0 | yes | none | Fix or re-fetch the manifest from the authenticated control plane. |
| `object_digest_mismatch` | terminal_failure | no | 0 | yes | quarantine | Final verification failed; transfer is quarantined. Escalate as integrity incident. |
| `quarantined` | security_rejection | no | 0 | yes | quarantine | Transfer or tenant is quarantined; operator release required. |
| `quota_exceeded` | policy_rejection | yes | 5 | no | none | Tenant quota exhausted; retry after in-flight transfers drain. |
| `replay_detected` | security_rejection | no | 0 | no | none | Token nonce reused; mint a new token. |
| `residency_violation` | policy_rejection | no | 0 | yes | none | Destination region not permitted for this tenant's data. |
| `resume_conflict` | terminal_failure | no | 0 | no | keep | Peer resume token disagrees with local verified progress; local state wins. |
| `security_service_unavailable` | retryable_failure | yes | 3 | no | keep | Key/identity/policy/time service unavailable; fail closed and retry later. |
| `stale_owner` | terminal_failure | no | 0 | no | keep | Fencing epoch superseded; another owner holds the transfer. |
| `timeout` | retryable_failure | yes | 3 | no | keep | Deadline exceeded; resume with the resume token. |
| `transfer_closed` | terminal_failure | no | 0 | yes | none | Transfer was closed; start a new transfer. |
| `transfer_incomplete` | partial_success | yes | 0 | no | keep | Resume: send the chunks listed in details.missing. |
| `unsupported_capability` | terminal_failure | no | 0 | yes | none | Platform lacks a required capability; choose a supported profile. |
| `version_incompatible` | terminal_failure | no | 0 | yes | none | No mutually supported protocol profile; upgrade a peer. |

### Lifecycle transition table (from `lifecycle.TRANSITIONS`)

Every (state, event) pair not listed is refused with `illegal_transition`; the state is left unchanged.

| From | Event | To |
|---|---|---|
| cancelled | close | closing |
| cancelling | cancel_done | cancelled |
| closing | close_done | closed |
| complete_unverified | cancel | cancelling |
| complete_unverified | quarantine | quarantined |
| complete_unverified | terminal_error | failed_terminal |
| complete_unverified | verify_fail | quarantined |
| complete_unverified | verify_ok | verified |
| created | cancel | cancelling |
| created | terminal_error | failed_terminal |
| created | validate | validating |
| disconnected | cancel | cancelling |
| disconnected | quarantine | quarantined |
| disconnected | reconnect | receiving |
| disconnected | terminal_error | failed_terminal |
| failed_retryable | cancel | cancelling |
| failed_retryable | quarantine | quarantined |
| failed_retryable | retry | receiving |
| failed_retryable | terminal_error | failed_terminal |
| failed_terminal | close | closing |
| quarantined | close | closing |
| quarantined | release | failed_terminal |
| ready | all_chunks | complete_unverified |
| ready | cancel | cancelling |
| ready | chunk | receiving |
| ready | disconnect | disconnected |
| ready | quarantine | quarantined |
| ready | terminal_error | failed_terminal |
| receiving | all_chunks | complete_unverified |
| receiving | cancel | cancelling |
| receiving | chunk | receiving |
| receiving | disconnect | disconnected |
| receiving | quarantine | quarantined |
| receiving | retryable_error | failed_retryable |
| receiving | terminal_error | failed_terminal |
| validating | cancel | cancelling |
| validating | reject | failed_terminal |
| validating | terminal_error | failed_terminal |
| validating | validated | ready |
| verified | close | closing |
| verified | quarantine | quarantined |

Idempotent repeats (no-op): `cancel` in {cancelled, cancelling}; `close` in {closed, closing}; `quarantine` in {quarantined}; `verify_ok` in {verified}
<!-- END GENERATED -->
