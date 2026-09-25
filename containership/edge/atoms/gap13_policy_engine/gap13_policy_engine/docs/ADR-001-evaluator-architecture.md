# ADR-001 — GAP-13 evaluator, trust boundary, distribution and concurrency model

**Status:** Proposed (approval pending — architecture authority in `OWNERS.yaml` is UNASSIGNED) · **Closes:** G13-MC-042 when approved · **Date:** 2026-09-22 · **Release:** 5.0.0

## Context
4.2.0 was a hardened in-process evaluator that trusted `{"verified": True}` from its caller, scanned all rules per request, had no persistence, no controls, and no telemetry. The missing-components checklist requires cryptographically derived trust, durable anti-rollback, safe staleness, operational controls and certification evidence.

## Decisions
1. **Evaluator model** — attribute-equality rules; most-specific-wins; deny before allow; rule-name tie-break. Kept from 4.x (SLO-bearing semantics); matching made type-strict.
2. **Conflict semantics** — tenant rules must bind `tenant` and may only narrow estate denies (checked at activation).
3. **Trust boundary** — only `PK_POLICY_SIGNED_BUNDLE/1` envelopes. Ed25519 over a domain-separated canonical payload; algorithm allowlist local to the verifier; key lifecycle, purpose, issuer and environment scope from a GAP-07-supplied trust store. `VerificationResult(VERIFIED)` can only be minted inside `verify.py`; the engine accepts nothing else. The evaluator never holds private keys.
4. **Canonical form** — sorted-key, NFC, integer-only JSON so signer and verifier cannot disagree on bytes; non-canonical payloads are rejected.
5. **Anti-rollback** — monotonic `generation` per `(issuer, policy_id, environment)`, persisted atomically; corrupt state fails closed.
6. **Distribution** — pull (file or HTTPS with bearer auth), idempotent by digest, capped exponential backoff with full jitter; never bypasses verification/controls.
7. **Caching** — cache signed envelopes only; re-verify on restart; persist activation time so age survives restart.
8. **Staleness** — age = max(monotonic age, wall age) + persisted base; wall rollback cannot extend trust; three hard-expiry modes, default `FAIL_CLOSED`.
9. **Concurrency** — read-copy-update: each activation builds a new immutable `PolicyEngine` + `CompiledIndex` and publishes it by one reference assignment; each evaluation reads the snapshot reference once. Writers serialise on an `RLock`. Multi-process deployments run one service per worker, each with its own cache/anti-replay files or a shared state dir guarded by atomic `os.replace` writes.
10. **Deployment form** — library plus optional stdlib HTTP/JSON `/v1` service bound to loopback behind a TLS-terminating sidecar/ingress.
11. **Emergency controls** — durable state machine (`NORMAL`, `UPDATE_FROZEN`, `DENY_ONLY`, `EVALUATION_DISABLED`) plus quarantine list; corrupt control state starts `DENY_ONLY`.

## Consequences
* Breaking change for 4.x callers of `PolicyEngine.load` (see `CHANGELOG.md`).
* Optional dependency on `cryptography` for Ed25519; without it every bundle fails closed.
* Bundle load cost is dominated by parsing and the tenant/estate scope check (≈1.8 s for 10 000 rules in the reference run); evaluation is near-constant (≈0.05 ms p99).

## Alternatives rejected
OPA/Rego (heavier runtime, different semantics), HMAC-signed bundles (evaluator would hold signing secret), push distribution (needs inbound listener at disconnected sites), lock-per-evaluation (contention).
