# ADR-0001 — INV-61 production architecture (wRPC over framed TCP/TLS)

* **Status:** Proposed — awaiting approval by the accountable owner (W-001). Not approved; do not treat as approved.
* **Date:** 2026-09-22 · **Supersedes:** implicit 4.2.0 in-process design

## Context
4.2.0 dispatched pre-decoded Python dicts in-process. The audit (M03/M04) required a real cross-host path, a canonical byte format and WIT-driven typing, with no third-party dependencies available in the supplied environment.

## Decision
1. Transport: length-prefixed frames (`PK_WRPC_FRAME/2`, 12-byte header) over TCP, TLS 1.3 mutual authentication mandatory in production. QUIC/HTTP-3 rejected for 4.3.0: no stdlib implementation; NATS rejected: adds a broker failure domain INV-61 does not own.
2. Contract: WIT subset `inv61-wit-subset/1`, dynamic binding from the parsed model (no generated code to drift).
3. Values: canonical little-endian codec modelled on the component-model canonical ABI's value shapes (not ABI-memory-layout compatible — see W-005).
4. Integrity: per-request HMAC envelope in addition to TLS so authenticity survives relays through INV-60 / INV-36.
5. Stateless data path; protocol state limited to the inventory in `docs/STATE_INVENTORY.md`.

## Consequences
+ Zero runtime dependencies; auditable; deterministic.
− Not wire-interoperable with Bytecode Alliance `wrpc` (W-005). − Thread-per-connection model caps connection scale (measured in `evidence/bench_results.json`); an asyncio transport is the planned successor.
