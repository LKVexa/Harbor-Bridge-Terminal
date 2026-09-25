# Third-party notices

No third-party code is bundled in this package. The runtime is Python-stdlib only.

| Component | Use | License | Bundled |
|---|---|---|---|
| wasm-tools 1.219.1 (Bytecode Alliance) | differential testing reference, invoked as an external process by tests and `tools/evidence.py` | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | no |
| OpenSSL 3.x | Ed25519 signing/verification, invoked as an external process | Apache-2.0 | no |
| pk_core | optional estate runtime used by the 4.2.0 component adapter | per estate | no |

No parts were pulled from the GitHub Junkyard for this pass; everything under
`wit/`, `tools/` and `tests/test_wit_*` was written new for 4.3.0.
