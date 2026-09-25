"""Secret-handling integration (item 21).

Secrets are referenced as ``secretRef:<name>`` and resolved through a provider
(mounted-file provider for Kubernetes projected volumes; in-memory for tests).
Resolved values are wrapped so ``repr``/``str``/logging never reveal them.
Missing secrets fail closed.
"""
from __future__ import annotations

import os
import re

_NAME = re.compile(r"^[a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?$")


class SecretError(Exception):
    pass


class Secret:
    __slots__ = ("_v", "name")

    def __init__(self, name: str, value: str):
        self.name, self._v = name, value

    def reveal(self) -> str:
        return self._v

    def __repr__(self):
        return f"Secret({self.name!r}, <redacted>)"

    __str__ = __repr__


def parse_ref(ref: str) -> str:
    if not isinstance(ref, str) or not ref.startswith("secretRef:"):
        raise SecretError("not a secretRef")
    name = ref.split(":", 1)[1]
    if not _NAME.match(name):
        raise SecretError("invalid secret name")
    return name


class FileSecretProvider:
    """Reads secrets from a projected-volume directory; refuses traversal and
    world-readable files."""

    def __init__(self, root: str):
        self.root = os.path.realpath(root)

    def get(self, ref: str) -> Secret:
        name = parse_ref(ref)
        path = os.path.realpath(os.path.join(self.root, name))
        if os.path.dirname(path) != self.root:
            raise SecretError("secret path escapes provider root")
        if not os.path.isfile(path):
            raise SecretError(f"secret {name} not found")
        if os.name == "posix" and os.stat(path).st_mode & 0o004:
            raise SecretError(f"secret {name} is world-readable")
        with open(path, encoding="utf-8") as fh:
            return Secret(name, fh.read().strip())


class MemorySecretProvider:
    def __init__(self, values: dict[str, str]):
        self.values = dict(values)

    def get(self, ref: str) -> Secret:
        name = parse_ref(ref)
        if name not in self.values:
            raise SecretError(f"secret {name} not found")
        return Secret(name, self.values[name])
