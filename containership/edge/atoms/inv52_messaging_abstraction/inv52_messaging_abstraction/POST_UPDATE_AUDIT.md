# INV-52 post-update audit — v4.3.0

Counts: {'present': 9, 'DOCUMENTED': 20, 'BLOCKED': 16, 'EVIDENCED_LOCAL': 55} (100 checklist requirements). 4.2.0 baseline: present 9 / partial 41 / missing 50 — preserved in `POST_UPDATE_AUDIT_4.2.0.md`.

Status meanings: see `governance/requirements.json` → `status_vocabulary`. Nothing is marked IMPLEMENTED because no owner, approval or deployed environment exists.

| ID | Dimension | 4.2.0 | 4.3.0 | Evidence | Blocker / residual |
|---|---|---|---|---|---|
| INV-52-C001 | Architecture & Scope | present | present | README.md; contract.py responsibility (unchanged; still present in 4.3.0) |  |
| INV-52-C002 | Architecture & Scope | present | present | README.md; contract.py owns/not_owns (unchanged; still present in 4.3.0) |  |
| INV-52-C003 | Architecture & Scope | partial | DOCUMENTED | `docs/SCOPE.md`<br>`governance/dependencies.json` |  |
| INV-52-C004 | Architecture & Scope | present | present | contract.py source_of_truth; runtime.py deep-copy canonical delivery (unchanged; still present in 4.3.0) |  |
| INV-52-C005 | Architecture & Scope | partial | DOCUMENTED | `docs/SCOPE.md` |  |
| INV-52-C006 | Architecture & Scope | present | present | contract.py boundaries (unchanged; still present in 4.3.0) |  |
| INV-52-C007 | Architecture & Scope | present | present | contract.py mandatory/optional (unchanged; still present in 4.3.0) |  |
| INV-52-C008 | Architecture & Scope | partial | DOCUMENTED | `docs/SCOPE.md` |  |
| INV-52-C009 | Architecture & Scope | missing | BLOCKED | `OWNERS.md`<br>`CODEOWNERS`<br>`governance/owners.json` | organisation must name accountable owner, deputy, security, release, on-call and reviewers |
| INV-52-C010 | Architecture & Scope | missing | BLOCKED | `docs/adr/ADR-0001-messaging-abstraction-dapr-pubsub.md` | ADR is PROPOSED; approval by owner + architecture reviewer required |
| INV-52-C011 | Requirements & Semantics | partial | EVIDENCED_LOCAL | `docs/REQUIREMENTS.md`<br>`examples/fixtures/conformance.json` |  |
| INV-52-C012 | Requirements & Semantics | missing | DOCUMENTED | `docs/REQUIREMENTS.md`<br>`examples/config/site.edge-1.json` |  |
| INV-52-C013 | Requirements & Semantics | partial | DOCUMENTED | `docs/REQUIREMENTS.md`<br>`perf/baseline.json` | NFR targets PROPOSED; need owner approval and production measurement |
| INV-52-C014 | Requirements & Semantics | missing | EVIDENCED_LOCAL | `docs/REQUIREMENTS.md`<br>`runtime.py`<br>`schemas/PK_MSG_DECISION_1.schema.json` |  |
| INV-52-C015 | Requirements & Semantics | missing | EVIDENCED_LOCAL | `lifecycle.py`<br>`runtime.py`<br>`docs/REQUIREMENTS.md` |  |
| INV-52-C016 | Requirements & Semantics | present | present | docs/VERSIONING.md; VERSION; __version__; schema/interface major identifiers (unchanged; still present in 4.3.0) |  |
| INV-52-C017 | Requirements & Semantics | partial | EVIDENCED_LOCAL | `resilience.py`<br>`docs/REQUIREMENTS.md` |  |
| INV-52-C018 | Requirements & Semantics | missing | EVIDENCED_LOCAL | `adapters.py`<br>`docs/REQUIREMENTS.md` |  |
| INV-52-C019 | Requirements & Semantics | missing | DOCUMENTED | `docs/REQUIREMENTS.md` |  |
| INV-52-C020 | Requirements & Semantics | missing | EVIDENCED_LOCAL | `governance/requirements.json`<br>`governance/RTM.md`<br>`gate.py` |  |
| INV-52-C021 | Interfaces & Integration | partial | DOCUMENTED | `docs/INTERFACES.md` |  |
| INV-52-C022 | Interfaces & Integration | partial | EVIDENCED_LOCAL | `schemas.py`<br>`schemas/PK_MSG_PUBLISH_1.schema.json`<br>`schemas/PK_MSG_CONFIG_1.schema.json` |  |
| INV-52-C023 | Interfaces & Integration | partial | EVIDENCED_LOCAL | `security.py`<br>`docs/INTERFACES.md` | production IdP binding (SPIFFE/OIDC) not available here |
| INV-52-C024 | Interfaces & Integration | partial | EVIDENCED_LOCAL | `security.py`<br>`docs/INTERFACES.md` |  |
| INV-52-C025 | Interfaces & Integration | missing | EVIDENCED_LOCAL | `resilience.py`<br>`docs/INTERFACES.md` |  |
| INV-52-C026 | Interfaces & Integration | present | present | runtime.py MessagingError subclasses and docs/INTERFACES.md failure catalog (unchanged; still present in 4.3.0) |  |
| INV-52-C027 | Interfaces & Integration | partial | EVIDENCED_LOCAL | `schemas.py`<br>`docs/COMPATIBILITY.md` |  |
| INV-52-C028 | Interfaces & Integration | partial | EVIDENCED_LOCAL | `docs/INTERFACES.md`<br>`runtime.py` |  |
| INV-52-C029 | Interfaces & Integration | partial | EVIDENCED_LOCAL | `examples/fixtures/conformance.json`<br>`examples/basic.py` |  |
| INV-52-C030 | Interfaces & Integration | missing | BLOCKED | `adapters.py` | tested against an in-process Dapr HTTP emulator only; live daprd + INV-46/INV-53 integration environment required |
| INV-52-C031 | Implementation & Configuration | missing | BLOCKED | `docs/COMPATIBILITY.md`<br>`tools/sbom.py` | Dapr 1.17.x is a candidate; exact version pin needs ADR approval; sibling INV-46 pins out-of-support 1.14.4 |
| INV-52-C032 | Implementation & Configuration | missing | DOCUMENTED | `docs/CONFIGURATION.md` |  |
| INV-52-C033 | Implementation & Configuration | missing | EVIDENCED_LOCAL | `config.py`<br>`schemas/PK_MSG_CONFIG_1.schema.json` |  |
| INV-52-C034 | Implementation & Configuration | partial | EVIDENCED_LOCAL | `config.py` |  |
| INV-52-C035 | Implementation & Configuration | partial | EVIDENCED_LOCAL | `config.py`<br>`examples/config/env.prod.json`<br>`examples/config/site.edge-1.json` |  |
| INV-52-C036 | Implementation & Configuration | missing | EVIDENCED_LOCAL | `config.py` |  |
| INV-52-C037 | Implementation & Configuration | partial | EVIDENCED_LOCAL | `config.py` |  |
| INV-52-C038 | Implementation & Configuration | missing | EVIDENCED_LOCAL | `config.py`<br>`docs/OPERATIONS.md` |  |
| INV-52-C039 | Implementation & Configuration | partial | EVIDENCED_LOCAL | `security.py`<br>`config.py`<br>`deploy/dapr/pubsub-component.yaml` |  |
| INV-52-C040 | Implementation & Configuration | partial | EVIDENCED_LOCAL | `lifecycle.py`<br>`__main__.py`<br>`docs/OPERATIONS.md` | production broker/identity bootstrap is external |
| INV-52-C041 | Security, Trust & Isolation | partial | BLOCKED | `docs/THREAT_MODEL.md`<br>`governance/threats.json` | independent security review required; T17/T18 enforced by platform |
| INV-52-C042 | Security, Trust & Isolation | partial | EVIDENCED_LOCAL | `security.py` | platform identity/RBAC least privilege unproven |
| INV-52-C043 | Security, Trust & Isolation | partial | EVIDENCED_LOCAL | `runtime.py`<br>`docs/SECURITY.md` |  |
| INV-52-C044 | Security, Trust & Isolation | missing | BLOCKED | `security.py` | node/peer/control-plane attestation needs the platform IdP; waiver W-001 |
| INV-52-C045 | Security, Trust & Isolation | missing | BLOCKED | `security.py` | signature verification (Sigstore/cosign) not implemented; waiver W-001 |
| INV-52-C046 | Security, Trust & Isolation | missing | EVIDENCED_LOCAL | `security.py` | execution/memory/network/device isolation is the host platform's |
| INV-52-C047 | Security, Trust & Isolation | missing | BLOCKED | `docs/SECURITY.md`<br>`deploy/dapr/pubsub-component.yaml` | transport mTLS (Dapr Sentry), broker TLS and at-rest encryption with KMS rotation are external; no evidence available |
| INV-52-C048 | Security, Trust & Isolation | missing | EVIDENCED_LOCAL | `lifecycle.py`<br>`security.py` |  |
| INV-52-C049 | Security, Trust & Isolation | missing | EVIDENCED_LOCAL | `security.py` | durable, externally anchored audit sink required in production |
| INV-52-C050 | Security, Trust & Isolation | partial | EVIDENCED_LOCAL | `tests/test_adversarial.py` |  |
| INV-52-C051 | Resilience & Failure Handling | partial | DOCUMENTED | `docs/RELIABILITY.md` |  |
| INV-52-C052 | Resilience & Failure Handling | missing | EVIDENCED_LOCAL | `runtime.py`<br>`lifecycle.py`<br>`docs/RELIABILITY.md` | thresholds PROPOSED |
| INV-52-C053 | Resilience & Failure Handling | partial | EVIDENCED_LOCAL | `resilience.py`<br>`deploy/dapr/resiliency.yaml` |  |
| INV-52-C054 | Resilience & Failure Handling | partial | EVIDENCED_LOCAL | `resilience.py` |  |
| INV-52-C055 | Resilience & Failure Handling | missing | BLOCKED | `docs/RELIABILITY.md` | failover execution needs INV-53/INV-54 multi-broker environment |
| INV-52-C056 | Resilience & Failure Handling | partial | EVIDENCED_LOCAL | `lifecycle.py`<br>`resilience.py` |  |
| INV-52-C057 | Resilience & Failure Handling | partial | EVIDENCED_LOCAL | `adapters.py`<br>`config.py`<br>`docs/RELIABILITY.md` | in-process dead letters volatile (waiver W-003) |
| INV-52-C058 | Resilience & Failure Handling | missing | EVIDENCED_LOCAL | `resilience.py` | broker consumer-group fencing is INV-54's |
| INV-52-C059 | Resilience & Failure Handling | partial | EVIDENCED_LOCAL | `runtime.py`<br>`lifecycle.py` |  |
| INV-52-C060 | Resilience & Failure Handling | missing | EVIDENCED_LOCAL | `tests/test_integration.py` | live broker/sidecar fault injection not run |
| INV-52-C061 | Performance & Resource Efficiency | missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json`<br>`docs/PERFORMANCE.md` | power and network baselines need representative hardware |
| INV-52-C062 | Performance & Resource Efficiency | partial | DOCUMENTED | `perf/baseline.json`<br>`docs/PERFORMANCE.md` | thresholds PROPOSED, not approved |
| INV-52-C063 | Performance & Resource Efficiency | missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json` | measured on one cloud container, not a representative fleet |
| INV-52-C064 | Performance & Resource Efficiency | missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json` |  |
| INV-52-C065 | Performance & Resource Efficiency | missing | EVIDENCED_LOCAL | `bench.py`<br>`docs/PERFORMANCE.md` |  |
| INV-52-C066 | Performance & Resource Efficiency | missing | EVIDENCED_LOCAL | `runtime.py`<br>`bench.py`<br>`docs/PERFORMANCE.md` |  |
| INV-52-C067 | Performance & Resource Efficiency | partial | EVIDENCED_LOCAL | `runtime.py`<br>`docs/INTERFACES.md` |  |
| INV-52-C068 | Performance & Resource Efficiency | missing | BLOCKED | `bench.py` | no instrumented edge node; waiver W-002 |
| INV-52-C069 | Performance & Resource Efficiency | partial | DOCUMENTED | `docs/PERFORMANCE.md`<br>`observability.py` | capacity model is linear extrapolation from one host; needs fleet data |
| INV-52-C070 | Performance & Resource Efficiency | missing | EVIDENCED_LOCAL | `gate.py`<br>`bench.py`<br>`perf/baseline.json` | thresholds PROPOSED |
| INV-52-C071 | Observability & Explainability | partial | EVIDENCED_LOCAL | `runtime.py`<br>`lifecycle.py`<br>`schemas/PK_MSG_HEALTH_1.schema.json` |  |
| INV-52-C072 | Observability & Explainability | partial | EVIDENCED_LOCAL | `runtime.py`<br>`observability.py` |  |
| INV-52-C073 | Observability & Explainability | missing | EVIDENCED_LOCAL | `observability.py` |  |
| INV-52-C074 | Observability & Explainability | missing | EVIDENCED_LOCAL | `runtime.py`<br>`adapters.py`<br>`observability.py` |  |
| INV-52-C075 | Observability & Explainability | partial | EVIDENCED_LOCAL | `observability.py`<br>`docs/OBSERVABILITY.md` |  |
| INV-52-C076 | Observability & Explainability | partial | EVIDENCED_LOCAL | `runtime.py` |  |
| INV-52-C077 | Observability & Explainability | missing | EVIDENCED_LOCAL | `runtime.py` |  |
| INV-52-C078 | Observability & Explainability | missing | BLOCKED | `observability.py` | live infrastructure graph service not available |
| INV-52-C079 | Observability & Explainability | missing | DOCUMENTED | `observability.py`<br>`docs/OBSERVABILITY.md` | policy PROPOSED; privacy approval needed |
| INV-52-C080 | Observability & Explainability | missing | BLOCKED | `deploy/observability/dashboard.json`<br>`deploy/observability/alerts.yaml`<br>`observability.py` | not loaded into a live Prometheus/Grafana |
| INV-52-C081 | Testing & Certification | present | present | tests/test_runtime.py unit-tests deterministic runtime behavior (unchanged; still present in 4.3.0) |  |
| INV-52-C082 | Testing & Certification | partial | EVIDENCED_LOCAL | `tests/test_runtime_ext.py`<br>`tests/test_governance.py` |  |
| INV-52-C083 | Testing & Certification | missing | BLOCKED | `tests/test_integration.py` | no live daprd/broker/tier environment |
| INV-52-C084 | Testing & Certification | missing | BLOCKED | `.github/workflows/ci.yml`<br>`docs/COMPATIBILITY.md` | CI matrix defined but not executed; one platform measured here |
| INV-52-C085 | Testing & Certification | missing | EVIDENCED_LOCAL | `tests/test_adversarial.py` |  |
| INV-52-C086 | Testing & Certification | present | present | tests/test_runtime.py includes concurrent publish/state-metric coverage (unchanged; still present in 4.3.0) |  |
| INV-52-C087 | Testing & Certification | partial | EVIDENCED_LOCAL | `governance/threats.json` | threat model not independently reviewed |
| INV-52-C088 | Testing & Certification | missing | EVIDENCED_LOCAL | `bench.py`<br>`evidence/perf.json` | soak and fleet-scale runs need an environment |
| INV-52-C089 | Testing & Certification | missing | BLOCKED | `tests/test_integration.py` | disaster / real partition / degraded control-plane tests need infrastructure |
| INV-52-C090 | Testing & Certification | missing | EVIDENCED_LOCAL | `gate.py`<br>`evidence/release_certification.json`<br>`tools/sbom.py` |  |
| INV-52-C091 | Operations, Release & Governance | partial | DOCUMENTED | `docs/SUPPORT_POLICY.md` | support commitments are the organisation's; SLO evidence needs production |
| INV-52-C092 | Operations, Release & Governance | partial | DOCUMENTED | `docs/OPERATIONS.md`<br>`lifecycle.py` | runbooks not exercised by an operator |
| INV-52-C093 | Operations, Release & Governance | missing | DOCUMENTED | `docs/COMPATIBILITY.md` | matrix mostly unverified |
| INV-52-C094 | Operations, Release & Governance | missing | DOCUMENTED | `docs/SUPPORT_POLICY.md` | SLAs PROPOSED |
| INV-52-C095 | Operations, Release & Governance | partial | DOCUMENTED | `docs/OPERATIONS.md` | broker backup/restore belongs to INV-54 owners |
| INV-52-C096 | Operations, Release & Governance | partial | DOCUMENTED | `docs/OPERATIONS.md` | not executed by an operator |
| INV-52-C097 | Operations, Release & Governance | missing | DOCUMENTED | `docs/OPERATIONS.md`<br>`governance/owners.json` | paging impossible while roles are UNASSIGNED |
| INV-52-C098 | Operations, Release & Governance | missing | DOCUMENTED | `governance/reviews.md` | no review performed |
| INV-52-C099 | Operations, Release & Governance | missing | EVIDENCED_LOCAL | `governance/waivers.json` | waiver owners UNASSIGNED |
| INV-52-C100 | Operations, Release & Governance | missing | BLOCKED | `gate.py`<br>`evidence/release_certification.json` | gate executes and reports NO_GO: owners, approvals, blocked items |
