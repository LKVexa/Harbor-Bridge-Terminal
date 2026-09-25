# Outcome semantics (INV-38-C014)

A closed, versioned outcome set — `SUCCESS`, `PARTIAL_SUCCESS`, `DEGRADED`,
`RETRYABLE_FAILURE`, `TERMINAL_FAILURE`, `REJECTED_POLICY` — with stable reason
codes. Authoritative source: `outcomes.py` (`REASONS`, `ERROR_CODE_TO_REASON`);
schema: `schemas/outcome-v1.schema.json`.

## Mapping from the reference model (C014-T02)
Every `BypassError.code` in `transport.py` maps to a reason code:
`OUT_OF_BOUNDS`→terminal, `NOT_REGISTERED`→terminal, `REGION_BUSY`→retryable
(after reconciliation), `RING_FULL`/`COMPLETION_RING_FULL`→retryable (safe),
`REGION_LIMIT`→retryable. Kernel fallback is `DEGRADED`
(`PK_BYPASS_KERNEL_FALLBACK`), a *successful* degraded operation, not a failure
requiring caller action (C014-T04).

## Retry safety (C014-T06) and tenant exposure (C014-T07)
Each reason carries a `Retryability` and a `tenant_safe` flag. `to_public()`
never leaks an internal-only reason. Table-driven tests in
`tests/test_outcomes.py` assert reason-code stability and full error-code
coverage. **Status:** `DONE`.
