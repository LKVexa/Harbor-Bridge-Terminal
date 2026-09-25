# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Secret handling (GAP-025). Config holds *references* (``env:NAME`` or ``file:/path``), never values.

``resolve`` refuses inline secrets, world-readable secret files and short keys.
``redact`` scrubs anything that looks like key material from diagnostics.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path

from .errors import ConfigInvalid

_REF = re.compile(r"^(env|file):(.+)$")
_SECRETY = re.compile(r"(?i)(key|secret|token|password|passwd|sig|mac|credential)")
_HEXBLOB = re.compile(r"\b[0-9a-fA-F]{32,}\b")


def resolve(ref: str, *, min_bytes: int = 32) -> bytes:
    m = _REF.match(ref or "")
    if not m:
        raise ConfigInvalid("secret must be a reference 'env:NAME' or 'file:/path', never an inline value")
    kind, target = m.groups()
    if kind == "env":
        val = os.environ.get(target)
        if val is None:
            raise ConfigInvalid(f"secret env var {target} not set")
        data = val.encode()
    else:
        p = Path(target)
        if not p.is_file():
            raise ConfigInvalid(f"secret file {target} missing")
        if os.name == "posix" and p.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise ConfigInvalid(f"secret file {target} is group/world accessible")
        data = p.read_bytes().strip()
    if len(data) < min_bytes:
        raise ConfigInvalid("secret shorter than the minimum key length")
    return data


def redact(obj):
    """Deep-copy ``obj`` with secret-looking keys and long hex blobs replaced."""
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if _SECRETY.search(str(k)) and not str(k).endswith("_ref") else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return _HEXBLOB.sub("[REDACTED-HEX]", obj)
    return obj
