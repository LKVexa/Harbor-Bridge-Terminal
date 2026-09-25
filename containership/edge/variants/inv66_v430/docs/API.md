# INV-66 public interfaces and compatibility (MC-012 – MC-018, MC-055, MC-057)

Document ID `INV66-API` · v1.0.0.

| Interface | Protocol id | Schema (bundled, `$id`) | Transport |
|---|---|---|---|
| Admission | `PK_ECP_ADMIT/1` | `schemas/admit_request.v1.json`, `schemas/admit_response.v1.json` | `POST /v1/admit` |
| RBAC bindings | `PK_ECP_RBAC/1` | `schemas/rbac_binding.v1.json` (inside config) | `POST /v1/config` (new revision), `POST /v1/config/rollback` |
| Audit events | `PK_ECP_AUDIT/1` | `schemas/audit_event.v1.json` | `GET /v1/audit`, `POST /v1/audit/export` |
| Errors | `PK_ECP_ERROR/1` | `schemas/error.v1.json`; catalog `errors.CATALOG` | every non-2xx |
| Configuration | `PK_ECP_CONFIG/1` | `schemas/config.v1.json` | file / `POST /v1/config` |
| Inventory / explain | `PK_ECP_INVENTORY/1`, `PK_ECP_EXPLAIN/1` | response shapes documented in `service.py` | `GET /v1/inventory`, `GET /v1/decisions/{id}/explain` |

## Request semantics (MC-017)

* `request_id` — caller correlation id, echoed.
* `idempotency_key` — optional; same key + same body (excluding `request_id`, `deadline_ms`) within `idempotency_ttl_s` returns the original decision with `replayed: true`; different body → `IDEMPOTENCY_CONFLICT`. Survives restart (journalled).
* `deadline_ms` — absolute budget (≤ 60 s, default 5 s) for the whole admission incl. policy call; exceeded → `DEADLINE_EXCEEDED`.
* Retry classification: `retryable` flag on every error. Retry only retryable codes, with exponential backoff + jitter; `OVERLOADED`/`QUOTA_EXCEEDED` are backpressure signals.
* Cancellation: client disconnect does not cancel a journalled decision; the decision id is returned by idempotent retry.
* Trace context: `traceparent` (W3C) accepted and propagated to GAP-13 and INV-63.

## Compatibility rules (MC-018)

* Protocol ids are versioned; `/version` lists supported ids. Unknown protocol → `PROTOCOL_UNSUPPORTED`.
* Within a major protocol version only **additive** changes: new optional fields, new error codes. Error codes are never removed or renamed (golden set in `tests/test_contracts.py`).
* Golden fixtures in `tests/fixtures/` must keep passing for every supported version.

| Server version | Admit | Audit | Config | Python | pk_core |
|---|---|---|---|---|---|
| 4.3.x | /1 | /1 | /1 | 3.11 – 3.13 (CI matrix, x86_64 + arm64) | optional (conformance only) |
| 4.2.x | legacy in-process API (`control_plane.ControlPlane`, retained for compatibility) | in-memory | constructor args | 3.11+ | required for conformance |

wasmCloud / Cosmonic Control versions are the concern of INV-63; the INV-63 contract (`adapters.HttpDeploymentManager`) is JSON `{delivery_id, lattice, manifest}` → `{delivery_id, accepted, ref}`.
