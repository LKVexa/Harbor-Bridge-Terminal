"""Windows provider: ``msvcrt.locking`` byte-range lock on the per-resource lock file.

Namespace: per-user by default (%LOCALAPPDATA%\\inv23\\claims).  Machine-wide
coordination between services and interactive users requires an operator-provisioned
directory whose ACL grants modify only to the participating principals (see
SECURITY.md); this module does not set ACLs itself.  Byte-range locks are released
by the OS when the process dies, so there is no abandoned-mutex state.
Hardware/OS-backed validation outstanding (COMPATIBILITY.md row WIN-*).
"""

from __future__ import annotations

import os
import time

from .filestore import FileClaimProvider


class WindowsClaimProvider(FileClaimProvider):  # pragma: no cover - exercised on Windows CI
    name = "windows-lockfile"

    def _os_lock(self, fd):
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)  # retries ~10s internally
                return
            except OSError:
                time.sleep(0.01)

    def _os_unlock(self, fd):
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
