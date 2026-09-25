# Compatibility matrix (C084, C093)

| Dimension | Supported | Tested in 4.3.0 |
|---|---|---|
| Python | CPython 3.10, 3.11, 3.12 | 3.11.15 only |
| OS / arch | Linux x86_64, Linux aarch64, macOS arm64 (spawn) | Linux x86_64 only |
| Wasm engine | wasmtime 25.0.0 exact | not installed (BLOCKED) |
| Protocols | RUN 1–2, RESULT 1–2, HOSTCALL 1 | all |
| Peer releases | 4.2.x, 4.3.x (N-1 minor) | enforced by `check_peer_release` |
| pk_core | optional; conformance suite skips without it | absent |

Enforcement: `semantics.negotiate` and `check_peer_release` reject anything outside the window. Every other cell in the "Supported" column needs a CI matrix job before it can be claimed as tested.
