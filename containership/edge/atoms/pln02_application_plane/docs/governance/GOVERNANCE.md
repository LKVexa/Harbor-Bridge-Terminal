# Support, vulnerability, incident and review governance — PLN-02 (MC-38)

## Support commitments (C091)
- SLOs: resolution p99 < 500 ms @ 200 components (1 % budget); zero mutated published revisions (no budget);
  zero revisions published with an unsatisfied required capability (no budget).
- Supported line: latest minor of the current major; previous minor receives security fixes for 6 months.

## Vulnerability / patch / EOL SLAs (C094)
| Severity (CVSS) | Triage | Fix released | Notes |
|---|---|---|---|
| Critical ≥ 9.0 | 24 h | 7 days | emergency-disable considered immediately |
| High 7.0–8.9 | 3 days | 30 days | |
| Medium 4.0–6.9 | 10 days | 90 days | |
| Low < 4.0 | 30 days | next minor | |
EOL: announced ≥ 6 months ahead in CHANGELOG; the version window in `versioning.py` carries the removal date.

## Incidents (C097)
SEV1 = security breach, integrity loss, or total publish outage; SEV2 = degraded/partial; SEV3 = single-tenant
or cosmetic. Procedure: detect (alerts in `docs/operations/alerts.json`) → page → contain (`freeze`,
`quarantine`, `disable`, key revoke) → recover (rollback, restore) → post-incident review within 5 business
days → corrective actions tracked in `registers/CORRECTIVE_ACTIONS.json` until a regression test proves the fix.

## Recurring reviews (C098)
| Review | Cadence | Evidence |
|---|---|---|
| Access / role grants | quarterly | signed review record |
| Entitlement & constraint policy | quarterly | config digest diff |
| Dependency & licence scan | every release + monthly | SBOM + scan report |
| Configuration drift | monthly | `active.json` digest vs. source |
| Architecture (ADR) | semi-annual or on trigger | ADR review entry |
| Tabletop exercises | semi-annual: key compromise, provider supply-chain compromise, store corruption, catalogue outage, cross-tenant authz incident | exercise report |

## Registers (C099)
`registers/EXCEPTIONS.json`, `registers/TECH_DEBT.json`, `registers/DEPRECATIONS.json`,
`registers/CORRECTIVE_ACTIONS.json`. Every entry: id, owner role, created, expiry, scope, risk, compensating
control, approver. The gate fails on an expired entry.

**Status:** policy text is complete; no review, exercise or on-call rota has yet been *performed*, so MC-38 is
reported as BLOCKED_OWNER until dated evidence exists.
