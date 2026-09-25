# PLN-05 IAM and capability model (policy 1.0.0, `security/capabilities.json`)

**Default deny.** Every externally callable operation authenticates a credential and authorises one action against the actor class's capability list, the credential's own (subset) capability claims, and the tenant/site scope — in `iam.Authenticator` before any state lookup.

| Actor class | Capabilities | Tenant scope | Trust bootstrap |
|---|---|---|---|
| demand_reporter | demand.submit | single, **source-bound** | workload identity attested via GAP-09; token minted by issuer |
| intent_plane | limits.update, status.read | single | PLN-01 service identity (mTLS) |
| power_thermal | ceiling.lower, status.read | single | GAP-10 service identity |
| operator | status.read(+admin), explain.read, control.freeze/quarantine/disable | single | SSO → short-lived token |
| platform_operator | config.change, config.rollback, status.read(+admin) | any | SSO, platform group; plane-global config only |
| policy_service, provider_adapter, telemetry_collector | status.read | single | service identity |
| sibling_plane | status.read, explain.read | single | service identity |
| release_agent | evidence.read, status.read | single | CI OIDC in a protected environment |
| emergency_admin | control.*, control.resume, config.rollback, status | any | break-glass issuance, **ticket required**, always audited |

- **Separation:** read (`status.read`, `explain.read`), control (`control.*`, `ceiling.lower`, `limits.update`), administrative (`config.*`, `control.resume`, `status.read_admin`). Demand submitters can never change the envelope (distinct capability, T02).
- **Identity mechanisms accepted at adapters:** mTLS with SPIFFE IDs (`TransportPolicy` checks identity, protocol ≥ TLS 1.2, approved ciphers, expiry, revocation) carrying an HMAC `v1` token issued by the identity issuer. Cloud workload identity is acceptable if the adapter maps it to the same token.
- **Lifetimes:** per class `max_lifetime_s` (≤ 3600 s); tokens issued > 5 s in the future are refused; signing keys rotate with overlap (`KeyRing`), revocation is immediate.
- **Replay resistance:** control/administrative actions (`single_use_actions`) consume the token nonce; demand is replay-protected by `message_id` + `seq`.
- **Source binding:** a reporter token's `src` must equal the message `source`; limits `issuer` must equal the principal (`E_AUTHZ_SCOPE`).
- **Break-glass:** `emergency_admin` only, ticket mandatory, lifetime ≤ 1 h, every use audited; resume needs two different principals.
- **Failure behaviour:** authentication/authorisation failures are audited (`result=denied`) and return `E_AUTHN_*`/`E_AUTHZ_*` without detail about which part failed beyond the code.
- **Runtime least privilege:** the library opens files only under the configured `state_dir`, `config_dir` and `audit_path`; it opens no sockets, spawns no processes and reads no environment variables. Deployment SHALL run it as a non-root user with a read-only root filesystem, those three paths writable, no Linux capabilities, and no device access (see `security/isolation-model.md`).
- **Versioning:** the policy version is reported in status and recorded in every explain record (`authorization.policy_version`).
- **Tests:** `tests/test_units.py::IamTest`, `tests/security/test_adversarial.py` (T01, T02, T06, T09, T10, T17).
