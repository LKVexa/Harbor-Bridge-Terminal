# INV-30 4.3.0 exit gate — CONDITIONAL_GO_MODEL_ONLY

* Generated 2026-09-23T16:55:07+00:00 · tree `sha256:776442044878e901d126ee2da8a3fc907fab1d9802c18fa157e8f4bfe517016c` · source `no-vcs`
* Hardware tier: **NO_GO** — no CHERI backend evidence: absent (Linux has no CHERI kernel support)
* Zero-budget invariant failures: 0 (unwaivable)
* Blockers: none
* Conditions: ['sign-off missing: owner', 'sign-off missing: security_reviewer', 'sign-off missing: independent_verifier']
* Benchmark regressions: none

| Suite | normal pass/ran | skipped | -O pass/ran | skipped |
|---|---|---|---|---|
| concurrency | 4/4 | 0 | 4/4 | 0 |
| config-supplychain | 16/16 | 0 | 16/16 | 0 |
| contracts | 12/12 | 0 | 12/12 | 0 |
| framework-conformance | 3/3 | 0 | 3/3 | 0 |
| framework-integration | 9/9 | 0 | 9/9 | 0 |
| hardware-conformance | 0/2 | 2 | 0/2 | 2 |
| model-core | 10/10 | 0 | 10/10 | 0 |
| model-properties | 6/6 | 0 | 6/6 | 0 |
| ops-tooling | 8/8 | 0 | 8/8 | 0 |
| resilience-faults | 12/12 | 0 | 12/12 | 0 |
| security-adversarial | 17/17 | 0 | 17/17 | 0 |
| service | 14/14 | 0 | 14/14 | 0 |
