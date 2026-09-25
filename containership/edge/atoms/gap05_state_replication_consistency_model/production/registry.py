"""Component registry for the 50 GAP-05 missing components (v4.3.0).

One entry per component carries the design record that the checklist's cross-cutting
items (013-030) ask for.  ``PRODUCTION.md`` is generated from this file, and the
evidence runner reads it, so the documentation cannot drift from what the runner cites.

Fields: t=title, m=modules, inv=invariants (safety/liveness/durability/isolation),
api=interfaces & error codes, per=persistence, con=concurrency, bnd=bounds,
obs=signals, cfg=configuration, rb=runbook, thr=threats, perf=performance evidence,
gap=what is NOT done in this build.  Owner/reviewer are UNASSIGNED everywhere: this
build cannot appoint people.
"""

C = {}


def c(n, t, m, inv, api, per, con, bnd, obs, cfg, rb, thr, perf, gap):
    C[n] = dict(t=t, m=m, inv=inv, api=api, per=per, con=con, bnd=bnd, obs=obs, cfg=cfg, rb=rb, thr=thr,
                perf=perf, gap=gap, owner="UNASSIGNED", reviewer="UNASSIGNED")


c(1, "Authenticated replica identity", "identity.py, membership.py",
  "A session's replica is derived only from a CA-verified credential + proof of possession bound to the channel; payload site names never authenticate; one identity maps to exactly one active replica per epoch.",
  "IdentityVerifier.challenge/authenticate -> AuthenticatedPeer; codes SEC_UNTRUSTED_ISSUER, SEC_BAD_CREDENTIAL, SEC_WRONG_TRUST_DOMAIN, SEC_WILDCARD, SEC_REVOKED, SEC_EXPIRED, SEC_REPLAY, SEC_CHANNEL_MISMATCH, SEC_BAD_POP, SEC_UNKNOWN_IDENTITY, SEC_STALE_MEMBERSHIP, SEC_AMBIGUOUS_IDENTITY, SEC_KEY_NOT_REGISTERED. Not retryable.",
  "Ephemeral (nonces in memory, bounded 10,000); trust bundle and revocation list are supplied by deployment - no durable revocation store in this build.",
  "Nonce table under a lock; single-use pop is atomic.",
  "max_outstanding_nonces=10,000 -> CAP_HANDSHAKE.",
  "Rejections carry codes into logs/metrics via the node; peer identity lands in audit 'principal'.",
  "trust_domain, grace_seconds, CA bundle.",
  "RB-06 identity/key failure.",
  "Spoofed site field, stolen credential without key, replayed handshake, rogue CA, revoked/expired cert, wildcard SAN.",
  "Not benchmarked separately (Ed25519 verify ~50us class).",
  "No real mTLS/SPIRE integration; no durable CRL/OCSP; credential renewal automation absent.")
c(2, "Signed/attested write provenance", "protect.py, schemas.py",
  "No write mutates frontier, dedupe, WAL or audit before its Ed25519 signature verifies against the key registered for the *author* in membership.",
  "sign_write/verify_write; SEC_UNSIGNED, SEC_BAD_ALG, SEC_UNKNOWN_AUTHOR, SEC_KEY_NOT_REGISTERED, SEC_KEY_NOT_PROVISIONED, SEC_BAD_SIGNATURE.",
  "Signature + key_id persist with the write in WAL/snapshot; private keys never persisted by the node.",
  "Pure functions.", "Signature text <=512 bytes (schema).", "Rejection counters by code.",
  "Algorithm fixed to ed25519 (no negotiation => no downgrade).", "RB-06.",
  "Field/vector/value substitution, cross-tenant replay, algorithm downgrade, truncated signature.",
  "Included in node_write latency.", "Per-batch/hierarchical signing not implemented; historical-key retirement policy not defined.")
