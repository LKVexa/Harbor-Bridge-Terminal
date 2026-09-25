# 01 — Audit of candidate v4.2.0

Map profile: unavailable (yard unreachable). Context graph (RCG): not run (yard office unreachable); findings below are from direct inspection and execution. Static inspection plus tests is not proof of safety.

**What it is.** A stdlib Python package: `engine.py` (`GravityManager.recommend`, residency-first move-compute vs move-data), `contract.py`/`component.py` (pk_core conformance component, 100 checks), 3 JSON Schemas, 14 tests (11 engine + 3 integrity; 2 skipped without `pk_core`). Licence: proprietary (LinearFinance.org), no third-party code.

**What works.** Strict input validation, immutable config snapshot, explicit route costs (no silent 1.0), asymmetric egress, stable reason codes, tie-break to keep data resident.

**Gaps (= the 40 checklist components, grouped).**
- P0: no pk_core pin/handshake; residency, topology, convergence, placement supplied by the caller as plain values (no signature, freshness, binding, provenance); no identity, tenancy, authN/Z; no provenance envelope or tamper-evident audit; no signed config lifecycle; no data-plane handoff; no integration tests.
- P1: no deadlines/cancellation/retry/breaker/admission; no freshness/stale policy; no health, metrics, logs, traces, explain; no fuzz/property/fault/benchmark evidence; no compatibility matrix, SBOM, packaging metadata.
- P2: two-option, money-only model; no partial/replication/DAG/carbon/transfer-time/storage/compat/quota/calibration/shadow/simulation; no runbooks.
- Latent: `pk_core` absence makes the 100-check gate unrunnable (correctly recorded as residual in v4.2.0).
