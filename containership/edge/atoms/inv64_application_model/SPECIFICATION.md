# INV-64 Application model — normative specification

**Specification version:** `INV64-SPEC/1.0` (reported in `status().versions.spec` and in `evidence/EXIT_GATE.json`)
**Applies to:** package 4.3.0, manifest schema `app/v1`, protocol `PK_APP_SUBMIT/1..2`
**Status:** implemented and tested; *approval by `architecture-review-board` pending* (ADR-0001).

The key words MUST, MUST NOT, SHALL, SHALL NOT, SHOULD, SHOULD NOT and MAY are
to be interpreted as described in RFC 2119 and RFC 8174 when, and only when,
they appear in all capitals. Every normative clause has a stable ID and at
least one verification method (T = automated test, E = evidence file,
I = inspection). Precedence of sources: `provenance/master-source.json`.

## 1. Function (C001-C008, C011)

INV-64 turns a declarative application topology — components, providers, links
between them and traits attached to components — into a validated, canonical
identity **before anything runs**. It never runs, reconciles or implements
providers (`contract.py` `not_owns`/`non_goals`).

| ID | Requirement | Verify |
|---|---|---|
| REQ-FN-1 | The validator SHALL refuse a manifest whose `schema` is not a supported identifier (`schema.unsupported`, `schema.type`). | T `test_manifest` |
| REQ-FN-2 | It SHALL refuse links whose `from` is not a declared component or whose `to` is not a declared component/provider. | T |
| REQ-FN-3 | It SHALL refuse traits on undeclared components. | T |
| REQ-FN-4 | It SHALL refuse duplicate names across components and providers. | T |
| REQ-FN-5 | It SHALL report every independent issue in one response, sorted by `(path, code)`, at most 1,000 issues plus a `truncated` flag and the full count. | T `ServiceTest.test_invalid_manifest_issues_sorted_and_bounded` |
| REQ-FN-6 | A canonical identity (SHA-256 of `PK_APP_CANONICAL/1` bytes) SHALL exist only for valid manifests. | T, fuzz I4 |
| REQ-FN-7 | Equivalent manifests (same content, any order of the four sections) SHALL share one digest; any semantic change SHALL change it. | T, fuzz I2/I3 |
| REQ-FN-8 | Validation and canonicalization SHALL NOT mutate the caller's object and SHALL NOT execute input. | T, fuzz I5 |
| REQ-FN-9 | Inline secret material SHALL be refused anywhere in the manifest (`secret.inline`); only `secretref://provider/key[@version]` references are accepted. | T `SecretsTest` |

### 1.1 Canonicalization semantics (MC-05 E03)

- Encoding: UTF-8, no BOM; object keys sorted by code point; separators `,` and `:`; `ensure_ascii=false`.
- The four sections are sorted by the canonical bytes of each entry; order inside extension values is preserved (meaningful).
- Unknown top-level and entry fields (extensions) are **kept and hashed**; they never change validation results except through REQ-FN-9.
- Numbers: JSON numbers as parsed by CPython (`int` arbitrary precision, `float` IEEE-754 binary64); `NaN`/`Infinity` are refused. `1` and `1.0` are different canonical values. Canonical bytes are platform-independent (text, no endianness).
- Unicode: names are restricted to `[A-Za-z0-9._-]`; other strings are **not** normalized (NFC and NFD spellings are different values). Secret scanning applies NFKC internally, never to stored values.
- Schema evolution: a new schema identifier (e.g. `app/v2`) is required for any change that alters the meaning of an existing field; `app/v1` only ever gains optional fields that old validators accept as extensions.

## 2. Deployment tiers (C012)

