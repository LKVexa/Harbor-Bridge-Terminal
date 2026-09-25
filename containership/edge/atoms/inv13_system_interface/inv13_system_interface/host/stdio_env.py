"""MC-008 -- environment / argv / stdio / secret boundary.

The guest environment is built *only* from an explicit allowlist of literal
values; the host ``os.environ`` is never consulted (non-inheritance).  Secrets
are passed as opaque ``SecretRef`` values resolved at use-time by an injected
resolver; they never appear in env, argv, repr, audit or telemetry.  Stdout /
stderr are bounded sinks that redact any registered secret value.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .errors import ErrorCode, Inv13Error

_ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]{0,127}$")
MAX_ENV_VALUE = 32768
MAX_ARGS = 256


@dataclass(frozen=True)
class SecretRef:
    name: str

    def __repr__(self) -> str:
        return f"SecretRef({self.name!r})"


def build_environment(allowed: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    out = []
    for k, v in allowed.items():
        if not isinstance(k, str) or not _ENV_NAME.match(k):
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, f"env name {k!r}")
        if isinstance(v, SecretRef):
            raise Inv13Error(ErrorCode.POLICY_DENIED, "secrets never enter the environment")
        if not isinstance(v, str) or "\0" in v or len(v) > MAX_ENV_VALUE:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, f"env value for {k}")
        out.append((k, v))
    return tuple(sorted(out))


def build_argv(args: Iterable[str]) -> tuple[str, ...]:
    out = tuple(args)
    if len(out) > MAX_ARGS:
        raise Inv13Error(ErrorCode.TOO_LONG, "argv")
    for a in out:
        if isinstance(a, SecretRef):
            raise Inv13Error(ErrorCode.POLICY_DENIED, "secrets never enter argv")
        if not isinstance(a, str) or "\0" in a:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT, "argv")
    return out


class BoundedSink:
    """stdout/stderr sink: size-capped and secret-redacting."""

    def __init__(self, limit: int = 1 << 20) -> None:
        self.limit, self._buf, self.truncated = limit, bytearray(), False
        self._secrets: list[bytes] = []

    def register_secret(self, value: str) -> None:
        if value:
            self._secrets.append(value.encode())

    def write(self, data: bytes) -> int:
        if not isinstance(data, (bytes, bytearray)):
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
        room = self.limit - len(self._buf)
        if room <= 0:
            self.truncated = True
            raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "stdio")
        chunk = bytes(data[:room])
        self.truncated = len(data) > room
        self._buf += chunk
        return len(chunk)

    def getvalue(self) -> bytes:
        out = bytes(self._buf)
        for s in self._secrets:
            out = out.replace(s, b"[REDACTED]")
        return out


class Stdio:
    def __init__(self, stdin: bytes = b"", *, grant_stdin: bool = False, out_limit: int = 1 << 20) -> None:
        self._stdin = stdin if grant_stdin else None
        self.stdout, self.stderr = BoundedSink(out_limit), BoundedSink(out_limit)

    def read_stdin(self, n: int = -1) -> bytes:
        if self._stdin is None:
            raise Inv13Error(ErrorCode.CAP_NOT_GRANTED, "stdin")
        data, self._stdin = (self._stdin, b"") if n < 0 else (self._stdin[:n], self._stdin[n:])
        return data


class SecretBroker:
    """Resolves SecretRef for a specific (workload, name) allow-list entry."""

    def __init__(self, resolver: Callable[[str], str], grants: Mapping[str, frozenset[str]]) -> None:
        self._resolver, self._grants = resolver, dict(grants)

    def reveal(self, workload: str, ref: SecretRef, *, sinks: Iterable[BoundedSink] = ()) -> str:
        if ref.name not in self._grants.get(workload, frozenset()):
            raise Inv13Error(ErrorCode.CAP_NOT_GRANTED, "secret")
        value = self._resolver(ref.name)
        for s in sinks:
            s.register_secret(value)
        return value
