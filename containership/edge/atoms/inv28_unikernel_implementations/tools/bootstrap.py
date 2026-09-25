"""Deterministic developer/CI bootstrap check (MC-089): interpreter, vendored pk_core, schemas, MASTER.md,
policy file, catalog - everything a clean checkout needs before tests.  evidence/BOOTSTRAP.json."""
from __future__ import annotations

import platform
import sys
import warnings

from ._common import EVIDENCE, ROOT, ensure_path, write_json


def main(argv=None) -> int:
    ensure_path()
    warnings.simplefilter("ignore", DeprecationWarning)
    checks = {}
    checks["python>=3.10"] = sys.version_info >= (3, 10)
    from . import deps_check, master
    checks["pk_core vendored digests"] = not [e for e in deps_check.check()["errors"] if "pk_core" in e]
    checks["MASTER.md consistent"] = not master.check()
    try:
        from inv28_unikernel_implementations.schema_check import SCHEMA_DIR, load
        for p in SCHEMA_DIR.glob("*.schema.json"):
            load(p.name[:-12])
        checks["schemas load"] = True
    except Exception:  # noqa: BLE001
        checks["schemas load"] = False
    try:
        from inv28_unikernel_implementations.policy import SelectionPolicy, default_policy
        checks["policy file == default"] = SelectionPolicy.load(ROOT / "config" / "policy.default.json").digest == \
            default_policy().digest
    except Exception:  # noqa: BLE001
        checks["policy file == default"] = False
    try:
        import inv28_unikernel_implementations as m
        m.COMPONENT()
        checks["component constructs (pk_core importable)"] = True
    except Exception:  # noqa: BLE001
        checks["component constructs (pk_core importable)"] = False
    ok = all(checks.values())
    write_json(EVIDENCE / "BOOTSTRAP.json", {"schema": "PK_BOOTSTRAP/1", "python": platform.python_version(),
                                             "checks": checks, "pass": ok})
    for k, v in checks.items():
        print("BOOTSTRAP", "OK " if v else "FAIL", k)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
