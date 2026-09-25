"""Named profile sources (profiles/*.json) -> canonical ``SandboxProfile``."""
from __future__ import annotations

import json
import pathlib
import re

from .errors import SandboxError
from .sandbox import SandboxProfile

PROFILE_DIR = pathlib.Path(__file__).resolve().parent / "profiles"


def load_profile(name: str, *, extra_syscalls=(), directory: pathlib.Path | None = None) -> SandboxProfile:
    if not re.fullmatch(r"[a-z0-9-]{1,64}", name or ""):
        raise SandboxError("E_PROFILE_INVALID", f"bad profile name {name!r}")
    path = (directory or PROFILE_DIR) / f"{name}.json"
    try:
        doc = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise SandboxError("E_PROFILE_INVALID", f"cannot load profile {name}: {e}") from None
    if doc.get("schema") != "INV39_PROFILE_SOURCE/1":
        raise SandboxError("E_SCHEMA_INVALID", "profile source schema mismatch")
    return SandboxProfile(doc["name"], frozenset(doc["syscalls"]) | frozenset(extra_syscalls),
                          frozenset(doc.get("capabilities", [])), frozenset(doc["namespaces"]))
