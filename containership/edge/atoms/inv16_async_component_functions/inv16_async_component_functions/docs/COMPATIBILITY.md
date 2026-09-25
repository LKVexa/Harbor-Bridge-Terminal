# Compatibility matrix (v4.3.0)

| Dimension | Supported | Evidence |
|---|---|---|
| CPython | 3.10, 3.11, 3.12, 3.13 (normal and `-O`) | `evidence/test_matrix.json` |
| OS / arch | Linux x86_64 tested; Windows, macOS, ARM **untested** | — |
| Other interpreters | PyPy etc. unsupported | preflight rejects out-of-range CPython |
| pk_core | `>=1.0,<2.0` exposing `contract`, `checklist`, `component`, `integration` | preflight fails closed otherwise |
| Declaration schema | `PK_ASYNC_DECL/1` | `declare.SUPPORTED_DECL_SCHEMAS` |
| Value transport | ABI envelope schema 1 | `abi.SUPPORTED_SCHEMAS` |
| Events / metrics | `inv16.event/1`, `inv16.metrics/1` | observability.py |
| Topology | single owner process per logical instance | preflight `INV16_TOPOLOGY` |
| Rollback target | 4.2.0 (behind generation fence) | `tools/rollback.py`, test_release_ops |
| Sibling fixtures | INV-15/10/11/17/20: surrogate-1 only | fixtures/ |