c(3, "Trusted monotonic counter allocation", "membership.py (CounterAllocator, CounterGuard)",
  "No two accepted writes by one replica share a (key, counter); counters never decrease across crash/restart/restore; jumps beyond max_gap and reuse are refused with evidence.",
  "CounterAllocator.next/observe; CounterGuard.check/record; SEC_COUNTER_JUMP, SEC_COUNTER_EQUIVOCATION, CORR_COUNTER_OWNER.",
  "Durable reservation ceiling (atomic write + fsync) under an exclusive flock; guard state in snapshots.",
  "Thread lock + cross-process flock; tested with 8 threads and 4 processes.",
  "Counter <= 2^63-1 (schema), max_gap default 1024.",
  "Guard evidence list; rejection counters.",
  "block size, max_gap.", "RB-06, RB-02.",
  "Rollback after restore, counter reuse, extreme jumps.",
  "Not separately benchmarked.", "An authenticated but compromised replica can still jump within max_gap; no external counter authority (lease/consensus).")
c(4, "Durable write-ahead log and recovery", "durable.py (WriteAheadLog), node.py",
  "A write is acknowledged only after its WAL frame is fsynced; recovery truncates only a torn tail and fails closed on mid-log corruption; replay is deterministic.",
  "WriteAheadLog.append/records_after/compact_before; CORR_WAL_CORRUPT, CORR_WAL_SEQUENCE, CORR_FAIL_STOP.",
  "Framed sha256 records with sequence numbers; optional AES-GCM value encryption; compaction after snapshot.",
  "Append under a lock; node shards serialize per key.",
  "Grows until checkpoint; checkpoint compacts.",
  "wal_records gauge; recovery_report (records, truncated bytes/reason, replayed, rejected, audit_backfilled).",
  "Data directory; fsync always on (not configurable by design).", "RB-02 WAL corruption.",
  "Torn writes, bit rot, truncated tails.",
  "recovery_records_per_s measured.", "Single WAL file (no segment rotation); group commit only per record.")
c(5, "Crash-consistent snapshots/checkpoints", "durable.py (SnapshotStore), node.checkpoint",
  "A snapshot is published only by atomic rename after fsync and embeds a sha256; recovery takes the newest valid generation and falls back; frontier incl. quarantine is preserved exactly.",
  "SnapshotStore.write/validate/latest_valid; CORR_SNAPSHOT_UNREADABLE/CHECKSUM/FORMAT.",
  "snapshot-<generation>.json, keep=3 generations.",
  "Checkpoint takes every shard lock (consistent cut).",
  "keep=3.", "snapshot_generation in health.", "keep.", "RB-02.",
  "Partial writes, corrupted generation.", "Not separately benchmarked.",
  "Snapshot is not signed (checksum only); no manifest-level signature.")
c(6, "Tenant/environment namespace enforcement", "node.py (state_key), schemas.py, authz.py",
  "State key = tenant \\x1f environment \\x1f key; the separator is forbidden in every component, so namespaces cannot alias; every operation is authorized per (tenant, environment).",
  "NamespaceError (SEC_NAMESPACE), AuthorizationError.",
  "Namespace is part of every persisted doc and of op_id.", "N/A.", "Per-tenant admission buckets.",
  "Denied cross-tenant operations audited.", "Grants per tenant/env.", "RB-07.",
  "Namespace confusion, separator injection, cross-tenant replay.", "N/A.",
  "Unicode normalisation (NFC) of identifiers not enforced - identifiers compared byte-exact.")
c(7, "Concrete wire schemas", "schemas.py, schemas/*.schema.json, schemas/corpus",
  "Strict ingress: unknown fields, duplicate JSON keys, lone surrogates, non-canonical vectors and op_id mismatch are rejected.",
  "validate_write_doc/validate_merge_result/validate_conflict_set; CORR_SCHEMA_* codes.",
  "Schemas shipped as JSON-Schema 2020-12 documents.", "Pure functions.", "Field byte limits from Limits.",
  "Rejection counters.", "Limits.", "-", "Parser abuse, oversized fields.",
  "codec_json_roundtrip_us measured.", "Only a Python validator exists; no second-language validator to cross-check.")
c(8, "Schema/version negotiation", "schemas.negotiate",
  "Highest common version per family; no common version is a refusal, never a silent downgrade.",
  "negotiate(); CORR_NEGOTIATION_MISSING, CORR_NEGOTIATION_NONE, CORR_INCOMPATIBLE_VERSION.",
  "Schema id persisted in every doc.", "Pure.", "-", "health.schemas.", "SUPPORTED map.", "-",
  "Downgrade attack.", "-", "Only version 1 exists; N+1 behaviour is tested only as rejection.")
