# Changelog - GAP-12

## 4.3.0 - 2026-09-22

Application of the GAP-12 Professional Engineering Checklist v4.2.0 (116 components / 2,420 sub-checks).

### Behaviour changes to v4.2.0 code
- `path.Path.retry_delay()` keeps millisecond resolution with a 0.5 s floor. v4.2.0 rounded up to whole seconds
  with a 1 s floor, so the first retry of every peer landed at exactly failure + 1 s: a 10,000-peer simulation put
  100 % of the fleet in one instant. Now the worst 10 ms window holds 2.3 % of the fleet. Two assertions in
  `tests/test_path.py` that pinned the old integer value were updated (commented in place).
- `__init__.py` no longer imports `pk_core` eagerly: the package (and `path.py`) import without the framework;
  `COMPONENT`/contract symbols resolve lazily. `VERSION` 4.3.0 (`tests/test_component.py` updated to match).

### Added
- `wan/` stdlib runtime (A-G groups), `wan/controller.py` integration, `wan/contracts.py`.
- `lab/` network-namespace NAT lab: veth over raw rtnetlink, netfilter NAT profiles (EIM/APDF, APDM, EIM/EIF,
  double NAT, UDP-blocked, 30 % loss), AF_PACKET pcap capture, 11 scenarios incl. end-to-end direct -> hole-punch
  and direct -> hole-punch -> relay through real NAT.
- `tests/` 130 new tests with per-sub-check coverage tags; `evidence/` runner with line coverage, benchmarks,
  fuzz regression corpus, the 2,420-item evaluator, waiver rules and the CI gate; `ops/` build/SBOM/CI/docs tools;
  `docs/` component documents, ADRs, threat models, runbooks, incident/compatibility/backup documents.

### Defects found and fixed during this pass (by its own lab, fuzzers, benchmarks and validators)
- STUN client discarded RFC 5780 CHANGE-REQUEST answers from the alternate address -> full-cone NAT was
  misclassified as port-restricted (lab).
- CGNAT assessment ignored "gateway WAN address differs from the mapped address" unless the WAN address was private (lab).
- Hole punching failed through Linux MASQUERADE: the first inbound probe created a conntrack entry that forced the
  peer's own mapping onto another port; fixed with low-TTL priming (lab).
- Config validator crashed on type-invalid documents (fuzzer, 20 crashers kept as regressions).
- DNS decoder raised `struct.error` on truncated questions (fuzzer).
- DNS resolver deadlines followed the injectable clock and could hang under a frozen test clock.
- Event-log repeat suppression grew one entry per peer without bound (benchmark heap).
- ICE recomputed SHA-256 foundations inside sort/loop (31.7 ms -> 1.6 ms per 32x32 agent).
- PathStore deep-copied the path on every transition (200 us -> 7 us).
- Benchmark timings were taken under tracemalloc (4-5x inflation); timing and heap are now separate runs, budgets unchanged.
- 60 coverage tags claimed sub-check kinds their component does not have (evaluator refused them; re-tagged).
- Kill-switch controls outside the node's scope were not audited; the controller reported NET_UNREACHABLE when it
  made no attempt inside a backoff window (new reason `BUDGET_BACKOFF_ACTIVE`).

## 4.2.0 - 2026-09-22

Audit, correctness, hardening, and evidence-alignment pass.

### Correctness fixes

- Fixed exponential backoff off-by-one: the first exhausted round now waits `BACKOFF_BASE` rather than `BACKOFF_BASE * BACKOFF_FACTOR`.
- Added bounded per-path retry jitter, satisfying the checklist requirement that safe retries use backoff **and jitter**.
- New paths are now `unknown` rather than incorrectly reported `partitioned` before any strategy has been tested.
- A stale successful probe is distinct from a confirmed partition.
- Future-dated success evidence no longer counts as healthy.
- Probe/plugin exceptions no longer abort the entire escalation chain; the exception type is recorded and the next strategy is tried.
- Attempt history now records `success`, `failure`, or sanitized `error` outcomes, not only strategy/timestamp.
- Implemented relay-byte accounting that had been declared by the contract but absent from the code.
- Added `retry_at`, `retry_in`, failure count, status, and sanitized last-error fields to path state.

### Security / hardening

- Validates peer identifiers, callable probers, non-negative finite time values, and relay byte counts.
- Does not persist exception messages from probe backends, reducing accidental secret/endpoint leakage into diagnostics.
- Keeps retry history strictly bounded.
- Retains `Exception`-only catch scope so process-control exceptions (`KeyboardInterrupt`, `SystemExit`) are not swallowed.
- Contract now explicitly requires jitter, attempt outcomes, sanitized diagnostics, and accurate unknown/stale/partitioned state.

### Architecture / test hardening

- Moved the networking state machine to dependency-free `path.py`, separating it from the `pk_core` evidence adapter.
- Corrected checklist evidence indexing: resilience behavior is no longer written into unrelated implementation/configuration checklist slots.
- Added 10 standalone stdlib tests covering path state transitions and failure behavior.
- Updated framework conformance version pin to 4.2.0.
- Corrected README claims about files that were not actually present and documented the package as a reference-control component rather than a complete NAT traversal stack.
- Added `AUDIT_REPORT.md` and `MISSING_COMPONENTS.md`.

### Validation in audit sandbox

- `python -m compileall`: PASS.
- `tests/test_path.py`: 10/10 PASS.
- `tests/test_component.py`: SKIPPED because the uploaded package does not include the external `pk_core` dependency. The skip is not counted as production evidence.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

- Replaced bare behavioral `assert` usage with optimizer-safe verification.
- Enforced the retry window after exhausted rounds.
- Cleared stale success evidence after complete strategy exhaustion.
- Bounded attempt history.
- Capped exponential growth.
- Added conformance test, `VERSION`, and `__version__`.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
