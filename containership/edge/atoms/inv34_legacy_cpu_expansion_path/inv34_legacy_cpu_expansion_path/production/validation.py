"""Shared boundary validation (re-uses the 5.0.0 rules). SPDX-License-Identifier: NOASSERTION"""
from __future__ import annotations

from ..expansion import InvalidRequest, _require_identifier, _require_int


def require_identifier(value: object, label: str) -> str:
    return _require_identifier(value, label)


def require_int(value: object, label: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    return _require_int(value, label, minimum=minimum, maximum=maximum)


__all__ = ["InvalidRequest", "require_identifier", "require_int"]
