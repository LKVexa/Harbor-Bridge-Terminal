# Release, canary, rollback and emergency disable (C092, C096, MC-28)

## Release checklist (all must be attached to the release record)
1. `python tools/run_gate.py` → `evidence/gate_result.json` verdict **GO** (no FAIL, no BLOCKED, zero unexplained skips).
2. Evidence bundle `evidence/evidence_bundle.jsonl` + signature verified (`python tools/run_gate.py --verify`).
3. Compatibility matrix `evidence/compat_matrix.json`: every claimed cell FULLY_SUPPORTED from this revision.
4. Security results: `tests/test_security_observability.py`, `tests/test_fuzz_adversarial.py` in the bundle.
5. Performance: `evidence/bench.json` decision PASS against `evidence/perf_baseline.json` on equivalent hardware.
6. SBOM `evidence/sbom.cdx.json`; signed `evidence/release_manifest.json` verifying (`tools/supply_chain.py verify`).
7. Production-exit record (`evidence/production_exit_record.json`) countersigned by the release approver.

## Canary
- Population: 1% of nodes per site, at least one node per supported cell, never all nodes of one tenant.
- Minimum duration: 24 h and at least one daily peak.
- Watched: `inv19_errors_total` rate, `inv19_untranslatable_errors_total`, `inv19_fallback_engagements_total`, `inv19_reap_latency_seconds` p99, `inv19_backend_health`.
- Automatic abort: error rate > 2× control; any untranslatable error; fallback rate > 1% where a fast path is expected; reap p99 > 1 ms or > 25% above control.
- Rollback command: redeploy the previous signed manifest (`release_manifest.json` of the last GO), then `config rollback` (`ConfigStore.rollback`).

## Rollback
- Previous known-good: the last release whose gate result was GO (none yet — first GO pending).
- Config rollback: `ConfigStore.rollback(actor)` restores the prior validated config (tested: `tests/test_contracts.py::ConfigTest`).
- Package rollback: reinstall the previous manifest's artifacts; `supply_chain.py verify` must pass.
- Emergency backend disable: set `backends.disabled` (dynamic) or `AsyncHost.quarantine(<backend>)`; portable cannot be disabled.
- Rollback in staging: **BLOCKED** — no staging environment is available to this repository; record evidence under `evidence/rollback/` when performed.

## Day-0 / Day-1 / Day-2
- Day 0: install; `python tools/pk_core_preflight.py` (must be GO for the pk_core gate); `python -c "from inv19_os_asynchronous_analogues.hostio.capabilities import *; print(snapshot(detect(), choose(detect())))"`.
- Day 1: run the full gate; deploy canary; watch the dashboard (alert rules in `hostio/observability.py`).
- Day 2: re-run gate on every change; `AsyncHost.snapshot()` for health/version/config/backend; explain view `AsyncHost.decisions.explain()`.