c(9, "Durable deduplication identity", "schemas.op_id_for, node.recent_ops",
  "op_id = sha256(canonical semantic content); exact replay is idempotent across restart/checkpoint; same author counter with different content is equivocation.",
  "Outcome 'duplicate'; SEC_COUNTER_EQUIVOCATION, SEC_VECTOR_EQUIVOCATION.",
  "Frontier op_ids + bounded recent window in snapshot; older replays fall back to causal 'superseded'.",
  "Under shard lock.", "recent_window=100,000.", "replay_total counter.", "recent_window.", "-",
  "Replay storms, equivocation.", "-", "Dedupe window not coordinated with an anti-entropy horizon setting.")
c(10, "Tamper-evident audit ledger", "audit.py",
  "Every accepted write, resolution, freeze, GC, checkpoint and authz denial is appended to a sha256 hash chain whose head is Ed25519-signed; verification detects modification, deletion, reorder and truncation against a retained head.",
  "AuditLedger.append/signed_head/verify; CORR_AUDIT_CHAIN/TAMPER/TRUNCATED/SEGMENT/HEAD_SIG.",
  "Segmented JSONL + .start markers; fsync per record; crash window WAL->audit back-filled on recovery.",
  "Append under lock.", "segment_records x max_active_segments.", "audit_pressure in health.",
  "segment size, archive dir.", "RB-05.", "Log tampering, truncation, forged head.", "-",
  "Signing key is the node key (no HSM/KMS); signed head is not yet shipped to an external witness.")
c(11, "Bounded audit/quarantine retention policy", "audit.py, node.py (CAP_FRONTIER_FULL)",
  "Reaching a bound refuses new work (retryable) instead of dropping recorded state; archive handoff verifies before deletion.",
  "CAP_AUDIT_FULL, CAP_FRONTIER_FULL.", "Archive directory.", "-",
  "max_unresolved_per_key, max_quarantine_total, audit segments.", "audit_pressure, quarantine_pressure.",
  "Limits.", "RB-03, RB-05.", "Conflict flooding.", "quarantine flood bench.",
  "No hysteresis/watermarks; no per-tenant byte quotas.")
c(12, "Encryption and managed key rotation", "protect.Keyring, node._seal",
  "Values in WAL/snapshots are AES-256-GCM with AAD bound to tenant/environment/purpose/key id; missing key = hard recovery failure (readiness false).",
  "Keyring.rotate/encrypt/decrypt/rewrap/retire; SEC_KEY_UNAVAILABLE, CORR_AEAD_TAG, CORR_KEY_IN_USE.",
  "Key ids persisted in envelopes; key material not persisted by the node.", "Lock around refs.", "-",
  "Recovery rejected count.", "Keyring injection.", "RB-06.", "Wrong-tenant decrypt, ciphertext tamper.",
  "-", "No KMS integration; transport encryption (TLS) not implemented; keyring is in-memory.")
c(13, "Authorization policy integration", "authz.py",
  "Default deny; every externally reachable mutation checks an explicit permission; provider failure denies; wildcard scopes only for declared break-glass principals.",
  "Authorizer.require; SEC_FORBIDDEN.", "Policy supplied per call (no cache).", "Stateless.", "-",
  "Denials and privileged decisions audited with policy_version.", "Policy provider.", "RB-07.",
  "Privilege escalation, confused deputy, stale grants.", "-", "No attribute-based conditions (key scope, epoch) in grants.")
c(14, "Atomic configuration/membership store", "membership.MembershipStore",
  "Exactly one active generation per node; activation is CAS on epoch; history is a digest chain; rollback is forward.",
  "activate/rollback_to/add/remove/reseed; CORR_CAS_CONFLICT, CORR_MEMBERSHIP_CHAIN.",
  "epoch-NNNNNNNN.json files via atomic write.", "RLock around CAS.", "-", "membership_epoch in health.",
  "Directory.", "RB-04.", "Racing controllers, tampered history.", "-",
  "Changes are not signed by the controller; distribution across nodes is out of scope (store is per node).")
