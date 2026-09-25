# Compatibility matrix (component 53)

| Surface | Version | Verified here | How |
|---|---|---|---|
| CPython | 3.11.15 (Linux x86_64) | yes | full suite, this pass |
| CPython | 3.10 floor | **not run** | declared floor; no 3.10 interpreter in the build container |
| CPython on Windows | any | **not run** | `VERIFY.cmd` wiring exists; run it on the target host |
| Node.js reporter (CSP/1) | 22.22.2 | yes | `test_c10_cross_language` |
| jsonschema lane | 4.26.0 | yes | `test_p2_conformance_fuzz_stress.TestSchemaConformance` |
| OpenSSL lane (mTLS) | system `openssl` | yes | `test_auth_server.TestMTLS` |
| Wire: PK_SIGNAL_SUBMISSION/2 | v5 schema | yes | server accepts only the schema shape |
| Wire: PK_SIGNAL_QUERY/2 | v5 schema | yes | present + absent responses validated |
| Wire: PK_SIGNAL_CATALOGUE/1 | v5 schema | yes | no `event` kind exists in the schema (finding F-03) |
| Signing profile | GAP09-CSP/1 | yes | RFC 8785 number/key-order vectors + Node |
| GAP-06 / GAP-07 / GAP-08 / GAP-01 / PLN-05 | — | **BLOCKED** | not in archive |
| pk_core | — | **BLOCKED** | not in archive |
