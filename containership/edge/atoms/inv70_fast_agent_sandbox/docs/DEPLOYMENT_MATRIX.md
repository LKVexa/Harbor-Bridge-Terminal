# Deployment-context applicability matrix (INV-70-C012)

Source of truth: `config.py::BASE` + `ENVIRONMENTS`. Verified by `tests/test_config.py` and the tier tests in `tests/test_integration.py`.

| Requirement area | dev | staging | prod | edge |
|---|---|---|---|---|
| Isolation | inline-dev (no pre-emption) | process | process (**required**) | process (**required**) |
| Wall clock | 10 s | 2 s | 1 s | 2 s |
| Concurrency / tenant | 64 / 16 | 64 / 16 | 64 / 16 | 8 / 4 |
| Memory / value ceiling | 64 KiB / 16 KiB | same | same | 32 KiB / 8 KiB |
| Warm workers | 0 | 4 | 4 | 1 |
| Caller auth, audit, fail-closed trust | required | required | required | required |
| Wasm backend (ADR-0001) | optional | required for certification | required for GA | required for GA |
| Perf gate (C070) | n/a | blocking | blocking | blocking (edge baseline) |
| Power/thermal (C068) | n/a | n/a | n/a | required — BLOCKED |

Site overlays (`_site`) may tighten anything. They may not weaken isolation in prod-like environments; `resolve()` rejects that.
