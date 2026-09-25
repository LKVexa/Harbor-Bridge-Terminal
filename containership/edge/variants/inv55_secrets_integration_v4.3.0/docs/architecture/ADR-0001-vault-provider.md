# ADR-0001: HashiCorp Vault as the production secret provider

| Field | Value |
|---|---|
| ID | INV55-ADR-0001 |
| Version | 4.3.0 |
| Status | Draft (decision proposed, `status: PENDING-OWNER-APPROVAL`) |
| Decider | `<UNASSIGNED: service-owner>` |
| Security reviewer | `<UNASSIGNED: security-owner>` |
| Approval date | `<PENDING>` |

## Context

INV-55 brokers secrets but explicitly does not store them (`contract.py::build` `not_owns`: "Secret storage backends", "Key custody and HSMs"). A provider behind the `providers/base.py::SecretProvider` protocol must own versions, revocation and at-rest protection.

## Decision

Use HashiCorp Vault through `providers/vault.py::VaultProvider`, a standard-library HTTP client (no `hvac`), supporting:

- KV v2 (read latest/pinned version, CAS write, metadata, destroy) and KV v1 (read/write only) — `VaultProvider.read/write/metadata/destroy_version`.
- Enterprise namespaces via `X-Vault-Namespace` — `VaultProvider._request`.
- Auth: `TokenAuth` (dev/break-glass only), `AppRoleAuth`, `KubernetesAuth`.
- Token re-login at `renew_fraction` (0.67) of TTL — `VaultProvider._ensure_token`; `renew_self` exists and is tested but is not called by the service.
- `sys/leases/renew` / `sys/leases/revoke` — `VaultProvider.renew/revoke`.
- `sys/health` status mapping incl. DR secondary → unreachable — `VaultProvider.health`.
- HTTPS with TLS >= 1.2; plaintext HTTP refused except loopback with `allow_insecure_http` — `VaultProvider.__post_init__`, `build_tls_context`.
- Server versions 1.15–1.18 (`vault.py::SUPPORTED_SERVER_VERSIONS`).

`providers/base.py::InMemoryProvider` is a reference/test provider and MUST NOT be used in production.

## Trust boundaries

1. Caller → INV-55 (workload token, `identity.py::HmacJwtAuthenticator`).
2. INV-55 → Vault (TLS, Vault token obtained via AppRole/Kubernetes).
3. Vault → its storage/seal (outside INV-55; delegated).

## Alternatives considered

| Option | Reason not chosen (proposed) |
|---|---|
| Cloud-native managers (AWS SM, GCP SM, Azure KV) | Would tie deployment patterns to one cloud; can be added as further `SecretProvider` implementations. NOT IMPLEMENTED. |
| `hvac` client library | Adds third-party runtime dependency; stdlib client keeps supply chain empty. |
| Kubernetes Secrets only | No versioning/CAS/leases; weak at-rest defaults. |
| Storing secrets in INV-55 | Explicit non-goal (`contract.py::build` `non_goals`). |

## Consequences

- Positive: no runtime third-party dependencies; CAS gives cross-instance rotation safety (see split-brain.md).
- Negative / known limits:
  - Dynamic-secret leases: `VaultProvider.read` carries `lease_id`/`lease_duration` as `provider_lease_id`/`provider_ttl_s`; `SecretsService.revoke` revokes it at the provider. Automatic renewal by the service is NOT IMPLEMENTED (`renew`/`renew_self` tested in `tests/test_vault_adapter.py::VaultHttp.test_lease_revoke_renew_and_token_renew`).
  - Real-Vault tests (`tests/test_vault_real.py`) run only when a server is configured; CI covers Vault 1.17 only (WVR-001).
  - Unsupported server versions are only flagged (`detail="unsupported_server_version"`), not refused.

## Change history

| Version | Date | Change | Author |
|---|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft | AI assistant at owner's request |
| 4.3.0 | 2026-09-22 | Dynamic lease ids, DR-secondary health, test evidence | AI assistant at owner's request |
