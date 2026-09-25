# GAP-14 v4.3.0 — Residual Components Register

Supersedes the v4.2.0 register. v4.3.0 implemented GAP-14's side of all 40 v4.2.0 residual components; this register lists what is still missing. The authoritative per-item view is `CERTIFICATION_MANIFEST.json` (102 open, 346 partial, 161 external of 1,831).

## Blocking production certification (P0)

1. **Certified `pk_core`**: install, record its digest in `compat.PKCORE_PIN`, run the 100-check gate at min/max/pinned versions (G14-P0-01 E01/G01/G02).
2. **Live estate integration**: GAP-13, GAP-03, GAP-05, SCH-01, PLN-06 implementing the v4.3.0 wire schemas and keys in the estate KMS; run `tests/test_p0_evidence_config_gate.py::EstateIntegrationTest` scenarios against them (P0-12 G01).
3. **Asymmetric signatures** replacing HMAC via the `Verifier` protocol (DESIGN R-1).
4. **Richer convergence proof** (replica set, epoch, consistency mode, nuanced states) — P0-04 A05/A08/A10, E03.
5. **PLN-06 execution lifecycle and completion attestation** — P0-06 A09/A10, G03.
6. **Owners, independent reproduction, security review** — every A01/G04/G05.

## Reliability / operability (P1)

Trace propagation into dependency requests; Retry-After handling; retry/circuit/queue-wait metrics; Hypothesis-style shrinking and a minimized-failure corpus; multi-hour soak and live-latency benchmark; generated compatibility matrix and CI across Python 3.11–3.13 and Windows; signed wheels/sdists, vulnerability scanning, CI enforcement of manifest/SBOM.

## Capability (P2)

Shard lineage and per-shard handoff completion; recurrence confidence; replica lifecycle/deletion; per-edge DAG breakdown; carbon/price feed freshness; RTT/setup latency and uncertainty for transfer time; currency/effective-dated pricing and staging double-storage; driver/API version ranges and immutable image digests; quota reservations/leases; minimum-sample drift rules; asynchronous shadow; multi-scenario simulation diff; compute-only safe mode; human exercise records.
