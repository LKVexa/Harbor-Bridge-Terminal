# Failure catalogue  (component 51)

| # | Failure | Detection | Code / outcome | Automatic response | Operator action | Test |
|---|---|---|---|---|---|---|
| F01 | partition unavailable / quorum lost | append ack count | E0402 retryable | write refused, HW unchanged | restore replicas | `test_c49_*` |
| F02 | offset out of range | bounds check | E0401 terminal | none | seek to low watermark | `test_c48_*` |
| F03 | subscriber backlog full | backlog length | E0204 retryable | reject or drop_oldest | scale consumer / quarantine | `test_c68_*` |
| F04 | conformance failure | `run_conformance` | FAIL result | adapter not admitted | fix adapter | `test_c24_*` |
| F05 | torn write on crash | recovery scan | — | truncate tail | none | `test_c57_*` |
| F06 | mid-file corruption | recovery scan | E0503 terminal | refuse to open | restore from backup | `test_c57_*` |
| F07 | stale leader | epoch check | E0501 terminal | write fenced | none | `test_c50_*` |
| F08 | key/secret service outage | resolver/authn | E0105 retryable | fail closed | restore KMS | `test_c42_*` |
| F09 | non-security dependency down | health probe | degraded | results flagged | investigate | `test_c56_*` |
| F10 | overload | admission | E0202 | priority shedding | scale / raise limits | `test_c54_*` |
| F11 | provider down | adapter translation | E0901 retryable | retry w/ backoff, breaker | provider incident | `test_c13_*`,`test_c14_*` |
| F12 | consumer stall | `stalls()` | health | alert | restart consumer | `test_c52_*` |
| F13 | config invalid / conflict | validator / CAS | E0701/E0702 | not activated | fix & restage | `test_c27_*`,`test_c29_c30_*` |
| F14 | audit tamper | `verify()` | E1001 | alert | incident | `test_c43_*` |
