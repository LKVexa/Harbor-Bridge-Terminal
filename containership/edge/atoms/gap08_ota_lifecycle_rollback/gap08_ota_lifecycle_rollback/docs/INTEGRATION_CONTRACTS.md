# Sibling/upstream integration contracts

GAP-08 does not implement these systems. It defines — and tests against executable doubles — exactly what it consumes. Each contract must be verified end-to-end against the real service before production (open items in `CHECKLIST_STATUS.md`).

## GAP-07 Artifact provenance/signing — `PK_VERIFICATION/1`
Fields consumed: `subject` (bundle id), `digest` (`sha256:<hex>`, the exact bytes later distributed and installed), `size`, `verified` (true), `kind` ("bundle"), `algorithm` (allow-listed), `verifier`, `verified_at`, `expires_at`, `provenance_ref`. Signed by a GAP-07 key the controller verifies. Rejected: wrong subject, missing digest, stale/not-yet-valid, unsigned/untrusted signer, revoked digest, disallowed algorithm. Persisted: `verification_ref` (statement digest) in state and audit. Unavailable after admission: forward progress (including deferred retries) blocks when the statement expires until `reverify` with the same digest succeeds; rollback unaffected.

## GAP-09 Unified observability — `PK_HEALTH_EVIDENCE/1`
Fields: `evidence_id`, `nonce`, `source`, `rollout_id`, `cohort`, `gate_class`, `observed_at`, `window_start`/`window_end`, `sampled_nodes`, `healthy_nodes`, `verdict`. Policy: max age 300 s, window must start ≥ `applied_at + settle_s`, coverage ≥ 90 %, healthy ratio ≥ 99 % for a healthy verdict, no replay. Correlation: rollout/cohort ids in evidence; node ids appear only in evidence and logs, never as metric labels.

## GAP-01 Edge Node Supervisor — `PK_NODE_COMMAND/1` → `PK_NODE_ACK/1`
Ops: drain, stage, install, activate, rollback, quarantine, query. Node MUST: dedup by `command_id` (return the stored result re-attested for the new nonce); reject `fence` below its floor per rollout; reject after `deadline`; tombstone a rollout after executing its rollback (late installs rejected); verify content digest before activation; sign acks with its enrolled key including observed version/digest and attestation. Terminal failures → quarantine/reconcile, never success.

## GAP-15 Runtime compatibility certification
Consumed as the compatibility profile checked against `schemas/compatibility_matrix.json` at creation; must be re-checked for deferred nodes when node state changed (**open**: per-node certification evidence binding is not yet consumed; only the rollout-level profile is).

## GAP-06 Device identity and attestation
Enrolment (node id → key id → expected measurements), single-use nonces, attestation freshness, rotation (old key revoked), revocation, replacement (generation++). Raw secrets are never persisted — only `ack_ref` digests.

## Topology/hardware discovery
`Inventory{nodes: {site, rack, device_class}, version, observed_at}`; stale (> 15 min) or unknown nodes fail closed; revalidated before every wave and deferred retry; overrides only via an approved, violation-bound override record.

## GAP-05 State replication/consistency
Must implement `store.StateStore`: `create`, `load`, `commit(expected_revision, fence)` with linearizable CAS, fence floor, `pinned_target` and audit-prefix immutability, digest verification, no-secrets guard, fsync-equivalent durability and point-in-time backup.
