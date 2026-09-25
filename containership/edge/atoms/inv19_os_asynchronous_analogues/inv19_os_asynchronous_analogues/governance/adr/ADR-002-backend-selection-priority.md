# ADR-002 — Backend selection priority (v1, PROPOSED)
**Decision.** Fixed priority io_uring > iocp > epoll > kqueue > portable, applied only to backends whose *operational probe* succeeded (`hostio/capabilities.py`). Administrative disablement and quarantine remove candidates; an override may pick an unavailable backend only in diagnostic mode. Every rejection is recorded with a reason code.
**Rejected.** Platform-name based selection (kernel may forbid io_uring via sysctl/seccomp); lexical ordering within semantics class (v4.1 behaviour — non-obvious).
