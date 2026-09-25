# Day-2: routine operations (MC-051-03)

## Certificate / key rotation
* Server cert: replace files, then call `ssl_context.load_cert_chain` (hot reload; new handshakes use the new cert, existing streams unaffected). Verified by `test_server_certificate_rotation_without_restart`.
* Client certs: issue before 2/3 of lifetime; revoke by serial in the authenticator's revocation list.
* Data key: add new kid to the keyring (`Keyring.rotate`); new WAL frames and snapshots use it; old kids remain until a checkpoint + backup cycle has rewritten all data, then remove.
* Token key: add new kid, switch active, remove old after max token TTL.

## Compaction
Automatic by `CompactionController` (retain + safety margin, never past protected revisions or the slowest live watcher). Manual override: `POST /v1/compact` (operator, audited). Watch `cstate_compaction_lag_revisions`.

## Scaling
Single member: vertical only (see CAPACITY.md headroom). Multi-member: blocked on ADR-002.

## Membership
See CONSENSUS_CONTRACT §2 (applies once a backend is approved).

## Upgrades
Follow `docs/ROLLOUT.md`.

## Audits
Weekly: verify audit chain against the stored anchor; monthly: review policy version & role map; quarterly: exceptions expiry.

## Tenant offboarding
Delete namespace prefix (`delete` with `prefix: true` under the tenant namespace by security-admin via `x-cstate-namespace`), compact past it, take a new backup, expire old backups per retention.
