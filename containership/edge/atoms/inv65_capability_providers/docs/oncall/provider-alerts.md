# Provider alerts (M22)

| Alert | Means | First action |
|---|---|---|
| ProviderIsolationViolation | a call hit a record from another scope | SEV1: emergency disable, preserve audit |
| ProviderNotReady | readiness false 5 min | check `/readyz` reasons |
| ProviderCircuitOpen | backend failing | check backend; calls are shedding by design |
| ProviderSaturation | OVERLOADED > 1 % 10 min | scale out / raise quotas deliberately |
| ProviderPolicyRejectSpike | FORBIDDEN spike | policy change or attack; check decision ids |
| ProviderAuthFailureSpike | UNAUTHENTICATED spike | key rotation gone wrong or spoofing |
| ProviderErrorBudgetBurn | call_overhead burn > 1 | block releases; profile |
