# INV-17 Streaming primitive — Threat Model

**Controls:** C041 (dedicated threat model); cross-references C023/C044, C024/C042-C043, C046, C047, C048, C049, C087
**Component version:** 4.3.0 (`observability::VERSION`, `__init__::__version__`)
**Owner:** UNASSIGNED — owner to fill
**Reviewer / approver:** UNASSIGNED — owner to fill (no review has taken place)
**Status:** DRAFT. Machine-readable companion: `security/threat-model.json` (maintained separately).

This document describes only behaviour present in the code. Every mitigation cites `module::symbol`.
Tests listed are the planned test modules; where a test file is being written concurrently, the
mapping is the intended location, not a claim that the test passes.

## 1. Scope and system description

INV-17 is an **instance-local, in-process** Python library. There is no network listener in the data
plane. The pieces are:

| Layer | Module | Role |
|---|---|---|
| Data plane | `stream::Stream` | Typed, credit-limited, bounded buffer with explicit EOS and drop errors |
| Control plane (instance-local) | `control::StreamRegistry` | Authorisation, tenant quotas, load shedding, circuit breaker, freeze/disable, health |
| Security | `security::CapabilityAuthority`, `KeyRing`, `TrustedClock`, `AuditLedger`, `DataPolicy` | HMAC capability tokens, replay cache, fail-closed trust deps, hash-chained audit |
| Configuration | `configuration::load_layers`, `ConfigManager` | Schema-validated layered config, provenance, atomic activation/rollback |
| Observability | `observability::MetricsExporter`, `StructuredLogger`, `TraceContext`, `explain`, `status`, `serve_status` | Operator surfaces; optional loopback HTTP endpoint |
| Seams | `adapters::WaitableSet`, `CanonicalCodec`, `drain_to_completion`, `HttpBody`, `OsReadinessBridge` | INV-15/12/18/20/19 adjacent-layer adapters |

## 2. Assets

| ID | Asset | Property at risk |
|---|---|---|
| A1 | Host memory / buffer capacity (`Stream.buffer`, `StreamRegistry.global_buffer_budget`) | Availability |
| A2 | Credit counter (`Stream.credit`) — the contract's source of truth | Integrity |
| A3 | Lifecycle state (`ended`, `reader_dropped`, `writer_dropped`, `frozen`) | Integrity, availability |
| A4 | Element payloads in flight | Confidentiality, integrity |
| A5 | Stream handles / stream ids in `StreamRegistry._streams` | Integrity (who may operate) |
| A6 | Capability tokens and HMAC keys (`KeyRing._keys`) | Confidentiality, integrity |
| A7 | Audit chain (`AuditLedger.events`, audit key) | Integrity, non-repudiation |
| A8 | Effective configuration + provenance (`ConfigManager._current`) | Integrity |
| A9 | Telemetry (metrics, logs, explain output) | Confidentiality (tenant ids, payloads), integrity |
| A10 | Emergency controls (`emergency_disable`, `quarantine`) | Integrity, availability |

## 3. Actors / attacker model

| Actor | Trust | Capabilities assumed |
|---|---|---|
| Trusted runtime / host (issuer of tokens) | Trusted | Holds `KeyRing`; constructs `StreamRegistry` |
| Tenant workload (benign) | Semi-trusted | Holds tokens for its own streams; may be slow or crash |
| Compromised workload | Untrusted | Can call any public API with arbitrary arguments, craft hostile element objects, retry/replay tokens it has seen |
| Malicious tenant | Untrusted | As above, plus attempts to reach other tenants' streams or exhaust shared budget |
| Operator (SRE) | Trusted-but-audited | Principals in `StreamRegistry.admins` (default `("sre-oncall",)`) |
| Trust dependency (key service, clock) | External | May be unavailable (modelled by `KeyRing.available`, `TrustedClock.available`) |
| Supply-chain attacker | Untrusted | Could tamper with package, `vendor/pk_core`, CI runner, schemas |

**Out of attacker model (explicit assumption):** an attacker executing arbitrary Python in the *same
interpreter* can read `KeyRing._keys`, mutate `Stream` attributes directly and bypass every check.
Python offers no memory isolation between objects in one process. In-process controls therefore
defend against **API misuse and malformed input**, not against code already running with interpreter
privileges. Hard isolation requires a process/component boundary (see `security/isolation-model.md`).

## 4. Trust boundaries

