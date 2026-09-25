# Versioning and compatibility policy — PLN-06 (WP #8, C016/C027/C084/C093)

## Surfaces and versions

| Surface | Current | Rule |
|---|---|---|
| Package | 4.3.0 (SemVer) | MAJOR = breaking API/schema/protocol; MINOR = additive; PATCH = fixes |
| Python runtime | ≥ 3.10 | Supported: 3.10, 3.11, 3.12, 3.13 (CI matrix). A Python version is dropped only in a MINOR release after it reaches upstream EOL |
| JSON schemas | `PK_TRANSFER/1`, `PK_RESIDENCY/1`, `PK_TRANSPORT_TIER/1`, `PK_DATA_PLANE_METRICS/1`, `PK_DATA_PLANE_HEALTH/1` (deprecated, DEP-001), `PK_DATA_PLANE_HEALTH/2`, `PK_PAYLOAD_MANIFEST/1`, `PK_LOG/1`, `PK_AUDIT_RECORD/1`, `PK_DATA_PLANE_EXPLAIN/1`, `PK_DATA_PLANE_CONFIG/1` | Adding optional fields → same major. Removing/renaming/changing meaning → new `/N+1` emitted in parallel for one deprecation window |
| Adapter SPI | `PK_TRANSPORT_SPI/1` | Same as schemas |
| Component interface | `pk:data-plane/transfer@1.0.0` | Exact match required (mismatch → `PK_TRANSPORT_UNSUPPORTED`) |
| Network protocol | `pk06-rpc` versions `(1,)` | Peers advertise a version list; highest common version wins; no common version → refused. A server supports N and N-1 |
| Adjacent protocols | `PK_GAP13_POLICY/1`, `PK_GAP14_GRAVITY/1`, `PK_PLN03_HANDOFF/1` | Unknown protocol string → refused (fail closed) |

## Skew rules

* Mixed fleet: nodes on N and N-1 MINOR interoperate; rolling upgrade order is receivers first, then senders.
* Policy: a node refuses policy with a lower serial than it has activated (anti-rollback).
* Journal/audit files: forward-compatible JSONL; readers ignore unknown fields; a MAJOR bump ships a migration tool.

## Deprecation window

Minimum two MINOR releases **and** 180 days. Deprecations are recorded in `WAIVERS.json` (kind `deprecation`) and CHANGELOG.

## Compatibility CI

`.github/workflows/ci.yml` runs the full suite on the Python × architecture matrix; `tests/test_contracts_fuzz.py` validates every emitted object against its schema; `tests/test_runtime.py` retains 4.1/4.2 call-shape tests. Results feed `COMPATIBILITY.md`.
