# Boundary and interface inventory (C021, C022, C023, C024, C025, C028)

## Boundary table

| # | Boundary | Producer → consumer | Trust | Transport | AuthN | AuthZ capability | Schema | Size limit | Timeout | Failure codes |
|---|---|---|---|---|---|---|---|---|---|---|
| B1 | `SfiService.submit` | workload submitter / CI → service | untrusted input | in-process API | identity token (HMAC, `PK_SFI_IDENTITY/1`) + Ed25519 artifact statement | `sfi.submit` @tenant | `PK_SFI_SUBMIT_REQUEST/1`, `PK_SFI_ARTIFACT_STATEMENT/1` | `limits.max_module_bytes` (≤ 64 MiB) | `limits.deadline_seconds` | input, security, auth, resource |
| B2 | `SfiService.load` (trusted loader) | runtime orchestrator → service | semi-trusted | in-process | identity token + descriptor MAC | `sfi.load` @tenant @digest | `PK_SFI_LOAD_REQUEST/1`, `PK_SFI_SEALED_DESCRIPTOR/1` | as B1 | verify deadline | security, auth, policy |
| B3 | `SfiService.execute` | orchestrator → engine | trusted caller, untrusted guest | subprocess stdin/stdout JSON | identity token | `sfi.execute` @tenant @digest | engine job/result (`PK_SFI_ENGINE_RESULT/1`) | 64 MiB job | `engine.call_timeout_seconds` (process killed) | dependency, resource |
| B4 | `SfiService.quarantine/release` | operator → service | privileged | in-process | identity token (human) | `sfi.quarantine`; global = dual human | `PK_SFI_QUARANTINE_REQUEST/1` | reason ≤ 256 | none (local) | auth, input |
| B5 | `activate_config / rollback_config` | policy controller → service | privileged | in-process + files | identity token | `sfi.policy.write` | `PK_SFI_CONFIG/1`, `PK_SFI_CONFIG_GENERATION/1` | strict JSON, bounded keys | none (local) | `SFI_CONFIG_*` |
| B6 | Config/state files | service ↔ disk | trusted storage | POSIX files, atomic rename | filesystem permissions | n/a | as B5, `PK_SFI_STATE/1` | — | — | `SFI_CONFIG_INVALID`, `SFI_UNSUPPORTED_VERSION` |
| B7 | Audit log | service → SIEM | append-only | JSONL file (+ external checkpoint) | n/a | `sfi.audit.read` (readers) | `PK_SFI_AUDIT/1` | event fields ≤ 256 chars | spool on sink failure | `SFI_AUDIT_TAMPERED`, `SFI_DEPENDENCY_UNAVAILABLE` |
| B8 | Health | probes → service | read-only | in-process / exporter | none (no secrets exposed) | — | `PK_SFI_HEALTH/1` | — | — | — |
| B9 | Metrics / logs / traces | service → telemetry | read-only | Prometheus text, JSON lines, W3C `traceparent` | n/a | `sfi.audit.read` for explain | TELEMETRY_POLICY.md | bounded series (256/metric) | — | — |
| B10 | CLI | operator → tools | privileged local | argv/stdout | local OS identity | local OS permissions | JSON outputs | as B1 | as B1 | exit 2 + `PK_SFI_ERROR/1` |
| B11 | Reference model | tests → `sfi_core.py` | test only | Python API | — | — | `PK_SFI_MODULE/1`, `PK_SFI_MASK/1` | — | — | reference `SfiSecurityError` codes |
| B12 | `pk_core` checklist binding | pk_core → `component.py` | trusted tooling | Python API | — | — | pk_core contract | — | — | NOT RUN when absent |
| B13 | Key/secret store | secret refs → service | trusted dependency | env / file | OS | — | `SecretRef` | ≥ 32 bytes | — | `SFI_DEPENDENCY_UNAVAILABLE`, `SFI_TRUST_STALE` |

There are no RPC, WIT, device or hypervisor boundaries in this release. Adding one requires a row here, a
schema in `schemas/`, contract tests and a threat-model update.

## Schema rules (C022)

