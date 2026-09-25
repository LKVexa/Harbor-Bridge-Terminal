# ADR-005 — Native/FFI architecture (v1, PROPOSED)
**Decision.** No compiled shim. io_uring is driven by raw `syscall(425/426/427)` + `mmap` through `ctypes`; IOCP by `ctypes.WinDLL(kernel32/ws2_32)`; epoll/kqueue by CPython's `select` module. Buffers passed to the kernel are pinned in the backend's in-flight table until their terminal CQE/packet is reaped, independent of GC.
**Consequences.** Zero build toolchain and no sanitizer targets (MC-25 "native fuzz" items are N/A while no C/C++ is introduced). arm64 io_uring memory ordering is unverified (see compat matrix).
**Rejected.** liburing via cffi (adds a native build + distribution problem); Rust shim (same, plus toolchain pinning).
