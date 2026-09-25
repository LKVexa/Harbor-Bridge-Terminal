# INV-61 Telemetry Retention, Privacy & Export Policy (M18 / C075, C079)

Machine-checked subset: `observability.TelemetryPolicy`.

## Data inventory and classification

| Signal | Contents | Class | Retention | Sampling |
|---|---|---|---|---|
| Metrics | counts/latency by interface, function, status, tenant class | Internal | 90 d | 100 % |
| Logs (`inv61-log/1`) | node, component, event, reason, request id (truncated) | Confidential | 30 d | 100 % WARN+, INFO configurable |
| Traces | span ids, allow-listed attributes only | Confidential | 7 d | `trace_sample_rate` (default 10 %); parent decision honoured |
| Audit (`audit.jsonl`) | security decisions, principal, tenant, key id | Restricted | 400 d, WORM storage | 100 %, never sampled |

## Collection minimisation

Never collected: argument or result payloads, MACs, nonces, key material, TLS private keys, raw client IPs in metrics. Raw tenant IDs never appear as metric labels (`raw_tenant_ids_in_metrics = False`); they appear only in audit records.

## Redaction

`StructuredLogger.redact` removes `mac, secret, token, password, args, result, key, nonce, authorization, cookie, tls_key, audit_key, keyring` and any key containing `secret`, `passw` or `token`, recursively. Bytes are logged as length only.

## Export governance

Exporters are denied unless the endpoint is in `telemetry_export_allowlist` (config, mutable, audited on activation). Export is over TLS only. Cross-region export of Confidential/Restricted classes requires a residency waiver.

## Tenant isolation

Tenant-scoped diagnostic requests are answered only from audit records filtered by the requesting tenant; operators with cross-tenant access are listed in the access review (monthly).

## Deletion

Expired data deleted by the sink's TTL; audit records past retention are archived to cold WORM storage with the chain head recorded, then deleted from hot storage.
