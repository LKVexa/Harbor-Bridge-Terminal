# Recurring reviews (work item 28B — C098)

| Review | Cadence | Scope |
|---|---|---|
| Access | quarterly | token issuers, capability grants, break-glass holders, CODEOWNERS validity |
| Policy | quarterly | permitted/forbidden classes, widening exceptions, authz policy revision |
| Dependency/version | monthly | pk_core, CI images, compatibility matrix stale cells |
| Configuration/defaults | quarterly | limits, rate limits, thresholds |
| Architecture/threat model | semi-annually | ADRs, threat model, telemetry/alert effectiveness |

Each review appends a record to `governance/reviews.json` (findings, owners, deadlines, closure evidence).
`tests/test_schemas_rtm.py::GovernanceTest` checks the register is well-formed and that no review is overdue
once the first review has been recorded.
