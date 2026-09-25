# INV-61 v4.2.0 → 4.3.0 — Missing-Components Checklist Execution Report

**Workflow executed:** *INV-61 v4.2.0 Missing Components — Professional Engineering Completion Checklist* (M01–M32)
**Candidate:** `inv61_distributed_wit_rpc_v4.2.0_hardened.zip` → released as 4.3.0
**Date:** 2026-09-22/23 · **Environment:** 2-vCPU x86-64 Linux container, CPython 3.10–3.13, OpenSSL CLI, no network package index

## Result in one paragraph

All 32 missing components now have an in-repository implementation, a normative document or both, with machine evidence where the environment allowed it. The suite grew from 11 to **107 tests** (104 pass, 3 skipped for the absent `pk_core`) and passes on **CPython 3.10, 3.11, 3.12 and 3.13, both normal and `-O`** (8/8 configurations). A byte-reproducible wheel, SBOM, provenance and checksums are generated and verified; the bootstrap installs from an empty prefix and passes its self-check. All performance gates pass. **The exit gate verdict is `NO_GO`.** No code gate fails. It is `NO_GO` for two governance reasons: `pk_core` is missing (3 skips, which the checklist does not allow), and none of the 12 waivers has a named owner or approver yet. Nobody was assigned to those roles, because the archive contains no ownership information and none was made up.

Following the checklist's own rule ("a checkbox may be marked complete only when an implementation artifact **and** objective evidence exist"), the ledger below uses three states instead of ticking boxes:

* **DONE**: implemented, and every Definition-of-Done gate that can be run from this repository has evidence.
* **PARTIAL**: implemented, but at least one DoD gate needs something outside this repository. The waiver ID names what is missing.
* **BLOCKED**: cannot proceed without an external input.

## Cross-Component Completion Ledger

