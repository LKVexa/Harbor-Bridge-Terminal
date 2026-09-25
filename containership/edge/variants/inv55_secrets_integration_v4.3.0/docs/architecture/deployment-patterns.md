# Deployment patterns

| ID | INV55-ARCH-DEPLOY | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Invariants (all patterns)

- Each site MUST run its own instance; nothing assumes a global singleton (`contract.py::build` `boundaries.site`).
- All broker state (leases, scopes, retirements, cache, idempotency) is per-process memory in `service.py::SecretsService.__init__`; instances MUST NOT be assumed to share it.
- Vault MUST be reached over HTTPS (`vault.py::VaultProvider.__post_init__`).

## Patterns

| Pattern | Topology | Provider | Notes |
|---|---|---|---|
| Cloud | N stateless-ish instances behind a load balancer, one Vault HA cluster per region | `VaultProvider` (AppRole or Kubernetes auth) | Callers SHOULD be sticky per lease: a `lease_id` is only valid on the instance that issued it (`SecretsService._leases`). |
| Datacenter | As cloud, Vault on-prem with HSM/auto-unseal | `VaultProvider` | Same stickiness constraint. |
| Near-edge | One instance per edge site, Vault performance standby or regional cluster reachable over WAN | `VaultProvider` | SHOULD set `stale_grace_s` only if the site accepts stale reads (disconnected-policy.md). |
| Far-edge | Single instance, intermittent WAN | `VaultProvider` | Offline-deny by default (`ServiceLimits.stale_grace_s = 0`). No edge sync or local replica: NOT IMPLEMENTED. |

## Unsupported matrix

| Configuration | Status | Reason |
|---|---|---|
| `InMemoryProvider` in production | REFUSED by bootstrap in `prod` | `bootstrap.build_service` |
| Static token auth in `prod` | REFUSED by bootstrap | `bootstrap.build_service` |
| HTTP (non-TLS) Vault on non-loopback | REFUSED by code | `VaultProvider.__post_init__` raises `ValueError`. |
| Shared lease across instances | UNSUPPORTED | Leases are in-process. |
| Vault < 1.15 or > 1.18 | UNSUPPORTED (flagged, not refused) | `SUPPORTED_SERVER_VERSIONS`. |
| KV v1 with rotate CAS / retire+destroy | UNSUPPORTED | KV v1 `write` ignores CAS and returns version 1; `destroy_version` raises. |
| Multi-provider / multi-endpoint failover | NOT IMPLEMENTED | failover.md. |

## Residency

- Secret values are read from the Vault cluster configured for that instance and held only in process memory (`SecretsService._cache`, `Lease.value`); INV-55 does not replicate them.
- Residency MUST therefore be enforced by choosing a Vault cluster in the permitted jurisdiction per site overlay (`config.py::load_layers`, `overlays/<env>.<site>.json`). No code-level residency guard exists: NOT IMPLEMENTED.
- Audit files (`audit.py::FileAuditSink`) contain secret names (not values); their storage location is subject to the same residency rule.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Bootstrap refusals |
