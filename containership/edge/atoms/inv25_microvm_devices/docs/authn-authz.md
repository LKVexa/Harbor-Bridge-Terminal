# Authentication and authorization (work items 9, 10 — C023, C024, C042, C044, C048)

## Actors
| Actor | Operations | Identity |
|---|---|---|
| Proposer (device owner / automation) | propose register/replace | signed workload/CI token |
| Approver (security reviewer) | approve | signed human/OIDC token |
| Release/activation system | activate, rollback | CI identity token |
| Break-glass operator | emergency_disable | break-glass token (`bg=true`) |
| Runtime (INV-24) | read active catalogue, `permits()` | in-process / node identity at its RPC edge |
| Auditor | read audit/history | `catalogue.audit` |

In-process construction of `DeviceCatalogue` is a trusted boundary; every **cross-zone** mutation
goes through `CatalogueStore`, which requires a verified token.

## Credential format (reference)
`base64url(claims).base64url(HMAC-SHA256)`; claims `kid, iss, sub, aud, cap[], env[], nbf, exp,
nonce, bg`. Production replaces the HMAC issuer with the estate's workload-identity provider
(mTLS/SPIFFE or OIDC) behind the same `Verifier` interface; semantics below are what is certified.

## Rules (all tested in `tests/test_authz.py`)
- Missing, malformed, oversize, wrong-issuer, wrong-audience, bad-signature, unknown/revoked key,
  revoked subject, expired or not-yet-valid (±30 s skew) credentials are rejected.
- Nonces are single-use (anti-replay), thread-safe.
- Clock failure ⇒ reject (fail closed). Audit sink failure ⇒ mutations refused. Policy/dependency
  probe failure ⇒ activation refused, `ready=false`.
- Unknown capabilities in a token are dropped; unknown operations are denied.
- Secrets never appear in catalogue payloads, errors (redacted) or audit (refused).

## Capabilities
`catalogue.read`, `.export`, `.audit`, `.register`, `.replace`, `.widen`, `.approve`, `.activate`,
`.rollback`, `.emergency_disable`. Capability set is versioned as `POLICY_REVISION = INV25-AUTHZ/1`.
- Proposal ≠ approval: the approver must differ from the proposer; activation requires ≥ 1 approval.
- Surface widening additionally requires `catalogue.widen`.
- Environment scoping: a token lists environments (`*` = all, reserve for break-glass).
- Workloads never hold catalogue capabilities: they request classes through INV-24, never registers.
- Break-glass: `emergency_disable` requires `bg=true`, records actor/reason/incident/expiry and can only
  *narrow* (disable) — it cannot add devices. Every decision emits an audit event.
