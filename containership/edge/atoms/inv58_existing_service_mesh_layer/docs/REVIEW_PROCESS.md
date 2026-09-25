# Recurring reviews (defined; not yet performed — reviewers UNASSIGNED)

| Review | Cadence | Scope | Output record |
|---|---|---|---|
| Access | monthly | role bindings in config, token issuers, break-glass arming log | `governance/reviews/<date>-access.json` |
| Policy | monthly | capability policy version/age, waivers & tech debt register | `…-policy.json` |
| Dependency | monthly | `governance/bom.json`, advisories for jsonschema/pk_core/Istio | `…-deps.json` |
| Configuration | per release + quarterly | config diff by digest, secure-default deviations | `…-config.json` |
| Architecture | quarterly | ADR-001, threat model, residual risks | `…-arch.json` |

Record fields: `review, date, reviewers[], scope_digests{}, findings[], actions[{id, owner, due}], next_due`. The release gate reads the newest record per review type once `governance/reviews/` exists and treats an overdue review as a blocker.
