# INV-41 compatibility certification

Declared matrix: `contracts/SUPPORT_MATRIX.json` (Python 3.10–3.13 CPython; Linux/Windows/macOS; x86_64/aarch64; stdlib-only). Certification runner: `tools/compat.py`; CI matrix: `.github/workflows/ci.yml`. Unsupported interpreters are refused by `preflight.run` (GV006; compat `unsupported_refused`).

**Evidence in this pass:** CPython 3.10.20, 3.11.15, 3.12.3 and 3.13.13 on Linux x86_64 all PASS (compile, self-check normal and -O, preflight, six suites — `evidence/compat.json`). Windows, macOS and aarch64 cells are recorded `NOT_RUN`, never PASS (B-COMPAT-01).

Definitions of supported / best-effort / deprecated / unsupported, notice windows, mixed-version and downgrade rules: see the matrix file. Schema skew beyond the window is refused (`ConfigRejected`, golden vector `future-schema`). Adjacent-layer (pk_core) incompatibility is reported by `tools/estate_gate.py` as FAIL with the provenance mismatch.
