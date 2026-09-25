"""Compatibility matrix (component 25).

The matrix is data (``schemas/compatibility_matrix.json``), versioned and
published; ``check`` fails closed on anything not explicitly listed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .errors import Incompatible

MATRIX_PATH = Path(__file__).resolve().parent / "schemas" / "compatibility_matrix.json"


def load(path: Path = MATRIX_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def check(profile: Mapping[str, str], matrix: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """``profile`` keys: python, arch, supervisor_protocol, node_runtime, state_schema, pk_core (optional)."""
    matrix = matrix or load()
    problems = []
    for dim, allowed in matrix["supported"].items():
        v = profile.get(dim)
        if v is None:
            if dim in matrix.get("optional", []):
                continue
            problems.append(f"{dim}: missing")
        elif v not in allowed:
            problems.append(f"{dim}: {v} not in {allowed}")
    for rule in matrix.get("excluded_combinations", []):
        if all(profile.get(k) == v for k, v in rule["when"].items()):
            problems.append(f"excluded: {rule['reason']}")
    if problems:
        raise Incompatible("; ".join(problems), problems=problems)
    return {"matrix_version": matrix["matrix_version"], "profile": dict(profile), "compatible": True}
