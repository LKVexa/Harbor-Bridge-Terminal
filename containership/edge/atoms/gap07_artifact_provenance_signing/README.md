# GAP-07 - Artifact provenance/signing

**Version:** 6.0.0
**Group:** 04_Gap_Subsystems · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Checklists:** 100 historical controls (`CHECKLIST.json`) plus the 48-component / 1,005-item production completion
checklist (`docs/GAP07_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST_v5.0.0.md`), both traced in `TRACEABILITY.json`.

GAP-07 is the estate's supply-chain admission gate. v6 adds a production path next to the v5 reference core:
asymmetric signatures under KMS/HSM custody, certificate-based signer identity, DSSE/in-toto/SLSA attestations,
transparency proofs, signed and rollback-protected trust and policy state, trusted time, and one fail-closed
admission controller.

## Module map

| concern | module | key API |
|---|---|---|
| stable refusal codes | `errors.py` | `ERROR_CODES`, `GapError`, `fail()` |
| strict parsing, JCS, length-delimited signing bytes | `canonical.py` | `strict_loads`, `canonical_bytes`, `ld_encode` |
| algorithm registry and agility | `algorithms.py` | `REGISTRY`, `get`, `verify_raw` |
| KMS/HSM custody | `keys.py` | `KeyRef`, `ResilientCustody`, AWS/Azure/GCP/Vault/PKCS#11 adapters |
| certificate trust model | `trust.py` | `TrustGeneration`, `issue_cert`, `validate_x509` |
| PK_SIGNATURE/3 | `signing.py` | `ArtifactSigner`, `verify_signature` |
| DSSE / in-toto / SLSA | `dsse.py` | `verify_envelope`, `AttestationPolicy` |
| transparency | `tlog.py` | `verify_inclusion_evidence`, `CheckpointCache`, `LocalTransparencyLog` |
| durable trust store, DR | `store.py` | `FileTrustRepository` (stage/commit/load/backup/restore), `TrustState` |
| distribution and propagation SLO | `distribution.py` | `SiteTrustAgent`, `make_snapshot`, `make_delta`, `PropagationTracker` |
| trusted time | `timesrc.py` | `TrustedClock`, `TimeAuthority` |
| GAP-13 policy adapter | `policy.py` | `PolicyStore`, `evaluate`, `verify_waiver` |
| SBOM | `sbom.py` | `facts_from_predicate` |
| OCI / Wasm / streaming | `registry.py` | `verify_oci`, `discover_referrers`, `verify_stream`, `VerifiedContentStore` |
| quarantine, replay, rate limits | `controls.py` | `QuarantineService`, `ReplayCache`, `AdmissionLimiter` |
| metrics / logs / traces / health | `telemetry.py` | `Metrics`, `StructuredLogger`, `TraceContext`, `Health` |
| audit export + anchoring | `audit_export.py` | `AuditExporter`, `AppendOnlyFileSink`, `verify_export` |
| admission hook | `admission.py` | `AdmissionController.admit / handoff`, `PK_ARTIFACT_BUNDLE/1` |
| key compromise | `compromise.py` | `respond_to_compromise` |
| HTTP service | `service.py` | `/admit`, `/readyz`, `/livez`, `/metrics` |
| v5 reference core (unchanged API) | `core.py` | `TrustStore` (HMAC reference), `provenance`, `AuditLedger` |

## Minimal production wiring

```python
from gap07_artifact_provenance_signing.store import FileTrustRepository, TrustState
from gap07_artifact_provenance_signing.policy import PolicyStore
from gap07_artifact_provenance_signing.timesrc import TrustedClock
from gap07_artifact_provenance_signing.admission import AdmissionController, AdmissionConfig

state = TrustState()
repo = FileTrustRepository("/var/lib/gap07/trust", namespace, config_authorities, state, audit=ledger)
repo.load()                                   # startup self-check; refuses corrupt/rolled-back state
clock = TrustedClock(site=..., device=..., authorities=time_authorities, state_path="/var/lib/gap07/time.json")
policy = PolicyStore(config_authorities, audit=ledger)
ctl = AdmissionController(trust_state=state, policy_store=policy, clock=clock, authorities=config_authorities,
                          log_keys=log_keys, checkpoint_cache=cache, audit=ledger,
                          config=AdmissionConfig(replay_cache_path="/var/lib/gap07/nonces.jsonl"))
decision = ctl.admit(request)                 # allow | deny | defer | error; only allow is runnable
payload = ctl.handoff(decision)               # TOCTOU-safe bytes for the runtime
```

## Verification

```text
pip install -r gap07_artifact_provenance_signing/requirements.txt
python -m unittest discover -s gap07_artifact_provenance_signing/tests -p "test_*.py" -v
python -O -m unittest discover -s gap07_artifact_provenance_signing/tests -p "test_*.py"
python gap07_artifact_provenance_signing/tools/traceability.py --check
python gap07_artifact_provenance_signing/tools/benchmark.py
python gap07_artifact_provenance_signing/tools/release.py evidence --bench
```

Current result: 143 tests pass (2 skipped because they need the estate `pk_core` adapter), in both normal and
`-O` mode. The fuzz and property suites accept `GAP07_SEED` / `GAP07_ITER`.

## Honest status

`TRACEABILITY.md` holds the per-item states. **production_ready = false.** Code and tests cover every P0/P1
component in-package. Remaining blockers are the things a package cannot do for itself: live KMS/registry/log
integrations, independent security review, `pk_core` and the adjacent-layer implementations, fleet and edge
measurements, and named owners. See `MISSING_COMPONENTS.md`.
