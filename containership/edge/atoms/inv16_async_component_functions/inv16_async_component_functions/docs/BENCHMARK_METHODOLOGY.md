# Bridge-cost benchmark methodology (SLO: p99 sync-caller bridging < 5 µs, 1% budget)

* **Measured interval.** Bridge cost = `SyncBridge.call` wall time minus the direct async path
  (`invoke` + `complete`) for an immediately-completing callee. Gate metric: `p99(bridged) − p99(direct)`
  over ≥100k samples each; the per-sample paired difference p99 is also reported (conservative, noise-inflated).
* **Timer.** `time.perf_counter_ns`; the null path is measured to expose timer + loop overhead.
* **Controls.** One warm process, 10k warm-up iterations, GC disabled during sampling, environment manifest
  (interpreter, platform, CPU count, affinity, `-O`) recorded. Pin CPU/frequency on the certified host.
* **Also reported.** Suspended bridge (completion from another thread) — dominated by OS thread wake-up,
  outside the SLO definition but needed for capacity planning.
* **Raw data.** `evidence/bench/bridge.raw.json` holds every sample for independent recomputation.
* **Gate.** `python bench/bridge_bench.py --gate` exits 3 when the SLO fails. A failing result must be fixed
  or the contract SLO revised through governance — never ignored.
* **Scope caveat.** This Python model is not the certified production runtime; its numbers bound the model,
  not the native implementation.
