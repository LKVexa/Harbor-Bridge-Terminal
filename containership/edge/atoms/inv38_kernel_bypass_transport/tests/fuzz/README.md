# Fuzz / property tests (INV-38-C085)
`fuzz_transport.py` runs a bounded, structure-aware fuzz + property campaign over
schema decoding and address arithmetic / region containment / outcome-code
determinism, with per-input time bounds. Regression corpus lives in `corpus/`.
Runnable in CI without hardware.
