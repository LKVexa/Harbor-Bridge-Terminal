# INV-64 interface inventory and contracts (MC-06, MC-09, MC-10)

## 1. Boundary inventory

| ID | Boundary | Direction | Transport | Caller → callee | Auth context | Contract (version) | Limits |
|---|---|---|---|---|---|---|---|
| B1 | submit / validate / canonicalize | inbound | in-process call (`ApplicationModelService.handle`); a host may expose it over HTTP/gRPC unchanged | submitter, control plane → INV-64 | token (`auth.py`) + channel binding + capability `app.*` | `PK_APP_SUBMIT_REQUEST/1` → `PK_APP_SUBMIT_RESPONSE/1`, errors `PK_APP_ERROR/1`; protocol `PK_APP_SUBMIT/2` (v1 deprecated) | 1 MiB body, depth 64, 1,000 issues, deadlines §3 |
| B2 | pure manifest API | inbound | Python import (`manifest.py`) | any trusted in-process caller | none (no authority: pure function) | `PK_APP_MANIFEST/1`, `PK_APP_VALIDATE/1`, `PK_APP_CANONICAL/1` | same byte/depth/collection ceilings |
| B3 | Wasm component (contract only) | inbound | WIT `pk:inv64/app-model@1.0.0` | Wasm host | host-provided | `wit/inv64-app-model.wit` | as B2 |
| B4 | overlays | inbound | file/in-process | operator → INV-64 | `authorize(author, overlay)` hook (capability `config.overlay.write`) | `PK_APP_OVERLAY/1` | 1,000 ops, 16 path segments |
| B5 | activation / rollback | inbound | in-process (`ConfigStore`) | operator, rollout controller | capability `config.activate` / `config.rollback` (host enforces via `Authorizer.require`) | `PK_APP_CONFIG_STATE/1` journal | 30 s deadline |
| B6 | status | inbound | in-process (`status()`); host maps to probes | orchestrator, operator | `status.inspect` for detail | `PK_APP_STATUS/1` | cached probes, TTL 5 s |
| B7 | explain | inbound | in-process | operator | `explain.read`, tenant-filtered | `PK_APP_EXPLAIN/1` over `PK_APP_DECISION/1` | last 50 decisions |
| B8 | audit ledger | outbound (file) | JSON lines + anchor | INV-64 → WORM store | ledger MAC key (optional), anchor key | `PK_APP_AUDIT/1`, `PK_APP_AUDIT_ANCHOR/1` | buffer 1,000 |
| B9 | telemetry | outbound | Prometheus text, JSON log lines, W3C traceparent | INV-64 → collector | collector auth is the host's | `PK_APP_TELEMETRY/1` (`telemetry.METRICS`, `LOG_FIELDS`) | 200 series/metric, log ring 10,000 |
| B10 | adjacent handoff | outbound | in-process contracts (emulated in 4.3.0) | INV-64 → INV-10/66/65/63 | tenant + correlation + traceparent carried; never replaced | `PK_COMPOSE_RESOLVE/1-2`, `PK_GUARDRAIL/1-2`, `PK_PROVIDER_BIND/1`, `PK_DEPLOY_HANDOFF/1` | activation deadline |
| B11 | artifact trust | inbound (files) | DSSE envelopes | release/security → INV-64 | trust-policy root keys | in-toto Statement v1 + `PK_APP_ARTIFACT_VERIFICATION/1` | — |
| B12 | release evidence | outbound (files) | JSON | tools → gate | — | `PK_APP_EXIT_GATE/1` and the evidence schemas in `ops/GATE_POLICY.json` | — |

Not applicable in 4.3.0 (stated explicitly): network listeners, message-bus
events, IPC sockets, device and hypervisor interfaces — INV-64 opens none. A
host that exposes B1 over a network MUST terminate TLS with
`crypto_policy.tls_context(server=True)` and pass the channel-binding value.

## 2. Contract rules

