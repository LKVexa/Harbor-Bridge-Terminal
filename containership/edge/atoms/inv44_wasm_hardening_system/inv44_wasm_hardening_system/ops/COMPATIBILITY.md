# Compatibility and lifecycle policy — INV-44 (C027, C092-C094, C098)

| Interface | Version | Rule |
|---|---|---|
| PK_WASM_HARDENING/1 | 1.0.0 | additive optional fields → minor; removed/renamed field or error code → /2 |
| PK_WASM_INSTANCE/1 | 1.0.0 | same |
| PK_WASM_VERIFY_RECEIPT/1 | 1.0.0 | receipts of an unknown schema are refused, never guessed |
| Python API | 4.3.0 | `Engine.instantiate(output_valid=)` is **deprecated** (legacy Boolean path) and removed in 5.0.0 |

Peers on a different major version get WH-VERSION-UNSUPPORTED; there is no
silent downgrade. Supported Python: 3.10-3.13 (CI matrix).

Patch/EOL SLA: UNASSIGNED (owner decision). Proposed default for review:
critical security fixes within 7 days; each minor supported 12 months after the next minor.
