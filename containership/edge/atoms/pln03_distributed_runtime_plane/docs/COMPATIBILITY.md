# Compatibility, deprecation and support policy (MC-007, MC-050)

## Versioning
- Interfaces: `PK_<NAME>/<major>`. Additive, optional fields → same major. Removing/renaming a field, tightening a limit, or remapping an error code → new major.
- Error codes (`envelope.CODES`) are append-only within a major.
- Runtime releases: SemVer (`VERSION`).

## Support window
- **N-1 policy:** a runtime release supports its interface majors and the immediately previous major for at least two minor releases after a new major ships.
- Deprecation is announced in CHANGELOG, listed in `negotiation.DEPRECATED`, surfaced in the negotiation `Agreement.deprecated` so telemetry can count callers, then removed no earlier than 90 days later.
- Compatibility exceptions require the approvers named in `OWNERS.yaml > emergency_authority.compatibility_exception`.

## Compatibility matrix
| Runtime | PK_STATE | PK_MESSAGE | PK_SECRET | PK_INVOKE | Config schema | Python |
|---|---|---|---|---|---|---|
| 4.3.0 | 1 | 1 | 1 | 1 | pk.pln03.config/1 | 3.10 – 3.13 (CI) |
| 4.2.0 | 1 (names only) | 1 | 1 | 1 | — | ≥ 3.10 |

## Vulnerability / patch / EOL SLA
| Severity (CVSS) | Fix released | Fleet patched |
|---|---|---|
| Critical ≥ 9.0 | 72 h | 7 days |
| High 7.0–8.9 | 7 days | 30 days |
| Medium | 30 days | next release |
| Low | next release | next release |

A release line reaches EOL 12 months after its successor ships. The runtime has **no third-party runtime dependencies**; `pk_core` (conformance only) is tracked in `DEPENDENCIES.lock.json`.
