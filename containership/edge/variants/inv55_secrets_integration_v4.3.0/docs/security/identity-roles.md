# Identity and roles

| ID | INV55-SEC-ROLES | Version | 4.3.0 | Status | Draft |
|---|---|---|---|---|---|

Owner: `<UNASSIGNED: security-owner>` · Approval: `status: PENDING-OWNER-APPROVAL`

Source: `identity.py::ROLE_ACTIONS`, `PolicyEngine.decide`.

| Role | Actions | Intended holder |
|---|---|---|
| `consumer` | resolve, use | application workloads |
| `rotator` | rotate | rotation jobs |
| `secret-admin` | scope, retire, revoke | secret owners |
| `operator` | freeze, status | SRE on-call |

- Token claims are validated: `tenant` `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$`, `sub` `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$`, `roles` a list of ≤ 16 strings; anything else (including non-object header/claims) → UNAUTHENTICATED, audited.
- `secret-admin` may revoke another subject's lease in its tenant; audited as `revoked_by_admin`.
- Access requires BOTH a role granting the action AND a `Rule(tenant, subject glob, secret glob, actions)` matching the principal's tenant (`decide`). Default is deny (`no_matching_rule` / `role_lacks_action`).
- `freeze`/`unfreeze` go through `SecretsService._operator`: the principal MUST hold role `operator` AND belong to tenant `PLATFORM_TENANT = "platform"`; operators of other tenants are denied (`not_platform_operator`). Every attempt, including unauthenticated ones, is audited; the free-text reason is sanitised. `status` is not enforced anywhere: `health()` is unauthenticated (the host MUST restrict network access to it).
- `resolve` additionally requires subject ∈ scope (`set_scope`).
- Policy digest (`PolicyEngine.digest`) is recorded in every decision and in `health()`.
- Policy changes MUST go through `PolicyEngine.replace(rules)`, which rebuilds the cached digest and per-tenant rule index under the lock. Direct mutation of `.rules` is unsupported. There is no decision cache, so a replaced policy applies on the next call (`tests/test_security_adversarial.py::FailClosed.test_policy_change_takes_effect_immediately`).

## Vault-side least privilege (proposed; NOT shipped as code)
INV-55's Vault identity SHOULD have a policy limited to `<mount>/data/<tenant>/*` (read, create, update), `<mount>/metadata/<tenant>/*` (read), `<mount>/destroy/<tenant>/*` (update), `sys/leases/renew|revoke` (update), `auth/token/renew-self`. Token TTL SHOULD be <= 1 h. Policy HCL bundle: NOT IMPLEMENTED.

## Change history

| Version | Date | Change |
|---|---|---|
| 4.3.0 | 2026-09-22 | Initial draft |
| 4.3.0 | 2026-09-23 | Platform operator; claim validation; admin revoke |
| 4.3.0 | 2026-09-23 | Policy cache and replace() |