* Every schema has a stable `$id` (`urn:pk:schema:<NAME>:<major>`) and `additionalProperties: false` except
  the audit event (allowlisted fields vary by event type).
* **Additive** change (new optional field) = minor component version; **breaking** change (new required
  field, removed field, enum narrowing, meaning change) = new schema major id, old id refused.
* Unknown fields in requests are rejected. Schema validation precedes semantic validation.
* JSON inputs are parsed with `config.load_json_strict`: duplicate keys, NaN/Infinity rejected; integer
  fields reject floats and bools; secure numeric bounds enforced.
* **Canonical serialization** for every hash/MAC/signature: `sfi.canonical_json` (sorted keys, `,`/`:`
  separators, UTF-8, `allow_nan=False`). Display JSON (indented) is never hashed. Artifact identity is
  SHA-256 over the exact binary bytes.

## Interaction semantics (C025)

| Operation | Class | Deadline | Cancellation | Idempotent? (key) | Retry |
|---|---|---|---|---|---|
| parse/rewrite/verify | local CPU-bound | `limits.deadline_seconds` checked every 1024 instructions and per section | `cancel()` callback; no partial output is returned | yes (artifact digest + profile digest) | never on deterministic rejection |
| seal | local CPU + key service | inherits submit | before seal nothing is trusted | no (fresh nonce) — safe to repeat, each descriptor loads once | on `SFI_DEPENDENCY_UNAVAILABLE`/`SFI_TRUST_STALE` |
| load | local | verify deadline | replay nonce consumed before re-verify: a cancelled/failed load burns the descriptor (fail closed) | no (one-time descriptor) | resubmit to get a new descriptor |
| execute | remote-ish (subprocess) | `engine.call_timeout_seconds`, process killed | kill = no state retained (fresh process per job) | caller-defined | retry only `SFI_DEADLINE_EXCEEDED`/`SFI_DEPENDENCY_UNAVAILABLE`, via `controls.retry` (full jitter, ≤ 4 attempts) and circuit breaker |
| config activate | local I/O | — | lock + CAS; crash mid-way leaves the previous generation active | no | on `SFI_CONFIG_CONFLICT` after re-read |
| audit emit | local I/O | — | — | no (sequence) | internal spool (bounded) |

Backpressure: admission control (bounded queue, per-tenant caps) sheds with retryable `SFI_OVERLOADED`
(`retry_after_ms` detail). A caller that disconnects during verify simply loses the result; no descriptor was
issued, so nothing is detached in a trusted state.

## Limits (C028)

| Limit | Default | Secure bounds | Where enforced |
|---|---|---|---|
| module bytes | 16 MiB | 1 KiB – 64 MiB | before parsing |
| functions | 100 000 | 1 – 1 000 000 | on declared count, before allocation |
| function body bytes | 1 MiB | 16 B – 16 MiB | per body |
| total instructions | 5 000 000 | 16 – 50 000 000 | during decode |
| locals per function | 50 000 | fixed | during decode |
| control nesting depth | 1 024 | fixed | during decode |
| br_table targets | 65 536 | fixed | during decode |
| types / imports / globals / exports | 10 000 / 1 000 / 10 000 / 10 000 | fixed | on declared count |
| table elements / data segments | 100 000 / 10 000 | fixed | on declared count |
| custom sections total | 1 MiB | fixed | during decode |
| names | 1 KiB each | fixed | during decode |
| deadline | 10 s | 0.05 – 60 s | cooperative |
| concurrent operations | 4 global, 2 per tenant, queue 64 | 1–256 / 1–256 / 0–10 000 | admission |
| replay cache | 100 000 unexpired nonces | fixed | fails closed when full |
| audit spool | 10 000 events | fixed | fails closed when full |
| metrics series | 256 per metric | fixed | overflow series |
| log tail / explain records | 1 000 / 10 000 | fixed | ring buffers |
| engine job | 64 MiB stdin, 256 MiB heap | fixed | runner |

Verification work is linear in instruction count (single pass decode + single pass type check + single pass
pattern check); there is no quadratic step (br_table validation is linear in targets × label arity).
