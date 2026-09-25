# INV-25 MicroVM Devices — 4.2.0 Audit Report

Audit date: 2026-09-23

## Result

The standalone repository was parsed, repaired, hardened, version-bumped from 4.1.0 to 4.2.0, and re-tested. The core catalogue rules now have dependency-free unit coverage and machine-readable schemas. The archive still cannot be certified as a complete production implementation because several required platform, evidence, and operational components are outside the archive or absent.

## Fixed in this pass

1. **Standalone verification blind spot** — prior tests were all skipped when `pk_core` was unavailable. Added `model.py` plus dependency-free tests.
2. **Weak input validation** — added closed-fail validation of environment, device names, classes, versions, register identifiers, rationale, reviewer, and entry type.
3. **No implemented explicit replacement path** — prior error text required an “explicit replacement” but no method existed. Added `DeviceCatalogue.replace()` with mandatory version change and surface-diff output.
4. **Public interface schemas absent** — added JSON Schemas for `PK_DEVICE_CATALOGUE/1` and `PK_DEVICE_SURFACE_DIFF/1`.
5. **Catalogue serialization unspecified in code** — added deterministic `export()` output matching the catalogue schema.
6. **Stale packaging claim** — README claimed `MASTER.md` was carried in the archive, but it was absent. Documentation now states this accurately.
7. **Version consistency** — bumped `VERSION`, package `__version__`, tests, README, and changelog to 4.2.0.

## Missing or externally required components after remediation

The following are the remaining gaps visible from this archive. Items explicitly outside INV-25 ownership are identified separately so they are not mistaken for implementation defects.

### A. Release-certification blockers in this standalone archive

1. **`pk_core` runtime/framework** — `component.py` and `contract.py` depend on `pk_core`, but it is not packaged here. As a result, the 100-item component assessment, evidence emission, gate evaluation, and optimized-mode integration test cannot run in this archive alone. A supported `pk_core` package/path and compatibility version are required.
2. **Historical `MASTER.md` audit corpus** — the previous README declared it present, but the file is absent. If verbatim master prompts/workflows are required as audit evidence, the authoritative file must be restored from its source. It was not fabricated during remediation.
3. **Machine-readable production gate evidence** — no generated `evidence/pk_evidence.jsonl` or `conformance/PK_GATE_RESULTS.json` is included. These must be produced by the surrounding `pk_core` gate flow before a production certification claim.
4. **Pinned dependency/release manifest** — there is no `pyproject.toml`, requirements/lock file, or equivalent declaration pinning the `pk_core` compatibility range and supported Python versions. This leaves build/release reproducibility under-specified.
5. **CI/release automation** — no workflow is present to run standalone tests, `pk_core` integration tests, optimized-mode checks, schema validation, and release gating on every change.

### B. Checklist evidence not implemented by this package itself

These capabilities are required by the 100-item checklist but are not evidenced by concrete local artifacts beyond generic contract declarations. They need platform-level implementation or additional repository artifacts before they can be independently certified:

6. **Named accountable owner and escalation procedure** (`C009`, `C097`).
7. **Approved ADR for virtio-net/virtio-block technology choices** (`C010`).
8. **Requirements traceability matrix** linking each checklist requirement to implementation and test/evidence artifacts (`C020`).
9. **Authentication/authorization boundary specification** for whichever control plane consumes the catalogue (`C023`–`C024`).
10. **Structured machine-readable error-code contract** beyond Python exceptions (`C026`).
11. **Peer-version compatibility matrix and negotiation policy** (`C027`, `C093`).
12. **Interface/resource ceilings** such as maximum device count, maximum registers per device/catalogue, and payload constraints (`C017`, `C028`, `C067`).
13. **Adjacent-layer integration tests** against the actual MicroVM runtime, high-performance I/O layer, snapshotting peer, and policy engine (`C030`, `C083`).
14. **Pinned virtio specification/implementation versions** and approved compatibility targets (`C031`, `C084`).
15. **Configuration provenance/activation record** and atomic configuration transaction mechanism (`C036`–`C038`).
16. **Artifact signature/digest/provenance verification** for policy or catalogue artifacts (`C045`).
17. **Tamper-evident security audit event implementation** for catalogue registration/replacement/rejection (`C049`).
18. **Adversarial/fuzz testing** for malformed/untrusted catalogue data and policy/control-plane boundaries (`C050`, `C085`, `C087`).
19. **Fault-injection and recovery testing** across dependency/control-plane failures (`C060`, `C089`).
20. **Performance benchmark corpus and release thresholds** for startup, CPU, memory, density, and tail latency (`C061`–`C070`, `C088`).
21. **Runtime telemetry implementation**: health/readiness endpoint or report, structured metrics/logs/traces, decision reasons, explain view, retention/export policy, dashboards and alerts (`C071`–`C080`). The contract names signals but this archive does not emit them.
22. **Cross-architecture/hypervisor compatibility test matrix** (`C084`).
23. **Concurrency/race test suite** for any shared or remotely managed catalogue implementation (`C086`). The in-memory model itself is not documented as thread-safe.
24. **Formal production acceptance evidence policy** and signed/immutable release gate artifact (`C090`, `C100`).
25. **Canary/staged rollout automation, emergency-disable implementation, and rollback tooling** beyond narrative README guidance (`C092`).
26. **Vulnerability response/EOL policy and recurring review process** (`C094`, `C098`).
27. **Exception/waiver/technical-debt register with owner and expiry** (`C099`).
28. **License/SBOM/supply-chain metadata** — not explicitly named as standalone checklist files, but needed to substantiate supply-chain/provenance controls and ordinary distributable-repository governance. No license, SBOM, or provenance manifest is present in this archive.

### C. Explicit non-ownership / external architectural dependencies

These are intentionally not implemented by INV-25 and should remain separate components rather than being added to this repository:

- Device backend implementations.
- MicroVM lifecycle/runtime implementation (`INV-24`).
- High-performance I/O datapath/backend (`INV-35`).
- Guest drivers.
- Snapshot serialization (`INV-26`).
- Device-permission policy engine (`GAP-13`).
- Transient-execution defense (`INV-43`, optional peer dependency).

## Re-audit conclusion

Version 4.2.0 materially improves the repository's fail-closed behavior, explicit change control, interface definition, and standalone testability. No known silent-overwrite path remains in the catalogue model, unknown device classes fail closed, malformed identifiers are rejected, and changed entries require an explicit versioned replacement.

The repository should **not** yet be described as independently production-certified: the full `pk_core` conformance/gate flow is unavailable in this archive, and the platform/operations evidence listed above remains missing or external.

## Addendum — 4.3.0 (2026-09-23)

The missing-components checklist was executed. Status of every work item: `WORK_ORDER_STATUS.md`. Gate: `conformance/PK_GATE_RESULTS.json` (NO_GO — see blocking list).
