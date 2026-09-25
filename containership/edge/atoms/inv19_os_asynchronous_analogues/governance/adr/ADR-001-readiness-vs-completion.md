# ADR-001 — Readiness and completion stay distinct (v1, status: PROPOSED — awaiting approver)
**Context.** epoll/kqueue/selectors report *readiness*; io_uring/IOCP report *completion*. Mapping one onto the other loses errors (a readiness backend cannot carry a completion error).
**Decision.** Every backend carries a `semantics` class. Readiness is surfaced to components only as INV-17 stream credit (permission to attempt). Completed values/errors come only from a completion CQE/packet or from the real syscall `ReadinessIO` performs after readiness. A readiness event never resolves a future.
**Consequences.** Component-visible tags are identical across backends (`value`/`error`), verified by `tests/test_integration.py::ParityTest`.
**Rejected alternatives.** (a) Treat readiness as completion with a synthetic result — loses ECONNRESET/EPIPE; (b) expose backend-specific tags to guests — violates non-goal "exposing backend detail to guests".
