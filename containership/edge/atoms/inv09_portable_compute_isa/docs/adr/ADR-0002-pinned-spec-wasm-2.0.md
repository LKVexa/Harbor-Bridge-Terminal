# ADR-0002: Pin the specification to Wasm core 2.0 and refuse everything else
Status: accepted. Decision: certify MVP + the six 2.0 feature families; recognise and refuse SIMD,
threads, EH, tail calls, typed refs, GC, memory64, multi-memory. Constant expressions follow 2.0 rules,
which is stricter than V8 (Wasm 3.0 relaxation) — recorded as a known divergence, never a false accept.
