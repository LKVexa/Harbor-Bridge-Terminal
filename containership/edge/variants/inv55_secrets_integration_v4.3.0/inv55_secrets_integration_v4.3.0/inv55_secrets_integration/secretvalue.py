"""Secret containers (checklist #49).

``SecretValue`` is a non-``str`` capability with redacted diagnostics.  The
plaintext is held in a ``bytearray`` so that ``wipe()`` can overwrite it in place
(best effort: CPython may already have produced transient copies, e.g. when the
value arrived as ``str`` or was decoded for the caller).  Hard confidentiality
must come from process isolation; see docs/security/memory-handling.md.
"""
from __future__ import annotations

import hmac


class SecretValue:
    __slots__ = ("_buf", "_wiped")

    def __init__(self, value: str | bytes | bytearray) -> None:
        if isinstance(value, str):
            self._buf = bytearray(value.encode("utf-8"))
        elif isinstance(value, (bytes, bytearray)):
            self._buf = bytearray(value)
        else:
            raise TypeError("secret value must be str or bytes")
        self._wiped = False

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return format(repr(self), spec)

    def __reduce_ex__(self, protocol):
        raise TypeError("secret values must not be serialized")

    def __copy__(self):
        raise TypeError("secret values must not be copied")

    def __deepcopy__(self, memo):
        raise TypeError("secret values must not be copied")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SecretValue):
            return NotImplemented
        return hmac.compare_digest(bytes(self._buf), bytes(other._buf))

    __hash__ = None  # type: ignore[assignment]

    def __len__(self) -> int:
        return len(self._buf)

    @property
    def wiped(self) -> bool:
        return self._wiped

    def reveal(self) -> str:
        """Materialize plaintext.  Only the broker's ``use`` path may call this."""
        if self._wiped:
            raise ValueError("secret value has been wiped")
        return self._buf.decode("utf-8")

    def reveal_bytes(self) -> bytearray:
        if self._wiped:
            raise ValueError("secret value has been wiped")
        return bytearray(self._buf)

    def wipe(self) -> None:
        for i in range(len(self._buf)):
            self._buf[i] = 0
        self._wiped = True
