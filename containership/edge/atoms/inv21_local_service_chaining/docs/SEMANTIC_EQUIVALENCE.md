# Semantic Equivalence of Local and Remote Hops

Corpus `SEQ-1.0` (`tests/test_semantic_equivalence.py`) runs every case through (L) direct local dispatch and (R) the PK_LOCAL_CHAIN/1 remote path — both in-process loopback and a real HTTP socket — with identical logical context, then compares `(ok, JSON-normalised value)` or `(code, category, retriable)`.

Covered: success values (dict, unicode, numbers, null), nested chains (trace + depth propagation), idempotent operation, idempotency key, handler exception, authz denial, handler type error, large boundary payload, deadline, cycle, depth, cancellation, cross-tenant.

## Allowed transport-only differences (exhaustive)
1. Values are JSON-normalised on the remote path: tuples → arrays, non-string keys → strings; non-JSON values (bytes, objects) fail on the remote path with `PK_CHAIN_HANDLER_FAILED` at the serialisation step. **Local handlers receive and may return the caller's object by reference (zero-copy); callers must treat payloads as immutable.**
2. Caller-side route telemetry reads `remote` for R.
3. Cross-tenant: L reports `PK_CHAIN_CROSS_TENANT` (the callee's tenant is known locally); R reports `PK_CHAIN_CAPABILITY_REFUSED` (the caller host cannot see a remote callee's tenant). Both refuse before dispatch and are non-retriable.

4. Policy `caller`: on a local nested hop the capability request names the calling component (chainer-sealed path); on the remote path the peer cannot authenticate the caller host's path, so `caller` is `None`. A policy that grants **only** by caller therefore refuses on the remote path (fail-closed direction). Peer authentication (mTLS) would remove this difference (ADR-005).

Any other divergence fails the suite and is release-blocking. N/N-1 rolling-version equivalence is not applicable (no 4.2 wire peer exists; see COMPATIBILITY.md).
