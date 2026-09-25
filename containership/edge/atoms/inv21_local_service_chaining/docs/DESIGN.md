# INV-21 Local Service Chaining — Design (4.3.0)

Status: **PROPOSED — awaiting owner approval** (approval is recorded in `governance/approvals.json`; none is recorded yet).

## 1. Responsibility and boundary

INV-21 owns the *call path* between components: residency lookup, the local-vs-network decision, loop and depth bounding, per-hop authorization, and preservation of identity, trace, deadline and cancellation across the hop. It does not own placement (INV-10 / scheduler), the network transport (only the handoff adapter), interface definitions of callees (INV-20), service discovery beyond the host, or business logic.

## 2. Trust boundaries

| Boundary | Trusted side | Untrusted / caller-controlled | Enforcement |
|---|---|---|---|
| Caller → chainer (`invoke`) | `Principal` re-derived from the carried credential by the chainer's own `IdentityVerifier` (HMAC-SHA256, issuer allow-list) | callee name, payload, operation, idempotency key, trace id, **path** | `CallContext` validation, `check_id` grammar; production refuses hand-built/mismatched principals and the 4.x string API; caller-supplied `path` only counts toward depth/cycle — nested-hop status and the policy `caller` come solely from chainer-sealed child contexts |
| Chainer → capability authority | `GuardedProvider` result that passes schema/version/correlation/revision checks | provider response bytes | fail-closed on timeout, error, malformed, stale, version mismatch |
| Chainer → residency | `Residency` table (INV-10 feed) with lease, epoch, verified flag | placement writes from other actors | tenant ownership, epoch arbitration, lease expiry, unverified-after-restore |
| Chainer → peer (remote hop) | nothing on the wire is trusted | whole PK_LOCAL_CHAIN/1 response | schema validation, size cap, error-code allow-list, TLS required off loopback |
| Peer endpoint ← network | credential re-verified on the peer | context, path, payload | credential/context match, own depth/cycle bounds, no second forwarding |

## 3. Authoritative inputs / systems of record

* Identity: the runtime identity issuer (key ids in `IdentityVerifier`; KMS distribution is an estate concern).
* Authorization: INV-13 system interface via the `PK_CAPABILITY/1` decision contract.
* Residency: INV-10 composition feed; the in-memory table is a *cache with leases*, never authority after a restart until `reconcile()`.
* Configuration: `ConfigStore` revisions (author, source, digest, time).

## 4. Call sequence (every hop)

lifecycle serving? → principal live / not cancelled / deadline not passed → cycle → depth → residency + tenant isolation → capability decision (topology-aware) → admission (outermost hop only) → local dispatch **or** breaker → transport with deadline-bounded timeout → bounded retry (idempotent only) → error normalization → telemetry + audit.

## 5. Failure behaviour (deterministic)

| Condition | Behaviour | Code |
|---|---|---|
| provider down/slow/garbage | **fail closed**, handler never runs | `PK_CHAIN_PROVIDER_UNAVAILABLE` |
| identity invalid/expired/replayed | fail closed | `PK_CHAIN_UNAUTHENTICATED` |
| lease expired / unverified / unhealthy placement | not served locally; network path | (routing, counted as `stale_hits`/`suppressed_hits`) |
| no transport (production) | fail | `PK_CHAIN_TRANSPORT_UNAVAILABLE` |
| peer partitioned | breaker opens after N failures; sheds without network I/O | `PK_CHAIN_CIRCUIT_OPEN` |
| saturation | shed immediately, never queued | `PK_CHAIN_OVERLOADED` (+`retry_after_ms`) |
| audit sink failure | fail closed (no unaudited decisions) | `PK_CHAIN_INTERNAL` |
| emergency disable | refuse all | `PK_CHAIN_QUARANTINED` |

## 6. State and lifecycle

`initializing → ready ↔ degraded`, any live state `→ quarantined → ready` (explicit, attributed release), any `→ stopped`. Mutable state: residency table (leased), admission counters, breaker table (bounded), decision ledger (bounded ring, max age), audit chain (append-only). Immutable: the wheel artifact, schemas, error-code registry.

## 7. Versioning and deprecation

Wire identifiers carry a major version (`PK_LOCAL_CHAIN/1`, `PK_CALL_CONTEXT/1`, `PK_RESIDENCY/1`, `PK_CHAIN_DEPTH/1`, `PK_CAPABILITY/1`, `PK_CHAIN_ERROR/1`, `PK_CHAIN_CONFIG/1`, `PK_CHAIN_AUDIT/1`). Breaking changes (see `tools/schema_diff.py`) require `/2` and a dual-read window of one minor release. Error codes are append-only; retired codes go to `errors.RETIRED_CODES` and are never reused. The 4.x string API (`Chainer.call`) is **deprecated**: development mode only, removal planned for 5.0.0 (tracked in `governance/waivers.json` as DEBT-001).

## 8. Rollback / recovery

Config: `ConfigStore.rollback()` (atomic, attributed). Binary: previous wheel by digest (`evidence/release_manifest.json`); canary rollback criteria in `rollout.py`. State: snapshot → restore (unverified) → reconcile against INV-10.

## 9. Per-gap design register

See `governance/gaps.json` (machine-readable: owner, system of record, trusted vs caller-controlled data, versioning, failure mode, status and evidence for each of GAP-001..042) and `docs/TRACEABILITY.md`.
