# INV-68 interface schemas (4.3.0)

JSON Schema 2020-12 documents for every externally visible INV-68 shape.

| Interface / document | Schema | Producer |
|---|---|---|
| `PK_PACK/1` request | `PK_PACK_REQUEST_1.schema.json` (4.2.0 requests still valid) | caller |
| `PK_PACK/1` engine result | `PK_PACK_RESPONSE_1.schema.json` | `PackingResult.to_dict()` |
| `PK_PACK_CAPACITY/1` | `PK_PACK_CAPACITY_1.schema.json` | `capacity_report()` |
| `PK_PACK_FRAG/1` | `PK_PACK_FRAG_1.schema.json` | `fragmentation()` |
| service envelope | `PK_PACK_SERVICE_RESPONSE_1.schema.json` | `PackingService.pack()` |
| errors | `PK_PACK_ERROR_1.schema.json` (+ `ERRORS.json` registry) | `PackError.to_dict()` |
| configuration | `PK_PACK_CONFIG_1.schema.json` | operators / `config.compose()` |
| status / readiness | `PK_PACK_STATUS_1.schema.json` | `PackingService.status()` |
| explain view | `PK_PACK_EXPLAIN_1.schema.json` | `explain.explain()` |
| audit record | `PK_PACK_AUDIT_1.schema.json` | `audit.AuditLog` |

The Python implementation is stricter than the shapes where JSON Schema cannot
express a rule: booleans and non-finite numbers are rejected as resources,
workload names must be unique, configuration ranges and the no-secrets rule are
enforced by `config.validate()`. Transport semantics (timeouts, cancellation,
retries, idempotency, backpressure, version negotiation, limits) are normative
in `../INTERFACES.md`. `tools/schemas_check.py` validates every example and a
live response/status/error/audit record against these schemas on every run.
