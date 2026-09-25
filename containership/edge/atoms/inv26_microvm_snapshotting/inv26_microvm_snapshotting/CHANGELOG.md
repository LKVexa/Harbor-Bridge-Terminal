# Changelog - INV-26

## 6.0.0 - 2026-09-23

Missing-component pass driven by `source/INV-26_v5.0.0_Missing_Component_Engineering_Checklist.md`
(87 missing controls, C086 partial, X001-X014), applied through the junkyard chop shop.

### Added (runtime)
- `service.py`: SnapshotService public boundary with the complete secure capture/restore path, delete with
  crypto-erase, quarantine/release, emergency disable, reconcile, scrub, metadata GC, KEK rewrap, health, explain.
- `hypervisor.py`: Firecracker and Cloud Hypervisor REST-over-UDS adapters (guest loaded paused, resumed only after
  entropy ack, destroyed on failure), vsock entropy injector with sha256(seed||nonce) proof, reference VMM.
- `crypto.py`: AES-256-GCM chunked envelope with context-bound AAD, KeyService port, LocalKeyService.
- `auth.py`: EdDSA credentials, trust store with roles/trust domains/revocation, deny-by-default capabilities,
  break-glass, one-shot restore grants.
- `metastore.py`: durable WAL/image metadata store with CAS, cross-process flock, torn-tail recovery, compaction
  epochs, leases + fencing tokens, checksummed export/import.
- `storage.py`, `config.py`, `resilience.py`, `schema.py`, `errors.py`, `lifecycle.py`, `policy.py`, `explain.py`.
- Carried from the owner's INV-68 4.3.0: `redaction.py`, `audit.py`, `provenance.py`, `telemetry.py` (adapted).
### Added (evidence/tooling)
- 106 unit/integration/concurrency/threat tests (normal and -O), fuzz, fault matrix (crash at every durable
  write), drills, benchmark + regression gate, soak, RTM generator/checker, release build/verify/install check,
  exit gate with fail-closed self-test, preflight/bootstrap/smoke, CI workflow.
- Governance and operations documents plus machine-readable ops/ files (see README).
### Changed
- Package imports no longer require `pk_core`; `COMPONENT`/`build_contract` resolve lazily.
- `contract.py`: owns envelope/grant/metadata; KMS and blob storage declared as upstream dependencies.
### Defects found and fixed by this pass (each has a regression test)
- FZ-1 config validation crashed when a section was not an object.
- FZ-2 envelope opening raised KeyError on incomplete envelope metadata.
- FZ-3 config validation raised KeyError when a nested key was missing.
- FI-1 a failure after the capture commit point deleted the committed snapshot's blob (AVAILABLE but unreadable);
  commit is now one transaction and post-commit failures never undo it.
- FI-2 an unreachable storage root escaped as SNAP_INTERNAL; now SNAP_STORAGE_UNAVAILABLE.
- MS-1 the metastore aliased the caller's dict, so post-commit mutation changed committed in-memory state.
- HV-1 (design review, before first run) overwriting the Firecracker File memory backend after load would corrupt
  a MAP_PRIVATE-mapped guest; mapped memory files are unlinked only.
- PERF-1 whole-blob SHA-256 on the restore hot path: 16 MiB restore p50 76 ms -> ~32 ms, 1 MiB 5.8 -> ~2.8 ms.
### Not done (see COMPONENTS_STATUS.json)
- No real VMM/KMS/object store/fleet; pk_core absent; no owner or reviewer sign-off; exit gate NO_GO.

## 5.0.0 - 2026-09-23

Security and correctness hardening with a breaking interface revision.

- Moved security-sensitive snapshot logic into dependency-free `snapshot.py`.
- Replaced the 64-bit truncated device fingerprint with full SHA-256 over strict canonical device identifiers.
- Added tenant, workload, and environment binding and refusal on restore.
- Added thread-safe capture/restore state and a read-only snapshot view.
- Added fresh 256-bit entropy generation per successful restore, injectable guest-RNG hook, fail-closed injection errors, and non-secret SHA-256 reseed proof.
- Added finite/non-negative timing validation and real monotonic measurement when no fixture duration is supplied.
- Bumped interfaces to `PK_SNAPSHOT/2` and `PK_SNAPSHOT_RESTORE/2`.
- Added 10 standalone unit/security/concurrency tests that run without `pk_core`.
- Removed the stale README claim that `MASTER.md` was present.

## 4.1.0 - 2026-09-22

Audit, fix and hardening pass (junkyard chop-shop).

### Systemic hardening

- component.py: every bare `assert` in the reference implementation and assess_* bands replaced by `_verify()`, so behavioural checks still run under `python -O` (previously stripped; INV-05 and GAP-12 crashed outright under -O because asserts carried side effects).
- component.py: every try/except that backs a finding with an expected refusal now has an `else:` that fails the check when the refusal does not happen, instead of silently keeping the contract-derived default finding.
- tests/test_component.py: new stdlib conformance test (100 findings, no unexpected partial/blocked, python -O parity, version pin).
- VERSION file and `__version__` added.

### Defects fixed

- component.py::SnapshotStore.restore: unknown snapshot name raised a bare KeyError; negative elapsed_ms accepted -> SnapshotNotFound(KeyError) / ValueError
- component.py::SnapshotStore.capture: a capture with an existing name silently overwrote it, letting another tenant rebind/replace a snapshot (defeats tenant binding) -> SnapshotExists; also validate non-empty ids and positive memory_mib
- component.py::model_fingerprint: "|".join encoding collided ({"a|b"} vs {"a","b"}), so a changed model could match -> JSON-encode the sorted device list
- component.py::assess_security (items[4]): signed an unrelated literal blob and cited SnapshotStore.capture, which signs nothing -> added Snapshot.canonical(); the finding now signs the real capture record and shows a tenant-rebound record fails verification (claim reworded to what is demonstrated; status unchanged)

### Gate

All 100 requirements satisfied under python and python -O.

## 4.0.0

- Initial master-applied component (Post-Kubernetes Master Prompt & Workflow Series v4.0.0).
