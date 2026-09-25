# Security model — PLN-06 data plane (4.3.0)

Threat model with test mapping: `docs/THREAT_MODEL.md`. Vulnerability reporting and SLAs: `docs/VULNERABILITY_POLICY.md`.

## Implemented controls (4.3)

| Control | Where | Fail mode |
|---|---|---|
| Boundary authentication (workloads, operators, nodes/peers, providers, control plane) | `security.Authenticator`, `pk06-rpc` mutual HMAC, mTLS | closed |
| Least-privilege capabilities, tenant scoping, per-tier transport capability | `security.Authorizer`, `service.submit` | closed |
| Signed classification labels bound to tenant + payload digest + expiry | `security.LabelAuthority` | closed |
| Key lifecycle: rotation, verify-only grace, revocation, expiry, KMS outage | `security.KeyRing` / `KeyProvider` | closed |
| End-to-end payload integrity: chunk + root manifest, receiver verification, quarantine | `integrity`, `transports` | closed, never auto-retried |
| Encryption in transit | `ssl.SSLContext` (TLS ≥ 1.2, mTLS) on `pk06-rpc` | `tls_required_for_remote` enforced by config floor |
| Tamper-evident audit ledger | `security.AuditLedger` | chain break detected on load |
| Adapter authority guard | `security.AuthorityGuard` + `Grant` | closed |
| Tenant isolation at admission and in shared memory | quotas, DRR, `tenant_namespace` | backpressure |
| Control-path isolation (INV-36) | `vm_control` locality, vsock verb allow-list, selector | closed |
| Anti-replay / anti-downgrade | single-use credentials, audience, policy serial, protocol negotiation | closed |
| Split-brain protection | fencing epoch on every journal write | closed |
| Redaction | logs, explain view, metrics labels | — |
| Operator containment | freeze, quarantine, drain, emergency-disable (audited) | — |

## Residual risks (tracked in `WAIVERS.json`)

OS-level sandbox / hostile-tenant process isolation (W-011); KMS/HSM custody and at-rest volume encryption (W-012); upstream wRPC interop (W-003); Sigstore/SLSA provenance (W-017); CVE scanning in CI (W-019); fleet-wide lease (TD-003); independent security review of the threat model (W-002).
