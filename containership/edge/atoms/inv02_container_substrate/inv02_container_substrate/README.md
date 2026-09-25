# INV-02 - Container substrate

**Version:** 5.0.0  
**Group:** 01_Source_Inventory  
**Series:** Post-Kubernetes Master Prompt & Workflow Series v4.0.0  
**Checklist:** 100 requirements across ten dimensions in `CHECKLIST.json`

INV-02 provides a **reference image-identity and integrity model** for the container substrate. It resolves image references to content digests, verifies manifests and layers, refuses mutable tags in protected environments, de-duplicates shared layers, records bounded provenance/resolution history, and supports quarantine of suspect content.

> Scope boundary (v5.0.0): the package now provides a stdlib-only production substrate — OCI image model, durable content store, registry client, layer unpack/snapshotter, OCI runtime-spec generation and a runc/crun/runsc/kata adapter, cgroups v2, admission policy, supply-chain verification, audit and observability. It drives an OCI runtime; it is not a kernel-level runtime, a registry service, an image builder or an orchestrator. Per-component status for all 78 checklist components is in `COMPONENT_STATUS.json`; the distribution contract is `MASTER.md`.

## v5.0.0 modules

| Module | Provides |
|---|---|
| `oci.py` | OCI image-spec v1.1 descriptors/manifests/indexes/configs, artifacts, platform selection |
| `store.py` | crash-safe CAS, metadata DB, compare-and-swap tags, resumable ingest, leases + GC, fsck/repair, durable two-person quarantine, backup/restore |
| `distribution.py` | OCI Distribution pull client: Bearer/Basic auth, TLS policy, mirrors (digest-only), offline mode, Range resume |
| `rootfs.py` | streaming layer unpack with escape/bomb defences and whiteouts, ChainID snapshotter, bind-mount policy |
| `runtime.py` | OCI runtime spec with fail-closed defaults (seccomp default-deny, no caps, NNP, read-only rootfs, userns, masked paths), cgroups v2, lifecycle state machine, runtime adapter, supervisor, secrets as files |
| `trust.py` | pure-Python Ed25519 (RFC 8032 vectors), keyring rotation/revocation, DSSE + in-toto/SLSA, SBOM ingestion, scan states |
| `policy.py` | admission engine with explanations, tenant isolation, waiver registry |
| `audit.py` · `observability.py` · `resilience.py` · `timeutil.py` · `config.py` · `migrations.py` | hash-chained audit ledger · metrics/logs/traces/health · quotas/admission/retry/breaker · deadlines · config · schema migrations |

## Responsibility

Own image identity and integrity: digest resolution, manifest/layer verification, mutable-tag policy by environment, layer de-duplication, and reference-model provenance.

## Owns

- Tag-to-digest resolution
- Manifest and layer digest verification
- Protected-environment mutable-tag policy
- Content-addressed layer de-duplication
- Bounded in-memory resolution/provenance records
- Quarantine/release controls for suspect content in the reference model

## Explicitly does not own

- Image building
- Runtime execution
- Host/container hardening policy
- Registry service operation
- Signing keys
- Orchestration

## Interfaces

- `policy` - `PK_IMAGE_TAGPOLICY/1` - where mutable tags are allowed
- `resolve` - `PK_IMAGE_RESOLVE/1` - reference to digest
- `verify` - `PK_IMAGE_VERIFY/1` - manifest and layer verification

## v4.2.0 hardening

- Added strict reference, name, tag, digest, and environment validation.
- Closed production-policy bypasses caused by exact-string matching (`PRODUCTION`, `prod`, and padded values).
- Digest resolution now requires the manifest to exist and not be quarantined.
- Added bounded layer/image/manifest/reference/history limits.
- Added schema-versioned, deterministic manifests with declared layer sizes while retaining v4.1.0 manifest read compatibility.
- Added defensive manifest parsing with normalized error types.
- Added `RLock` protection around compound registry operations.
- Added bounded provenance records for tag movement.
- Added quarantine/release controls.
- Made the stdlib-only registry model importable without `pk_core`; conformance exports load lazily.
- Added standalone tests that run even when `pk_core` is absent.

## Validation

From the directory containing this package:

```text
python -m compileall -q inv02_container_substrate
python -m unittest discover -s inv02_container_substrate/tests -t . -v
python -O -m unittest discover -s inv02_container_substrate/tests -t . -v
python -m inv02_container_substrate.tools.release_evidence      # evidence/, SBOM, manifest, gate verdict
python -m inv02_container_substrate.tools.bench                 # capacity numbers
```

`tests/integration/test_runc.py` runs real containers when root + `runc` + `gcc` are present and skips with a stated reason otherwise; set `INV02_SKIP_INTEGRATION=1` to skip explicitly. `INV02_FUZZ_ITERS` scales the fuzz campaign.

`tests/test_registry.py` is self-contained and does not require network access or `pk_core`.
`tests/test_component.py` exercises the estate-wide 100-requirement conformance adapter when `pk_core` is available. If `pk_core` is not installed or supplied through `PK_CORE_PATH`, those conformance tests are intentionally skipped rather than reported as passing.

## pk_core integration

When the estate framework is present:

```text
python inv02_container_substrate/tests/test_component.py
python -m pk_core list
python -m pk_core run INV-02 --evidence evidence/pk_evidence.jsonl
python -m pk_core gate INV-02 --out conformance/PK_GATE_RESULTS.json
python -m pk_core verify evidence/pk_evidence.jsonl
```

## Day-0 / day-1 / day-2

- **Day 0:** import the package, run the standalone tests, then run `pk_core run INV-02` in the full estate checkout and archive the evidence ledger.
- **Day 1:** run the gate before deployment; reject a `NO_GO` result and explicitly record conditions for any conditional result.
- **Day 2:** re-run tests/gates on contract or implementation changes and verify evidence continuity before release.

## Package notes

`MASTER.md` is restored in v5.0.0. See `AUDIT_REPORT.md` for the audit history, `COMPONENT_STATUS.json` / `CHECKLIST_v5.0.0_ANNOTATED.md` for per-component status, and `docs/operations/OPERATIONS.md` for runbooks. Owner actions still open: licence (`LICENSE-STATUS.md`), named owners (`OWNERS.yaml`), approval of the SLA/EOL defaults (`SECURITY.md`).
