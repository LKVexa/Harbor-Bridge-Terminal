"""Immutable, content-addressed image objects (MC-004; closes the verify-to-execute TOCTOU gap).

An ``ImageBlob`` is constructed from bytes once; its sha256/sha512 digests are computed at
construction and the bytes are held as immutable ``bytes``.  Everything downstream - parser,
signature check, VMM launch - receives the *same object*; the VMM adapter writes those exact
bytes into a fresh private file and re-hashes it immediately before launch (``materialize``).
Paths are never accepted as image identity.
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass

from ..errors import UkError

DIGEST_ALG = "sha256"


@dataclass(frozen=True)
class ImageBlob:
    data: bytes
    sha256: str
    sha512: str
    size: int

    @classmethod
    def of(cls, data: bytes | bytearray | memoryview, *, max_bytes: int = 64 * 1024 * 1024) -> "ImageBlob":
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("ImageBlob.of takes bytes")
        b = bytes(data)
        if len(b) > max_bytes:
            raise UkError("UK_PARSE_TOO_LARGE", f"{len(b)} > {max_bytes}")
        return cls(b, hashlib.sha256(b).hexdigest(), hashlib.sha512(b).hexdigest(), len(b))

    @property
    def ref(self) -> str:
        return f"sha256:{self.sha256}"

    def check(self, expected: str) -> None:
        """Compare against an externally bound digest ``sha256:<hex>`` (constant-time)."""
        import hmac
        if not isinstance(expected, str) or not expected.startswith("sha256:") or len(expected) != 71:
            raise UkError("UK_DIGEST_MISMATCH", "bound digest must be 'sha256:<64 hex>'")
        if not hmac.compare_digest(expected, self.ref):
            raise UkError("UK_DIGEST_MISMATCH", f"image is {self.ref}, bound digest is {expected}")

    def materialize(self, directory: str | None = None) -> str:
        """Write the bytes to a new 0600 file (O_EXCL) and verify the on-disk digest before returning."""
        fd, path = tempfile.mkstemp(prefix="inv27-", suffix=".img", dir=directory)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(self.data)
                fh.flush()
                os.fsync(fh.fileno())
            os.chmod(path, 0o400)
            with open(path, "rb") as fh:
                if hashlib.sha256(fh.read()).hexdigest() != self.sha256:
                    raise UkError("UK_DIGEST_MISMATCH", "materialized image changed on disk")
            return path
        except BaseException:
            try:
                os.chmod(path, 0o600)
                os.unlink(path)
            except OSError:
                pass
            raise
