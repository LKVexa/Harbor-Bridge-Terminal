"""Secret-reference model (MC-027).

Configuration never contains secret material; it contains references of the
form ``env://NAME`` or ``file:///abs/path``.  A :class:`SecretProvider`
resolves them at activation time.  Resolved values are wrapped in
:class:`Secret`, whose ``repr``/``str`` never reveal content, so they cannot be
leaked through logs, audit entries or explain views.  External KMS/Vault
providers implement the same ``resolve`` protocol (see docs/ADAPTERS.md).
"""
from __future__ import annotations

import os
import pathlib
from typing import Mapping, Protocol

from .errors import fail


class Secret:
    __slots__ = ("_value", "ref")

    def __init__(self, value: bytes, ref: str):
        self._value = value
        self.ref = ref

    def reveal(self) -> bytes:
        return self._value

    def __repr__(self) -> str:
        return f"Secret(ref={self.ref!r}, value=<redacted>)"

    __str__ = __repr__


class SecretProvider(Protocol):
    def resolve(self, ref: str) -> Secret: ...


class LocalSecretProvider:
    """Resolves ``env://`` and ``file://`` references; refuses anything else."""

    def __init__(self, environ: Mapping[str, str] | None = None, allowed_dirs: tuple[str, ...] = ()):
        self._env = os.environ if environ is None else environ
        self._allowed = tuple(pathlib.Path(d).resolve() for d in allowed_dirs)

    def resolve(self, ref: str) -> Secret:
        if ref.startswith("env://"):
            name = ref[6:]
            if name not in self._env or not self._env[name]:
                raise fail("CONFIG_INVALID", f"secret reference {ref} is unset", target=ref)
            return Secret(self._env[name].encode(), ref)
        if ref.startswith("file://"):
            path = pathlib.Path(ref[7:]).resolve()
            if self._allowed and not any(path.is_relative_to(d) for d in self._allowed):
                raise fail("CONFIG_INVALID", "secret file outside allowed directories", target=ref)
            try:
                mode = path.stat().st_mode
            except OSError:
                raise fail("CONFIG_INVALID", "secret file unreadable", target=ref) from None
            if mode & 0o077 and os.name == "posix":
                raise fail("CONFIG_INVALID", "secret file must not be group/world accessible", target=ref)
            return Secret(path.read_bytes().strip(), ref)
        raise fail("CONFIG_INVALID", "unsupported secret reference scheme", target=ref)