| M | Component | State | Implementation | Evidence | Open (waiver) |
|---|---|---|---|---|---|
| M01 | `pk_core` dependency & manifest | **BLOCKED** | Lazy import, `require_pk_core()` symbol/version check with actionable error, `pyproject.toml` `gate` extra pinned `pk_core==4.0.*`, runtime decoupled | Protocol suite runs without it; 3 gate tests report *skipped* (never passed) | Artifact, index, digest, owner, clean-env CI (W-002) |
| M02 | `MASTER.md` | **DONE** (superseded) | ADR-0002: `CHECKLIST.json` authoritative; loss record; generated `TRACEABILITY.json` | `test_traceability` (100 unique sequential IDs, bidirectional trace, freshness, README claims) | Original not recoverable from the archive (W-003) |
| M03 | Cross-host transport | **PARTIAL** | `transport.py`: TCP+mTLS, HELLO, conn cap, accept bucket, handshake/idle timeouts, header-before-alloc, multiplexing, CANCEL, drain, reconnect | Real-socket loopback, **two-OS-process** test, hostile-bytes, slowloris, conn cap, drain | Two-host/netns run not executed (`ci/netns_two_host.sh` ready; container has no `ip`) (W-010); no independent peer (W-005) |
| M04 | WIT parser & canonical wire codec | **PARTIAL** | `wit_model.py` (strict subset, digest), `codec.py` (canonical values, NaN canonicalisation, limits, `PK_WRPC_FRAME/2`) | Parser rejections, round-trips, 1 500 property cases, 4 000 mutation-fuzz cases, 3 000 random-envelope cases, corpus, golden fixtures + drift check | Not wire-compatible with Bytecode Alliance `wrpc`/canonical ABI (W-005) |
| M05 | Negotiation & compatibility matrix | **DONE** | `negotiation.py`, `COMPAT_MATRIX.json` | Choose/refuse, downgrade detection, 2.0 fallback over sockets, matrix-vs-code consistency | — |
| M06 | Peer authentication | **DONE** | Key ring (≥256-bit, windows, rotation, revocation), HMAC envelope, TLS-CN binding, handshake key check | Tamper, unknown/revoked/expired key, spoofed sender, CN mismatch, no-cert and plaintext-vs-TLS clients | — |
| M07 | Authorization / capabilities | **DONE** | Default-deny `Policy`, deny-wins, tenant/interface/function scope, expiry, audited denies | `AuthzTest`, `ExplainTest` | — |
| M08 | Encryption & key lifecycle | **PARTIAL** | TLS 1.3-only mTLS contexts, rotation with overlap, fail-closed on key/cert load failure (ADR-0004) | `TlsTest`, rotation/revocation tests | At-rest encryption of `state.json` delegated to host volume (W-004) |
| M09 | Replay / spoofing / request identity | **DONE** | Request ID, sender, nonce, issue time, MAC; bounded replay cache sized to window+skew; restart-safe (`issued-before-boot`) | Replay, stale, future-skew, weak nonce, restart replay, cache-full → retryable shed | — |
| M10 | Cancellation / idempotency / retry / reconnect | **DONE** | Tokens + CANCEL frames, idempotency cache (conflict detection, durable), full-jitter retry only for keyed calls, reconnect, ambiguous-completion signalling | Cancel over sockets, server restart + reconnect, non-keyed call not retried, duplicate race → 1 execution | — |
| M11 | Backpressure / admission / breakers | **DONE** | Global + per-tenant ceilings, token buckets, tenant-table cap, per-function breaker (single half-open probe), conn caps | Unit tests + 64-caller overload over sockets (8 admitted, 56 shed in 76 ms) | — |
| M12 | Configuration & provenance | **DONE** | Schema, overlays, secret refs only, immutable keys, provenance, atomic activate/rollback with change hook | `ConfigTest` | — |
| M13 | Tamper-evident audit | **DONE** | HMAC-chained JSONL, fsync, verify, anchored head in checkpoint, refuse-to-start on broken chain | Edit/delete/truncate detection, 800 concurrent appends, explain tool refuses a tampered log | WORM storage is host responsibility (documented) |
| M14 | Health / readiness | **DONE** | Liveness with stall detection; readiness with dependencies, drain, disable, version, config digest, capabilities | `test_health`, drain/disable tests | — |
| M15 | Metrics exporter | **PARTIAL** | Prometheus text exposition, histograms, series cap, alert rules, dashboard | Render/cardinality tests | Scrape endpoint wiring and live dashboards not deployed (W-012) |
| M16 | Structured logging | **DONE** | `inv61-log/1` JSON schema, recursive redaction, size cap, failure-isolated sink | Redaction, schema and secret-leak tests | — |
| M17 | Trace propagation | **DONE** | W3C `traceparent` strict parse, child spans, sampling, attribute allow-list, bounded buffer | Parse/propagate-through-service tests | OTLP exporter not included (allow-list governs export) |
| M18 | Telemetry policy | **DONE** | `docs/TELEMETRY_POLICY.md` + `TelemetryPolicy` checks | Policy/allow-list tests | — |
| M19 | Failover / split-brain / duplicate execution | **PARTIAL** | Leases + monotonic fencing, mutating calls fenced, quarantine via disable (ADR-0003) | Split-brain, zombie-owner and fenced-mutation tests | Needs a linearizable lease store (W-007) |
| M20 | Durable restart / replay | **DONE** | State inventory; atomic, digest-checked checkpoint (idempotency, epochs, audit anchor, disable flag) | Restart preserves no-duplicate execution, disable and epoch; corrupt checkpoint refused | — |
| M21 | Requirements & traceability | **DONE** | `docs/REQUIREMENTS.md` (39 RQ, SHALL-level, taxonomy, precedence, NFRs); `TRACEABILITY.json` for C001–C100 | `build_traceability.py --check` in the test suite: missing artifact, test, requirement or waiver fails it | — |
| M22 | Owner / escalation / ADR | **BLOCKED** | Escalation structure and four ADRs written (status *Proposed*) | — | No owner or approver identifiable (W-001) |
| M23 | Security architecture & adversarial suite | **PARTIAL** | STRIDE threat model T01–T18, trust-boundary diagram, 14 abuse-case tests plus TLS/replay suites | `AdversarialSuite` etc. | Side-channel tests (W-008); external security review (W-001) |
| M24 | Fuzzing & property tests | **PARTIAL** | Seeded property generator, mutation fuzzer, envelope random fuzz, regression corpus | 8 500 generated cases per run, deterministic seed | Coverage-guided fuzzing (e.g. Atheris) not available offline (W-010) |
| M25 | Concurrency & races | **DONE** | Thread-safe counters and all shared structures | 16 000-call counter exactness, idempotent race, slot-leak check, register-during-dispatch, concurrent audit | Free-threaded CPython not tested |
| M26 | Adjacent-layer integration | **PARTIAL** | Contract-exact stubs for INV-11/60/65/36 | `AdjacentLayerTest` | Real siblings not in archive (W-006) |
| M27 | Cross-runtime certification | **PARTIAL** | Runtime matrix tool; CI workflow for 4 OS × 4 Pythons | `evidence/runtime_matrix.json`: 8/8 pass | Windows, macOS, aarch64 and Wasm hosts not executed (W-010) |
| M28 | Performance / capacity / power | **PARTIAL** | Reproducible bench (7 scenarios), thresholds, perf gate, capacity model | `evidence/bench_results.json`, `perf_gate.json`: all 9 gates pass | Fleet-scale and power not measured (W-010) |
| M29 | Fault / soak / disaster | **PARTIAL** | Server loss mid-call, restart+reconnect, overload, drain, conn cap, slowloris, 60 s soak | 121 013 calls, 0 errors, RSS plateau | 24 h soak, partitions across hosts (W-010) |
| M30 | Supply chain / SBOM | **PARTIAL** | CycloneDX SBOM, SLSA-style provenance, manifest with source digests, SHA256SUMS, verifier, hash-pinned install | Reproducible wheel (identical digest from 3.12 and 3.13 builds), tamper detection | No signing identity (W-011) |
| M31 | Packaging / bootstrap | **DONE** | Stdlib PEP 427 wheel builder, `bootstrap.sh` (verify, hash-pinned venv install, config validation, self-check, rollback), systemd unit, Dockerfile | `PackagingTest` installs from an empty prefix and passes `inv61-selfcheck` | Container base digest pin (W-011) |
| M32 | Operations / release / governance | **PARTIAL** | SLOs/budgets, canary/staged rollout, rollback, emergency disable, runbooks, incident severities, CVE/EOL SLAs, review cadence, waiver register, exit-gate tool | `evidence/EXIT_GATE.json` | Approvals and owners (W-001) |

