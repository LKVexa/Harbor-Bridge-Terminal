# ADR-005 — Audit and telemetry export

**Status:** Accepted · **Date:** 2026-09-22

* The in-process 4.2.0 hash chain is retained; durable export is a JSONL file opened `O_APPEND`, `fsync` per record, each record bound to node / release / workload, SHA-256 chained, with HMAC checkpoints every N records and at seal (`host/audit_sink.py`).
* A standalone verifier (`python -m inv13_system_interface.host.audit_sink verify <file>`) detects edit, delete, reorder, truncation and recomputed-digest forgeries without the checkpoint key (`tests/test_ops.py::Audit`).
* The sink refuses to append to a log that fails verification.
* Records pass the MC-029 `PrivacyFilter` *before* they are written.
* Remaining gap: shipping to WORM/object-lock storage and key custody in the org KMS.