| Tier | Supported | Required dependencies | Resource ceiling (per process) | Offline assumption | Not supported |
|---|---|---|---|---|---|
| cloud | full API (`service.py`), overlays, activation, audit, telemetry | Python 3.10-3.13; identity issuer; policy source; audit sink | 256 in-flight, 32 per tenant, 1 MiB manifest | identity/policy reachable; cached trust ≤ 300 s | — |
| datacenter | as cloud | as cloud; HSM/KMS for sealed storage if used | as cloud | as cloud | — |
| near-edge | as cloud; activation per site | as cloud; local audit ledger with delayed anchor shipping | 64 in-flight suggested | control plane may be unreachable for hours; §7 | fleet-wide atomic activation |
| far-edge | pure validation/canonicalization (`manifest.py`) and local activation | Python only (stdlib); no network | 16 in-flight suggested; 1 MiB manifest | fully disconnected | authentication of remote submitters without cached trust; new trust establishment |

## 3. Non-functional requirements (C013)

| ID | Requirement | Verify |
|---|---|---|
| REQ-NF-1 | `validate@10` p99 ≤ 5 ms; `parse+validate@100` p99 ≤ 10 ms; `canonical@100` p99 ≤ 10 ms; `parse+validate@5000` p99 ≤ 1 s; invalid@1000 p99 ≤ 150 ms; cold import p50 ≤ 1 s; peak memory for a 5,000-component manifest ≤ 80 MiB. | E `PERF.json`, `PERF_GATE.json` |
| REQ-NF-2 | Availability: the library has no shared state across processes; availability is the host's. Readiness MUST be false when a required dependency is unhealthy. | T `test_status_readiness` |
| REQ-NF-3 | Durability: an acknowledged activation/rollback is fsync'ed to the journal before the call returns. | I `activation.py`, T crash tests |
| REQ-NF-4 | Consistency: per target, activation is linearizable at the COMMIT journal record (§5). | T, E `FAULTS.json` |
| REQ-NF-5 | Determinism: identical inputs SHALL produce identical digests, decisions IDs and gate verdicts. | T |
| REQ-NF-6 | Isolation: §8. | T `TenancyTest`, E `STRESS.json` |

## 4. Outcomes (C014)

Every response carries exactly one `outcome` (`errors.Outcome`):

| Outcome | Meaning | Mapping |
|---|---|---|
| `success` | request completed, effect (if any) committed | no error |
| `partial_success` | reserved: not produced by 4.3.0 operations (all are all-or-nothing) | — |
| `degraded` | completed while a non-critical dependency is down; status is `degraded` | status only |
| `retryable_failure` | nothing committed; the same request MAY succeed later | codes with `retryable=true` |
| `terminal_failure` | nothing committed; retrying the same request will fail | non-retryable 5xx codes |
| `rejected_before_activation` | refused by validation/authn/authz/tenancy/idempotency before any effect | non-retryable 4xx codes |

REQ-OUT-1: no operation SHALL leave a partial effect (adjacent handoff unbinds providers on any failure; activation aborts or rolls forward).

## 5. Lifecycle (C015)

Revision states and legal transitions are `activation.TRANSITIONS`:

| From | To | Guard |
|---|---|---|
| proposed | validated / rejected | full validation of the effective manifest; digest not quarantined |
| validated | prepared / rejected | CAS: `expected_active` equals the active revision |
| prepared | active / aborted | COMMIT journaled within the activation deadline (30 s) |
| active | superseded / rolled_back / quarantined | newer commit / operator rollback / failed health probe |
| superseded | active | only as a rollback target that was once healthy |
| rolled_back | active | operator re-activation of a known-good revision |
| quarantined | validated | only after `reapprove` by an actor other than the original |
| aborted | validated | a fresh attempt re-validates |
| rejected | — | terminal |

REQ-LC-7: after a crash, restart SHALL converge to exactly one documented terminal state: an interrupted PREPARE is ABORTED; a journaled COMMIT is rolled FORWARD. A second restart is a no-op. (T `test_crash_recovery_each_phase`, E `FAULTS.json` f05/f06)

## 6. Capacity, quotas, fairness (C017)

