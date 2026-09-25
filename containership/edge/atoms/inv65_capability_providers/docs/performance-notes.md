# Performance notes (C065/C066)

Two avoidable costs were found by profiling on 2026-09-22 and fixed:
1. `schemas.load` re-read and re-parsed the schema file on **every** validation (≈35% of call time) → cached.
2. The authentication replay cache swept **every** remembered nonce on every call (O(n) per call, growing with traffic) → heap-ordered expiry, O(log n).

Effect on the full-stack dispatch benchmark on the build host: p99 ≈1.16 ms (FAIL vs the 1 ms SLO) → ≈0.46–0.58 ms (PASS).

Remaining known costs: thread-pool hop per call (kept: it is what makes deadlines/cancellation enforceable), JSON canonicalisation for HMAC checks. Zero-copy/kernel-bypass is not applicable to this Python reference host.
