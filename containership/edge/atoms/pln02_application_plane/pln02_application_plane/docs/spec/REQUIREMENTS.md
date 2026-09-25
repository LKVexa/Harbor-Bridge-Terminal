# PLN-02 Application Plane — Normative Requirements Specification

**Spec id:** PLN02-SPEC/1 · **Package:** 4.3.0 · **Status:** Draft for approval (see ADR-PLN02-001)
**Closes:** MC-03 (C011–C015). Keywords SHALL / SHOULD / MAY per RFC 2119.

Every requirement has an `AP-REQ-nnn` id. `TRACEABILITY.json` links each id to code, tests and evidence.

## 1. Source function (C011)

The source function is *"OAM/WIT-based application definitions and portable components."* v4.3 honours it
to the exact extent below, and no further:

| Source clause | Implemented as | Limit |
|---|---|---|
| OAM application definitions | `oam.translate()` | `core.oam.dev/v1beta1` `Application` subset; traits `pk.capabilities`, `pk.interfaces`, `pk.bindings`; policy `pk.constraints`. All other traits/policies/workflow **refused**. |
| WIT interface contracts | `wit.parse()`, `wit.check_compatible()` | WIT text subset (records, enums, variants, flags, aliases, funcs, worlds). `resource`, `use`, `include`, handles, gates **refused**. |
| Portable components | `PK_APPLICATION/1` component model | Components are composition units; execution belongs to PLN-03. |

## 2. Functional requirements (C012)

| Id | Requirement | Contexts |
|---|---|---|
| AP-REQ-001 | The plane SHALL resolve every *required* capability of every component to exactly one provider, or refuse with `UNSATISFIED_CAPABILITY` / `NO_ELIGIBLE_PROVIDER`. | all |
| AP-REQ-002 | The plane SHALL drop an *optional* capability that has no eligible provider and SHALL record it in `dropped_optional`. | all |
| AP-REQ-003 | Every declared import SHALL be bound by exactly one edge from a producer exporting the same interface at a compatible version. | all |
| AP-REQ-004 | Revision identity SHALL be the full SHA-256 of the canonical normalized semantic content; identical semantics SHALL yield identical identity regardless of input order. | all |
| AP-REQ-005 | A published revision SHALL NOT be mutated; it MAY only be superseded, quarantined or rolled back to. | all |
| AP-REQ-006 | Provider selection SHALL follow the fixed precedence `security > residency > consistency > slo > locality > cost`; soft constraints SHALL NOT admit a hard-rejected candidate. | all |
| AP-REQ-007 | Every selection SHALL produce an explain record (chosen, eligible, rejected with reason, policy version). | all |
| AP-REQ-008 | Catalogues SHALL be signed, scope-bound (environment + site), generation-monotonic and fresh. | all |
| AP-REQ-009 | Near-edge and far-edge sites MAY resolve from a cached signed catalogue only under a live autonomy lease and within `max_offline_seconds`; the result SHALL be marked degraded. | near-edge, far-edge |
| AP-REQ-010 | Datacenter and cloud deployments SHALL run with `max_offline_seconds` ≤ 3600 unless an approved exception exists. | cloud, datacenter |
| AP-REQ-011 | Callers SHALL be authenticated; tenants SHALL be entitled to every capability they request. | all |
| AP-REQ-012 | Publication SHALL be fenced by an epoch; a stale controller SHALL NOT publish. | all |
| AP-REQ-013 | Operators SHALL be able to freeze a scope, disable the plane, and quarantine a revision; each action SHALL be audited. | all |
| AP-REQ-014 | Security-relevant actions and refusals SHALL be written to a tamper-evident audit ledger. | all |
| AP-REQ-015 | OAM and WIT inputs outside the supported subset SHALL be refused, never partially interpreted. | all |

## 3. Non-functional requirements (C013)

| Id | Dimension | Requirement | Evidence |
|---|---|---|---|
| AP-REQ-101 | Latency | p99 resolution < 500 ms at 200 components (contract SLO). | `evidence/perf_baseline.json` |
| AP-REQ-102 | Latency | p99 full submit path < 250 ms at 20 components on reference host. | same |
| AP-REQ-103 | Availability | Readiness SHALL report `fail` when the catalogue is stale without lease, the store is disabled, or an operation stalls. | tests MC06/MC24 |
| AP-REQ-104 | Durability | Revision, head and control writes SHALL be atomic (tmp + fsync + rename); restart SHALL remove partial writes and quarantine corrupt revisions. | test_crash_leftovers… |
| AP-REQ-105 | Consistency | Single fenced writer per store root. Multi-process writers SHALL use an external lock/lease service (deployment requirement). | ISOLATION_PROFILE |
| AP-REQ-106 | Isolation | Tenant scope SHALL partition store paths, admission buckets, metrics labels and entitlements. | tests |
| AP-REQ-107 | Bounds | Every input collection, parser depth, cache and retained history SHALL be bounded (see §6). | code constants |
| AP-REQ-108 | Confidentiality | Errors, logs and metrics SHALL NOT contain secrets, keys, raw policy or principal tokens. | MC14/MC18/MC30 tests |

## 4. Outcome semantics (C014)

| Outcome | Meaning | Wire signal | Caller action |
|---|---|---|---|
| **Success** | Revision resolved, published, audited. | `ok: true` | Use `publication.revision`. |
| **Partial success** | Success with ≥1 optional capability dropped. | `ok: true`, non-empty `revision.dropped_optional` | Accept or re-submit when providers exist. |
| **Degraded** | Success using an offline cached catalogue under lease. | `ok: true`, `provenance.catalogue_degraded: true` | Re-resolve after reconnect. |
| **Retryable failure** | Transient dependency/capacity condition. | `PK_ERROR/1` with `retryable` = `safe` or `after_backoff` | Retry with backoff, same idempotency key. |
| **Terminal failure** | Input, policy, auth or integrity refusal. | `retryable: "never"` | Fix input/policy; do not retry. |

## 5. Lifecycle (C015)

Revision states and the only legal transitions (enforced by `store.py`):

```
 (submitted) ──resolve──▶ REJECTED            [terminal, not stored]
      │
      └──resolve+publish──▶ CURRENT ──publish(newer)──▶ SUPERSEDED
                              │   ▲                        │
                              │   └────────rollback────────┘
                              ├──quarantine──▶ QUARANTINED ──release──▶ (previous state)
                              └──(corrupt on read/restart)──▶ QUARANTINED
```

Plane states: `ENABLED ⇄ DISABLED` (admin), scope `OPEN ⇄ FROZEN` (admin). All admin transitions require the
`plane-admin` role and the current fencing epoch, and are audited.

## 6. Limits

200 components · 4 096 edges · 4 096 catalogue entries · 64 candidates per capability · 128 capabilities and
128 imports/exports per component · 1 MiB request payload (configurable 1 KiB–16 MiB) · WIT source 256 KiB,
type depth 32 · token TTL ≤ 900 s · idempotency cache 10 000 · metric series 2 000 per metric · revision history 1 000.