| Dimension | Ceiling | Enforced by |
|---|---|---|
| manifest bytes | 1 MiB encoded | `MAX_MANIFEST_BYTES` (raw path and request envelope) |
| JSON nesting | 64 | `MAX_DEPTH` (raw scan + decoded walk) |
| components / providers | 10,000 each (the byte ceiling binds first at ~7,000 small entries) | `MAX_COMPONENTS`, `MAX_PROVIDERS` |
| links / traits | 50,000 each | `MAX_LINKS`, `MAX_TRAITS` |
| issues returned | 1,000 | `MAX_ISSUES_RETURNED` |
| in-flight requests | 256 per process | `AdmissionController.max_inflight` |
| per-tenant in-flight | 32 | `AdmissionController.per_tenant_max` |
| registry entries | 10,000 per tenant | `TenantRegistry` |
| idempotency keys | 100,000, TTL 24 h | `IdempotencyStore` |
| auth replay cache | 100,000 tokens until expiry | `Authenticator` (full cache refuses, never forgets) |
| audit buffer during sink outage | 1,000 records | `AuditLog.buffer_limit` |

Fairness (REQ-CAP-1): a tenant can never hold more than `per_tenant_max` slots, so no tenant can starve others of the global pool; overflow is rejected immediately with `admission.*` and a `retry_after_ms` hint — nothing is queued (REQ-CAP-2: no unbounded buffering).

## 7. Disconnected and degraded operation (C018, C048, C055, C056)

1. Pure validation/canonicalization is always available locally (stdlib only).
2. Authentication with cached trust material continues for `cache_ttl` (300 s); after that, and for any *new* issuer or key, requests fail with `auth.trust_unavailable` (fail closed).
3. Authorization keeps enforcing the last verified policy; a policy that fails verification is never activated; no policy ⇒ deny everything.
4. **Reconnect after partition (REQ-DIS-4):** the control plane's desired revision wins. A site that diverged locally re-activates the desired digest with CAS; its local revisions stay in history (auditable), never silently merged. (E `STRESS.json` s7)
5. Stale configuration: a site keeps its last active, healthy revision; it never falls back to "no configuration".
6. Reconciliation of running workloads is INV-63's responsibility, not INV-64's.

Service-outage behaviour per trust service: `crypto_policy.OUTAGE_RULES`.

## 8. Isolation (C046)

Isolation profile `inv64-process-v1`: logical isolation in one process. Tenant scope comes from the authenticated principal, never from the manifest; every key (registry, idempotency, cache) is tenant-prefixed; storage paths are hashes; metrics never carry tenant labels. Residual risk: no memory isolation between tenants in one interpreter (REG-005).

## 9. Security outage and time

Tokens are evaluated with ±60 s skew; if the host's clock uncertainty exceeds the skew, the host MUST mark `trusted-time` unavailable, which fails expiry-sensitive decisions closed (`OUTAGE_RULES["trusted-time"]`).

## 10. Precedence of conflicting constraints (C019)

When constraints conflict the outcome is decided in this order, and the decision record names the dominating one (`explain.dominant`):

**security > residency > isolation > capacity > SLO > cost > validity**

Consequences: a valid manifest that violates security policy is refused; a
security control that costs latency (secret scanning, fsync'd audit) stays on
even if an SLO or cost target suffers (REG-004 records the accepted cost); an
unknown/internal error is classified `defect` and pages the owner.

## 11. Versioning and compatibility (C016, C027)

- Package: semantic versioning. Patch = fixes only; minor = additive (new optional fields, new error codes, new capabilities); major = removal or change of meaning of any field, code, capability, schema or protocol.
- Contracts are versioned independently (`PK_APP_*/n`); unknown **request** fields are refused (`request.invalid`), unknown **manifest** fields are extensions (§1.1). Unknown enum values are refused.
- Peer versions: `negotiate` picks the highest common protocol and refuses one that lacks a locally required security feature (`version.downgrade_refused`); no overlap ⇒ `version.unsupported`. Adjacent contracts are checked **before** any semantic call.
- Supported combinations: `compatibility.json` (single source of truth).
