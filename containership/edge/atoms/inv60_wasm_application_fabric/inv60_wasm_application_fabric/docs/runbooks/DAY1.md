# Day 1 — deployment and certification (M82/M86)

1. `python3 -B tools/ci.py` — full local gate: compile, all tests (incl. `pk_core` conformance under `python` and `python -O`), fixtures (Python + Node), SBOM, traceability, benchmark regression, evidence, exit gate.
2. Read `release/EXIT_GATE.json`:
   - `NO_GO` blocks rollout. Each blocking reason names an M-item and its waiver.
   - `CONDITIONAL_GO` requires every listed condition to be accepted and recorded in `WAIVERS.json` with approver + expiry.
3. Promote config: `python3 -B tools/config_promote.py --from staging --to production` prints the rendered diff; a production revision needs an independent approver (enforced).
4. Roll out per `ROLLOUT.md`.

**Validation:** `status()` reports `ready: true`, the active config digest matches the approved revision, ledger verifies against the anchored head.
