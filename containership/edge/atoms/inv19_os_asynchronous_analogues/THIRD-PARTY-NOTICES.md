# Third-party notices — INV-19 5.0.0

No third-party source code was copied into this package. The GitHub Junkyard was consulted for an io_uring / IOCP / pk_core donor and none was found in the listing reachable in this session (build-new).

Runtime: CPython standard library (PSF-2.0). Optional: `cryptography` (Apache-2.0 OR BSD-3-Clause) for Ed25519 signatures — imported, not vendored.
Interfaces consumed: Linux io_uring UAPI (`include/uapi/linux/io_uring.h`, syscall ABI, GPL-2.0 WITH Linux-syscall-note — ABI use only); Win32/Winsock APIs (ABI use only).
