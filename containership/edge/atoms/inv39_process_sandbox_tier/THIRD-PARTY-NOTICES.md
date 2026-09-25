# Third-party notices

No third-party source code is included in INV-39 5.1.0. The runtime uses only the Python standard library and the
host C library (via `ctypes`). `linux/syscall_tables.py` is data generated from the build host's Linux UAPI headers
(syscall numbers, which are interface facts; the headers are GPL-2.0 WITH Linux-syscall-note).

The package itself carries **no licence yet** — the owner must choose one before redistribution (MC-106, BLOCKED).
