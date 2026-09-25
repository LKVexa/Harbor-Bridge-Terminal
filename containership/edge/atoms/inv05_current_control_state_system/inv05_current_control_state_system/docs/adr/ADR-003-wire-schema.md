# ADR-003 — Canonical JSON wire schema with a frozen lock file

* Status: **Proposed** · Traceability: C022, C027, MC-012-01..06

JSON (UTF-8, duplicate keys rejected, non-finite numbers rejected) with schemas declared in `schema.py::MESSAGES` and frozen in `conformance/schema_lock.json`. Chosen over protobuf because the package is stdlib-only and control operations are low-rate; field names are the stable identifiers. Toolchain: none (no code generation); `tools/check_compat.py` diffs the live schema against the lock and fails CI on removal, type change, required-ness change or capability removal. A future protobuf mapping must be generated *from* the lock file so identities stay stable.
