# M15 differential dispositions (reference: V8 `WebAssembly.validate`, Node 22)

| Class | Meaning | Disposition | Release impact |
|---|---|---|---|
| FALSE_ACCEPT | we accept, V8 rejects | release-blocking Sev-1 | observed: **0** |
| FALSE_REJECT | we reject (not proposal/limit), V8 accepts | investigate; fix or record below | observed after fixes: **0** |
| PROPOSAL_GAP | we refuse `UNSUPPORTED_PROPOSAL`, V8 accepts (it enables GC, EH, tail-call, SIMD, threads…) | expected by ADR-0002 | none |
| LIMIT_GAP | we refuse on an M13 ceiling | expected | none |

Known divergences (stricter than reference; never a false accept):

| Case | Rationale | Owner | Review by |
|---|---|---|---|
| `global.get` of a locally-defined immutable global in a constant expression | Wasm 2.0 forbids; V8 implements the Wasm 3.0 relaxation | TBD (OWNERS.yaml) | next spec-pin change |

Open: a second independent reference (wasmtime or wabt `wasm-validate`) is required by M15-007 and was not
installable in this offline build.
