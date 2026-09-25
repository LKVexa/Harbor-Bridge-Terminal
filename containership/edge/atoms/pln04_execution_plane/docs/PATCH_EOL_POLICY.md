# PLN-04 patch, vulnerability and end-of-life policy (PLN-04-C094, C098, C099) — PROPOSED

| Class | Response | Patch released |
|---|---|---|
| Critical (sandbox escape, auth bypass, cross-tenant) | 4 h triage | 72 h |
| High | 1 business day | 7 days |
| Medium | 5 business days | 30 days |
| Low | next minor | next minor |

- Supported: the current minor and the previous minor. A minor reaches EOL 6 months after its successor ships.
- Runtime floor: CPython ≥ 3.10. Each CPython minor is dropped at its upstream EOL.
- Every waiver lives in `ops/WAIVERS.json` with an owner, an expiry and an approver. The release gate treats an unapproved waiver as a blocker.
- Deprecations: an error code or schema field is marked deprecated for one minor before removal (`errors.ErrorSpec.deprecated`).
- Recurring reviews: quarterly access, policy, dependency, config and architecture review, recorded in the work log.

Approval: owner UNASSIGNED.
