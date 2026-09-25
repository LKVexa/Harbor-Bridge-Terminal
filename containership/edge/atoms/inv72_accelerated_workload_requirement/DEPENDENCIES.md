# Dependencies

* **Runtime:** CPython 3.10–3.13 standard library only (`tools/deps_check.py` enforces it; `requirements.lock`
  is intentionally empty).
* **pk_core:** the owner's PK conformance framework, vendored unchanged under `_vendor/pk_core` from
  `PK_Master_Applied_All_Batches.zip → UC270/pk_core` (identical in all four batch copies). Provenance and
  per-file digests: `_vendor/PK_CORE_PROVENANCE.json`. Used only by `component.py`, `contract.py`,
  `tools/pk_gate.py` and `tests/test_component.py`.
* **Adjacent elements** (GAP-02 discovery, GAP-11 scheduling, INV-68 packing, INV-69 agentic layer): not in
  this archive. `adapters.py` implements their contract-level seams; certification against the real
  elements is waiver W-002.
* **Host-owned stack** (GPU passthrough/partitioning, drivers, local-inference runtime): unselected and
  unpinned here; waiver W-003.
