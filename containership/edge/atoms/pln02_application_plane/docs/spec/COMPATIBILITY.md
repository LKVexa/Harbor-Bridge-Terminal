# Version policy and compatibility matrix (MC-04, MC-34, C016, C027, C084, C093)

## Contract versions (`versioning.POLICY`)
| Contract | Supported majors | Status | Removal date |
|---|---|---|---|
| PK_APPLICATION | 1 | current | — |
| PK_PROVIDER_CATALOGUE | 1 | current | — |
| PK_SIGNED_CATALOGUE | 1 | current | — |
| PK_APPLICATION_REVISION | 1 | current | — |
| PK_ERROR | 1 | current | — |
| PK_PLANE_CONFIG | 1 | current | — |

Rules: additive, optional fields → same major, minor package bump; anything that changes meaning, identity or
refusal behaviour → new major, both majors served for ≥ 6 months with a removal date set in `POLICY`;
negotiation picks the highest mutually supported major (`versioning.negotiate`); downgrade never
reinterprets a newer document. Interface versions between components: exact string match in
`PK_APPLICATION/1`; for WIT-derived versions, semver compatibility via `wit.check_compatible` before
composing.

## Runtime / platform matrix
| Python | OS | Arch | Status | Evidence |
|---|---|---|---|---|
| 3.11 | Linux | x86_64 | verified | local gate run (evidence/) |
| 3.9, 3.10, 3.12, 3.13 | Linux / Windows / macOS | x86_64, arm64 | declared — CI matrix defined in `.github/workflows/ci.yml`, **not yet executed** | — |
| < 3.9 | any | any | unsupported | — |

## Adjacent layers
See `versioning.COMPATIBILITY_MATRIX`: all six peers (PLN-01, INV-65, PLN-03, SCH-01, INV-11, GAP-04) are
`verified-mock` — contract-faithful mocks, not live peers.