```
 [tenant workload A] --token--> TB1 --> StreamRegistry.open/get/write/transfer --> Stream (object)
 [tenant workload B] --token--> TB1 ----^                       |
 [operator]         --principal--> TB2 --> emergency_disable/quarantine/release/enable
 [config author]    --overlay--> TB3 --> ConfigManager.activate (schema-validated)
 [KeyRing/TrustedClock] <-- TB4 (trust dependencies, fail closed)
 [adjacent INV layer] --bytes/readiness--> TB5 --> CanonicalCodec.lift / OsReadinessBridge.on_ready
 [scraper/operator] <-- TB6 -- serve_status (loopback HTTP, unauthenticated), MetricsExporter, explain
```

- **TB1 registry boundary:** token verification in `control::StreamRegistry._authorize` -> `security::CapabilityAuthority.verify`.
  Important: `StreamRegistry.get` and `open` return the live `Stream` object. After that, direct
  calls on the object (`read`, `grant`, `end`, `drop_*`) are **not** re-authorised — the object
  reference is itself the capability (object-capability model). Only `StreamRegistry.write` routes
  element writes through quota/shed checks.
- **TB2 operator boundary:** `control::StreamRegistry._admin` checks membership of `admins`
  (a string allow-list, no cryptographic authentication of the principal).
- **TB3 config boundary:** `configuration::load_layers` + `validate` + cross-field rule CFG-X1.
- **TB4 trust dependencies:** `security::KeyRing.get`, `security::TrustedClock.now`.
- **TB5 adapter seams:** `adapters::CanonicalCodec.lift` (1 MiB cap `MAX`, tag check, type re-check),
  `adapters::OsReadinessBridge.on_ready` (clamps to remaining credit ceiling).
- **TB6 telemetry boundary:** `observability::redact`, `pseudonymise`, `ALLOWED_LABELS`, `MAX_SERIES`.

## 5. Abuse cases (STRIDE + resource abuse)

