"""INV-38-C093 — Supported-version matrix + preflight compatibility check."""
from __future__ import annotations

SUPPORTED = {
    "pk_core": {"min": "1.4.0", "max": "2.x"},
    "INV-35": {"min": "4.0.0", "max": "4.x"},
    "INV-36": {"min": "4.0.0", "max": "4.x"},
    "INV-37": {"min": "4.0.0", "max": "4.x"},
    "GAP-12": {"min": "1.0.0", "max": "1.x"},
    "schema": {"min": "1", "max": "2"},
}

class UnsupportedVersion(RuntimeError):
    code = "PK_BYPASS_UNSUPPORTED_VERSION"

def _major(v: str) -> int:
    return int(v.split(".")[0])

def check(dependency: str, version: str) -> None:
    spec = SUPPORTED.get(dependency)
    if spec is None:
        raise UnsupportedVersion(f"unknown dependency {dependency}")
    lo = _major(spec["min"]); hi = _major(spec["max"].replace("x", "999"))
    if not (lo <= _major(version) <= hi):
        raise UnsupportedVersion(f"{dependency} {version} outside supported range {spec}")

def preflight(env: dict) -> list[str]:
    problems = []
    for dep, ver in env.items():
        try:
            check(dep, ver)
        except UnsupportedVersion as e:
            problems.append(str(e))
    return problems
