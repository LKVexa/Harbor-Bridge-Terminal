# Migration 4.2.0 → 4.3.0

- **No breaking changes.** `capabilities.py`, `discovery.py`, `component.py`, `contract.py` and the four v1 schemas are unchanged; `discover()` behaves as before.
- New, opt-in: `gap02_hardware_capability_discovery.production`. Consumers wanting signed reports use `production.envelope.seal/open_envelope` (schema `PK_SIGNED_CAPABILITIES/1`) and must supply a GAP-07 `Signer`/`Verifier`, a GAP-06 identity, a `TrustedClock` and a `ReplayGuard`.
- Capability names added by the production probes are namespaced (`cpu.x86.avx2`, `gpu.compute.nvidia`, `cc.sev-snp.attested`, …). The 4.2 names (`cpu`, `gpu`, `npu`, `tpm`, …) are still produced by `discovery.report_from_inventory`.
- Config: `GAP02_PROBE_CONFIG/1`; unknown keys are errors; only `interval_seconds`, `probe_timeout_seconds`, `max_concurrency`, `log_level` may be overridden via `GAP02_*` env vars.
