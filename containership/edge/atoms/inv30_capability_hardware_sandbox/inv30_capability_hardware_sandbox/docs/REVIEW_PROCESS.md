# Recurring reviews (INV30-GAP-068 · INV-30-C098)

| Review | Cadence | Inputs | Output |
|---|---|---|---|
| Access (principals, actions, tenants, keys ≥256 bit, key age) | quarterly | principal registry, secret refs | revoke unused; rotate > 1 year |
| Policy (precedence, limits, authz) | quarterly | policy.py, limits.py, decisions sample | ADR update if changed |
| Dependency (Python, pk_core, siblings, CHERI toolchain) | monthly | SBOM, COMPATIBILITY_MATRIX | matrix update |
| Configuration (overlay drift, provenance) | monthly | ConfigStore history | drift report |
| Architecture (ADR validity, threat model) | semi-annually or on trust-boundary change | ADR-0001, THREAT_MODEL | re-approval |
| Waivers & tech debt | monthly | WAIVERS.json | close/extend (never class 1) |

Each review is logged in `evidence/REVIEWS.jsonl` (date, reviewer, scope, findings).
