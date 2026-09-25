# Interfaces, auth, semantics, limits (INV30-GAP-015..022 · INV-30-C021–C030)

## Boundary inventory (C021)
| Boundary | Kind | Schema | Auth |
|---|---|---|---|
| `mint` | in-process API / RPC body | `schemas/capability.schema.json` (op=mint) | HMAC principal with `mint` |
| `derive` | API/RPC | `capability.schema.json` (op=derive) → PK_CAPABILITY/1 | principal with `derive` on tenant |
| `access` | API/RPC | `access.schema.json` → `access_result.schema.json` | principal with `access` on tenant |
| `invalidate` | API/RPC | `capability.schema.json` (op=invalidate) | principal with `invalidate` |
| failures | all | `failure.schema.json` (PK_FAILURE/1) | — |
| health | operator endpoint (`ops health`) | `health.schema.json` | operator host access |
| config | file | `config.schema.json` | file permissions + review |
| decision/explain | operator | `decision.schema.json` | operator |
| GAP-02 publish | sibling call | PK_NODE_CAPABILITIES/1 (GAP-02) | in-process |
| CHERI helper | subprocess stdin/stdout JSON | `CHERI_BACKEND.md` | exec path pinned in config; digest verified (planned) |
| audit ledger | append-only JSONL | INV30_AUDIT/1 | HMAC key |

WIT/protobuf: not used by this element; JSON Schema 2020-12 is the canonical IDL (C022).

## Authentication (C023)
Request MAC = HMAC-SHA256(key, canonical_json({p, a, b, ts, n})). Skew ≤ 30 s; nonce single-use within 2×skew
(bounded cache). Keys ≥ 256 bit via `secret_refs`. Action is inside the MAC (no cross-action replay).

## Authorization & capability acquisition (C024, C041–C044)
Deny by default. Principal → {actions} × {tenants}. Root capabilities are minted **only** by `MintingAuthority`:
signed grant {grant_id, tenant, base, length, permissions, enforcement, minted_by, minted_at}; verified on every
use; tenant mismatch → `TENANT_MISMATCH`. Derived handles inherit the root grant and can only narrow.

## Timeouts, cancellation, retry, idempotency, backpressure (C025)
`deadline_ms` 1–60 000 (default 5 000); cancellation via `Deadline.cancel()`; retry only where
`retryable=true` with full-jitter exponential backoff (base 50 ms, cap 2 s, 4 attempts); `derive` accepts
`idempotency_key` (same body → same handle; different body → `IDEMPOTENCY_CONFLICT`); backpressure via admission
control (`OVERLOADED`, retryable) and circuit breaker (`CIRCUIT_OPEN`).

## Failure envelope (C026) — see `errors.CODES` for the full table (25 codes).

## Compatibility (C027)
Schema ids carry the major version (`/1`). Peers MUST match major. Unknown fields are refused (fail closed) until
a minor id is negotiated. 4.2.0 access records lacking `enforcement` are not trusted as hardware evidence. Fixtures:
`fixtures/compat/cases.json`.

## Limits (C028) — `limits.py`
64-bit addresses; 65 536 caps/tenant; 1 048 576 total; derivation depth 64; access size ≤ 1 GiB; request ≤ 16 KiB;
256 in flight; queue 1 024; 4 096 tenants; idempotency cache 65 536; nonce cache 262 144. Edge overlays lower these.

## Reference fixtures (C029, C030)
`fixtures/integration/reference_flow.json` (PLN-04 → INV-30 admission flow) is executed by `test_contracts`.
