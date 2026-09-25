# Third-party notices: INV-28 v4.3.0

This release contains no third-party code.

| Part | Source | Licence | How used |
|---|---|---|---|
| `_vendor/pk_core/` | Owner's own PK series (`New folder\PK_Master_Applied_All_Batches.zip → UC270/pk_core`), taken from the INV-72 v4.3.0 work order on the yard | Owner's material, no licence file | Vendored unchanged. Digests are in `_vendor/PK_CORE_PROVENANCE.json` and re-verified by `tests/test_repository.py` |
| `tools/rtm.py`, `tools/manifest.py`, `tools/release_gate.py`, `tools/pk_gate.py`, `tools/governance_check.py` | Owner's own sibling element INV-72 v4.3.0 (`_YARDOFFICE/work-orders/INV72-20260923-missing-components`), which adapted them from INV-69 | Owner's material, no licence file | Adapted: INV-28 identifiers, the MC-001..MC-100 axis, extra lanes |

Everything else was written new for this release using the Python standard library only.
