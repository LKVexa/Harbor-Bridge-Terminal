# Test strategy (INV30-GAP-056, 057, 030–032, 039 · INV-30-C081–C089)

| Suite | File | Mandatory | Zero-budget |
|---|---|---|---|
| model core (unit) | test_capability_core.py | ✔ | ✔ |
| properties / fuzz (seeded, 20 000 cases/property) | test_properties.py | ✔ | ✔ |
| concurrency / races | test_concurrency.py | ✔ | ✔ |
| contracts (every interface, envelopes, compat, fixtures) | test_contracts.py | ✔ | |
| adversarial security (T-01…T-16) | test_security.py | ✔ | ✔ |
| service semantics | test_service.py | ✔ | |
| resilience / fault injection | test_resilience.py | ✔ | |
| config / supply chain / license | test_config_integrity.py | ✔ | |
| ops tooling, clean-env bootstrap | test_ops.py | ✔ | |
| framework conformance (pk_core) | test_component.py | ✔ | |
| framework + sibling integration | test_framework_integration.py | ✔ | |
| hardware conformance (differential, tag forgery) | test_hardware_backend.py | only for hardware claim | ✔ |

Every suite runs under normal Python and `python -O`. A mandatory suite with any skip is **BLOCKED**, not passed.
Reproduce a fuzz failure with `INV30_FUZZ_SEED=<seed>`.
