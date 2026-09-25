"""Component 32 - secrets boundary.

Reference format ``PK_DYN_SECRETREF/1``: ``secretref://<name>#<version>``
  name: [a-z0-9][a-z0-9._/-]{0,127} (no "..", no leading "/")
  version: positive integer, or ``latest``.
Config and logs carry only references; values exist only inside
``SecretValue`` whose repr/str are "[REDACTED]".

Providers: ``SecretProvider`` protocol with ``get(name, version) -> (value,
resolved_version)``.  Doubles: ``EnvSecretProvider`` (injected mapping,
``INV08_SECRET_<NAME>__V<n>``) and ``FileSecretProvider`` (``<dir>/<name>/<n>``,
files must not be group/world readable).  A real secret manager/KMS
integration is BLOCKED (none available).

Cache policy: TTL on the injected clock, bounded entries (LRU-ish eviction of
oldest).  Pinned versions are cached for ttl; ``latest`` is re-resolved after
ttl so rotation takes effect without redeploy.  ``revoke(name, version)``
evicts and blocks that version immediately.
"""
from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Protocol

from .core import Inv08Error, Outcome, redact_text

_REF = re.compile(r"^secretref://([a-z0-9][a-z0-9._/-]{0,127})#(latest|[1-9][0-9]{0,8})$")


@dataclass(frozen=True)
class SecretRef:
    name: str
    version: int | None  # None == latest

    @classmethod
    def parse(cls, text: str) -> "SecretRef":
        if not isinstance(text, str):
            raise TypeError("secret reference must be a string")
        m = _REF.match(text)
        if not m or ".." in m.group(1) or m.group(1).endswith("/"):
            raise ValueError("invalid secret reference")  # never echo the input: it may be a secret
        v = m.group(2)
        return cls(m.group(1), None if v == "latest" else int(v))

    def __str__(self) -> str:
        return f"secretref://{self.name}#{'latest' if self.version is None else self.version}"


class SecretValue:
    __slots__ = ("_v",)

    def __init__(self, v: str) -> None:
        self._v = v

    def reveal(self) -> str:
        return self._v

    def __repr__(self) -> str:
        return "SecretValue([REDACTED])"

    __str__ = __repr__


class SecretProvider(Protocol):
    def get(self, name: str, version: int | None) -> tuple[str, int]: ...


def _missing(name: str, version) -> Inv08Error:
    return Inv08Error("INV08.SECRET.NOT_FOUND", f"secret {name}#{version or 'latest'} not found",
                      outcome=Outcome.OPERATOR_REQUIRED, remediation="provision the secret version")


class EnvSecretProvider:
    def __init__(self, environ: Mapping[str, str]) -> None:
        self.env = environ

    @staticmethod
    def _key(name: str, v: int) -> str:
        return "INV08_SECRET_" + re.sub(r"[^A-Z0-9]", "_", name.upper()) + f"__V{v}"

    def get(self, name: str, version: int | None) -> tuple[str, int]:
        if version is None:
            prefix = self._key(name, 0)[:-1]
            vs = [int(k[len(prefix):]) for k in self.env if k.startswith(prefix) and k[len(prefix):].isdigit()]
            if not vs:
                raise _missing(name, version)
            version = max(vs)
        key = self._key(name, version)
        if key not in self.env:
            raise _missing(name, version)
        return self.env[key], version


class FileSecretProvider:
    def __init__(self, root: str | os.PathLike) -> None:
        self.root = Path(root)

    def get(self, name: str, version: int | None) -> tuple[str, int]:
        d = self.root / name
        if version is None:
            vs = [int(p.name) for p in d.glob("*") if p.name.isdigit()] if d.is_dir() else []
            if not vs:
                raise _missing(name, version)
            version = max(vs)
        p = d / str(version)
        if not p.is_file():
            raise _missing(name, version)
        if os.name == "posix" and stat.S_IMODE(p.stat().st_mode) & 0o077:
            raise Inv08Error("INV08.SECRET.INSECURE_FILE", f"secret file for {name} is group/world accessible",
                             outcome=Outcome.OPERATOR_REQUIRED, remediation="chmod 600")
        return p.read_text().rstrip("\n"), version


class SecretResolver:
    def __init__(self, provider: SecretProvider, *, clock: Callable[[], float], ttl: float = 300.0,
                 max_entries: int = 128) -> None:
        if ttl <= 0 or max_entries < 1:
            raise ValueError("ttl > 0 and max_entries >= 1 required")
        self.provider, self.clock, self.ttl, self.max_entries = provider, clock, ttl, max_entries
        self._cache: dict[tuple[str, int | None], tuple[float, str, int]] = {}
        self._revoked: set[tuple[str, int]] = set()
        self.fetches = 0
        self._seen: set[str] = set()

    def resolve(self, ref: str | SecretRef) -> SecretValue:
        r = ref if isinstance(ref, SecretRef) else SecretRef.parse(ref)
        now = self.clock()
        key = (r.name, r.version)
        hit = self._cache.get(key)
        if hit and now - hit[0] < self.ttl and (r.name, hit[2]) not in self._revoked:
            return SecretValue(hit[1])
        value, ver = self.provider.get(r.name, r.version)
        self.fetches += 1
        if (r.name, ver) in self._revoked:
            raise Inv08Error("INV08.SECRET.REVOKED", f"secret {r.name}#{ver} is revoked",
                             outcome=Outcome.OPERATOR_REQUIRED, remediation="rotate to a new version")
        if len(self._cache) >= self.max_entries and key not in self._cache:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            del self._cache[oldest]
        self._cache[key] = (now, value, ver)
        self._seen.add(value)
        return SecretValue(value)

    def revoke(self, name: str, version: int) -> None:
        self._revoked.add((name, version))
        for k in [k for k, v in self._cache.items() if k[0] == name and v[2] == version]:
            del self._cache[k]

    def invalidate(self, name: str | None = None) -> None:
        for k in [k for k in self._cache if name is None or k[0] == name]:
            del self._cache[k]

    def scrub(self, text: str) -> str:
        """Remove every secret value this resolver has handed out, then apply
        the generic pattern redaction from core."""
        for v in sorted(self._seen, key=len, reverse=True):
            if len(v) >= 4:
                text = text.replace(v, "[REDACTED]")
        return redact_text(text)
