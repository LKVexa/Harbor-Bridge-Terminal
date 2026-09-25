# Lifecycle and result-state model (INV30-GAP-012 · INV-30-C014, C015) — implemented in `lifecycle.py`

## Capability (per handle)
`minted → active → invalidated` (terminal, absorbing). `minted → invalidated` allowed. No other edges.

## Service
```
bootstrapping → ready | failed
ready ⇄ degraded
ready|degraded → quarantined | disabled | draining
quarantined → ready (operator) | disabled
disabled → bootstrapping (fresh start; all handles already revoked)
draining → stopped (terminal)
failed → bootstrapping
```
## Result states
| State | Meaning | Client action |
|---|---|---|
| success | operation done | — |
| partial | batch where some items refused (each item carries its own envelope) | inspect items |
| degraded | success while a non-critical dependency is down (e.g. telemetry export) | none |
| retryable_failure | envelope `retryable=true` (OVERLOADED, CIRCUIT_OPEN, DEADLINE_EXCEEDED, BACKEND_UNAVAILABLE) | back off + jitter (`RetryPolicy`) |
| terminal_failure | everything else — including **all** security/policy refusals | do not retry |
