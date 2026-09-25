# GAP-11 compatibility matrix (GAP11-P2-40)

| Dimension | Supported | Evidence | Status |
|---|---|---|---|
| CPython | >= 3.10 (uses `X | Y` types, dataclass slots) | CI run on CPython 3.11 (see evidence/RUN.json) | 3.11 tested; 3.10 declared, not run here |
| OS/arch | Linux x86_64 | cloud container | other platforms untested |
| Runtime dependencies | none (stdlib only) | `release/SBOM.cdx.json` | verified |
| pk_core | optional; only `component.py`/`contract.py` import it; range `>=4.0,<5` declared, **not tested** (pk_core not supplied) | — | UNTESTED |
| Wire schemas | PK_ACCELERATOR_ALLOCATION_REQUEST/1, PK_ACCELERATOR_ALLOCATION/1, PK_ACCELERATOR_RELEASE_REQUEST/1, PK_ACCELERATOR_RELEASE/1, PK_SCRUB_REQUEST/1, PK_SCRUB/1, PK_ACCELERATOR_INVENTORY/1, PK_ERROR/1 | golden fixtures | tested |
| WAL format | v1 (4.3.0) | crash tests | tested |
| Accelerator families / drivers / firmware / hypervisors | simulated NVML-like, ROCm-SMI-like, NPU payloads only | `test_hardware` | **UNTESTED on real hardware (BLK-HW)** |

## Compatibility rules
- Requests are closed schemas: unknown fields are errors. Responses are open: readers ignore unknown fields.
- Within `/1`: additive optional fields only. Enum growth in responses is a minor bump; readers map unknown values to `UNKNOWN`.
- Removal or rename of a field, or any change in meaning, is a new major (`/2`); the controller serves `/1` and `/2` side by side for at least one minor release; deprecation is announced in the CHANGELOG with a removal version.
- Mixed-version controllers: all 4.x controllers must read WAL v1 and the `ctl/leader` record; a controller that sees an unknown WAL format refuses to open (STORE_CORRUPT) rather than guessing.
