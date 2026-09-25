# Third-party and vendored parts — INV-17 4.3.0

| Part | Path | Source | Licence |
|---|---|---|---|
| pk_core 4.0.0 | `vendor/pk_core/` | owner's `PK_Master_Applied_All_Batches.zip` → `UC270/pk_core` (byte-identical in DF_Fabric, UC32, BOTTLE_ROCKET_110K) | No LICENSE file shipped in the source estate. Treated as the owner's own code; **flag before redistributing outside the owner's projects.** |
| Sibling contracts INV-12/15/18/19/20 | `vendor/pk_siblings/*/contract.py` | same estate, `UC270/pk_components/…/contract.py` | Same as above (owner's own code, no LICENSE file). |
| 4.2.0 runtime (benchmark reference only) | `benchmarks/reference/stream_4_2_0.py` | the 4.2.0 input archive | Same package lineage. |

The runtime has no third-party dependencies (stdlib only). Dev tools pinned in `pyproject.toml`
(ruff, mypy) are MIT-licensed and are not redistributed.
