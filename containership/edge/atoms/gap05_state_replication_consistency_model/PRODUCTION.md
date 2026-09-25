# GAP-05 v4.3.0 - Production layer design record

Generated from `production/registry.py` by `evidence/run_evidence.py`. Unreviewed.
Owner and reviewer are **UNASSIGNED** for every component.

## MC01 - Authenticated replica identity <a id="mc01"></a>

- **Modules:** identity.py, membership.py
- **Invariants (safety / liveness / durability / isolation):** A session's replica is derived only from a CA-verified credential + proof of possession bound to the channel; payload site names never authenticate; one identity maps to exactly one active replica per epoch.
- **Interfaces, error codes, retry semantics:** IdentityVerifier.challenge/authenticate -> AuthenticatedPeer; codes SEC_UNTRUSTED_ISSUER, SEC_BAD_CREDENTIAL, SEC_WRONG_TRUST_DOMAIN, SEC_WILDCARD, SEC_REVOKED, SEC_EXPIRED, SEC_REPLAY, SEC_CHANNEL_MISMATCH, SEC_BAD_POP, SEC_UNKNOWN_IDENTITY, SEC_STALE_MEMBERSHIP, SEC_AMBIGUOUS_IDENTITY, SEC_KEY_NOT_REGISTERED. Not retryable.
- **Persistence:** Ephemeral (nonces in memory, bounded 10,000); trust bundle and revocation list are supplied by deployment - no durable revocation store in this build.
- **Concurrency:** Nonce table under a lock; single-use pop is atomic.
- **Bounds:** max_outstanding_nonces=10,000 -> CAP_HANDSHAKE.
- **Observability:** Rejections carry codes into logs/metrics via the node; peer identity lands in audit 'principal'.
- **Configuration:** trust_domain, grace_seconds, CA bundle.
- **Runbook:** RB-06 identity/key failure.
- **Threat model:** Spoofed site field, stolen credential without key, replayed handshake, rogue CA, revoked/expired cert, wildcard SAN.
- **Performance evidence:** Not benchmarked separately (Ed25519 verify ~50us class).
- **Not done in this build:** No real mTLS/SPIRE integration; no durable CRL/OCSP; credential renewal automation absent.

## MC02 - Signed/attested write provenance <a id="mc02"></a>

- **Modules:** protect.py, schemas.py
- **Invariants (safety / liveness / durability / isolation):** No write mutates frontier, dedupe, WAL or audit before its Ed25519 signature verifies against the key registered for the *author* in membership.
- **Interfaces, error codes, retry semantics:** sign_write/verify_write; SEC_UNSIGNED, SEC_BAD_ALG, SEC_UNKNOWN_AUTHOR, SEC_KEY_NOT_REGISTERED, SEC_KEY_NOT_PROVISIONED, SEC_BAD_SIGNATURE.
- **Persistence:** Signature + key_id persist with the write in WAL/snapshot; private keys never persisted by the node.
- **Concurrency:** Pure functions.
- **Bounds:** Signature text <=512 bytes (schema).
- **Observability:** Rejection counters by code.
- **Configuration:** Algorithm fixed to ed25519 (no negotiation => no downgrade).
- **Runbook:** RB-06.
- **Threat model:** Field/vector/value substitution, cross-tenant replay, algorithm downgrade, truncated signature.
- **Performance evidence:** Included in node_write latency.
- **Not done in this build:** Per-batch/hierarchical signing not implemented; historical-key retirement policy not defined.

## MC03 - Trusted monotonic counter allocation <a id="mc03"></a>

- **Modules:** membership.py (CounterAllocator, CounterGuard)
- **Invariants (safety / liveness / durability / isolation):** No two accepted writes by one replica share a (key, counter); counters never decrease across crash/restart/restore; jumps beyond max_gap and reuse are refused with evidence.
- **Interfaces, error codes, retry semantics:** CounterAllocator.next/observe; CounterGuard.check/record; SEC_COUNTER_JUMP, SEC_COUNTER_EQUIVOCATION, CORR_COUNTER_OWNER.
- **Persistence:** Durable reservation ceiling (atomic write + fsync) under an exclusive flock; guard state in snapshots.
- **Concurrency:** Thread lock + cross-process flock; tested with 8 threads and 4 processes.
- **Bounds:** Counter <= 2^63-1 (schema), max_gap default 1024.
- **Observability:** Guard evidence list; rejection counters.
- **Configuration:** block size, max_gap.
- **Runbook:** RB-06, RB-02.
- **Threat model:** Rollback after restore, counter reuse, extreme jumps.
- **Performance evidence:** Not separately benchmarked.
- **Not done in this build:** An authenticated but compromised replica can still jump within max_gap; no external counter authority (lease/consensus).

