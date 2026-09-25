# ADR-0001: Production maturity policy (MC-094)

**Status:** PROPOSED. This release implements it; the owner must approve it. Until approval, the release gate carries it as an open decision (`ops/DECISIONS.json` D-001).
**Date:** 2026-09-23

## Context
v4.2.0 contradicted itself. The contract boundary said production "may permit only mature toolchains", while the mandatory logic excluded only `experimental`, so `beta` stayed selectable.

## Decision
- Production admits `mature` only. The rule is `PK_TOOLCHAIN_POLICY/1`, `environments.production.min_maturity = "mature"`, set in `config/policy.default.json` and not as a code constant.
- `beta` is admitted in production only through a waiver for `TC_MATURITY_BELOW_POLICY`. The waiver must be approved, unexpired, scoped to that exact `name@version` and environment, and approved by someone other than its owner and not by a service identity.
- `experimental` is never admitted in production. No waiver can cover it.
- Staging admits `beta`, and dev admits everything.
- A candidate refused on this rule gets the stable code `TC_MATURITY_BELOW_POLICY`.

## Consequences
- This is the stricter of the two readings, so no toolchain that v4.2.0 refused becomes selectable. A beta toolchain v4.2.0 would have picked in production is now refused unless a waiver covers it. That change is safety-relevant and is called out in `CHANGELOG.md`.
- The deprecated v1 `ToolchainRegister.select` applies the same rule.
- Tests: `tests/test_selection.py::ProductionMaturityPolicy`, which covers the 3×3 environment × maturity matrix plus waiver variants.

## Alternative rejected
Keep `beta` selectable in production and change the contract text instead. This was rejected because loosening a production gate to match an implementation is the wrong direction to resolve a conflict.