c(15, "Replica membership-change protocol", "membership.py",
  "Removed replicas are fenced above their drained high-water; names are never reused (reseed => new incarnation name~N).",
  "remove_replica(high_water)/reseed_replica; SEC_FENCED_RETIRED.", "Via membership store.", "-", "-",
  "Audit via controller (not in store).", "-", "RB-04.", "Old incarnation writes.", "-",
  "Joining/draining are not explicit states (only active/retired); drain protocol computing high_water is the operator's.")
c(16, "Production conflict-resolution adapter", "resolution.py, node.resolve",
  "Unavailable policy keeps the conflict open; a decision applies only if the frontier digest is unchanged; the resolving write dominates every active and quarantined sibling.",
  "ResolutionAdapter.request; DEP_POLICY_UNAVAILABLE, CORR_POLICY_DECISION, CORR_STALE_DECISION.",
  "Decision evidence + policy version in audit.", "Worker thread per adapter.", "retries, timeout.",
  "adapter.calls.", "timeout_s, retries, backoff_s.", "RB-03.", "Compromised policy output.", "-",
  "No circuit breaker; no dry-run/explain mode; no live GAP-13 engine tested.")
c(17, "Anti-entropy/reconciliation engine", "anti_entropy.py",
  "Two replicas with eventual connectivity reach identical digest roots and frontiers; repair uses the normal authenticated accept path; floors travel first.",
  "digest_tree/sync_one_way/reconcile.", "Stateless.", "Per-node shard locks.", "256 leaves.",
  "rounds report (differing leaves, sent, applied, rejected).", "max_rounds.", "RB-01.",
  "Unauthenticated repair.", "anti_entropy_keys_per_s measured.",
  "Full scan to build the tree each call (no incremental maintenance); no scheduling/prioritisation.")
c(18, "Replication transport adapter", "transport.py",
  "Transport faults (drop/dup/reorder/delay) change only timing, never causal outcome; queues are bounded.",
  "encode_frame/decode_frame, ReliableSender, Link; CORR_FRAME_*, CAP_FRAME_SIZE, CAP_LINK_FULL, CAP_SENDER_BACKLOG.",
  "None.", "Single-threaded pump.", "window, max_pending, capacity, max_frame_bytes.", "Link.stats.",
  "window/timeout/retries.", "RB-01.", "Malformed frames, slowloris (not tested).", "-",
  "No real sockets/TLS; no keepalive or session state machine; no jitter in backoff.")
c(19, "Delete/tombstone semantics", "node.delete, gc_tombstones",
  "Deletes are causal writes; concurrent update vs delete is a conflict; GC only after all active replicas acknowledge, leaving a floor vector that blocks resurrection.",
  "delete/gc_tombstones.", "Floors in snapshot and WAL 'gc' records.", "-", "-", "tombstone_gc audit.",
  "-", "RB-01.", "Stale resurrection.", "-", "Acknowledgement collection is supplied by the caller.")
c(20, "Vector compaction strategy", "node floors, membership retirement",
  "Collected keys keep one floor vector (retired-replica summary); dominance queries against pre-GC history are unchanged.",
  "-", "Floors persisted.", "-", "max_vector_entries.", "vector_entries histogram.", "-", "-", "-",
  "vector_bytes_N_replicas measured.", "No dotted version vectors; live vectors are not compacted.")
c(21, "CRDT/commutative type registry", "crdt.py",
  "Only registered types merge; merges are commutative/associative/idempotent; read-time merge (no new writes).",
  "REGISTRY, merge_all; CORR_SCHEMA for unregistered.", "value_type in the signed doc.", "Pure.", "-",
  "read() reports merged type.", "-", "-", "Type confusion.", "-", "No delta/op-based CRDTs; no cross-language vectors.")
