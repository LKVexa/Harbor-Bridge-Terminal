# Capacity model (C069)

Saturation signals: `pk_denied_total{code="PK_PROVIDER_OVERLOADED"}` rate, dispatch shed count, admission `rejected` counters, p99 `pk_dispatch_seconds`. Rule of thumb from the local benchmark: one host process ≈ 1.7k full-stack calls/s single-threaded caller. Scale out when OVERLOADED > 1% of calls for 10 min (alert `ProviderSaturation`). Unvalidated at fleet scale.
