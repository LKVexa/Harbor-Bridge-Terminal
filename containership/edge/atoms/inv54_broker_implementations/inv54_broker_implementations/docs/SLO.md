# Support and SLO commitments  (component 91) — PROPOSED, requires owner sign-off

| SLO | Objective | Error budget | Source |
|---|---|---|---|
| ordering | zero per-key reorderings | none | contract.py |
| fan-out completeness | every subscriber receives every accepted message (reject policy) | none | contract.py |
| append latency | p99 < 2 ms (in-process reference); provider-specific otherwise | 1 % | contract.py |
| availability (durable replicated) | 99.9 % monthly writable | 43 min/month | PROPOSED |
| incident ack | Sev1 15 min, Sev2 1 h, Sev3 next business day | — | PROPOSED; no on-call exists (OWN-3) |
Support scope: INV-54 package code and adapters; provider clusters are supported by their operators.
