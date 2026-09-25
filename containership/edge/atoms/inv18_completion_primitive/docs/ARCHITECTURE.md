# INV-18 architecture specification (C012–C019, C021, C032)

Labels: **[S]** source fact (contract.py / README / CHECKLIST), **[O]** observed in code
or measurement, **[D]** implementation decision made in v4.3.0, **[P]** proposal awaiting
owner approval.

## 1. Deployment-context applicability matrix (C012)

The primitive is **process-local** [D]: a future lives in one Python process; it
never spans processes, nodes or sites by itself. Distributed completion is the wire
adapter's job and keeps a single authoritative owner (docs/INTERFACES.md §5).

| Context | Status | Minimum runtime | Threads | Notes |
|---|---|---|---|---|
| local / embedded dev | supported | CPython 3.10 | ≥1 | reference context for CI |
| cloud | supported | CPython 3.10 | ≥1 | no network needed by the core |
| datacenter | supported | CPython 3.10 | ≥1 | same as cloud |
| near-edge | conditionally supported | CPython 3.10 | ≥1 | memory budget per §5 must be configured (`max_outstanding`) |
| far-edge | conditionally supported | CPython 3.10 | ≥1 | power/thermal unmeasured (W-C068); set `max_outstanding` ≤ 10 000 on <256 MB nodes |

Assumptions for every context [D]: a working monotonic clock (only for latency/age
telemetry and stall detection — correctness never depends on time); no storage; no
network; no scheduler beyond OS threads. Offline operation is identical to online
operation for the core. Security controls per context: `network_exposure=none`
(default) everywhere; `mtls` + `auth_required` + `signing_key_ref` mandatory when the wire
adapter is exposed (config.validate enforces). Observability per context: logs and
metrics are in-memory bounded rings; exporters are optional. Test evidence is labelled
with the context via `INV18_CONTEXT` (tools/run_tests.py) and CI emulates `local` and
`cloud` (identical for a process-local primitive); near/far-edge are emulated with a
tight-limit config (`config/site-far-edge.json`).

## 2. Non-functional requirements (C013)

| NFR | Target | Method |
|---|---|---|
| resolve / resolve_error / abandon / take latency (bare) | p50 ≤ 2 µs, p95 ≤ 4 µs, p99 ≤ 8 µs, max ≤ 1 ms [P] | `bench.micro`, 3 000 samples × 5 runs, GC disabled during sampling |
| governed create→resolve→take cycle | p50 ≤ 120 µs, p99 ≤ 800 µs at 1 thread [P] | `bench.runtime_cycle` |
| contention (16 resolvers) | exactly one winner, 0 invariant errors [S] | `bench.contention`, tests/test_future.py |
| throughput (bare cycle, 1 thread) | ≥ 100 000 cycles/s [P] | `bench.throughput` |
| memory | ≤ 2 KB per bare future, ≤ 4.5 KB per governed future [P] | tracemalloc, 5 000 futures |
| import latency | ≤ 100 ms [P] | fresh interpreter subprocess, median of 3 |
| CPU overhead | ≤ 1 CPU-second per 30 000 governed cycles [O] | derived from runtime_cycle |
| availability | N/A — library, not a service; adapters inherit the host service's availability SLO |
| durability | **none** by design: pending futures die with the process [D] |
| consistency | linearizable per future (single lock) [O] |
| isolation | capability + tenant check on every call [D] |
| determinism | same sequence of calls on one thread ⇒ same outcomes and codes [O] |
| lock contention | aggregate throughput must not collapse below 20 % of 1-thread value at 16 threads — **currently violated (DEBT-PERF-01)** |
| resource exhaustion | `RESOURCE_EXHAUSTED` before allocation; no unbounded queue [O] |
| observability overhead | ≤ 50 % of governed cycle [O: telemetry is ~35 % of cycle cost by profile] |
| security-control overhead | capability check ≤ 3 µs [O] |
| platform variance | thresholds re-baselined per CI hardware class; regression gate uses ratios |

