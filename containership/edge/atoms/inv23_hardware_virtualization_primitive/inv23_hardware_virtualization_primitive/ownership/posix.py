"""POSIX provider: advisory ``flock`` held only for each read-modify-write critical
section; ownership lifetime is the durable record + lease + liveness."""

from __future__ import annotations

from .filestore import FileClaimProvider


class PosixClaimProvider(FileClaimProvider):
    name = "posix-flock"

    def _os_lock(self, fd):
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_EX)

    def _os_unlock(self, fd):
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
