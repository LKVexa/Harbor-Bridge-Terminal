# GAP-13 - Policy engine

**Version:** 5.0.0 (see `CHANGELOG.md`)
**Group:** 04_Gap_Subsystems
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0
**Conformance checklist:** 100 requirements in `CHECKLIST.json`
**Production work packages:** 51 components + 5 external contracts, status in `COMPONENT_STATUS.json`
**Master audit source:** `MASTER.md` was never bundled and is superseded — see `docs/MASTER_SOURCE.md`

The policy engine is where the estate's rules are evaluated rather than scattered. Decisions default to deny, the most specific matching rule wins with deterministic tie-breaking, and every verdict carries the rule and the exact signed bundle that produced it -- so an operator can always answer why.

## What 5.0.0 adds
5.0.0 turns the 4.2.0 evaluator library into a production policy service:

| Layer | Modules |
|---|---|
| Trust | `verify.py` (Ed25519 envelope verification, trust store, key lifecycle), `bundle.py` + `canonical.py` (strict bounded `PK_POLICY_BUNDLE/1` parser), `replay.py` (durable anti-rollback) |
| Evaluation | `engine.py` (type-strict rules, compiled index, explain with redaction), `attributes.py` (typed allowlist, trusted-context-only protected attributes) |
| Control plane | `service.py` (stale modes, RCU swap, rollback, freeze/deny-only/disable/quarantine, health/status, admission control), `cache.py`, `storage.py`, `distribution.py`, `rpc.py` (`/v1` HTTP/JSON) |
| Security ops | `authz.py` (capabilities, step-up, SoD, token validation), `audit.py` (hash-chained audit log) |
| Observability | `telemetry.py` (metrics, logs, tracing, redaction, lineage), `ops/` dashboards and alerts |
| Certification | `bench.py`, `certify.py` (evidence manifest), `release_gate.py` (rc + production gates), `schemas/`, `fixtures/`, `docs/` |

**Breaking change:** `PolicyEngine.load(rules, version, {"verified": True})` is refused. Bundles enter only as signed `PK_POLICY_SIGNED_BUNDLE/1` envelopes verified by `BundleVerifier`. See `CHANGELOG.md`.

## Responsibility
Own policy evaluation for the estate: evaluate a request against versioned, signature-verified rules, default to deny, and return an explainable verdict naming the deciding rule and the bundle it came from.

## Explicitly does not own
Policy authorship (EXT-01), enforcement at the call site (EXT-02), identity/attestation (EXT-03), signing and key custody (GAP-07/EXT-04), topology (EXT-05). Contracts: `docs/INTEGRATION_CONTRACTS.md`.

## Interfaces
| Interface | Contract |
|---|---|
| load / stage / activate | `PK_POLICY_SIGNED_BUNDLE/1` wrapping `PK_POLICY_BUNDLE/1` (`schemas/`) |
| evaluate | `PK_POLICY_VERDICT/1` |
| explain | `PK_POLICY_EXPLANATION/1` (values redacted; matched list needs `policy.explain.detailed`) |
| errors | `PK_POLICY_ERROR/1`, codes in `docs/ERROR_CODES.md` |
| health / status | `PK_POLICY_HEALTH/1`, `PK_POLICY_STATUS/1` |
| RPC | `/v1/*` — see `rpc.py` and `docs/RUNBOOKS.md` |

## Quick start (library)
```python
from gap13_policy_engine import BundleVerifier, EngineConfig, PolicyService, StaticTrustSource, TrustStore
verifier = BundleVerifier(StaticTrustSource(TrustStore.from_dict(trust_store_doc)), environment="prod")
svc = PolicyService(EngineConfig(environment="prod", site="dc1"), verifier, state_dir="state", context=provider)
svc.restore_from_cache()                  # re-verifies last-known-good after restart
digest = svc.stage(admin_a, envelope)["digest"]
svc.activate(admin_b, digest)             # separation of duties
verdict = svc.evaluate(service_principal, {"action": "read", "resource": "db/orders"})
```

## Running it
```
python -m unittest discover -s gap13_policy_engine/tests          # full suite (needs cryptography; jsonschema optional)
python -m gap13_policy_engine.bench [--quick]                      # performance
python -m gap13_policy_engine.certify --out evidence [--full]      # evidence manifest
python -m gap13_policy_engine.certify --verify evidence/5.0.0/manifest.json
python -m gap13_policy_engine.release_gate --profile rc            # engineering regression gate
python -m gap13_policy_engine.release_gate --profile production    # production-exit gate
python -m pk_core run GAP-13 ...                                   # conformance, when pk_core is installed
```

## Production status
Engineering work for all 51 components is in the package and passes automated verification; nothing is marked `DONE` because the checklist requires independent review and acceptance. Four components are `BLOCKED` on things this package cannot supply (named owners, ADR approval, edge hardware, real adjacent-system builds). The production-exit gate therefore reports `NO_GO` until those are resolved — see `COMPONENT_STATUS.json`, `WAIVERS.json` and `docs/PRODUCTION_EXIT_GATE.md`.

Day-0/1/2, emergency controls and incident response: `docs/RUNBOOKS.md`. SLOs: `docs/SLO.md`. Threat model: `docs/THREAT_MODEL.md`.
