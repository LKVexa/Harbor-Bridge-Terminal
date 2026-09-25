# Dependencies — INV-44 v4.3.0

| Dependency | Used by | Required? | Pinned? | Status |
|---|---|---|---|---|
| CPython >= 3.10 standard library | everything | yes | range | OK |
| `pk_core` (Contract, Dependency, Slo, ChecklistItem, Finding, Component) | `contract.py`, `component.py`, `PkCoreConformanceTest` | for estate conformance only | **no** | **BLOCKED** — not in the supplied archive; version, source and digest unknown |
| Node.js >= 18 (`WebAssembly.validate`) | `IndependentValidatorLane` test | optional lane | no | declared lane NODE_WASM; skips with its reason when absent |
| setuptools >= 68 | wheel build | build-time | range | declared lane PACKAGING |
| Swivel toolchain / hardened Wasm runtime | component 8 | for production | **no** | **BLOCKED** — not supplied |

## Rule for pinning `pk_core`

When it is supplied, pin it by exact version **and** sha256 of the artifact
(`pk_core==X.Y.Z --hash=sha256:...` in a requirements lock, or a vendored copy
under a manifest). A version range or a guessed version is not a pin. Until
then the conformance lane reports NOT RUN — never PASS.
