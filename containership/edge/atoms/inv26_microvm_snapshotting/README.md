# INV-26 — MicroVM snapshotting

**Version:** 6.0.0 (see `CHANGELOG.md`) · **Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0 ·
**Checklist:** 100 requirements (`CHECKLIST.json`) + the v5.0.0 missing-component checklist (`source/`)
**Production status:** **NO_GO** — see `evidence/EXIT_GATE.json`. This is a substantially complete,
tested reference implementation of the secure capture/restore path; it has **not** run against a real
hypervisor, managed KMS or fleet, and no owner has signed anything off.

MicroVM snapshotting turns a ~100 ms cold boot into a restore — and is also the easiest way to leak one
tenant's memory into another's process or to clone one RNG state into many guests. INV-26 binds every
snapshot to tenant, workload, environment, site and device model; stores it only as authenticated ciphertext;
restores only against a one-shot grant; and never lets a restored guest run before fresh entropy is
acknowledged.

## What is in the box
| Module | Role |
|---|---|
| `service.py` | the public boundary (`SnapshotService.handle`) and the full capture/restore/delete/quarantine/disable path, reconcile, scrub, gc, rewrap, health, explain |
| `hypervisor.py` | `HypervisorPort`; Firecracker and Cloud Hypervisor REST-over-UDS adapters; vsock entropy injector with proof-of-receipt; reference VMM |
| `crypto.py` | AES-256-GCM chunked envelope, `KeyService` port, `LocalKeyService` (versions, rotate, rewrap, disable, destroy) |
| `auth.py` | EdDSA credentials, trust store (role/trust-domain/revocation), capabilities, restore grants |
| `metastore.py` | durable WAL + image metadata store, CAS transactions, leases/fencing, export/import |
| `storage.py` | `BlobStore` port; durable filesystem adapter |
| `config.py` | `PK_SNAPSHOT_CONFIG/1`, overlays, validation, atomic activation, provenance, rollback |
| `resilience.py` | deadlines, bounded retry + budget, circuit breakers, admission control |
| `schema.py`, `errors.py`, `lifecycle.py`, `policy.py` | typed schemas + bounded parser, error catalog, state machine, tier/precedence/outage policy |
| `telemetry.py`, `explain.py`, `audit.py`, `redaction.py` | metrics/logs/trace/health, decision records, tamper-evident audit, secret redaction |
| `snapshot.py`, `contract.py`, `component.py` | the 5.0.0 domain model (kept, still tested) and the `pk_core` conformance adapter |
| `tools/` | evidence producers: fuzz, faults, drills, bench, soak, rtm, release, gate, preflight, bootstrap, smoke |

## Running it
```
python -m unittest discover -s inv26_microvm_snapshotting/tests -t .     # 106 tests; 3 skip without pk_core
python -m inv26_microvm_snapshotting.tools.run_evidence                  # all evidence + exit gate
python -m inv26_microvm_snapshotting.tools.gate --selftest               # verdict + fail-closed self-test
python -m inv26_microvm_snapshotting.tools.release all --dist dist       # wheel, sdist, SBOM, SHA256SUMS, DSSE
```
`pk_core` (needed only by `contract.py`/`component.py`) is not included; `COMPONENT` resolves lazily and
fails loudly without it, and the gate counts the skipped conformance tests as a blocker.

## Where to read next
`COMPONENTS_STATUS.json` / `REQUIREMENTS_TRACEABILITY.md` (per-control status and evidence) ·
`AUDIT_REPORT.md` (what changed, what was found) · `ADR-0001-microvm-snapshotting.md` · `THREAT_MODEL.md` ·
`SEMANTICS.md` · `INTERFACES.md` · `SECURITY.md` · `CONFIGURATION.md` · `FAILURE_MODEL.md` · `BENCHMARKS.md` ·
`OBSERVABILITY.md` · `RUNBOOK.md` · `INCIDENT_RESPONSE.md` · `GOVERNANCE.md`.

## Day-0 / day-1 / day-2
See `RUNBOOK.md`. The emergency switch is `handle("disable", <admin credential>, {"reason": …})`.