| ID | Threat | STRIDE | Mitigation (code) | Test (planned) | Residual |
|---|---|---|---|---|---|
| T01 | **Memory exhaustion** via unbounded buffering / write flooding | D | `stream::Stream.write` requires credit and enforces `StreamConfig.max_buffer`; `Stream.grant` rejects grants beyond `max_credit` (`CreditLimitExceeded`); `control::StreamRegistry.write` enforces `TenantQuota.max_buffered` and `global_buffer_budget` (`QuotaExceeded`, `LoadShed`); `configuration::load_layers` caps values via schema and CFG-X1 | `tests/test_adversarial.py`, `tests/test_control.py`, `tests/test_property.py` | Bounds are **element counts, not bytes**: large elements are bounded only at the `CanonicalCodec` seam (1 MiB). Direct `Stream.write` bypasses tenant/global budgets. |
| T02 | Unbounded credit grant | D/T | `Stream.grant` validates positive int and ceiling; `OsReadinessBridge.on_ready` clamps to `max_credit - credit` | `tests/test_adversarial.py`, `tests/test_adapters.py` | None known |
| T03 | **Writer-after-drop** (writer keeps producing after reader gone) | D/I | `Stream.drop_reader` clears buffer, zeroes credit, counts `dropped_items`; subsequent `write`/`end`/`grant` raise `EndDropped` on first attempt | `tests/test_stream.py`, `tests/test_adversarial.py` | None known |
| T04 | **Type confusion** (wrong element on a stream) | T | `Stream.write` `isinstance` check plus explicit `bool`-is-not-`int` guard -> `ElementTypeMismatch`; `CanonicalCodec.lift` re-checks type; `HttpBody` requires `bytes` streams | `tests/test_adversarial.py`, `tests/test_adapters.py` | Subclasses are accepted (e.g. `int` subclasses on an `int` stream); `element_type` with a custom metaclass `__instancecheck__` is trusted. |
| T05 | **Lost EOS** (reader waits forever) | D | Explicit `Stream.end`; `read` returns `None` only after EOS; `drop_writer` makes `read` raise `EndDropped` after drain; `read_wait` has `timeout` + `CancelToken` and never infers EOS from timeout (`StreamTimeout`); `drain_to_completion` resolves trailer with the error on drop | `tests/test_stream.py`, `tests/test_fault_injection.py` | A writer that neither ends nor drops leaves the stream `credit_stalled`/`open`; detection is by `StreamRegistry.health` stall thresholds, not automatic. |
| T06 | **Token forgery** | S | `CapabilityAuthority.verify`: HMAC-SHA256 over canonical claims, `hmac.compare_digest`, `v == 1`, key id lookup, 4096-byte length cap, malformed input -> `AuthError`; keys >= 256 bits (`KeyRing.__init__`, `rotate`) | `tests/test_security.py` | Security reduces to secrecy of `KeyRing` keys in process memory. |
| T07 | **Token replay** | S/E | Nonce per token; tokens with `transfer` right or `single_use=True` carry signed claim `su=true` (`Capability.single_use`) and are single-use -> `TokenReplay`; expiry via `exp` vs `TrustedClock`; `max_ttl` (default 300 s); `revoke` | `tests/test_security.py`, `tests/test_adversarial.py` | Non-single-use tokens are **bearer tokens** re-presentable until expiry. Only single-use nonces enter the replay cache (`replay_cache=65536`); it never evicts a live nonce and **fails closed** when full (`TrustServiceUnavailable`, `dependency="replay-cache"`), so a flood of single-use tokens can deny further single-use verifies until entries expire. `_revoked` set is unbounded and never pruned. |
| T08 | **Cross-tenant access** | E/I | `StreamRegistry.get` refuses when `s.tenant/workload` differs (audited `authz.denied`); token claims bind `aud`, `ten`, `wl`; transfer only via `StreamRegistry.transfer` with single-use `transfer` right | `tests/test_security.py`, `tests/test_control.py` | Object references handed out by `get`/`open` are not revocable; a workload that leaks its `Stream` object leaks access. `transfer` does not require consent from the destination tenant. |
| T09 | **Trust-service outage** (keys/time) | D/E | `KeyRing.get` and `TrustedClock.now` raise `TrustServiceUnavailable`; `_authorize` audits `trust.unavailable` and re-raises (fail closed) | `tests/test_security.py`, `tests/test_fault_injection.py`, `tests/test_disaster.py` | Outage denies all new opens/gets — availability traded for safety by design. |
| T10 | **Hostile element objects** (`__eq__`, `__hash__`, `__class__` property, huge objects, finalizers) | D/T | Data plane never calls element methods except via `isinstance`; buffer is a `deque` (no hashing/equality); `redact` replaces `payload/element/value` with a type name; `CanonicalCodec` rejects unknown types | `tests/test_adversarial.py` | `isinstance` may consult a hostile `__class__` property **while `Stream._lock` is held** (lock-contention DoS within that stream). `__del__` of dropped elements runs under the lock during `drop_reader`’s `buffer.clear()`. |
| T11 | **Audit tampering** (edit, reorder, delete, truncate) | T/R | `AuditLedger`: per-event HMAC, `prev` chaining, `seq`; `verify` detects edits/reorder/deletion; truncation detectable with `verify(expected_head=anchor())` | `tests/test_security.py` | Ledger is in-memory; default key is random per process so a chain cannot be verified after restart unless the key is supplied and persisted. Anchors must be stored externally (not implemented here). Attacker with in-process access can recompute MACs. |
| T12 | Close/drop spoofing | S/T | Registry checks tenant/workload before handing out object; `END_RIGHTS` defines reader/writer right sets | `tests/test_security.py` | `END_RIGHTS` is declarative only — not enforced on direct `Stream` method calls (see TB1). |
| T13 | Starvation between tenants | D | `control::FairCreditScheduler` weighted deficit round-robin, per-tenant `TenantQuota` | `tests/test_control.py`, `tests/test_property.py` | Scheduler is not wired into `StreamRegistry`; callers must use it explicitly. |
| T14 | Log / metric injection & high cardinality | T/I/D | `_esc` label escaping; `ALLOWED_LABELS`; `MAX_SERIES`; JSON logging via `json.dumps`; `redact` secret-like keys | `tests/test_observability.py` | `inv17_build_info` labels come from env vars (operator-controlled). |
| T15 | Config poisoning | T/D | `load_layers` validates full merged doc against schema, CFG-X1; `ConfigManager.activate` requires author/revision, health probe with auto-rollback, audit `config.activate`/`config.rollback` | `tests/test_control.py` (config cases), `tests/test_fault_injection.py` | No signature on config overlays; provenance is self-declared. |
| T16 | Emergency-control abuse | E | `_admin` allow-list; all actions audited (`control.*`) | `tests/test_control.py` | Principal string is not authenticated. |
| T17 | Unauthenticated status endpoint | I | `serve_status` binds `127.0.0.1` by default; `explain` redacts tenant/workload | `tests/test_observability.py` | If bound to a non-loopback host, `/explain` and `/metrics` are exposed without auth. |
| T18 | Supply chain (`vendor/pk_core`, packaging, CI, schemas) | T | Runtime modules are stdlib-only; `pk_core` imported lazily (`__init__::__getattr__`); SBOM planned via `tools/sbom.py`; evidence via `tools/evidence_bundle.py` | CI (planned) | No signatures or provenance attestations exist yet. |
| T19 | Timing / lock contention DoS | D | Per-stream `RLock`; `_wait` polls in 50 ms slices; registry uses one `RLock` | `tests/test_soak.py` | `StreamRegistry.buffered_total` is O(streams) under the registry lock on every write. |
| T20 | Privacy of telemetry | I | `pseudonymise` (salted SHA-256, 12 hex), `redact` | `tests/test_observability.py` | Default salt `"inv17"` is public unless `INV17_TELEMETRY_SALT` is set; 12-hex pseudonyms over a small tenant set are dictionary-reversible. |

