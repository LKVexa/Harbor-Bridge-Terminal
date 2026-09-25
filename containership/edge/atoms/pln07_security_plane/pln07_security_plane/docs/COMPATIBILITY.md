# Compatibility and supported versions (MC-16, MC-50, MC-51, MC-66)

## Version matrix
| Artifact | Accepts | Emits | Notes |
|---|---|---|---|
| Service API | `api_version` "1" | "1" | negotiation picks highest common, else `api.unsupported_version` |
| Grant body | `PK_GRANT/1`, `PK_GRANT/2` | v2 from service; v1 when no v2 fields | `require_v2` retires v1 |
| Revocation | `PK_REVOCATION/1` ids (16-hex) via `Verifier.revoked`, `PK_REVOCATION/2` records | `/2` | |
| Signature | `PK_SIG/1` | `PK_SIG/1` | |
| Python | 3.10 – 3.13 | | tested on 3.11 in this build |
| OS | Linux, Windows, macOS | | fsync + `os.replace` used for atomicity |

Mixed-version rule: a peer that does not know a field refuses it; nothing is dropped silently.

## Supported releases
| Release | Status | Security fixes until |
|---|---|---|
| 4.3.x | current | 12 months after 4.4.0 |
| 4.2.x | maintenance | 2027-03-31 |
| ≤ 4.1 | end of life | — |

## Adjacent-layer integration matrix (MC-50) — pending siblings
| Neighbour | Contract | Test | Status |
|---|---|---|---|
| GAP-06 identity | `Authenticator` | adapter conformance | blocked |
| GAP-13 policy | `PolicyEngine` | allow/deny parity | blocked |
| GAP-07 signing | KeyStore backend | sign/verify/rotate | blocked (reference passes) |
| GAP-04 autonomy | revocation horizon + lease | partition drill | blocked (reference passes) |
| PLN-01/03/04 | enforce `verify` before use | end-to-end deny | blocked |

## Architecture/runtime compatibility (MC-51)
Pure Python; the gate runs on each target (`python -m pln07_security_plane.ci.gate`). Ed25519 needs `cryptography` wheels for the target; HMAC path needs nothing.
