# Compatibility, lifecycle, patching and vulnerability response (C093, C094, MC-16, MC-28)

- Support matrix: generated `evidence/compat_matrix.json` (`tools/certify.py matrix`); a cell is supported only with current evidence from this revision.
- Deprecation notice period: 2 minor releases or 90 days, whichever is longer; interface majors (`PK_ASYNC_*/N`) coexist for one major overlap.
- OS/kernel lifecycle: Linux ≥ 5.6 for io_uring (older kernels use epoll); Windows 10 1809 / Server 2019+; macOS 13+. Drop a platform only after its vendor EOL + one notice period.
- Python/runtime lifecycle: CPython 3.10–3.13; drop a version at upstream EOL.
- Dependency EOL: `tools/supply_chain.py vulns` flags EOL runtimes; EOL dependency = release blocker.
- Security patch SLA: Critical 72 h, High 7 d, Medium 30 d, Low next release.
- Critical operational patch SLA: 24 h for SEV1 regressions.
- Vulnerability scanning: automated per build; result INDETERMINATE (no feed) never counts as PASS. Prohibited severity for release: Critical or High without an approved, unexpired exception.
- Exception process: `EXCEPTIONS.md`.
