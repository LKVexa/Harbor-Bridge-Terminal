# GAP-12 - WAN resilience and NAT traversal

**Version:** 4.3.0 (from the audited/hardened 4.2.0 candidate)
**Group:** 04_Gap_Subsystems · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklist applied:** GAP-12 WAN Resilience & NAT Traversal Professional Engineering Checklist v4.2.0 — 116 components, 2,420 sub-checks (`evidence/GAP12_CHECKLIST_v4.2.0.md`)

## What this is

v4.2.0 was a hardened path-selection state machine (`path.py`) with no networking. v4.3.0 keeps that
machine and its `pk_core` adapter (`component.py`, `contract.py`, `CHECKLIST.json` unchanged) and adds a
standard-library runtime under `wan/` that implements, tests and measures the checklist's components:

| Area | Modules |
|---|---|
| A. Traversal | `wan/stun.py` (RFC 8489/5780 client+server), `wan/turn.py` (RFC 8656 client+relay), `wan/ice.py` (RFC 8445), `wan/holepunch.py`, `wan/natclass.py` (RFC 4787/5780/6598/6052/7050), `wan/portmap.py` (PCP/NAT-PMP/UPnP guards), `wan/transport.py` (TCP, Happy Eyeballs v2, TLS; QUIC explicitly unsupported) |
| B. Network | `wan/netenv.py` (snapshot, route watcher, debounce, multi-WAN, pinning, captive, firewall diagnosis, PLPMTUD, MSS), `wan/dns.py` |
| C. Quality | `wan/quality.py` (hard deadlines, probe scheduling, RTT/loss/jitter, bandwidth, hysteresis scoring, keepalive, resumption, caches, relay quota + automatic byte instrumentation, multipath, prediction) |
| D. Trust | `wan/security.py` (GAP-06 trust gate, AES-GCM E2E channel, replay window, TURN credentials, tenancy, rate limits, breaker + shared retry budget, egress policy, secrets, redaction, anomalies, hash-chained audit) |
| E. State | `wan/state.py` (lock-owned PathStore, atomic/idempotent transitions, durable snapshots, clocks, supervision, dependency health, degraded policy, quarantine, fencing, migration) |
| F. Config | `wan/config.py` (schema -> generated docs/fixtures, fail-closed validation, overlays, atomic apply/rollback, provenance, flags) |
| G. Observability | `wan/obs.py`, `wan/reasons.py` (metrics, structured events, tracing, /livez /readyz /metrics, explain view, generated dashboard + burn-rate alerts) |
| Integration | `wan/controller.py` wires the v4.2.0 `Path` to adapters behind every policy gate |
| H. Certification | `tests/` (143 tests), `lab/` (kernel network-namespace NAT lab with pcaps), `evidence/` (runner, benchmarks, evaluator) |
| I. Release | `pyproject.toml`, `ops/build.py` (reproducible), `ops/sbom.py`, `ops/ci.sh`, `wan/rollout.py` (canary + kill switch), `docs/` runbooks/matrices, `ops/waivers.json` |

## Result (this build)

`evidence/out/STATUS.md` and `evidence/out/evaluation.json` hold the per-item verdicts.

- **615 PASS · 1,805 NOT-EVIDENCED · 0 FAIL · 0 WAIVED** of 2,420 sub-checks.
- **0 of 116 component exit gates pass; production gate NO-GO.** Every component still needs named owners and a security review (human decisions), and the environment cannot provide IPv6/NAT64, independent STUN/TURN implementations, tc/netem impairment, a signing identity or a vulnerability scanner.
- Tests 140 PASS / 3 SKIP (the `pk_core` conformance tests; `pk_core` is not in this package). Lab 11/11 scenarios through real netfilter NAT. 17/17 benchmarks inside their proposed budgets. Two builds byte-identical.

## Running

```text
bash ops/ci.sh                         # everything: tests, lab (root), bench, build, SBOM, evaluation
python3 -B evidence/run_tests.py       # tests + coverage -> evidence/out/test_results.json
sudo python3 -B lab/scenarios.py       # kernel NAT lab (Linux, root, iptables) -> evidence/out/lab/
python3 -B evidence/evaluate.py        # all 2,420 verdicts -> evidence/out/evaluation.json
python3 gap12_wan_resilience_and_nat_traversal/tests/test_path.py   # the v4.2.0 standalone tests
```

The package imports without `pk_core` (v4.2.0 did not); `COMPONENT` resolves lazily when `pk_core` is present.

## Integration contract

Unchanged from 4.2.0 (`connect(prober, now)`, `state(now)` -> `PK_PATH_STATE/1`, `record_relay_bytes`), plus
`wan.contracts` for `PK_PATH_REQUEST/1`, `PK_BACKOFF/1` and `PK_RELAY_ACCOUNTING/1`. One behaviour change:
`Path.retry_delay()` now returns seconds with millisecond resolution (0.5 s floor) instead of whole seconds — see CHANGELOG.
