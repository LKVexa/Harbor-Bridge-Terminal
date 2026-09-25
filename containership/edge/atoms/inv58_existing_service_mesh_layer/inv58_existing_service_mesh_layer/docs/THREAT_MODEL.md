# INV-58 Threat model (v4.3.0)

Machine-readable source: `governance/threat_model.json` (18 threats, each with mitigations, tests and residual risk). `tests/test_security_regression.py` fails if any threat lacks an existing test.

**Assets:** retry budgets / dependent-service availability, runtime identities, tenant route policy, bypass evidence, configuration and keys, audit trail, release artifacts.
**Actors:** malicious tenant, compromised workload, compromised node agent, stale controller, insider operator, compromised CI publisher, network attacker, supply-chain attacker.
**Trust boundaries:** mesh → node agent (SPIFFE), controller → INV-58 (SPIFFE), operator/CI → INV-58 (token), INV-58 → key/identity/policy/time services, INV-58 → audit sink, artifact intake.

| STRIDE | Covered by |
|---|---|
| Spoofing | T-02, T-07, T-15 |
| Tampering | T-08, T-10, T-11, T-16 |
| Repudiation | T-10 (every privileged/denied action audited) |
| Information disclosure | T-09, T-17 |
| Denial of service | T-01, T-12 |
| Elevation of privilege | T-05, T-06, T-18 |

## Least privilege
Roles (`authz.DEFAULT_ROLES`, inventory via `authz.privilege_inventory()`):

| Role | Capabilities | Why |
|---|---|---|
| mesh-node | identity.map, bypass.report | node agents only report and map |
| mesh-controller | status, reconcile, route read/migrate, bypass read, artifact.verify | route migration owner |
| mesh-observer | status, route read, bypass read | read-only |
| config-publisher | config.validate/activate, artifact.verify | CI publishes; cannot roll back or freeze |
| mesh-operator | status, reads, config.validate/rollback, freeze, quarantine, state.restore | cannot *activate* config (separation of duties) |
| security-auditor | status, audit.read/export, reads | only role that exports audit |
| break-glass | control.break_glass | only with an armed window |

No wildcard capabilities exist; the validator refuses them and refuses granting break-glass to any other role or to a mesh identity.

## Ambient authority
The package performs no filesystem, network, subprocess, environment-variable or device access on its own. Secrets are resolved only through providers injected into `SecretResolver`; the only file write is the optional audit JSONL sink at a path the host passes in (created 0600, append-only). Host-level sandboxing (seccomp, read-only root, no egress) is outside this archive — INV-58-C043 is PARTIAL for that reason.

## Crypto
- In transit: provided by the incumbent mesh mTLS (TLS 1.3 preferred, TLS 1.2 minimum — `governance/bom.json`); INV-58 consumes the SAN.
- Integrity at rest: audit records are hash-chained and HMAC-sealed; snapshots are HMAC-sealed; configs are digest-addressed.
- Confidentiality at rest: **not provided** — persisted audit/snapshots are integrity-protected, not encrypted (RR-01).
- Rotation: keys are referenced (`secretref://`) and re-resolved on every activation, so rotation = publish new key under the reference + activate config. Audit chain continuity across audit-key rotation requires exporting and sealing the old segment first (runbook).
