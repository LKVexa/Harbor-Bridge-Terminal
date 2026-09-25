# pk_core dependency (M02) — BLOCKED

`component.py`/`contract.py` import `pk_core.checklist`, `pk_core.component`, `pk_core.contract`. No copy, version, source URL or digest of `pk_core` was supplied, and none exists in this environment, so it **cannot be pinned** without inventing one.

What 4.3.0 did: (1) the whole production runtime no longer imports `pk_core` (lazy import in `__init__.py`); (2) `pyproject.toml` declares `pk_core` in an optional `conformance` extra with no fabricated version; (3) `tests/test_component.py` conformance tests still skip explicitly; (4) `ci/scripts/check_pk_core.py` fails the release gate when `pk_core` is not importable or its version/digest is not recorded in `lock/pk_core.lock.json`.

To close: supply pk_core's source or wheel → record `name, version, sha256, source` in `lock/pk_core.lock.json` → run the 100-item conformance.