c(22, "Quarantine operator API", "node.quarantine_list/export/freeze/unfreeze/resolve",
  "Operator actions are authorized, audited and routed through normal invariant checks; freeze survives restart.",
  "CORR_KEY_FROZEN, CORR_STALE_DECISION.", "freeze/unfreeze WAL records.", "Shard lock.", "-",
  "Audit events.", "-", "RB-03.", "Operator error, stale view.", "-", "No pagination cursor; no per-item immutable IDs beyond op_id.")
c(23, "Immutable/read-only state views", "node.FrontierView",
  "Views are frozen dataclasses of deep-copied MappingProxy docs; mutation cannot reach state.",
  "view().", "-", "Built under the key's shard lock.", "-", "-", "-", "-", "Out-of-band mutation.", "-",
  "Core ReplicatedKey still exposes mutable lists (kept for v4.2.0 compatibility).")
c(24, "Persistence migration framework", "lifecycle.migrate_*",
  "Migrations are versioned, backed up first, idempotent, re-validated; downgrades and unknown formats refused; namespace never guessed.",
  "migrate_state/migrate_snapshot_dir; CORR_DOWNGRADE_REFUSED, CORR_NO_MIGRATION.", "*.pre-migration-vN backups.",
  "Offline.", "-", "Report list.", "dry_run.", "RB-08.", "-", "-", "Only one hop (1->2); WAL format has no migration yet.")
c(25, "Backup/restore/reseed workflow", "lifecycle.backup/verify_backup/restore",
  "Restore verifies every digest and the audit chain first, never overwrites live state, and fences the node (recovery mode) until a peer reconcile completes.",
  "CORR_BACKUP_DIGEST, CORR_RESTORE_TARGET, CORR_RECOVERY_MODE.", "MANIFEST.json + copies.", "Offline.", "-",
  "health reasons.", "-", "RB-01.", "Tampered backup, stale restore.", "-",
  "Backups are not encrypted as a set (values inside are, if a keyring is used); no RPO/RTO measurement at scale.")
c(26, "Observability package", "observe.Metrics", "Series are bounded; overflow is counted.",
  "exposition() Prometheus text.", "In memory.", "Lock.", "max_series.", "self.", "-", "-", "Label cardinality attack.",
  "-", "No SLO definitions agreed; no dashboards.")
c(27, "Structured logs/tracing", "observe.StructuredLog",
  "Values/secrets redacted by salted digest; errors never sampled out; trace ids are correlation only.",
  "emit().", "In memory ring + sink.", "-", "max_lines.", "-", "sample_rate.", "-", "Log injection, secret leak.", "-",
  "No OpenTelemetry export.")
c(28, "Health/readiness endpoints", "node.health", "Readiness fails on fail-stop, recovery mode, rejected recovery records, audit/quarantine pressure, invalid membership.",
  "health() dict.", "-", "-", "-", "self.", "-", "all RBs.", "Info disclosure (no HTTP endpoint).", "-",
  "No HTTP server/authentication; no startup progression states.")
c(29, "Admission control/backpressure", "observe.Admission", "Hot keys throttle without blocking unrelated keys/tenants; metadata bounded.",
  "CAP_TENANT_RATE, CAP_HOT_KEY, CAP_RECOVERY_BURST (retryable).", "-", "Called under shard lock.", "max_tracked_keys.",
  "rejections Counter.", "capacities/refills.", "RB-03.", "Noisy neighbour.", "-", "No reserved control-traffic class; buckets tick logically, not by time.")
c(30, "Resource limits", "limits.Limits", "All limits positive, consistent, validated at startup.",
  "LimitExceeded CAP_* codes.", "-", "-", "self.", "-", "Limits.", "-", "Oversize inputs.", "-",
  "No decompression (no compression implemented).")
c(31, "Time-independent expiry semantics", "observe.EpochExpiry", "Expiry is epoch-based and never influences causal order.",
  "expired().", "-", "-", "-", "-", "ttl_epochs.", "-", "Clock skew.", "-", "Expiry intent is not replicated as data.")
c(32, "Split-brain fencing", "membership.check_authorship", "Only replicas active in the stamped epoch may author; future epochs refused; retired above high-water refused.",
  "SEC_FUTURE_EPOCH, SEC_UNKNOWN_EPOCH, SEC_NOT_ACTIVE_IN_EPOCH, SEC_FENCED_RETIRED.", "Membership files.", "-", "-",
  "Rejection counters.", "-", "RB-04.", "Old primary after partition.", "-", "No leases; epoch distribution to all nodes is out of scope.")