## 3. Outcome semantics (C014, C015)

`PARTIAL_SUCCESS` cannot exist: a terminal record holds exactly one value or one error
(proved by tests/test_errors.py::OutcomeMatrixTest). Categories and every code live in
`errors.CODES`; tests/test_errors.py::OutcomeMatrixTest checks this table against it.

| Category | Meaning | Caller retry safe? | Consumes receiver? |
|---|---|---|---|
| SUCCESS | `("ok", v)` or a delivered `("error", msg)` resolution | n/a | yes |
| DEGRADED | component disabled/drained; request refused | yes, later | no |
| RETRYABLE_FAILURE | RESOURCE_EXHAUSTED, DEPENDENCY_UNAVAILABLE, TIMEOUT | yes (adapters with idempotency key) | no |
| TERMINAL_FAILURE | state-machine, auth, version, argument errors | no | no (cancel: yes) |
| ABANDONED | writer dropped | no | yes |

Precedence when several conditions coexist [D, policy `INV18-PREC/1`]:
internal invariant → disabled → authentication → authorization → replay/epoch → version → config → limits →
timeout → state machine → type → argument. `errors.precedence()` implements it.

Lifecycle (C015): see ADR-001 diagram; `Future.state` exposes `PENDING|VALUE|ERROR|ABANDONED|CANCELLED` plus `taken`.

## 4. Versioning (C016)

Semantic Versioning for the package (`VERSION`). Independently versioned contracts:
`PK_FUTURE*/<major>` wire schemas, `PK_FUTURE_ERROR/1`, config `schema_version`.

* API-major: removing/renaming a public name, changing a state transition, changing an exception type or code meaning.
* Schema-major: removing/renaming a field, tightening a type, changing canonical encoding.
* Minor: new optional `ext` members, new error codes, new public helpers.
* Patch: fixes that do not change any documented behaviour.
* Deprecation: announced in CHANGELOG + WAIVERS `deprecations`, window ≥ one minor release and ≥ 90 days.
* Error/status records: fields are never removed within a major; unknown codes map to `UNKNOWN`.
* `pk_core`: integration pinned in `requirements.lock.json` (currently BLOCKED, W-C031).
* Peer policy: N and N-1 majors supported once N-1 exists (today only major 1).
* Enforcement: `tools/api_snapshot.py` compares the public API and schemas with
  `conformance/API_SNAPSHOT.json`; an undeclared difference fails CI unless VERSION's major
  (API break) or minor (addition) changed and CHANGELOG mentions it.

## 5. Capacity, quotas, fairness (C017, C028)

| Limit | Default | Config key |
|---|---|---|
| outstanding futures / process | 100 000 hard, 80 000 soft | `max_outstanding`, `soft_outstanding` |
| outstanding futures / tenant | 10 000 | `max_per_tenant` |
| wire payload | 1 MiB (checked before parsing) | `max_payload_bytes` |
| identifier length | 128 | `max_id_len` |
| metadata/details | 4 KiB, 16 items | `max_metadata_bytes`, errors.MAX_DETAIL_ITEMS |
| error message | 4 096 chars | future.MAX_ERROR_MESSAGE |
| diagnostics ring | 1 024 decisions | `max_diag_records` |
| receivers per future | exactly 1 | structural |
| terminal resolutions | at most 1 | structural |

Memory budget ≈ `max_outstanding × 3.0 KB` (measured) ⇒ ~300 MB at the default hard
limit; far-edge sites must lower it. Admission is checked under the registry lock
before allocation; the only queues are bounded rings. Fairness: none beyond "exactly
one winner" — `threading.Lock` is not FIFO; starvation of a specific producer is
possible in theory but cannot violate correctness; the mixed-workload stress test shows
no starvation in practice (tests/test_perf.py). Hard limits are protected: they change
only through a validated, audited `ConfigStore.activate` by the operator.

