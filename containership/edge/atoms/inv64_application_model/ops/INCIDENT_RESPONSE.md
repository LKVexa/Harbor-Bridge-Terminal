# Incident response — INV-64 (MC-34; C097)

Status: procedure defined; roles unassigned; paging paths and tabletop exercises **not yet performed** (MC-34 blocker).

## Severity

| Sev | Definition (INV-64 examples) | Declared by | Page |
|---|---|---|---|
| SEV1 | cross-tenant leakage; auth/authz bypass; audit integrity failure or dropped audit events; compromised signing/trust key; invalid manifests reaching deployment at scale | anyone on the roster | immediately (ops/owners.json SEV1 chain) |
| SEV2 | service blocked or error-budget burn > 14.4x; bad configuration rollout auto-rolled back on several targets; dependency outage > 30 min | on-call | yes |
| SEV3 | degraded (optional dependency), isolated tenant misconfiguration, telemetry gaps | on-call | business hours |

Roles: incident commander (inv64-sre-oncall until handed off), operations, security (inv64-security-contact), communications (owner), scribe.

## Standard flow

1. **Declare** in the incident log: time, severity, commander, correlation IDs, release/config/policy digests from `status()`.
2. **Preserve evidence** before destructive action when safe: copy the audit ledger + anchor, `ConfigStore` directory, `evidence/`, recent logs; record their SHA-256 in the incident log.
3. **Contain** (bounded blast radius, confirm each step):
   - freeze changes: abort in-flight rollouts (`Rollout.abort`), stop new activations;
   - rollback: `store.rollback(...)` per affected target (known-good only);
   - disable: `service.emergency_disable(...)` if no known-good exists or the flaw is in INV-64 itself;
   - credentials: revoke tokens/subjects in `TrustConfig`, rotate issuer keys;
   - artifacts: add digests to trust-policy `denied_digests`;
   - providers: remove the provider from `SharedResources` / INV-65 grants.
4. **Recover**: re-enable in stages via `rollout.py`; criteria — status ready on every target, audit verify PASS, no rejections of security codes above baseline for 1 h.
5. **Communicate**: notify affected tenants for any confirmed cross-tenant exposure or security-relevant rejection of their traffic; sensitive details only under the disclosure process (SECURITY_RESPONSE.md).
6. **Hand off** to adjacent owners (INV-10/63/65/66, pk_core) when the fault is theirs; INV-64 keeps command until they acknowledge.
7. **Post-incident review** for SEV1/SEV2 within 5 business days; corrective actions go to `ops/REGISTER.json` (type technical-debt) with owner and date.

<a id="auth-bypass"></a>
## Scenario: authentication/authorization bypass or attack pattern (alert A05)
Contain by revoking the affected subjects/token IDs and, if a key is suspect, rotating it; raise `failure_limit` strictness; check `authz` audit records for `allowed` decisions that should not exist; SEV1 if any bypass is confirmed.

<a id="audit"></a>
## Scenario: audit integrity failure or dropped events (alert A07)
Treat as SEV1. Run `python -m inv64_application_model.audit verify` with the anchor; if it fails, the ledger is evidence — copy, do not repair; start a new ledger with a new anchor key; critical operations refuse while the sink is down (by design).

<a id="key-compromise"></a>
## Scenario: key compromise or crypto failures (alert A10)
Revoke the kid (trust policy / KeyRing), rotate, rewrap sealed objects, re-sign artifacts with the managed signer, rotate audit MAC/anchor keys and seal a fresh checkpoint.

## Other scenarios
Widespread invalid deployments (roll back the policy/config that admitted them; check `explain` records); artifact/provenance compromise (deny digests, rebuild from a clean source revision); cross-tenant leakage (disable, preserve, notify); dependency outage (RUNBOOK dependency-outage); performance collapse (abort rollout, roll back release); bad configuration rollout (auto-rollback + quarantine, then RUNBOOK activation).

## Exercises

Required before production: one security tabletop (auth bypass) and one availability tabletop (bad config rollout); page-path test for SEV1. Record in ops/REVIEWS.json history.
