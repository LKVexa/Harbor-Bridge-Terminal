# Compatibility matrices
## Interface versions
| Peer offers | Result |
|---|---|
| 1.0 / 1.1 | accept, use min(peer max, 1.1) |
| 2.x only / 0.x only | UNSUPPORTED_VERSION before any workload runs |
| handle format ≠ 1 | UNSUPPORTED_VERSION |
| unknown must-understand handle bit | UNSUPPORTED_FEATURE |
| legacy INV-14 pollable | accepted via `PollableShim` with deprecation counter until `cutover=True` |

## Runtime/architecture matrix
| Platform | Status |
|---|---|
| Linux x86_64, CPython 3.11 | **RUN** (this delivery) |
| CPython 3.10 (declared minimum: `slots=True` dataclasses) | NOT RUN |
| Windows, macOS, aarch64, PyPy | NOT RUN |
| Wasmtime / other Component Model hosts | NOT APPLICABLE — no production host exists |

## Adjacent components
INV-11/12/14/16/17/18 and SCH-01 are not in this archive; the adapters target contract major 1 and fail fast on any other major.