## 6. Intermittent / absent network (C018)

The core `Future` needs **no network** [O, verified by tests/test_security.py
AuthorityTest]. Network loss cannot affect its correctness. Only `adapters.py`
introduces a network dependency. For it: a vanished remote producer is detected by
the owner's `abandon` (explicit) or by the receiver's caller-owned deadline
(`take_wait` → TIMEOUT); timeouts belong to the caller; reconnection re-sends with the
same idempotency key (duplicate delivery returns the cached response); stale
completions from a fenced epoch are rejected (STALE_EPOCH); during a partition the
client gets DEPENDENCY_UNAVAILABLE after its bounded retry budget; telemetry is buffered
in bounded rings and dropped (counted) when full; when identity/key/time services are
unavailable the adapter fails closed (docs/SECURITY.md §7).

## 7. Constraint precedence (C019) — policy `INV18-PREC/1`

1. Security & isolation  2. Correctness/consistency (at-most-once, single receiver)
3. Residency (futures never leave their tenant/instance)  4. Availability/SLO
5. Resource/cost.  Forbidden trade-offs: weakening at-most-once for latency; failing open
on authentication; logging payloads for debuggability in prod. Fail-closed cases:
invalid security config, unavailable key/identity/time service, unknown capability.
Degraded (not failed) cases: telemetry sink down, soft limit exceeded, widespread stalls.
Exceptions require approving_authority sign-off via WAIVERS.json. Every rejection writes a
decision record carrying `policy_version` (tests/test_runtime.py::PrecedenceTest).

## 8. Boundary inventory (C021)

| Boundary | Kind | Trust | Auth |
|---|---|---|---|
| `Future` Python API | in-process call | same process | none (object reference is the authority) |
| `Runtime` capability API | in-process call | same process, multi-tenant | capability tokens |
| `adapters.RemoteEndpoint.handle` | RPC (PK_FUTURE*/1 JSON) | remote | HMAC bearer tokens (auth.py) |
| `pk_core` component (`component.py`) | library import | supply chain | pinned digest (blocked) |
| `config/*.json`, `INV18_CFG_*` env | files / env | operator | review + validation |
| `conformance/*.json`, evidence | files | release pipeline | SHA-256 + optional HMAC seal |
| CLI `python -m inv18_completion_primitive` | process | operator | OS account |
No device, hypervisor, WIT or kernel boundary is exposed [O].

## 9. Artifact / configuration / state layout (C032)

| Kind | Location | Mutable at runtime? | Survives restart? |
|---|---|---|---|
| code & schemas | package dir (`*.py`, `schemas/`) | **no** (tested read-only) | yes |
| configuration | `config/*.json` or `INV18_CFG_*` env | via ConfigStore only, in memory | file yes / activation no |
| runtime state (futures, metrics, audit) | process memory | yes | **no** (reconstructable: nothing to reconstruct) |
| evidence | `$INV18_EVIDENCE_DIR` (default `evidence/`) | written by tools only | yes |
| logs/telemetry | sink callback supplied by host | — | host decides |
| secrets | secret store, referenced as `secret://…` | never on disk here | — |

## 10. Unsupported deployment patterns and non-goals (C008)

Source non-goals [S]: carrying many values, retrying the producer, broadcasting to
several receivers, allowing a resolution to be overwritten. Unsupported patterns [D]:

* sharing a `Future` or capability across processes (pickling, `multiprocessing`, `os.fork` after creation);
* durable / persisted futures or replay after restart;
* using a future as a stream or a broadcast channel;
* passing a capability across tenants or runtimes;
* exposing the wire adapter without mTLS + authentication (config refuses it);
* free-threaded (no-GIL) CPython builds — untested;
* more than ~3 threads contending on one `Runtime` in latency-sensitive paths (DEBT-PERF-01).