## MC04 - Durable write-ahead log and recovery <a id="mc04"></a>

- **Modules:** durable.py (WriteAheadLog), node.py
- **Invariants (safety / liveness / durability / isolation):** A write is acknowledged only after its WAL frame is fsynced; recovery truncates only a torn tail and fails closed on mid-log corruption; replay is deterministic.
- **Interfaces, error codes, retry semantics:** WriteAheadLog.append/records_after/compact_before; CORR_WAL_CORRUPT, CORR_WAL_SEQUENCE, CORR_FAIL_STOP.
- **Persistence:** Framed sha256 records with sequence numbers; optional AES-GCM value encryption; compaction after snapshot.
- **Concurrency:** Append under a lock; node shards serialize per key.
- **Bounds:** Grows until checkpoint; checkpoint compacts.
- **Observability:** wal_records gauge; recovery_report (records, truncated bytes/reason, replayed, rejected, audit_backfilled).
- **Configuration:** Data directory; fsync always on (not configurable by design).
- **Runbook:** RB-02 WAL corruption.
- **Threat model:** Torn writes, bit rot, truncated tails.
- **Performance evidence:** recovery_records_per_s measured.
- **Not done in this build:** Single WAL file (no segment rotation); group commit only per record.

## MC05 - Crash-consistent snapshots/checkpoints <a id="mc05"></a>

- **Modules:** durable.py (SnapshotStore), node.checkpoint
- **Invariants (safety / liveness / durability / isolation):** A snapshot is published only by atomic rename after fsync and embeds a sha256; recovery takes the newest valid generation and falls back; frontier incl. quarantine is preserved exactly.
- **Interfaces, error codes, retry semantics:** SnapshotStore.write/validate/latest_valid; CORR_SNAPSHOT_UNREADABLE/CHECKSUM/FORMAT.
- **Persistence:** snapshot-<generation>.json, keep=3 generations.
- **Concurrency:** Checkpoint takes every shard lock (consistent cut).
- **Bounds:** keep=3.
- **Observability:** snapshot_generation in health.
- **Configuration:** keep.
- **Runbook:** RB-02.
- **Threat model:** Partial writes, corrupted generation.
- **Performance evidence:** Not separately benchmarked.
- **Not done in this build:** Snapshot is not signed (checksum only); no manifest-level signature.

## MC06 - Tenant/environment namespace enforcement <a id="mc06"></a>

- **Modules:** node.py (state_key), schemas.py, authz.py
- **Invariants (safety / liveness / durability / isolation):** State key = tenant \x1f environment \x1f key; the separator is forbidden in every component, so namespaces cannot alias; every operation is authorized per (tenant, environment).
- **Interfaces, error codes, retry semantics:** NamespaceError (SEC_NAMESPACE), AuthorizationError.
- **Persistence:** Namespace is part of every persisted doc and of op_id.
- **Concurrency:** N/A.
- **Bounds:** Per-tenant admission buckets.
- **Observability:** Denied cross-tenant operations audited.
- **Configuration:** Grants per tenant/env.
- **Runbook:** RB-07.
- **Threat model:** Namespace confusion, separator injection, cross-tenant replay.
- **Performance evidence:** N/A.
- **Not done in this build:** Unicode normalisation (NFC) of identifiers not enforced - identifiers compared byte-exact.

## MC07 - Concrete wire schemas <a id="mc07"></a>

