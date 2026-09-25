# Interface limits (C028)

| Limit | Value | Where |
|---|---|---|
| HTTP body | 64 KiB | transport/http_adapter.py |
| Identifier length | 256 | provider.py |
| Config depth / items / string | 8 / 256 / 4096 | provider.py |
| Config bytes per link | 16 KiB | runtime/quotas.py |
| Links per tenant / workload | 1000 / 100 | runtime/quotas.py |
| Token size / TTL | 4096 B / 3600 s | authn |
| Decision TTL | 900 s | authz |
| Deadline | 1..600000 ms | call_metadata/v1 |
| Dispatch workers / queue | 8 / 64 | runtime/call_control.py |
| Tenant rate / burst / concurrency | 200/s / 400 / 16 | runtime/admission.py |
| Global in-flight | 256 | runtime/admission.py |
| Metric series per name | 200 | observability |
| Idempotency keys | 10000, 600 s | runtime/idempotency.py |
