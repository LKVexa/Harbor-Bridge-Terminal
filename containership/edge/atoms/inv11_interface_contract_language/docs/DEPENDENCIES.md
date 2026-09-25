# Dependencies

| Dependency | Scope | Contract |
|---|---|---|
| Python | runtime | 3.10–3.13 declared; 3.11 is the only version exercised by the builder's run |
| (none) | runtime | the structural model and WIT front end are stdlib-only |
| `pk-core>=4.0,<5` | optional (`[estate]`) | estate conformance runtime; consumed API: `pk_core.checklist.ChecklistItem`, `Finding`, `pk_core.component.Component`, `python -m pk_core run/gate/verify`. Source: internal estate index (authoritative location unknown to this package — owner input required). `ops.pk_core_status()` reports BLOCKED when absent and FAILED on a major-version mismatch. `PK_CORE_PATH` remains supported for development only. |
| wasm-tools 1.219.1 | test only | differential testing and component round-trip; pinned by release tarball SHA-256 in `conformance/SUPPORT_MATRIX.json`; never bundled |
| OpenSSL ≥ 3.0 | tooling | Ed25519 signing/verification; absence is reported BLOCKED |
| ruff 0.15.11, mypy 1.20.2 | dev | lint/security rules and strict typing |
