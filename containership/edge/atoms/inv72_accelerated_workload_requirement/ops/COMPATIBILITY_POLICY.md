# INV-72 versioning, compatibility and deprecation policy (C016, C027)

* **Component version:** SemVer (`VERSION`, `__init__.__version__`, `compat.COMPONENT_VERSION` must
  agree — `tools/governance_check.py` fails otherwise).
  * patch: fixes only; no schema change
  * minor: additive optional fields, new reason codes, new profiles
  * major: removal or meaning change of anything on a wire schema or in `errors.REGISTRY`
* **Wire schemas** are `NAME/<major>` with JSON Schema files under `schemas/`. Within a major:
  additive-optional only. Readers ignore the documented optional fields of a newer minor
  (`compat.IGNORABLE_OPTIONAL`) and reject everything else, including any unknown field that could
  carry security meaning.
* **Mixed-version peers:** supported when majors match and minors differ by at most one
  (`compat.peer_supported`). `compat.negotiate` picks the highest common major or fails closed.
* **Error codes** are append-only; a code is never renamed or reused.
* **Deprecation:** announced one minor ahead in `CHANGELOG.md` and `ops/WAIVERS.json`
  `deprecated_behaviors`, removed only at the next major. Current: D-001 (legacy `match(reserve=True)`
  ownership mutation, removal 5.0.0).
* **Backward compatibility of 4.3.0:** `match()` keeps its v4.2.0 signature and return shape;
  `LimitExceededError` subclasses `ValueError` so v4.2.0 callers still catch it.
