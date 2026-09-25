# Compatibility matrix (C016, C027, C084, C093)

| Surface | Supported | Behaviour on other versions |
|---|---|---|
| Request schema | `PK_INVOKE_REQUEST/1` | refused, `INV31-E-UNSUPPORTED-VERSION` with supported list |
| Response schema | `PK_INVOCATION/1`, `PK_FUNCTION_POOL/1` | additive changes only within /1; removal or meaning change → /2 |
| Config schema | `PK_INV31_CONFIG/1` | refused |
| Python | CPython 3.10+ | tested: see `evidence/ci_run.json` (interpreter recorded as run evidence) |
| CPU arch | any CPython platform (pure Python) | only the CI host's arch is tested |
| pk_core | **UNPINNED** | absence/incompatibility → `INV31-E-PKCORE-UNAVAILABLE` |
| Dandelion | **UNRESOLVED** | BLOCKED (A03) |
| PLN-04 / INV-26 / PLN-05 / GAP-09 | Protocols in `adapters.py` | only reference doubles tested |

Deprecation rule: a schema version is supported for at least one minor release after its
successor ships; deprecated behaviours are listed in `GOVERNANCE.md` with an expiry.