**Totals:** 17 DONE · 13 PARTIAL · 2 BLOCKED. Traceability over C001–C100: 62 implemented · 16 documented · 20 partial · 2 external.

## Defects found and fixed while executing the workflow

1. **Response-encoding crash path:** when argument limits were tighter than the envelope's own field sizes, encoding the response raised out of `handle()`. Envelope limits and argument limits are now separate, with a fallback `internal` response that always fits (AC-13).
2. **Replay across restart:** the in-memory nonce cache was empty after a restart, so a captured frame could be replayed. Frames issued at or before process boot are now refused. A flaky test exposed a same-millisecond edge case, which was also closed.
3. **Replay-cache capacity under sustained load:** the 60 s soak produced **27 504 false `replay` rejections**. Nonces were being kept for 2× the window, and a full cache reported itself as an attack. Retention is now the window plus a bounded future skew, the cache is sized for that, and a full cache sheds as retryable `overloaded`. The soak now shows 0 errors.
4. **Framing performance:** the codec was reworked (cached record plans, a `bytes` reader). The pipeline gained an `inline` export mode. In-process pipeline p50 dropped from 185 µs to 76 µs, and the p99 framing-overhead SLO is met (43 µs against a 50 µs budget).

## Measured performance (reference container)

| Scenario | p50 | p99 | Other |
|---|---|---|---|
| Framing (envelope encode+decode), SLO < 50 µs p99 | 16.3 µs | 43.2 µs | pass, but close to the limit: this 2-vCPU host has measured 47–51 µs on noisy runs |
| Full in-process pipeline (inline callee) | 75.9 µs | 132 µs | — |
| Loopback TCP, sequential | 341 µs | 878 µs | 2 694 calls/s |
| Loopback, 32 concurrent callers on one connection | 15.8 ms | 31.7 ms | 1 930 calls/s: the thread-per-request model is the scaling limit (ADR-0001) |
| Per-tenant fairness (8 tenants) | — | spread 1.15× | — |
| Soak 60 s | — | — | 121 013 calls, 0 errors, second-half RSS growth 7.4 MB (bounded caches filling) |

## What was deliberately not done

* No owner, approver, licence, `pk_core` artifact or `MASTER.md` content was invented.
* ADRs are marked *Proposed*, not approved.
* The exit-gate tool records evidence. It never approves a release.
* The chop-shop yard ledger was not updated. The candidate came in as an upload, and the session had no shell on the machine that holds the yard.