## 6. Mitigation -> code -> test matrix (summary)

| Control | Code | Test |
|---|---|---|
| Bounded memory | `stream::Stream.write`, `Stream.grant`, `StreamConfig`, `control::StreamRegistry.write` | `tests/test_adversarial.py`, `tests/test_property.py` |
| Drop detection | `stream::Stream.drop_reader`, `drop_writer`, `EndDropped` | `tests/test_stream.py` |
| Typing | `stream::Stream.write`, `adapters::CanonicalCodec.lift` | `tests/test_adversarial.py` |
| Explicit EOS / bounded waits | `stream::Stream.end`, `read_wait`, `write_wait`, `CancelToken` | `tests/test_stream.py`, `tests/test_fault_injection.py` |
| Authentication | `security::CapabilityAuthority.verify` | `tests/test_security.py` |
| Replay | `security::CapabilityAuthority._replay`, `security::Capability.single_use`, `TokenReplay` | `tests/test_security.py` |
| Isolation | `control::StreamRegistry.get`, `transfer`, `TenantQuota` | `tests/test_security.py`, `tests/test_control.py` |
| Fail closed | `security::KeyRing.get`, `TrustedClock.now`, `control::StreamRegistry._authorize` | `tests/test_fault_injection.py` |
| Audit integrity | `security::AuditLedger.record`, `verify`, `anchor` | `tests/test_security.py` |
| Overload | `control::CircuitBreaker`, `LoadShed` | `tests/test_control.py` |
| Telemetry privacy | `observability::redact`, `pseudonymise`, `ALLOWED_LABELS` | `tests/test_observability.py` |

## 7. Residual risks (accepted pending owner decision)

| ID | Residual risk | Proposed treatment | Owner |
|---|---|---|---|
| R1 | Byte-size of elements unbounded on direct `Stream` use | Document; add optional byte accounting in a future version | UNASSIGNED — owner to fill |
| R2 | Bearer (multi-use) tokens replayable until expiry | Short TTLs; use `single_use=True` for sensitive rights | UNASSIGNED — owner to fill |
| R3 | Replay cache full (>65 536 live single-use nonces) fails closed, denying single-use verifies (availability, not replay) | Size `replay_cache` to peak single-use rate x `max_ttl` | UNASSIGNED — owner to fill |
| R4 | Stream object is an unrevocable capability once handed out | Use `freeze`/`quarantine` to neutralise | UNASSIGNED — owner to fill |
| R5 | Audit ledger in-memory, random key | Integrator persists key and exports `export_jsonl` + `anchor()` externally | UNASSIGNED — owner to fill |
| R6 | Admin principal unauthenticated string | Integrator authenticates principal before calling | UNASSIGNED — owner to fill |
| R7 | Hostile `__class__` under lock | Accept (in-process code is trusted-equivalent) | UNASSIGNED — owner to fill |
| R8 | No supply-chain signatures | SBOM + evidence bundle tooling; signing not yet available | UNASSIGNED — owner to fill |

## 8. Review triggers

Re-review on: any new transport boundary, schema/protocol version change (`stream::PROTOCOL_VERSIONS`),
change to the capability model (`security::RIGHTS`, token format `v`), or new configuration mechanism.
No review has been recorded to date.
