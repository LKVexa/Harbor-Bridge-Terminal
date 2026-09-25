# GAP-15 Requirements Traceability Matrix (100 source requirements)

Generated from `CHECKLIST.json` × `MISSING_COMPONENTS.md` source references × this run's control results. Owner and reviewer columns are empty because no owner is assigned (MC-41-05 blocked).

| Requirement | Dimension | Missing components | Status | Modules |
|---|---|---|---|---|
| GAP-15-C001 | Architecture & Scope | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C002 | Architecture & Scope | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C003 | Architecture & Scope | 04, 05, 30 | BLOCKED | attestation.py, provenance.py, service.py |
| GAP-15-C004 | Architecture & Scope | 02 | BLOCKED | state.py, store.py |
| GAP-15-C005 | Architecture & Scope | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C006 | Architecture & Scope | 25 | BLOCKED | partition.py |
| GAP-15-C007 | Architecture & Scope | 19, 22 | BLOCKED | features.py, scheduler.py |
| GAP-15-C008 | Architecture & Scope | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C009 | Architecture & Scope | 43 | BLOCKED | — |
| GAP-15-C010 | Architecture & Scope | 16, 42 | BLOCKED | negotiation.py |
| GAP-15-C011 | Requirements & Semantics | 16, 17 | BLOCKED | capability.py, negotiation.py |
| GAP-15-C012 | Requirements & Semantics | 16, 17 | BLOCKED | capability.py, negotiation.py |
| GAP-15-C013 | Requirements & Semantics | 16, 17 | BLOCKED | capability.py, negotiation.py |
| GAP-15-C014 | Requirements & Semantics | 06, 16, 17, 19, 21, 31 | BLOCKED | capability.py, features.py, negotiation.py, service.py, state.py, timepolicy.py |
| GAP-15-C015 | Requirements & Semantics | 16, 17, 20, 21 | BLOCKED | capability.py, negotiation.py, service.py, state.py |
| GAP-15-C016 | Requirements & Semantics | 16, 17, 18, 21 | BLOCKED | capability.py, negotiation.py, state.py, versions.py |
| GAP-15-C017 | Requirements & Semantics | 32 | BLOCKED | capacity.py |
| GAP-15-C018 | Requirements & Semantics | 24 | BLOCKED | offline.py |
| GAP-15-C019 | Requirements & Semantics | 23 | BLOCKED | policy.py |
| GAP-15-C020 | Requirements & Semantics | 02, 40, 41 | BLOCKED | release.py, state.py, store.py |
| GAP-15-C021 | Interfaces & Integration | 09, 10, 14, 17 | BLOCKED | canonical.py, capability.py, http_api.py, schemas.py, serve.py, service.py |
| GAP-15-C022 | Interfaces & Integration | 09, 10 | BLOCKED | canonical.py, schemas.py, service.py |
| GAP-15-C023 | Interfaces & Integration | 07, 10 | BLOCKED | authn.py, service.py |
| GAP-15-C024 | Interfaces & Integration | 08, 10, 23 | BLOCKED | authz.py, policy.py, service.py |
| GAP-15-C025 | Interfaces & Integration | 10, 11, 14 | BLOCKED | http_api.py, serve.py, service.py, store.py |
| GAP-15-C026 | Interfaces & Integration | 09, 10, 14, 31 | BLOCKED | canonical.py, http_api.py, schemas.py, serve.py, service.py, state.py |
| GAP-15-C027 | Interfaces & Integration | 09, 14, 16, 18, 19 | BLOCKED | canonical.py, features.py, http_api.py, negotiation.py, schemas.py, serve.py, versions.py |
| GAP-15-C028 | Interfaces & Integration | 14, 32 | BLOCKED | capacity.py, http_api.py, serve.py |
| GAP-15-C029 | Interfaces & Integration | 34 | BLOCKED | fixtures_matrix.py |
| GAP-15-C030 | Interfaces & Integration | 30, 33 | BLOCKED | service.py |
| GAP-15-C031 | Implementation & Configuration | 44, 45 | BLOCKED | config.py, release.py, serve.py |
| GAP-15-C032 | Implementation & Configuration | 01, 44 | BLOCKED | config.py, release.py, serve.py, store.py |
| GAP-15-C033 | Implementation & Configuration | 44 | BLOCKED | config.py, release.py, serve.py |
| GAP-15-C034 | Implementation & Configuration | 10, 44 | BLOCKED | config.py, release.py, serve.py, service.py |
| GAP-15-C035 | Implementation & Configuration | 25, 44 | BLOCKED | config.py, partition.py, release.py, serve.py |
| GAP-15-C036 | Implementation & Configuration | 02, 20, 44 | BLOCKED | config.py, release.py, serve.py, service.py, state.py, store.py |
| GAP-15-C037 | Implementation & Configuration | 01, 10, 11, 44 | BLOCKED | config.py, release.py, serve.py, service.py, store.py |
| GAP-15-C038 | Implementation & Configuration | 44 | BLOCKED | config.py, release.py, serve.py |
| GAP-15-C039 | Implementation & Configuration | 44 | BLOCKED | config.py, release.py, serve.py |
| GAP-15-C040 | Implementation & Configuration | 44 | BLOCKED | config.py, release.py, serve.py |
| GAP-15-C041 | Security, Trust & Isolation | 13, 36 | BLOCKED | service.py, state.py |
| GAP-15-C042 | Security, Trust & Isolation | 08 | BLOCKED | authz.py |
| GAP-15-C043 | Security, Trust & Isolation | 08 | BLOCKED | authz.py |
| GAP-15-C044 | Security, Trust & Isolation | 04, 05, 07 | BLOCKED | attestation.py, authn.py, provenance.py |
| GAP-15-C045 | Security, Trust & Isolation | 03, 04, 45 | BLOCKED | ed25519.py, provenance.py, release.py, signing.py |
| GAP-15-C046 | Security, Trust & Isolation | 25 | BLOCKED | partition.py |
| GAP-15-C047 | Security, Trust & Isolation | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C048 | Security, Trust & Isolation | 05, 06, 13, 23, 24 | BLOCKED | attestation.py, offline.py, policy.py, service.py, state.py, timepolicy.py |
| GAP-15-C049 | Security, Trust & Isolation | 02, 03, 12 | BLOCKED | ed25519.py, service.py, signing.py, state.py, store.py |
| GAP-15-C050 | Security, Trust & Isolation | 35, 36 | BLOCKED | — |
| GAP-15-C051 | Resilience & Failure Handling | 06 | BLOCKED | timepolicy.py |
| GAP-15-C052 | Resilience & Failure Handling | 14, 22 | BLOCKED | http_api.py, scheduler.py, serve.py |
| GAP-15-C053 | Resilience & Failure Handling | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C054 | Resilience & Failure Handling | 14, 32 | BLOCKED | capacity.py, http_api.py, serve.py |
| GAP-15-C055 | Resilience & Failure Handling | 15, 25 | BLOCKED | cli.py, partition.py, store.py |
| GAP-15-C056 | Resilience & Failure Handling | 15, 24 | BLOCKED | cli.py, offline.py, store.py |
| GAP-15-C057 | Resilience & Failure Handling | 01, 15 | BLOCKED | cli.py, store.py |
| GAP-15-C058 | Resilience & Failure Handling | 11, 15, 37 | BLOCKED | cli.py, store.py |
| GAP-15-C059 | Resilience & Failure Handling | 13, 15, 31 | BLOCKED | cli.py, service.py, state.py, store.py |
| GAP-15-C060 | Resilience & Failure Handling | 15, 38 | BLOCKED | cli.py, store.py |
| GAP-15-C061 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C062 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C063 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C064 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C065 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C066 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C067 | Performance & Resource Efficiency | 14, 26, 32, 39 | BLOCKED | capacity.py, http_api.py, observability.py, serve.py |
| GAP-15-C068 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C069 | Performance & Resource Efficiency | 22, 26, 32, 39 | BLOCKED | capacity.py, observability.py, scheduler.py |
| GAP-15-C070 | Performance & Resource Efficiency | 26, 39 | BLOCKED | observability.py |
| GAP-15-C071 | Observability & Explainability | 14, 26 | BLOCKED | http_api.py, observability.py, serve.py |
| GAP-15-C072 | Observability & Explainability | 26 | BLOCKED | observability.py |
| GAP-15-C073 | Observability & Explainability | 12, 27 | BLOCKED | observability.py, service.py, store.py |
| GAP-15-C074 | Observability & Explainability | 27 | BLOCKED | observability.py |
| GAP-15-C075 | Observability & Explainability | 27 | BLOCKED | observability.py |
| GAP-15-C076 | Observability & Explainability | 28 | BLOCKED | service.py |
| GAP-15-C077 | Observability & Explainability | 28 | BLOCKED | service.py |
| GAP-15-C078 | Observability & Explainability | 04, 12, 27 | BLOCKED | observability.py, provenance.py, service.py, store.py |
| GAP-15-C079 | Observability & Explainability | 27 | BLOCKED | observability.py |
| GAP-15-C080 | Observability & Explainability | 29 | BLOCKED | ops.py |
| GAP-15-C081 | Testing & Certification | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C082 | Testing & Certification | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C083 | Testing & Certification | 30, 33 | BLOCKED | service.py |
| GAP-15-C084 | Testing & Certification | 16, 17, 34 | BLOCKED | capability.py, fixtures_matrix.py, negotiation.py |
| GAP-15-C085 | Testing & Certification | 35 | BLOCKED | — |
| GAP-15-C086 | Testing & Certification | 11, 37 | BLOCKED | store.py |
| GAP-15-C087 | Testing & Certification | 36 | BLOCKED | — |
| GAP-15-C088 | Testing & Certification | 39 | BLOCKED | — |
| GAP-15-C089 | Testing & Certification | 06, 15, 24, 38 | BLOCKED | cli.py, offline.py, store.py, timepolicy.py |
| GAP-15-C090 | Testing & Certification | 02, 03, 40 | BLOCKED | ed25519.py, release.py, signing.py, state.py, store.py |
| GAP-15-C091 | Operations, Release & Governance | 43 | BLOCKED | — |
| GAP-15-C092 | Operations, Release & Governance | 13, 22, 46 | BLOCKED | release.py, scheduler.py, service.py, state.py |
| GAP-15-C093 | Operations, Release & Governance | 16, 18 | BLOCKED | negotiation.py, versions.py |
| GAP-15-C094 | Operations, Release & Governance | 20, 21, 45 | BLOCKED | release.py, service.py, state.py |
| GAP-15-C095 | Operations, Release & Governance | 01, 15, 47 | BLOCKED | cli.py, store.py |
| GAP-15-C096 | Operations, Release & Governance | 48 | BLOCKED | — |
| GAP-15-C097 | Operations, Release & Governance | 31, 43, 48 | BLOCKED | service.py, state.py |
| GAP-15-C098 | Operations, Release & Governance | — | NO_MISSING_COMPONENT_MAPPED | — |
| GAP-15-C099 | Operations, Release & Governance | 20, 23, 49 | BLOCKED | policy.py, service.py, state.py |
| GAP-15-C100 | Operations, Release & Governance | 40, 50 | BLOCKED | release.py |
