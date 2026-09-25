# Security architecture  (components 19, 20, 37, 39, 40, 41, 42, 43)

- **Authentication (19):** `security.HmacAuthenticator` — HMAC-SHA256 bearer tokens with expiry, nonce-replay protection and key-ring rotation. `auth.mode=provider` delegates to the provider's native auth (SASL/SCRAM, AMQP creds, IAM) configured from secret references.
- **Authorization (20):** `security.Authorizer` — deny-by-default grants `(tenant, actions, resource_glob, subject|role)`. Actions: publish, subscribe, consume, seek, admin, config.
- **Least privilege / ambient authority (37):** the core imports no network or subprocess modules; filesystem access is confined to `storage.path`; secrets are reachable only via `SecretResolver` with an explicit provider map. OS-level sandboxing (seccomp, read-only rootfs, network policy) is a deployment control — **UNVERIFIED** here; see `RUNBOOKS.md` day-0 hardening checklist.
- **Tenant isolation (39):** per-tenant broker instances in `BrokerService`; cross-tenant principal→target always `INV54-E0103`.
- **Transport TLS (40):** config enforces TLS ≥ 1.2, hostname verification in production; Kafka adapter sets `security.protocol=SSL|SASL_SSL` and `ssl.endpoint.identification.algorithm=https`; RabbitMQ uses `amqps://` URLs; SQS uses the AWS SDK's HTTPS endpoints. **Live TLS handshake tests: UNVERIFIED (no provider environment).**
- **At rest (41):** `storage.Cipher` AES-256-GCM, key from `storage.key_ref`; encrypted store refuses to open without the key; rotation = new store + `backup`/`restore` re-encrypt (online re-keying not implemented → PARTIAL).
- **Outage (42):** key/secret/identity source failure → `INV54-E0105` (fail closed); `BrokerService` enters `degraded` for non-security dependencies only.
- **Audit (43):** every allow/deny, lifecycle, quarantine event is appended to an HMAC hash chain; `verify(expected_head)` detects edit/delete/reorder/truncation; the head is exported in `health()` for external retention.
