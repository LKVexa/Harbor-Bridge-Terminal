# Support matrix (M04, M05, M27)

## Protocol
| Item | Supported |
|---|---|
| Handshake | `wrpc/2` only; deprecated set empty |
| Frame | `PK_WRPC_FRAME/2` (binary). `PK_WRPC_FRAME/1` dict frames remain the in-process `rpc.py` API |
| WIT | package/interface/func/record/enum/variant/type alias; bool, u8–u64, s8–s64, f32, f64, char, string, list, option, result, tuple |
| WIT rejected (stable code) | resource, flags, stream, future, use, world, own, borrow |

## Runtime
| Platform | Status |
|---|---|
| CPython 3.11, Linux x86_64 | **verified in this build** (full suite + bench) |
| CPython 3.10/3.12/3.13; Linux arm64; Windows; macOS | **declared, not verified** — CI matrix committed (`.github/workflows/inv61-ci.yml`), not executed |
| Wasm runtimes / non-Python peers | not verified; golden vectors (`fixtures/golden_vectors.json`) are the interop contract |

Endianness: all multi-byte fields are explicitly big-endian (`struct` `>`), so host byte order
does not affect the wire.
