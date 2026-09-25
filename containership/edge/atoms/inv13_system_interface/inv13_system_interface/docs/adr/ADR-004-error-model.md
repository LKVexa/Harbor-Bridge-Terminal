# ADR-004 — Error model

**Status:** Accepted · **Date:** 2026-09-22

Stable codes `E1xxx` denied, `E2xxx` invalid, `E3xxx` unavailable, `E4xxx` quota, `E5xxx` timeout/cancel, `E6xxx` state, `E9xxx` terminal (`host/errors.py`). Codes are append-only; values are pinned by `test_errors_resources.py::test_code_stability_snapshot` and mirrored in the WIT `error-code` enum. Host detail (errno text, paths, engine messages) lives only in `Inv13Error.host_detail`, which `to_guest()`, `str()` and `repr()` never include (`test_no_host_detail_crosses`, `V8Adapter.test_trap_maps_to_stable_code_without_detail`).
