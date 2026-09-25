# Backward-compatibility policy (MC-006)

* Semantic versioning of the package. Interfaces are versioned independently (`PK_*/<major>`).
* Within an interface major version changes are **additive only**; a breaking change creates `/2` and both are
  accepted for at least **two minor releases or 180 days**, whichever is longer.
* Error codes (`schemas/error_codes.v1.json`) are **append-only**; codes are never renumbered or repurposed and their
  `retryable` flag never changes (enforced by `test_error_codes_are_frozen_against_registry`).
* Storage format: newer readers migrate older formats; older readers **refuse** newer formats (downgrade refused).
* Python: 3.10–3.13 supported; the build sandbox run is recorded in `docs/compatibility_matrix.json`.
* Upgrade/downgrade windows and peer versions: `docs/compatibility_matrix.json` (machine-readable, test-checked).
