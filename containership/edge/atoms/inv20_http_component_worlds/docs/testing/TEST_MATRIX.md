# Test matrix (component 18)

| Layer | Suite | Runs here | Notes |
|---|---|---|---|
| Unit | test_runtime, test_protocol, test_config, test_identity | yes (normal + `-O`) | host canon, allow-list, limits, chunks, completions, config precedence, error mapping |
| State machine / concurrency | test_aio | yes | legal/illegal transitions, races on head/trailers, 200-request cancellation leak check |
| Security / adversarial | test_egress, test_identity, fuzz/ | yes | rebinding, mixed answers, CNAME, mapped IPv6, redirects, forged/replayed/revoked caps |
| Contract | test_ops.WitTest, test_protocol | partial | WIT structure + error-variant parity; no generated ABI |
| Evidence / gate | test_evidence | yes | disposition + gate semantics |
| Packaging | test_ops.PackagingTest, tools/release.py | yes | version single-source, clean-room install, tests against installed wheel |
| Benchmark | bench/run_bench.py | yes (sandbox) | not controlled hardware |
| pk_core conformance | test_component | **BLOCKED** | mandatory; skip ⇒ gate BLOCKED |
| Runtime integration (wasmtime/jco) | — | **BLOCKED** | no runtime available |
| INV-13/16/17/18/21 integration | — | **BLOCKED** | sibling components not supplied |
| DNS/transport/TLS adjacent | — | **BLOCKED** | owning layer unnamed |
| Compatibility (arch/OS/runtime/pk_core versions) | — | **BLOCKED** | single platform: Linux x86_64, CPython 3.11 |
| Soak / fleet / disaster / partition | — | **BLOCKED** | needs infrastructure |

Hygiene: `test_component` is the only skip-capable suite and its skip is recorded as
`skipped_mandatory` → gate cannot return GO. Fuzz seeds are recorded; benchmark runs record platform.