- **Modules:** schemas.py, schemas/*.schema.json, schemas/corpus
- **Invariants (safety / liveness / durability / isolation):** Strict ingress: unknown fields, duplicate JSON keys, lone surrogates, non-canonical vectors and op_id mismatch are rejected.
- **Interfaces, error codes, retry semantics:** validate_write_doc/validate_merge_result/validate_conflict_set; CORR_SCHEMA_* codes.
- **Persistence:** Schemas shipped as JSON-Schema 2020-12 documents.
- **Concurrency:** Pure functions.
- **Bounds:** Field byte limits from Limits.
- **Observability:** Rejection counters.
- **Configuration:** Limits.
- **Runbook:** -
- **Threat model:** Parser abuse, oversized fields.
- **Performance evidence:** codec_json_roundtrip_us measured.
- **Not done in this build:** Only a Python validator exists; no second-language validator to cross-check.

## MC08 - Schema/version negotiation <a id="mc08"></a>

- **Modules:** schemas.negotiate
- **Invariants (safety / liveness / durability / isolation):** Highest common version per family; no common version is a refusal, never a silent downgrade.
- **Interfaces, error codes, retry semantics:** negotiate(); CORR_NEGOTIATION_MISSING, CORR_NEGOTIATION_NONE, CORR_INCOMPATIBLE_VERSION.
- **Persistence:** Schema id persisted in every doc.
- **Concurrency:** Pure.
- **Bounds:** -
- **Observability:** health.schemas.
- **Configuration:** SUPPORTED map.
- **Runbook:** -
- **Threat model:** Downgrade attack.
- **Performance evidence:** -
- **Not done in this build:** Only version 1 exists; N+1 behaviour is tested only as rejection.

## MC09 - Durable deduplication identity <a id="mc09"></a>

- **Modules:** schemas.op_id_for, node.recent_ops
- **Invariants (safety / liveness / durability / isolation):** op_id = sha256(canonical semantic content); exact replay is idempotent across restart/checkpoint; same author counter with different content is equivocation.
- **Interfaces, error codes, retry semantics:** Outcome 'duplicate'; SEC_COUNTER_EQUIVOCATION, SEC_VECTOR_EQUIVOCATION.
- **Persistence:** Frontier op_ids + bounded recent window in snapshot; older replays fall back to causal 'superseded'.
- **Concurrency:** Under shard lock.
- **Bounds:** recent_window=100,000.
- **Observability:** replay_total counter.
- **Configuration:** recent_window.
- **Runbook:** -
- **Threat model:** Replay storms, equivocation.
- **Performance evidence:** -
- **Not done in this build:** Dedupe window not coordinated with an anti-entropy horizon setting.

## MC10 - Tamper-evident audit ledger <a id="mc10"></a>

- **Modules:** audit.py
- **Invariants (safety / liveness / durability / isolation):** Every accepted write, resolution, freeze, GC, checkpoint and authz denial is appended to a sha256 hash chain whose head is Ed25519-signed; verification detects modification, deletion, reorder and truncation against a retained head.
- **Interfaces, error codes, retry semantics:** AuditLedger.append/signed_head/verify; CORR_AUDIT_CHAIN/TAMPER/TRUNCATED/SEGMENT/HEAD_SIG.
- **Persistence:** Segmented JSONL + .start markers; fsync per record; crash window WAL->audit back-filled on recovery.
- **Concurrency:** Append under lock.
- **Bounds:** segment_records x max_active_segments.
- **Observability:** audit_pressure in health.
- **Configuration:** segment size, archive dir.
- **Runbook:** RB-05.
- **Threat model:** Log tampering, truncation, forged head.
- **Performance evidence:** -
- **Not done in this build:** Signing key is the node key (no HSM/KMS); signed head is not yet shipped to an external witness.

## MC11 - Bounded audit/quarantine retention policy <a id="mc11"></a>

- **Modules:** audit.py, node.py (CAP_FRONTIER_FULL)
- **Invariants (safety / liveness / durability / isolation):** Reaching a bound refuses new work (retryable) instead of dropping recorded state; archive handoff verifies before deletion.
- **Interfaces, error codes, retry semantics:** CAP_AUDIT_FULL, CAP_FRONTIER_FULL.
- **Persistence:** Archive directory.
- **Concurrency:** -
- **Bounds:** max_unresolved_per_key, max_quarantine_total, audit segments.
- **Observability:** audit_pressure, quarantine_pressure.
- **Configuration:** Limits.
- **Runbook:** RB-03, RB-05.
- **Threat model:** Conflict flooding.
- **Performance evidence:** quarantine flood bench.
- **Not done in this build:** No hysteresis/watermarks; no per-tenant byte quotas.

## MC12 - Encryption and managed key rotation <a id="mc12"></a>

- **Modules:** protect.Keyring, node._seal
- **Invariants (safety / liveness / durability / isolation):** Values in WAL/snapshots are AES-256-GCM with AAD bound to tenant/environment/purpose/key id; missing key = hard recovery failure (readiness false).
- **Interfaces, error codes, retry semantics:** Keyring.rotate/encrypt/decrypt/rewrap/retire; SEC_KEY_UNAVAILABLE, CORR_AEAD_TAG, CORR_KEY_IN_USE.
- **Persistence:** Key ids persisted in envelopes; key material not persisted by the node.
- **Concurrency:** Lock around refs.
- **Bounds:** -
- **Observability:** Recovery rejected count.
- **Configuration:** Keyring injection.
- **Runbook:** RB-06.
- **Threat model:** Wrong-tenant decrypt, ciphertext tamper.
- **Performance evidence:** -
- **Not done in this build:** No KMS integration; transport encryption (TLS) not implemented; keyring is in-memory.

## MC13 - Authorization policy integration <a id="mc13"></a>

- **Modules:** authz.py
- **Invariants (safety / liveness / durability / isolation):** Default deny; every externally reachable mutation checks an explicit permission; provider failure denies; wildcard scopes only for declared break-glass principals.
- **Interfaces, error codes, retry semantics:** Authorizer.require; SEC_FORBIDDEN.
- **Persistence:** Policy supplied per call (no cache).
- **Concurrency:** Stateless.
- **Bounds:** -
- **Observability:** Denials and privileged decisions audited with policy_version.
- **Configuration:** Policy provider.
- **Runbook:** RB-07.
- **Threat model:** Privilege escalation, confused deputy, stale grants.
- **Performance evidence:** -
- **Not done in this build:** No attribute-based conditions (key scope, epoch) in grants.

## MC14 - Atomic configuration/membership store <a id="mc14"></a>

- **Modules:** membership.MembershipStore
- **Invariants (safety / liveness / durability / isolation):** Exactly one active generation per node; activation is CAS on epoch; history is a digest chain; rollback is forward.
- **Interfaces, error codes, retry semantics:** activate/rollback_to/add/remove/reseed; CORR_CAS_CONFLICT, CORR_MEMBERSHIP_CHAIN.
- **Persistence:** epoch-NNNNNNNN.json files via atomic write.
- **Concurrency:** RLock around CAS.
- **Bounds:** -
- **Observability:** membership_epoch in health.
- **Configuration:** Directory.
- **Runbook:** RB-04.
- **Threat model:** Racing controllers, tampered history.
- **Performance evidence:** -
- **Not done in this build:** Changes are not signed by the controller; distribution across nodes is out of scope (store is per node).

## MC15 - Replica membership-change protocol <a id="mc15"></a>

- **Modules:** membership.py
- **Invariants (safety / liveness / durability / isolation):** Removed replicas are fenced above their drained high-water; names are never reused (reseed => new incarnation name~N).
- **Interfaces, error codes, retry semantics:** remove_replica(high_water)/reseed_replica; SEC_FENCED_RETIRED.
- **Persistence:** Via membership store.
- **Concurrency:** -
- **Bounds:** -
- **Observability:** Audit via controller (not in store).
- **Configuration:** -
- **Runbook:** RB-04.
- **Threat model:** Old incarnation writes.
- **Performance evidence:** -
- **Not done in this build:** Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.

## MC16 - Production conflict-resolution adapter <a id="mc16"></a>

- **Modules:** resolution.py, node.resolve
- **Invariants (safety / liveness / durability / isolation):** Unavailable policy keeps the conflict open; a decision applies only if the frontier digest is unchanged; the resolving write dominates every active and quarantined sibling.
- **Interfaces, error codes, retry semantics:** ResolutionAdapter.request; DEP_POLICY_UNAVAILABLE, CORR_POLICY_DECISION, CORR_STALE_DECISION.
- **Persistence:** Decision evidence + policy version in audit.
- **Concurrency:** Worker thread per adapter.
- **Bounds:** retries, timeout.
- **Observability:** adapter.calls.
- **Configuration:** timeout_s, retries, backoff_s.
- **Runbook:** RB-03.
- **Threat model:** Compromised policy output.
- **Performance evidence:** -
- **Not done in this build:** No circuit breaker; no dry-run/explain mode; no live GAP-13 engine tested.

## MC17 - Anti-entropy/reconciliation engine <a id="mc17"></a>

- **Modules:** anti_entropy.py
- **Invariants (safety / liveness / durability / isolation):** Two replicas with eventual connectivity reach identical digest roots and frontiers; repair uses the normal authenticated accept path; floors travel first.
- **Interfaces, error codes, retry semantics:** digest_tree/sync_one_way/reconcile.
- **Persistence:** Stateless.
- **Concurrency:** Per-node shard locks.
- **Bounds:** 256 leaves.
- **Observability:** rounds report (differing leaves, sent, applied, rejected).
- **Configuration:** max_rounds.
- **Runbook:** RB-01.
- **Threat model:** Unauthenticated repair.
- **Performance evidence:** anti_entropy_keys_per_s measured.
- **Not done in this build:** Full scan to build the tree each call (no incremental maintenance); no scheduling/prioritisation.

## MC18 - Replication transport adapter <a id="mc18"></a>

- **Modules:** transport.py
- **Invariants (safety / liveness / durability / isolation):** Transport faults (drop/dup/reorder/delay) change only timing, never causal outcome; queues are bounded.
- **Interfaces, error codes, retry semantics:** encode_frame/decode_frame, ReliableSender, Link; CORR_FRAME_*, CAP_FRAME_SIZE, CAP_LINK_FULL, CAP_SENDER_BACKLOG.
- **Persistence:** None.
- **Concurrency:** Single-threaded pump.
- **Bounds:** window, max_pending, capacity, max_frame_bytes.
- **Observability:** Link.stats.
- **Configuration:** window/timeout/retries.
- **Runbook:** RB-01.
- **Threat model:** Malformed frames, slowloris (not tested).
- **Performance evidence:** -
- **Not done in this build:** No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.

## MC19 - Delete/tombstone semantics <a id="mc19"></a>

- **Modules:** node.delete, gc_tombstones
- **Invariants (safety / liveness / durability / isolation):** Deletes are causal writes; concurrent update vs delete is a conflict; GC only after all active replicas acknowledge, leaving a floor vector that blocks resurrection.
- **Interfaces, error codes, retry semantics:** delete/gc_tombstones.
- **Persistence:** Floors in snapshot and WAL 'gc' records.
- **Concurrency:** -
- **Bounds:** -
- **Observability:** tombstone_gc audit.
- **Configuration:** -
- **Runbook:** RB-01.
- **Threat model:** Stale resurrection.
- **Performance evidence:** -
- **Not done in this build:** Acknowledgement collection is supplied by the caller.

## MC20 - Vector compaction strategy <a id="mc20"></a>

- **Modules:** node floors, membership retirement
- **Invariants (safety / liveness / durability / isolation):** Collected keys keep one floor vector (retired-replica summary); dominance queries against pre-GC history are unchanged.
- **Interfaces, error codes, retry semantics:** -
- **Persistence:** Floors persisted.
- **Concurrency:** -
- **Bounds:** max_vector_entries.
- **Observability:** vector_entries histogram.
- **Configuration:** -
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** vector_bytes_N_replicas measured.
- **Not done in this build:** No dotted version vectors; live vectors are not compacted.

## MC21 - CRDT/commutative type registry <a id="mc21"></a>

- **Modules:** crdt.py
- **Invariants (safety / liveness / durability / isolation):** Only registered types merge; merges are commutative/associative/idempotent; read-time merge (no new writes).
- **Interfaces, error codes, retry semantics:** REGISTRY, merge_all; CORR_SCHEMA for unregistered.
- **Persistence:** value_type in the signed doc.
- **Concurrency:** Pure.
- **Bounds:** -
- **Observability:** read() reports merged type.
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Type confusion.
- **Performance evidence:** -
- **Not done in this build:** No delta/op-based CRDTs; no cross-language vectors.

## MC22 - Quarantine operator API <a id="mc22"></a>

- **Modules:** node.quarantine_list/export/freeze/unfreeze/resolve
- **Invariants (safety / liveness / durability / isolation):** Operator actions are authorized, audited and routed through normal invariant checks; freeze survives restart.
- **Interfaces, error codes, retry semantics:** CORR_KEY_FROZEN, CORR_STALE_DECISION.
- **Persistence:** freeze/unfreeze WAL records.
- **Concurrency:** Shard lock.
- **Bounds:** -
- **Observability:** Audit events.
- **Configuration:** -
- **Runbook:** RB-03.
- **Threat model:** Operator error, stale view.
- **Performance evidence:** -
- **Not done in this build:** No pagination cursor; no per-item immutable IDs beyond op_id.

## MC23 - Immutable/read-only state views <a id="mc23"></a>

- **Modules:** node.FrontierView
- **Invariants (safety / liveness / durability / isolation):** Views are frozen dataclasses of deep-copied MappingProxy docs; mutation cannot reach state.
- **Interfaces, error codes, retry semantics:** view().
- **Persistence:** -
- **Concurrency:** Built under the key's shard lock.
- **Bounds:** -
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Out-of-band mutation.
- **Performance evidence:** -
- **Not done in this build:** Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).

## MC24 - Persistence migration framework <a id="mc24"></a>

- **Modules:** lifecycle.migrate_*
- **Invariants (safety / liveness / durability / isolation):** Migrations are versioned, backed up first, idempotent, re-validated; downgrades and unknown formats refused; namespace never guessed.
- **Interfaces, error codes, retry semantics:** migrate_state/migrate_snapshot_dir; CORR_DOWNGRADE_REFUSED, CORR_NO_MIGRATION.
- **Persistence:** *.pre-migration-vN backups.
- **Concurrency:** Offline.
- **Bounds:** -
- **Observability:** Report list.
- **Configuration:** dry_run.
- **Runbook:** RB-08.
- **Threat model:** -
- **Performance evidence:** -
- **Not done in this build:** Only one hop (1->2); WAL format has no migration yet.

## MC25 - Backup/restore/reseed workflow <a id="mc25"></a>

- **Modules:** lifecycle.backup/verify_backup/restore
- **Invariants (safety / liveness / durability / isolation):** Restore verifies every digest and the audit chain first, never overwrites live state, and fences the node (recovery mode) until a peer reconcile completes.
- **Interfaces, error codes, retry semantics:** CORR_BACKUP_DIGEST, CORR_RESTORE_TARGET, CORR_RECOVERY_MODE.
- **Persistence:** MANIFEST.json + copies.
- **Concurrency:** Offline.
- **Bounds:** -
- **Observability:** health reasons.
- **Configuration:** -
- **Runbook:** RB-01.
- **Threat model:** Tampered backup, stale restore.
- **Performance evidence:** -
- **Not done in this build:** Backups are not encrypted as a set (values inside are, if a keyring is used); no RPO/RTO measurement at scale.

## MC26 - Observability package <a id="mc26"></a>

- **Modules:** observe.Metrics
- **Invariants (safety / liveness / durability / isolation):** Series are bounded; overflow is counted.
- **Interfaces, error codes, retry semantics:** exposition() Prometheus text.
- **Persistence:** In memory.
- **Concurrency:** Lock.
- **Bounds:** max_series.
- **Observability:** self.
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Label cardinality attack.
- **Performance evidence:** -
- **Not done in this build:** No SLO definitions agreed; no dashboards.

## MC27 - Structured logs/tracing <a id="mc27"></a>

- **Modules:** observe.StructuredLog
- **Invariants (safety / liveness / durability / isolation):** Values/secrets redacted by salted digest; errors never sampled out; trace ids are correlation only.
- **Interfaces, error codes, retry semantics:** emit().
- **Persistence:** In memory ring + sink.
- **Concurrency:** -
- **Bounds:** max_lines.
- **Observability:** -
- **Configuration:** sample_rate.
- **Runbook:** -
- **Threat model:** Log injection, secret leak.
- **Performance evidence:** -
- **Not done in this build:** No OpenTelemetry export.

## MC28 - Health/readiness endpoints <a id="mc28"></a>

- **Modules:** node.health
- **Invariants (safety / liveness / durability / isolation):** Readiness fails on fail-stop, recovery mode, rejected recovery records, audit/quarantine pressure, invalid membership.
- **Interfaces, error codes, retry semantics:** health() dict.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** self.
- **Configuration:** -
- **Runbook:** all RBs.
- **Threat model:** Info disclosure (no HTTP endpoint).
- **Performance evidence:** -
- **Not done in this build:** No HTTP server/authentication; no startup progression states.

## MC29 - Admission control/backpressure <a id="mc29"></a>

- **Modules:** observe.Admission
- **Invariants (safety / liveness / durability / isolation):** Hot keys throttle without blocking unrelated keys/tenants; metadata bounded.
- **Interfaces, error codes, retry semantics:** CAP_TENANT_RATE, CAP_HOT_KEY, CAP_RECOVERY_BURST (retryable).
- **Persistence:** -
- **Concurrency:** Called under shard lock.
- **Bounds:** max_tracked_keys.
- **Observability:** rejections Counter.
- **Configuration:** capacities/refills.
- **Runbook:** RB-03.
- **Threat model:** Noisy neighbour.
- **Performance evidence:** -
- **Not done in this build:** No reserved control-traffic class; buckets tick logically, not by time.

## MC30 - Resource limits <a id="mc30"></a>

- **Modules:** limits.Limits
- **Invariants (safety / liveness / durability / isolation):** All limits positive, consistent, validated at startup.
- **Interfaces, error codes, retry semantics:** LimitExceeded CAP_* codes.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** self.
- **Observability:** -
- **Configuration:** Limits.
- **Runbook:** -
- **Threat model:** Oversize inputs.
- **Performance evidence:** -
- **Not done in this build:** No decompression (no compression implemented).

## MC31 - Time-independent expiry semantics <a id="mc31"></a>

- **Modules:** observe.EpochExpiry
- **Invariants (safety / liveness / durability / isolation):** Expiry is epoch-based and never influences causal order.
- **Interfaces, error codes, retry semantics:** expired().
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** -
- **Configuration:** ttl_epochs.
- **Runbook:** -
- **Threat model:** Clock skew.
- **Performance evidence:** -
- **Not done in this build:** Expiry intent is not replicated as data.

## MC32 - Split-brain fencing <a id="mc32"></a>

- **Modules:** membership.check_authorship
- **Invariants (safety / liveness / durability / isolation):** Only replicas active in the stamped epoch may author; future epochs refused; retired above high-water refused.
- **Interfaces, error codes, retry semantics:** SEC_FUTURE_EPOCH, SEC_UNKNOWN_EPOCH, SEC_NOT_ACTIVE_IN_EPOCH, SEC_FENCED_RETIRED.
- **Persistence:** Membership files.
- **Concurrency:** -
- **Bounds:** -
- **Observability:** Rejection counters.
- **Configuration:** -
- **Runbook:** RB-04.
- **Threat model:** Old primary after partition.
- **Performance evidence:** -
- **Not done in this build:** No leases; epoch distribution to all nodes is out of scope.

## MC33 - Fuzz tests <a id="mc33"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC34 - Property-based causal tests <a id="mc34"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC35 - Process-crash fault injection <a id="mc35"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC36 - Network partition/reconnect integration tests <a id="mc36"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC37 - Membership churn tests <a id="mc37"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC38 - Security tests <a id="mc38"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC39 - Soak/burst/fleet benchmarks <a id="mc39"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC40 - Compatibility matrix <a id="mc40"></a>

- **Modules:** tests/production/*, bench.py, COMPATIBILITY.json
- **Invariants (safety / liveness / durability / isolation):** Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).
- **Interfaces, error codes, retry semantics:** unittest / python -m ... entry points.
- **Persistence:** Test artefacts only.
- **Concurrency:** Tests run serially.
- **Bounds:** Budgets stated per test.
- **Observability:** Evidence records.
- **Configuration:** Seeds.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** Quick bench only.
- **Not done in this build:** See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).

## MC41 - Hot-key sharding/partitioning strategy <a id="mc41"></a>

- **Modules:** node._shard
- **Invariants (safety / liveness / durability / isolation):** Deterministic blake2s(key) mod shards; one key always one lock.
- **Interfaces, error codes, retry semantics:** shards param.
- **Persistence:** -
- **Concurrency:** Striped RLocks.
- **Bounds:** shards.
- **Observability:** -
- **Configuration:** shards.
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** -
- **Not done in this build:** No partition-count migration; single process only.

## MC42 - Batch apply API <a id="mc42"></a>

- **Modules:** lifecycle.apply_batch
- **Invariants (safety / liveness / durability / isolation):** Per-item outcomes; retry adds nothing; optional all-or-nothing validation.
- **Interfaces, error codes, retry semantics:** apply_batch; CAP_BATCH_*.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** max_batch_items/bytes.
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** -
- **Not done in this build:** No batch id / batch-level audit record.

## MC43 - Zero-copy/binary encoding path <a id="mc43"></a>

- **Modules:** transport.encode_write_bin/decode_write_bin
- **Invariants (safety / liveness / durability / isolation):** Lossless; re-validates op_id; lazy value view is read-only.
- **Interfaces, error codes, retry semantics:** SchemaError CORR_BIN_*.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** Length-prefixed fields.
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Over-read, allocation abuse.
- **Performance evidence:** codec bench measured.
- **Not done in this build:** No cross-language codec.

## MC44 - Conflict analytics <a id="mc44"></a>

- **Modules:** observe.ConflictAnalytics
- **Invariants (safety / liveness / durability / isolation):** Counts agree with audit ground truth.
- **Interfaces, error codes, retry semantics:** report().
- **Persistence:** In memory.
- **Concurrency:** -
- **Bounds:** top_n.
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Key exposure (keys are raw here).
- **Performance evidence:** -
- **Not done in this build:** Raw keys in report (should be digests for unauthorised viewers).

## MC45 - Administrative tooling/UI <a id="mc45"></a>

- **Modules:** cli.py
- **Invariants (safety / liveness / durability / isolation):** Read-only; mutations only via the audited node API.
- **Interfaces, error codes, retry semantics:** gap05-admin commands.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** -
- **Configuration:** -
- **Runbook:** RUNBOOKS.md
- **Threat model:** -
- **Performance evidence:** -
- **Not done in this build:** No UI; no operation receipts.

## MC46 - Capacity model and release regression gates <a id="mc46"></a>

- **Modules:** bench.GATES
- **Invariants (safety / liveness / durability / isolation):** Gates are PROPOSED and never reported as certified.
- **Interfaces, error codes, retry semantics:** gate().
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** bench results.
- **Not done in this build:** No owner-approved thresholds, no baseline history, no variance analysis.

## MC47 - Runbooks and incident automation <a id="mc47"></a>

- **Modules:** RUNBOOKS.md, lifecycle.triage/contain
- **Invariants (safety / liveness / durability / isolation):** Automation only freezes (reversible) through audited API.
- **Interfaces, error codes, retry semantics:** triage/contain.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** -
- **Configuration:** -
- **Runbook:** self.
- **Threat model:** -
- **Performance evidence:** -
- **Not done in this build:** No game-day evidence.

## MC48 - Formal invariant specification/model checking <a id="mc48"></a>

- **Modules:** modelcheck.py, spec/GAP05.tla
- **Invariants (safety / liveness / durability / isolation):** Bounded exhaustive check of the real code.
- **Interfaces, error codes, retry semantics:** run_all().
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** Bounds stated.
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** -
- **Performance evidence:** 4-site run ~11 s.
- **Not done in this build:** TLC not run.

## MC49 - Packaging/CI/release metadata <a id="mc49"></a>

- **Modules:** pyproject.toml, ci.sh, sbom.cdx.json, SHA256SUMS.txt
- **Invariants (safety / liveness / durability / isolation):** Versions agree; checksums verify.
- **Interfaces, error codes, retry semantics:** ci.sh.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Supply chain.
- **Performance evidence:** -
- **Not done in this build:** No signing, no provenance attestation, no vulnerability scan, no reproducible-build check.

## MC50 - Missing master-prompt evidence artifact <a id="mc50"></a>

- **Modules:** EVIDENCE_GAPS.json, tools/check_evidence_refs.py
- **Invariants (safety / liveness / durability / isolation):** MASTER.md is not reconstructed; the gap is recorded and surfaced on every CI run.
- **Interfaces, error codes, retry semantics:** check_evidence_refs.py.
- **Persistence:** -
- **Concurrency:** -
- **Bounds:** -
- **Observability:** -
- **Configuration:** -
- **Runbook:** -
- **Threat model:** Fabricated evidence.
- **Performance evidence:** -
- **Not done in this build:** Artifact not recovered; waiver not granted.
