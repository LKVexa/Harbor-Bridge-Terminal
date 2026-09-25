# Supported-version & compatibility matrix (INV30-GAP-020, 058, 063 · INV-30-C027, C084, C093)

| Dimension | Supported | Tested in 4.3.0 | Evidence |
|---|---|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 | 3.11.15 (local); matrix in CI | RELEASE_EVIDENCE.json / CI |
| pk_core | >=4.0.0,<5.0.0 | 4.0.0 (UC270 estate) | test_framework_integration |
| GAP-02 | estate 4.0.x | yes | test_framework_integration |
| PLN-04, INV-41, INV-45 | estate 4.0.x | yes | test_framework_integration |
| OS for model | Linux, macOS, Windows | Linux | CI matrix |
| CPU for model | x86_64, aarch64 | x86_64 | CI matrix |
| **CHERI: Morello / CheriBSD** | target | **not tested — no hardware** | hardware-conformance suite (skipped ⇒ NO_GO) |
| **CHERI: CHERI-RISC-V** | target | **not tested** | same |
| CHERI-QEMU | dev only | not tested | never counts as production evidence |
| Hypervisors / providers | host-agnostic (pure userspace) | n/a for model | — |
| Protocol | PK_CAPABILITY/1, PK_CAPABILITY_ACCESS/1, PK_FAILURE/1 | yes | fixtures/compat |
| Previous INV-30 | 4.2.0 requests accepted; 4.2.0 access records untrusted as hw | yes | test_contracts |
