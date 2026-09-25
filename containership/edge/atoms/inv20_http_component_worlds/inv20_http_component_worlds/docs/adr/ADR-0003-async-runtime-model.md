# ADR-0003 — Async runtime model
- **Status:** Proposed · **Work item:** WI-INV20-03

`aio.py` is the executable specification of the request lifecycle on `asyncio`: bounded
`AsyncBodyStream` queues (producers await capacity), exactly-once `AsyncCompletion` for head and
trailers, absolute `Deadline`s whose remaining budget is propagated (child stages take
`min(stage cap, remaining)`), and idempotent release of every resource. The component-runtime binding
(wasmtime async / WASI 0.3 native async) must satisfy the same state machine
(`docs/spec/STATE_MACHINE.md`); conformance is by running `tests/test_aio.py` scenarios against the
binding's transport adapter. Head wait is event-driven (no polling) — this is what brought dispatch
p99 from 1.6 ms to ~0.3 ms in the 4.3.0 benchmark and restored the 1 ms SLO.
