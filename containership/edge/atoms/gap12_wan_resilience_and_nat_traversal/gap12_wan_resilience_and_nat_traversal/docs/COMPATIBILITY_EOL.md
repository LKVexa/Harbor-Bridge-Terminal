# GAP-12 compatibility matrix and end-of-life policy

## Compatibility
| Contract | v4.2.0 | v4.3.0 | Rule |
|---|---|---|---|
| PK_PATH_STATE/1 | emitted | unchanged | additive fields only within /1 |
| PK_BACKOFF/1 | named only | emitted by wan.contracts | new |
| PK_RELAY_ACCOUNTING/1 | named only | emitted by wan.contracts | new |
| PK_PATH_REQUEST/1 | named only | schema + builder | new |
| config g12-config | n/a | 1.1 | major bump = breaking; unknown fields rejected |
| state snapshot | n/a | schema 2 (migrates 1) | future schema refused |

Runtime matrix: see `pyproject.toml [tool.gap12.support-matrix]` (only CPython 3.11 / Linux verified).

## End of life
Proposed policy (requires owner approval, NOT approved): a minor release is supported for 12 months
after its successor ships; security fixes for 18 months; EOL is announced 6 months ahead.
