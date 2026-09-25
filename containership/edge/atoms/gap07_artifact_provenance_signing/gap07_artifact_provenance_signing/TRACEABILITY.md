# GAP-07 traceability matrix (generated - do not edit)

Checklist digest `fa43b10af23166f0…`. P0 items not production-validated: **240**. production_ready = **False**.

| priority | design-complete | code-complete | test-complete | integrated | production-validated | waived | blocked |
|---|---|---|---|---|---|---|---|
| External | 33 | 29 | 0 | 0 | 0 | 0 | 58 |
| Global | 21 | 0 | 0 | 0 | 0 | 0 | 4 |
| P0 | 0 | 15 | 169 | 0 | 0 | 0 | 56 |
| P1 | 12 | 17 | 236 | 0 | 0 | 0 | 55 |
| P2 | 78 | 63 | 80 | 0 | 0 | 0 | 79 |

## Component view

| # | component state | implementation | blocker / external |
|---|---|---|---|
| 1 | test-complete | `algorithms.py`, `signing.py`, `canonical.py` | independent crypto review (#37); CI matrix run on Windows/edge/Wasm verifiers |
| 2 | code-complete | `keys.py`, `docs/KEY_CEREMONY.md` | live-provider conformance runs against the estate's chosen KMS/HSM; IAM least-privilege evidence |
| 3 | test-complete | `trust.py`, `docs/adr/ADR-002-trust-roots.md` | CRL/OCSP not implemented (revocation via signed trust deltas); PKI review |
| 4 | test-complete | `dsse.py`, `docs/adr/ADR-005-attestation-format.md` | conformance fixtures from external SLSA producers (e.g. slsa-github-generator) not bundled |
| 5 | test-complete | `tlog.py`, `docs/adr/ADR-004-transparency.md` | live Rekor/private-log service; RekorClient is an adapter skeleton |
| 6 | test-complete | `store.py`, `docs/adr/ADR-007-persistence.md` | encryption-at-rest of trust metadata is deployment-side (integrity is enforced) |
| 7 | test-complete | `distribution.py` | authenticated transport (mTLS relay) is estate-side |
| 8 | test-complete | `policy.py`, `fixtures/gap13/` | real GAP-13 engine end-to-end run |
| 9 | test-complete | `registry.py` | live OCI registry client + auth; tested against local content store |
| 10 | test-complete | `admission.py`, `service.py`, `docs/ADMISSION_PATHS.md` | AdmissionReview translation + runtime plugins; penetration testing |
| 11 | test-complete | `audit_export.py` | WORM/object-lock storage configuration and retention tests |
| 12 | test-complete | `timesrc.py` | NTS/TPM time sources feeding the time authority |
| 13 | test-complete | `policy.py`, `dsse.py` | — |
| 14 | test-complete | `compromise.py` | incident drill with estate SOC |
| 15 | test-complete | `controls.py` | — |
| 16 | test-complete | `sbom.py` | vulnerability feed integration (VEX producer) estate-side |
| 17 | test-complete | `admission.py`, `schemas/PK_ARTIFACT_BUNDLE-1.schema.json` | — |
| 18 | test-complete | `canonical.py`, `vectors/v6_vectors.json`, `tools/gen_vectors.py` | non-Python consumer implementations must run the vectors |
| 19 | test-complete | `algorithms.py`, `COMPATIBILITY.json` | — |
| 20 | test-complete | `controls.py` | — |
| 21 | test-complete | `trust.py`, `signing.py`, `admission.py` | — |
| 22 | test-complete | `controls.py` | — |
| 23 | test-complete | `registry.py` | — |
| 24 | test-complete | `store.py` | — |
| 25 | test-complete | `telemetry.py`, `service.py` | OTel SDK exporter wiring (IDs/attributes are OTel-compatible) |
| 26 | design-complete | `ops/alerts/gap07-rules.yaml`, `ops/dashboards/gap07-dashboard.json` | load into estate Prometheus/Grafana and fire-drill alerts |
| 27 | test-complete | `distribution.py`, `ops/slo-budgets.json` | fleet-wide measurement |
| 28 | code-complete | `COMPATIBILITY.json`, `tools/traceability.py` | — |
| 29 | test-complete | `tests/test_v6_assurance.py` | coverage-guided fuzzing (atheris/OSS-Fuzz) for long campaigns |
| 30 | test-complete | `tests/test_v6_assurance.py` | — |
| 31 | test-complete | `tests/test_v6_assurance.py`, `tests/test_v6_state.py` | — |
| 32 | test-complete | `tests/test_v6_assurance.py`, `tests/test_v6_state.py`, `tests/test_v6_keys.py` | network-partition / real disk-full on target hosts |
| 33 | code-complete | `tools/benchmark.py`, `ops/slo-budgets.json` | edge-node power/thermal measurement on target hardware |
| 34 | code-complete | `tools/soak.py` | fleet-scale soak on real sites |
| 35 | test-complete | `store.py`, `docs/RUNBOOKS.md` | RPO/RTO drill evidence |
| 36 | design-complete | `docs/THREAT_MODEL.md` | threat-model review sign-off |
| 37 | blocked | `docs/SECURITY_REVIEW.md` | independent reviewer - cannot be self-certified |
| 38 | code-complete | `tools/release.py` | — |
| 39 | design-complete | `DEPENDENCIES.md`, `requirements.txt`, `tools/release.py` | pip-audit + lockfile run in CI |
| 40 | design-complete | `docs/RUNBOOKS.md` | game-day exercises |
| 41 | design-complete | `OWNERS.yaml` | named owners/on-call to be assigned by the estate |
| 42 | design-complete | `docs/adr/` | ADR-003/004 have open estate decisions |
| 43 | code-complete | `tools/traceability.py`, `TRACEABILITY.json` | — |
| 44 | blocked | `contract.py`, `component.py` | estate pk_core package not supplied |
| 45 | blocked | `fixtures/gap13/` | GAP-06/GAP-08/PLN-06/PLN-07 implementations not supplied; only GAP-13 contract fixtures included |
| 46 | design-complete | `ci/github-workflow.yml` | install into the estate repository and run |
| 47 | design-complete | `deploy/k8s/gap07.yaml` | image build, registry, cert-manager issuer, PVC class are estate-specific |
| 48 | code-complete | `tools/release.py` | release-authority key ceremony + pinned SPKI distribution |
