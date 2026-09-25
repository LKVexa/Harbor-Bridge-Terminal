# Supported-version compatibility matrix

| ID | INV55-ARCH-COMPATMATRIX | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: service-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

| Dimension | Supported | Source | Verified? |
|---|---|---|---|
| Vault server | 1.15, 1.16, 1.17, 1.18 | `vault.py::SUPPORTED_SERVER_VERSIONS` (prefix match in `VaultProvider.health`) | Fake Vault over real HTTP+TLS: `tests/test_vault_adapter.py`; real server: `tests/test_vault_real.py` (skips unless `INV55_VAULT_ADDR`/`INV55_VAULT_TOKEN`; a skip is NOT a pass); CI job `vault-real` uses `hashicorp/vault:1.17` only (WVR-001). Not run in the authoring environment: no Vault binary, container registry blocked. |
| Vault HTTP API | `/v1` | `VaultProvider._request` | `tests/test_vault_adapter.py` (fake Vault) |
| KV engine | v2 (full), v1 (read/write only; no CAS, metadata, destroy) | `VaultProvider.read/write/metadata/destroy_version` | `tests/test_vault_adapter.py` (fake Vault) |
| Vault auth | Token (dev), AppRole, Kubernetes | `TokenAuth`, `AppRoleAuth`, `KubernetesAuth` | `tests/test_vault_adapter.py` (fake Vault) |
| Vault Enterprise namespaces | Yes | `X-Vault-Namespace` header | `tests/test_vault_adapter.py` (fake Vault) |
| Python | 3.11, 3.12, 3.13 | Uses `X | Y` unions, `dataclass`, `ssl.TLSVersion` | CI job `test` matrix 3.11–3.13 (`.github/workflows/ci.yml`) |
| Runtime dependencies | CPython stdlib only | imports in all modules | Yes (by inspection) |
| `pk_core` | Required only by `contract.py`/`component.py` conformance path; not bundled | `contract.py` import | `tests/test_component.py` skips without it (WVR-002) |
| Wire protocols | `PK_SECRET_RESOLVE/1`, `PK_SECRET_ROTATE/1`, `PK_SECRET_SCOPE/1` | `service.py::PROTOCOLS` | — |
| TLS | >= 1.2 | `build_tls_context` | `tests/test_vault_adapter.py::VaultTls.test_min_tls_version` |
| Test-only dependency | `jsonschema` (pinned in `requirements-test.txt`) | `tests/test_schemas_fixtures.py` | — |
| Packaging | `pyproject.toml`, setuptools, zero runtime deps | — | — |

Unsupported Vault versions are reported as `health()["dependencies"]["provider"]["detail"] == "unsupported_server_version"` but are NOT refused.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-22 | Linked tests, CI matrix, packaging |
