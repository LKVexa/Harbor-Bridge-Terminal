# GAP-07 missing components after v6.0.0

v6.0.0 implements the 48-component completion checklist inside the package: code, tests, docs and ops assets.
What remains needs the estate, other teams or independent parties. The authoritative per-item state is
`TRACEABILITY.json`, where items that cannot be closed in-package are marked `blocked` with their dependency.

## Still blocked on the estate (cannot be closed in-package)

| # | item | what exists now | what is still needed |
|---|---|---|---|
| 2 | KMS/HSM live conformance | 5 provider adapters + resilience layer, tested with SDK-shaped fakes | runs against the chosen provider, IAM least-privilege evidence, key ceremony records |
| 3 | CRL/OCSP | revocation through signed trust deltas; X.509 path validation | CRL/OCSP fetch, if the estate PKI requires it |
| 4 | multi-producer SLSA fixtures | native SLSA v1 validator and negative fixtures | real attestations from the estate builders (e.g. slsa-github-generator) |
| 5 | live transparency service | local RFC 9162 log, signed checkpoints, cache, Rekor client skeleton | a private log or Rekor deployment and checkpoint-format bridging |
| 9 | live registry | OCI manifest/index/referrers/Wasm verification over a content-store interface | an authenticated registry client bound to that interface |
| 10 | orchestrator/runtime wiring | controller, HTTP service, webhook manifest (`failurePolicy: Fail`) | AdmissionReview → bundle translation, runtime plugins, penetration test |
| 11 | WORM storage | append-only sink, anchoring, independent verifier with truncation references | object-lock/WORM configuration and retention/legal-hold tests |
| 12 | time sources | signed time attestations + persisted floor | NTS/TPM/PTP feeding the time authority |
| 26/27 | alert fire-drills, fleet SLO | rules, dashboard, propagation tracker | load into Prometheus/Grafana; measure across real sites |
| 33/34 | edge benchmarks, fleet soak | `tools/benchmark.py`, `tools/soak.py` | runs on target hardware and at fleet scale |
| 37 | independent security/crypto review | review packet `docs/SECURITY_REVIEW.md` | a reviewer who is not the implementer (**P0 admission blocker**) |
| 41 | named owners / on-call | `OWNERS.yaml` role structure | people |
| 44 | `pk_core` | adapter (`component.py`, `contract.py`) unchanged | the estate package |
| 45 | GAP-06/GAP-08/PLN-06/PLN-07 fixtures | GAP-13 contract fixtures only | the adjacent implementations |
| 46/47/48 | CI, deployment, release signing | workflow file, k8s manifests, release tooling | install and run in the estate; release-authority key ceremony |

## Known design residuals (documented, not hidden)

* **T5 single config authority.** Waiver, break-glass and recovery approvals are approver names inside a
  document signed by one config-authority key. Dual control therefore depends on the authority ceremony, not on
  independent approver signatures. Planned for v6.1: M-of-N config-authority co-signatures.
* **T7 floor on the same disk.** Generation and time floors are files. A hardware monotonic counter (TPM NV) is
  recommended.
* The default `ReplayCache` is in-memory. Production break-glass is refused unless `AdmissionConfig.replay_cache_path`
  is set.
* Python admission throughput is GIL-bound (about 240 uncached admissions/s on 8 threads in this sandbox; p95 tail
  under contention). Scale horizontally, or rely on the decision cache (sub-millisecond hits).