for n, t in [(33, "Fuzz tests"), (34, "Property-based causal tests"), (35, "Process-crash fault injection"),
             (36, "Network partition/reconnect integration tests"), (37, "Membership churn tests"),
             (38, "Security tests"), (39, "Soak/burst/fleet benchmarks"), (40, "Compatibility matrix")]:
    c(n, t, "tests/production/*, bench.py, COMPATIBILITY.json", "Test/certification component: its invariant is that the evidence it produces is real and reproducible (seeds recorded).",
      "unittest / python -m ... entry points.", "Test artefacts only.", "Tests run serially.", "Budgets stated per test.",
      "Evidence records.", "Seeds.", "-", "-", "Quick bench only.", "See CHECKLIST_EVIDENCE for gaps (multi-hour soak, native fuzzers, fleet scale).")
c(41, "Hot-key sharding/partitioning strategy", "node._shard", "Deterministic blake2s(key) mod shards; one key always one lock.",
  "shards param.", "-", "Striped RLocks.", "shards.", "-", "shards.", "-", "-", "-", "No partition-count migration; single process only.")
c(42, "Batch apply API", "lifecycle.apply_batch", "Per-item outcomes; retry adds nothing; optional all-or-nothing validation.",
  "apply_batch; CAP_BATCH_*.", "-", "-", "max_batch_items/bytes.", "-", "-", "-", "-", "-", "No batch id / batch-level audit record.")
c(43, "Zero-copy/binary encoding path", "transport.encode_write_bin/decode_write_bin",
  "Lossless; re-validates op_id; lazy value view is read-only.", "SchemaError CORR_BIN_*.", "-", "-", "Length-prefixed fields.",
  "-", "-", "-", "Over-read, allocation abuse.", "codec bench measured.", "No cross-language codec.")
c(44, "Conflict analytics", "observe.ConflictAnalytics", "Counts agree with audit ground truth.", "report().", "In memory.", "-", "top_n.", "-", "-", "-", "Key exposure (keys are raw here).", "-", "Raw keys in report (should be digests for unauthorised viewers).")
c(45, "Administrative tooling/UI", "cli.py", "Read-only; mutations only via the audited node API.", "gap05-admin commands.", "-", "-", "-", "-", "-", "RUNBOOKS.md", "-", "-", "No UI; no operation receipts.")
c(46, "Capacity model and release regression gates", "bench.GATES", "Gates are PROPOSED and never reported as certified.", "gate().", "-", "-", "-", "-", "-", "-", "-", "bench results.", "No owner-approved thresholds, no baseline history, no variance analysis.")
c(47, "Runbooks and incident automation", "RUNBOOKS.md, lifecycle.triage/contain", "Automation only freezes (reversible) through audited API.", "triage/contain.", "-", "-", "-", "-", "-", "self.", "-", "-", "No game-day evidence.")
c(48, "Formal invariant specification/model checking", "modelcheck.py, spec/GAP05.tla", "Bounded exhaustive check of the real code.", "run_all().", "-", "-", "Bounds stated.", "-", "-", "-", "-", "4-site run ~11 s.", "TLC not run.")
c(49, "Packaging/CI/release metadata", "pyproject.toml, ci.sh, sbom.cdx.json, SHA256SUMS.txt", "Versions agree; checksums verify.", "ci.sh.", "-", "-", "-", "-", "-", "-", "Supply chain.", "-", "No signing, no provenance attestation, no vulnerability scan, no reproducible-build check.")
c(50, "Missing master-prompt evidence artifact", "EVIDENCE_GAPS.json, tools/check_evidence_refs.py", "MASTER.md is not reconstructed; the gap is recorded and surfaced on every CI run.", "check_evidence_refs.py.", "-", "-", "-", "-", "-", "-", "Fabricated evidence.", "-", "Artifact not recovered; waiver not granted.")

TITLES = {n: v["t"] for n, v in C.items()}
