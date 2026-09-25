# Least-privilege identities, roles and confinement (checklist #39, #40, #41)

Roles (`runtime/identity.py::ROLES`) grant verbs only; names come from per-secret scope:

| Role | Verbs | Typical holder |
|---|---|---|
| secret-consumer | resolve, use | workloads |
| secret-rotator | rotate | rotation automation (separate identity from consumers) |
| scope-admin | scope.read, scope.write | platform team (two-person review via config commit) |
| operator | freeze, unfreeze, health.read | on-call |
| auditor | audit.read | security |

INV-55's own Vault identity (AppRole) gets the policy in `deploy/vault/policies/inv55-runtime.hcl`: read/list on `secret/data/<tenant>/*` for tenants it serves, create/update for rotation, destroy only via a separate break-glass role. **Not applied to any Vault** (no Vault provisioned).

Ambient authority confinement: the runtime reads trust roots only from files named by `INV55_*_FILE` environment variables; it opens no listening socket itself (embedding/sidecar hosts it); it spawns no processes; it writes only the audit path. OS-level confinement (read-only root FS, seccomp, non-root UID, no network egress except the Vault address) is specified here and must be applied by the deployment platform — **not verifiable in this repository** (W-005).

Peer authentication: workloads → HMAC-signed tokens (in-repo verifier); INV-55 → Vault: token/AppRole + optional mTLS (tested against an in-repo TLS double). External IdP / SPIFFE issuer binding is BLOCKED on provisioning (W-003).
