# Source of truth (MC-005, MC-038)

**The journal is the only authority.** `contract.py` says "the control plane's state is what the
log says was admitted". 4.3.0 makes that literally true:

| Record kind | Body (authoritative fields) | Projection it drives |
|---|---|---|
| `config.stage` / `config.approve` / `config.activate` | generation digest, full document, author, source repo/rev, ticket, approvers, previous generation | active `Policy`, config history |
| `rbac.bind` / `rbac.unbind` | binding, actor, reason, request id | RBAC overlay, `rbac_revision` |
| `admit.decision` | decision id, request id, idempotency key + request digest, principal ref, tenant/lattice/org/app, admitted, typed reasons, manifest digest, config generation, provenance + policy evidence, trace id, source (GitOps), the manifest (only if admitted) | lifecycle, inventory, idempotency cache |
| `admit.refused` | request id, code, principal ref, trace id, generation | none (evidence only) |
| `lifecycle.transition` | decision id, target state, delivery work item, revision, error code | lifecycle, inventory state, pending deliveries |
| `quarantine.freeze` / `release_vote` / `release` | scope, actor, reason, approvers | freezes |
| `audit.export` | actor, range | none |
| `state.checkpoint` | full projection snapshot | everything, so older segments can be compacted |

## Identity, ordering and integrity fields

`seq` (gap-free, monotonic within one journal), `prev`, `hash` = SHA-256 over the
domain-separated canonical record, `ts` (the writer's clock, informational only), `kind`. Correlation
fields: `decision_id`, `request_id`, `idempotency_key`, `trace_id`. Actor: `principal`
(subject, issuer, kind, org, tenant, auth method, token id). No token material is stored.

## Durability rule

`Journal.append` returns only after `write` + `fsync` under a cross-process `flock`. The service
exposes a decision only after `append` returns (invariant I1), and an append failure is raised as
`ECP_AUDIT_UNAVAILABLE`, which means no admission (I2). **The RPO for acknowledged operations is 0.**
An append in flight during a crash was never acknowledged. Recovery truncates it as a torn tail and
reports the truncated bytes.

## Replay and snapshots

A restart replays every segment in order. `state.checkpoint` records make compaction possible:
`enforce_retention` writes a checkpoint first, then drops whole segments older than
`retention_days` that are not under a legal hold, after the optional `archive` callback
succeeds. Replay is deterministic because every projection transition is a pure function of
`(kind, body, seq)`.

Schema evolution: the record schema is `PK_ECP_AUDIT/2`. Readers keep accepting every prior major
version. A change is a new major version (`release/compatibility.json`).

## Protection

Access to the journal volume is limited to the service identity. Record bodies are optionally sealed
with AES-256-GCM using a versioned keyring, with the record `seq` bound as AAD. Ed25519 anchors are
signed with a key the writer doesn't hold. Backups are verified on creation and again on restore.
Legal holds block compaction.

## Convergence evidence

- `test_backup_restore_reconstructs_identical_state`: the restored state matches the live state.
- `test_crash_between_decision_and_delivery_resumes_after_restart`: state after a crash matches the replayed state.
- `test_retention_compaction_then_restart_preserves_state`: state after compaction and restart matches.
- `test_query_export`: an export verifies independently.