- Every public error is `PK_APP_ERROR/1` (`schema/error-v1.schema.json`): `code` from `errors.CATALOG`, `status`, fixed `message`, `retryable`, `correlation_id`, bounded `details` (≤ 64 keys). Free text is never the only signal.
- Issues are typed arrays `{code, path, message}`, sorted by `(path, code)`, at most 1,000, with `issue_count` and `truncated`.
- Canonical results carry `form`, `algorithm`, `digest`, `precondition: "validated"`.
- Unknown request fields ⇒ `request.invalid`; unknown enums ⇒ refused; manifest extensions ⇒ preserved (SPECIFICATION §1.1).
- Transport-specific behaviour (HTTP status codes, headers) is advisory; the envelope is the contract. Undocumented fields are not commitments.
- Compatibility per family: adding optional response fields or error codes = minor; anything else = major (`compatibility.json` records families).

## 3. Operation semantics matrix (MC-09; source of truth `semantics.OPERATIONS`)

| Operation | State-changing | Auto-retry safe | Idempotency key | Default / max deadline | Overload response |
|---|---|---|---|---|---|
| validate | no | yes | none | 1 s / 5 s | `admission.overloaded` / `admission.tenant_quota` + `retry_after_ms` |
| canonicalize | no | yes | none | 1 s / 5 s | same |
| submit | yes (registry upsert, audit) | no — caller retries **with the same key** | required, `[A-Za-z0-9_-]{16,128}`, tenant-scoped, 24 h | 2 s / 10 s | same |
| activate | yes | no (CAS makes a blind retry fail with `activation.conflict`) | required (host) | 10 s / 30 s | — |
| rollback | yes | yes (idempotent: already-active target is a no-op) | required (host) | 10 s / 30 s | — |
| status | no | yes | none | 0.5 s / 2 s | cached |
| explain | no | yes | none | 1 s / 5 s | — |

Deadlines propagate as an absolute `deadline_at_ms`; a hop may shorten but never extend it. Cancellation (`CancelToken`) is checked between stages: cancelled-before-start ⇒ nothing happens; cancelled in flight ⇒ `request.cancelled` before any commit; completed-concurrently ⇒ the completed result stands (commit is the linearization point); irreversible effects (audit append) happen only after the last cancellation check. Retries: exponential backoff with full jitter (50 ms base, 2 s cap), ≤ 4 attempts, ≤ 10 s elapsed, plus a shared retry budget (10 tokens, refilled 0.1 per success) that stops retry storms when a shared dependency fails.

### Client guidance

Branch on `error.code` and `error.retryable`, never on `message`. For `submit`, persist the idempotency key with the request before sending so it survives a client restart; reuse it for every retry; a reused key with a different body is `idempotency.conflict`. Respect `retry_after_ms`. Treat `deadline.exceeded` as "unknown whether a *downstream* effect happened" only for adjacent handoffs; INV-64's own effects are all-or-nothing.

## 4. Adjacent-layer responsibility split (MC-10)

| Layer | Owns | INV-64 sends | INV-64 expects | Failure mapping |
|---|---|---|---|---|
| INV-10 composition | what a component reference is | component `type`s, ctx | `{unresolved: []}` | unresolved ⇒ `manifest.invalid`; down ⇒ `admission.overloaded`; malformed ⇒ `internal` |
| INV-66 control plane | guardrail policy | tenant, canonical digest, manifest | `{verdict: allow/deny, reasons}` | deny ⇒ `authz.denied` |
| INV-65 providers | provider implementations and grants | tenant, provider names | `{bound, denied}` | denied ⇒ `authz.denied`; partial binds are released on any later failure |
| INV-63 deployment | running | canonical document + digest + tenant + correlation + traceparent | `{accepted, deployment}` | digest mismatch or missing context ⇒ refused |

Order: version check for all four → resolve → guardrail → bind → deploy; any
failure after bind unbinds (no partial activation). Evidence:
`evidence/INTEGRATION.json` (emulated). The real-implementation profile is
`BLOCKED_EXTERNAL` and is recorded as a failing gate control, never a skip.
