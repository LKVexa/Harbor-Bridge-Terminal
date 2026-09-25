# INV-63 Compatibility Matrix

| Field | Value |
|---|---|
| Document ID | INV63-GOV-COMPAT |
| INV-63 C-IDs covered | C093 (with C084) |
| Status | DRAFT — pending approval |
| Owner | Release approver (role) — UNASSIGNED |
| Reviewers | Service owner (role), SRE lead (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, and on every change to `pins.json`. |

## Runtime and dependencies (`pins.json`)
| Component | Declared | Tested | Approved | Notes |
|---|---|---|---|---|
| Python | `>=3.11,<3.14` (3.11–3.13) | 3.11.15 locally (`perf/results.json`); 3.11/3.12/3.13 in `.github/workflows/ci.yml` matrix — no CI run results recorded | no | |
| cryptography | 46.0.7 | yes (same container) | no | Ed25519, AES-256-GCM; pinned in `requirements.lock` (wheel hashes to be filled at approval) |
| Wadm | **UNPINNED** (OAM `core.oam.dev/v1beta1`) | no — manifest rendering only | no | live Wadm required (evidence `wadm-live`, `wadm-pin`) |
| pk_core | UNPINNED | no | no | required by `contract.py`; not supplied |
| NATS transport | not bundled | no | — | injected into `WadmAdapter` |

## Schemas (`schema.SUPPORTED`)
| Contract | Majors | Notes |
|---|---|---|
| PK_DEPLOY_DESIRED | 1, 2 | v1 deprecated 2027-09-30; rejected when signing required |
| PK_DEPLOY_DIFF | 1 | — |
| PK_DEPLOY_ROLLOUT | 1 | — |
| PK_DEPLOY_ERROR | 1 | — |
| PK_DEPLOY_EVENT | 1 | — |
| PK_DEPLOY_CONFIG | 1 | — |
| PK_DEPLOY_REQUEST | 1 | — |
| PK_DEPLOY_GATE | 1 | — |

## Peers
| Peer | Interface | Tested |
|---|---|---|
| INV-64 | `PK_DEPLOY_DESIRED/2` | fixtures only |
| INV-60 / Wadm | B-10 | `InMemoryLattice`; `WadmAdapter` over a fake transport only |
| INV-66 | `PK_DEPLOY_REQUEST/1` | fixtures only |

## OS / architecture
| Platform | Status |
|---|---|
| Linux x86_64 (glibc 2.39, kernel 6.18) | tested locally in a container; `ubuntu-24.04` in CI matrix |
| Linux aarch64 | `ubuntu-24.04-arm` in CI matrix; no run results recorded (evidence `multi-arch-ci` open) |
| Other OS | unsupported (fsync/`os.replace` semantics assumed POSIX) |

CI `.github/workflows/ci.yml`: tests (normal and `-O`), `perf/bench.py --quick --gate`, `audit.py`, `gate.py` per matrix cell.
