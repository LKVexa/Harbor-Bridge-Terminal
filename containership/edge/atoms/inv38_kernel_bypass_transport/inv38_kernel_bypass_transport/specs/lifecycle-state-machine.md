# Lifecycle state machine (INV-38-C015)

Component, memory-region and provider states with a legal-transition table.
Source: `lifecycle.py`; schema: `schemas/lifecycle-v1.schema.json`.

- **Component:** UNINITIALIZED→BOOTSTRAPPING→READY↔DEGRADED→DRAINING→QUIESCED→STOPPED, with FAILED edges.
- **Region:** REGISTERING→ACTIVE→DRAINING→DEREGISTERING→REVOKED, FAILED edges. `ACTIVE→DEREGISTERING` while descriptors are in flight is prohibited — this formalises the existing `RegionBusy` behaviour (C015-T05).
- A monotonic `generation` (bumped on BOOTSTRAPPING/READY) identifies stale observers and stale keys (C015-T07, feeds C057/C058).

Illegal transitions raise `IllegalTransition` without mutating state; model-based
tests in `tests/test_lifecycle.py` cover every legal edge and assert illegal
edges fail deterministically. **Status:** `DONE`.
