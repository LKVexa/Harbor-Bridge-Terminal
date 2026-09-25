# ADR-004: PK_LOCAL_CHAIN/1 JSON wire protocol and PK_CHAIN_ERROR/1 envelope
Status: PROPOSED · Date: 2026-09-23
Decision: a single versioned JSON request/response over HTTP(S) (TLS mandatory off loopback) whose error envelope is identical to the local one, so local and remote hops are semantically comparable (SEQ corpus). Stdlib-only; the estate transport can replace `HttpJsonTransport` by implementing `send(callee, request, ctx, timeout_s)`.
