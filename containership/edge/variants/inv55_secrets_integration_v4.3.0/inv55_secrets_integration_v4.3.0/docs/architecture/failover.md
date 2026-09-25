# Failover

| ID | INV55-ARCH-FAILOVER | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

## Implemented: Vault HA via a single address

`VaultProvider` talks to one `address` (typically a load-balanced or DNS name for the Vault HA cluster). `VaultProvider.health` treats `sys/health` codes as follows:

| Code | Vault meaning | `ProviderHealth.reachable` |
|---|---|---|
| 200 | active, unsealed | true |
| 429 | unsealed standby | true (standbys forward/redirect requests) |
| 472 | DR secondary | false (`replication_dr_mode == "secondary"`) |
| 473 | performance standby | true |
| 501 | not initialised | false (`initialized` false) |
| 503 | sealed | false |
| other / transport error | — | false |

Data requests returning 429/500/502/503/504 raise `ProviderUnavailable` and are retried then circuit-broken. Failover between Vault nodes is therefore Vault's/the load balancer's responsibility.

Evidence: `tests/test_vault_adapter.py::VaultHttp.test_health_sealed_and_version`, `test_status_mapping`.

## NOT IMPLEMENTED

- Multi-endpoint / multi-cluster failover inside `VaultProvider` (list of addresses, health-ordered selection).
- Cross-site failover, residency guard during failover, failback policy.
- Requires: a provider-selection component and a residency policy input per site (deployment-patterns.md).

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | DR secondary now unreachable |
