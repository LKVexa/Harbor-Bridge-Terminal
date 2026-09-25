# Recurring reviews (C098)

| Review | Cadence | Inputs | Owner | Last held |
|---|---|---|---|---|
| Access (trust-store keys, revocations, capability registrations) | quarterly | TrustStore key list, `capability.registered` audit events | security reviewer | never |
| Policy (precedence, degraded rules, telemetry policy) | semi-annual | docs/PRECEDENCE.md, resilience.DEGRADED_RULES, TELEMETRY_POLICY | owner | never |
| Dependency (wasm.lock, CPython, pk_core) | monthly | advisories, lock check | reliability reviewer | never |
| Configuration drift | monthly | `ConfigStore.history` across sites | reliability reviewer | never |
| Architecture (ADRs, EXCEPTIONS.yaml expiry) | semi-annual | docs/adr, EXCEPTIONS.yaml | owner | never |

Each review adds a dated row to `ops/review_log.md` with findings and actions.
