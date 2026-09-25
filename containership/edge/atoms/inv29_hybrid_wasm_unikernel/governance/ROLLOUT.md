# Canary / staged rollout procedure (INV29-MC094)

**Entry criteria:** `RELEASE_CHECKLIST.md` complete; gate verdict for the exact release digest is GO or CONDITIONAL_GO with recorded conditions; rollback target identified (`inv29ctl rollback --seq`).

| Stage | Scope | Duration | Exit criteria | Abort triggers |
|---|---|---|---|---|
| 0 Shadow | new build evaluates in parallel, decisions not enforced | 24 h | decision diff vs current = 0 unexpected admits; refusals explained | any admit the current build refused |
| 1 Canary | 1 tenant / 1 site | 24 h | no SEV1/2; p99 within threshold; `INV29-E-INTERNAL` = 0 | any SEV1/2 alert; dependency breaker flapping |
| 2 Partial | 10 % of tenants | 48 h | same | same |
| 3 Full | all tenants | — | reconcile shows no unexpected revocations | same |

**Invariant preservation at every stage:** policy `required_layers ≥ 2`, denylist unchanged or stricter, signing key present, PLN-04 verifying signatures, schema consumers upgraded first.

**Rollback:** `inv29ctl disable --reason <incident>` (stops new admissions immediately; running compositions continue) → redeploy previous artifact from the rollback target → `inv29ctl enable` → run `reconcile` → confirm `/readyz` 200 and decision stream healthy. Record timestamps, actor, commands and resulting evidence hashes in the ledger.

**Status:** procedure defined and the disable/enable/rollback tooling is tested; the procedure has **not** been exercised in a non-production estate (IMPLEMENTED_LOCAL).
