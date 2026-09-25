# RB-DAY2 — Operate (MC-064-T03..T06)

## Policy change (RBAC, registries, signers, rules, quotas)
1. Author edits the layered config in git. Run `cli validate-config` and record the generation.
2. Run a dry-run impact check: `svc.policy_impact(doc, principal)`. Every listed `violations[]` entry would be refused after activation. Decide before proceeding.
3. `stage_config` (author) → `approve_config` ×N (distinct approvers, never the author) → `activate_config(gen, expected_active=<current>)`. `ECP_CONFIG_CONFLICT` means someone else activated first: re-read and re-assess.
4. Verify: `/version` shows the new generation. The explain view for new decisions references it.

## Delegated RBAC (tenant admins)
Use `POST /v1/rbac` with `op: list`, then `bind`/`unbind` with `if_revision` from the list and a `reason`. `ECP_CONFIG_CONFLICT` means a concurrent change happened: list again.

## Key and certificate rotation
- **Signer rotation:** add the new signer (new id), then activate. Re-sign releases. Set `revoked: true` on the old signer in a later generation after the overlap window. Use `policy_impact` first to find workloads still signed with the old key.
- **Anchor key:** create a new anchor key, run `cli anchor` with it, and add its public key to the auditors' trusted set. Keep the old public key for verifying earlier anchors.
- **TLS:** `Server.reload_tls(cert, key)`. New handshakes use the new chain with no restart. Watch the certificate expiry alert.
- **Data key (at-rest sealing):** `Keyring.rotate()`. Old keys stay decrypt-only. Call `retire(old)` only after confirming no live segment needs it (debt D-04: no re-encryption tool yet).

## Scaling
Follow `docs/CAPACITY.md`. Scale followers for read load. Admission write throughput is bounded by the leader's fsync.

## Retention and legal hold
`svc.enforce_retention(archive=<copy-to-WORM>)`, run daily. It checkpoints first and never drops held or active segments. Set a hold with `journal.set_hold(id, from_seq, to_seq, reason)`.

## Backup verification
Run RB-BACKUP §Verify weekly.

## Tenant onboarding / offboarding
Onboarding: bindings plus quota overrides in a new generation. Offboarding: `freeze(org/tenant)`, then retire workloads through INV-63, then remove the bindings. **The journal is never edited**, so tenant data stays under retention.

## Troubleshooting by error code

| Code | Likely cause | Action |
|---|---|---|
| ECP_AUDIT_UNAVAILABLE | journal volume full or read-only | free space / fix the mount; `/readyz` recovers automatically on the next successful append |
| ECP_STORE_CORRUPT (startup) | interior corruption | **do not edit**; restore from backup (RB-BACKUP), preserve the corrupt copy as evidence |
| ECP_AUDIT_TAMPERED | chain or anchor mismatch | SEV1 security incident (RB-INCIDENT) |
| ECP_NOT_LEADER | replica lost its lease | expected on followers; if every replica returns it, check `lease.json` and storage locks |
| ECP_CIRCUIT_OPEN / ECP_DELIVERY_FAILED | INV-63 down | admissions continue as `delivery_pending`; after recovery call `redeliver_pending()` |
| ECP_DEPENDENCY_UNAVAILABLE (policy) | GAP-13 down | deny by default; engage the GAP-13 owners |
| ECP_UNAUTHENTICATED spike | IdP key rotated / attack | check the JWKS config; watch `ecp_authn_failures_total` |
| ECP_QUOTA_EXCEEDED | tenant over quota | raise the quota via a generation, or push back on the tenant |
| ECP_OVERLOADED | global in-flight cap reached | scale, or raise `max_inflight` within capacity |

## Emergency freeze / resume criteria
Freeze: `POST /v1/quarantine/freeze {"scope": "acme[/tenant[/lattice]]", "reason": "<ticket>"}`.
Resume only when the root cause is fixed, `verify-journal` is INTACT and the active generation has been re-checked.
Release needs 2 distinct `quarantine` holders: `POST /v1/quarantine/release` from each.
