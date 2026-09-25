# Continuation after UC-2.3.0

The attached 96,000-task series remains the authoritative detailed backlog. This document records what the implementation pass did not complete. No component was promoted.

## Next dependency route

Finish review and integration of UC-M01.01–01.08, then the UC-M07.01/07.05/07.08 local transaction/capacity/recovery qualifications and UC-M12.03/12.04 fault campaign. In parallel, select and pin one actual library-OS guest target and its toolchain. Do not replace a real guest with a host interpreter under a different label.

For the first guest, link one supported C engine and nontrivial workload into a guest image; boot it; verify actual semantic output; supervise and stop it; restore a validated checkpoint. Then qualify host restrictions, authorization, independent artifact trust, resource bounds and operational health. Optional federation stays unimplemented until separate multi-host gates pass.

Current blockers include guest boot/ABI and library-OS selection; VMM/tender; sandbox/default-deny networking; aggregate CPU/memory/process/I/O quotas; authentication/authorization; independent signatures and update trust; full live epoch/checkpoint rollover; history-aware GC; actual Windows/macOS qualification; and native parser/escape assessment.

## Per-component disposition

### UC-M01.01 — Trust-boundary and capability model

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: None; foundational decision.

Local trust model and honest capability/assurance declarations. No independent review, authorization, guest or host isolation.

**Original acceptance remains:** A reviewed threat model maps every entry point to its actual enforcement boundary; no declaration is labeled enforcement.

Related artifacts: `docs/CONTROL_CONTRACTS.md`, `ship/unikernel/contracts.py`.

### UC-M01.02 — Versioned runtime and guest contracts

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M01.01

Versioned strict validation and local CLI surfaces. No real guest boot/stop/restore adapter; contract-check is validation only.

**Original acceptance remains:** Contract tests reject unknown incompatible versions, duplicate fields and unsupported capabilities before mutation.

Related artifacts: `ship/unikernel/contracts.py`, `ship/unikernel/foundation_cli.py`.

### UC-M01.03 — Lifecycle state machine

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M01.02

Durable local operation model. Not a continuous reconciler or guest-readiness implementation; SQLite and file journal reconciled through recovery.

**Original acceptance remains:** Every transition has a durable reason and legal predecessor; failed readiness cannot produce a running status.

Related artifacts: `ship/unikernel/control_store.py`.

### UC-M01.04 — Canonical manifest and schema evolution

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M01.02

Ship-layer duplicate-safe bounded JSON and integer-only canonical format for new contracts. No migration of historical hull formats or complete schema migration framework.

**Original acceptance remains:** Equivalent manifests hash consistently; malicious duplicates and lossy downgrade migrations are rejected.

Related artifacts: `ship/unikernel/strictjson.py`, `ship/unikernel/contracts.py`.

### UC-M01.05 — Stable workload identity and generations

**PARTIAL_ADVANCE** · Source MISSING · P1 · Milestone A

Prerequisites: UC-M01.03, UC-M01.04

Immutable local IDs and monotonic generations guard cooperating CLI result publication. Direct filesystem/native writers are not fenced by a kernel boundary.

**Original acceptance remains:** A stale process cannot write state or publish results for a replacement with the same display name.

Related artifacts: `ship/unikernel/control_store.py`, `ship/unikernel/cli.py`.

### UC-M01.06 — Closed-world source and dependency inventory

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M01.04

No component acceptance claimed in this application pass. Required work remains: Every original archive member is either hash-accounted cargo or has a documented policy disposition; no silently lost dependencies.

**Original acceptance remains:** Every original archive member is either hash-accounted cargo or has a documented policy disposition; no silently lost dependencies.

### UC-M01.07 — Application semantics versus witness contract

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M01.02, UC-M01.06

No component acceptance claimed in this application pass. Required work remains: A nontrivial application passes semantic input/output tests on its target; a row-sequence hash alone never satisfies execution.

**Original acceptance remains:** A nontrivial application passes semantic input/output tests on its target; a row-sequence hash alone never satisfies execution.

### UC-M01.08 — Artifact and dependency graph

**PARTIAL_ADVANCE** · Source MISSING · P1 · Milestone A

Prerequisites: UC-M01.04, UC-M01.06

Typed DAG validation and exact descendant reporting. Caller-supplied graph; no automatic authoritative build/state/evidence invalidation integration.

**Original acceptance remains:** Changing any dependency invalidates exactly the affected images/evidence; cycles and missing dependencies are rejected.

Related artifacts: `ship/unikernel/artifacts.py`.

### UC-M02.01 — Chosen library-OS integration

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M01.07

No component acceptance claimed in this application pass. Required work remains: A clean build links the application and only required OS libraries into a guest image, not a host Python command.

**Original acceptance remains:** A clean build links the application and only required OS libraries into a guest image, not a host Python command.

### UC-M02.02 — Boot ABI and startup path

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.01

No component acceptance claimed in this application pass. Required work remains: The chosen VMM loads the image and reaches a guest-originated ready signal without a conventional guest OS boot.

**Original acceptance remains:** The chosen VMM loads the image and reaches a guest-originated ready signal without a conventional guest OS boot.

### UC-M02.03 — Linker, image layout and permissions

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.02

No component acceptance claimed in this application pass. Required work remains: Malformed images are rejected; executable and writable regions follow the selected platform protection policy.

**Original acceptance remains:** Malformed images are rejected; executable and writable regions follow the selected platform protection policy.

### UC-M02.04 — Guest allocator and memory lifecycle

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.03

No component acceptance claimed in this application pass. Required work remains: Memory exhaustion yields a documented failure without host escape or cross-guest corruption.

**Original acceptance remains:** Memory exhaustion yields a documented failure without host escape or cross-guest corruption.

### UC-M02.05 — Guest execution loop and scheduling

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.02, UC-M02.04

No component acceptance claimed in this application pass. Required work remains: A deliberately non-terminating workload can be stopped at the host boundary and cannot starve other guests.

**Original acceptance remains:** A deliberately non-terminating workload can be stopped at the host boundary and cannot starve other guests.

### UC-M02.06 — Clock and entropy interfaces

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.02

No component acceptance claimed in this application pass. Required work remains: Replay uses recorded inputs while security keys never derive from deterministic witness seeds or replay clocks.

**Original acceptance remains:** Replay uses recorded inputs while security keys never derive from deterministic witness seeds or replay clocks.

### UC-M02.07 — Minimal console, block and transport drivers

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.02, UC-M02.04

No component acceptance claimed in this application pass. Required work remains: Malformed descriptors and unavailable devices fail safely; no unused device is exposed by default.

**Original acceptance remains:** Malformed descriptors and unavailable devices fail safely; no unused device is exposed by default.

### UC-M02.08 — Guest ABI conformance and panic reporting

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M02.03, UC-M02.05, UC-M02.06, UC-M02.07

No component acceptance claimed in this application pass. Required work remains: A boot-success artifact includes image digest, ABI version, workload output and intentionally induced panic evidence.

**Original acceptance remains:** A boot-success artifact includes image digest, ABI version, workload output and intentionally induced panic evidence.

### UC-M03.01 — Pluggable execution backend boundary

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M01.02, UC-M02.08

Host-process isolation class is explicit; hypervisor-required admission refuses before execution. No VMM/tender implementation.

**Original acceptance remains:** An isolation-required workload cannot silently fall back to an in-process or ordinary subprocess adapter.

Related artifacts: `ship/unikernel/contracts.py`, `ship/unikernel/cli.py`.

### UC-M03.02 — Real hypervisor or tender integration

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.01

No component acceptance claimed in this application pass. Required work remains: Two guest instances are independently booted, inspected and stopped; host-only VM interpreter runs cannot pass this gate.

**Original acceptance remains:** Two guest instances are independently booted, inspected and stopped; host-only VM interpreter runs cannot pass this gate.

### UC-M03.03 — Host process sandbox profile

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.02

No component acceptance claimed in this application pass. Required work remains: An adversarial guest cannot access unrelated host files or make forbidden host operations through exposed devices.

**Original acceptance remains:** An adversarial guest cannot access unrelated host files or make forbidden host operations through exposed devices.

### UC-M03.04 — Enforced default-deny networking

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.03

No component acceptance claimed in this application pass. Required work remains: A guest traffic probe demonstrates denied egress and lateral access; policy text alone is not evidence.

**Original acceptance remains:** A guest traffic probe demonstrates denied egress and lateral access; policy text alone is not evidence.

### UC-M03.05 — CPU, memory, I/O and process quotas

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.03

No component acceptance claimed in this application pass. Required work remains: Memory, fork, log and I/O flood probes remain inside quota and preserve another guest's health.

**Original acceptance remains:** Memory, fork, log and I/O flood probes remain inside quota and preserve another guest's health.

### UC-M03.06 — Supervisor, watchdog and child-tree cleanup

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M03.01, UC-M03.05

Bounded helper subprocess capture, deadlines and POSIX process-group cleanup. Not a global child registry, crash-persistent supervisor, cgroup quota or adversarial tree boundary. Windows branch untested.

**Original acceptance remains:** Timeout and parent crash leave no executable orphan; failure reason and last bounded log survive.

Related artifacts: `ship/unikernel/supervisor.py`, `ship/unikernel/engines.py`, `ship/unikernel/gates.py`.

### UC-M03.07 — Privilege-separated resource broker

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.03

No component acceptance claimed in this application pass. Required work remains: Unprivileged ship operation succeeds with only narrowly scoped broker requests; arbitrary paths and commands are denied.

**Original acceptance remains:** Unprivileged ship operation succeeds with only narrowly scoped broker requests; arbitrary paths and commands are denied.

### UC-M03.08 — Host capability and isolation evidence

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M03.02, UC-M03.04, UC-M03.05

No component acceptance claimed in this application pass. Required work remains: Admission records the selected backend and verified constraints; unavailable virtualization blocks rather than degrades security.

**Original acceptance remains:** Admission records the selected backend and verified constraints; unavailable virtualization blocks rather than degrades security.

### UC-M04.01 — Locked toolchain and dependency closure

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone B

Prerequisites: UC-M01.08

No component acceptance claimed in this application pass. Required work remains: Build works from an explicit dependency cache without implicit PATH/download substitutions; missing inputs are refused.

**Original acceptance remains:** Build works from an explicit dependency cache without implicit PATH/download substitutions; missing inputs are refused.

### UC-M04.02 — Hermetic and reproducible build recipe

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M04.01

No component acceptance claimed in this application pass. Required work remains: Two isolated clean builders produce matching declared image digests or a precisely documented reproducibility boundary.

**Original acceptance remains:** Two isolated clean builders produce matching declared image digests or a precisely documented reproducibility boundary.

### UC-M04.03 — Sandboxed build workers

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M03.03, UC-M03.05, UC-M04.01

No component acceptance claimed in this application pass. Required work remains: A hostile build cannot read operator secrets, contact unapproved endpoints or persist outside its workspace.

**Original acceptance remains:** A hostile build cannot read operator secrets, contact unapproved endpoints or persist outside its workspace.

### UC-M04.04 — Semantic translation validation

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone B

Prerequisites: UC-M01.07, UC-M02.08

No component acceptance claimed in this application pass. Required work remains: Generated and hand-written semantic test programs agree under edge cases; unsupported features are refused explicitly.

**Original acceptance remains:** Generated and hand-written semantic test programs agree under edge cases; unsupported features are refused explicitly.

### UC-M04.05 — Immutable content-addressed image store

**PARTIAL_ADVANCE** · Source MISSING · P0 · Milestone B

Prerequisites: UC-M01.04, UC-M04.02

Local bounded atomic content-addressed blobs. Images/builds not automatically enrolled; no signer authentication, GC, remote store or corruption quarantine workflow.

**Original acceptance remains:** Interrupted publication exposes no partial image; a modified blob is rejected even when its filename matches.

Related artifacts: `ship/unikernel/artifacts.py`.

### UC-M04.06 — Software bill of materials and license inventory

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone B

Prerequisites: UC-M04.01, UC-M04.05

No component acceptance claimed in this application pass. Required work remains: Every linked or shipped runtime dependency maps to a source/version/license and a reviewable provenance record.

**Original acceptance remains:** Every linked or shipped runtime dependency maps to a source/version/license and a reviewable provenance record.

### UC-M04.07 — Build provenance attestations

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone B

Prerequisites: UC-M04.02, UC-M04.05

No component acceptance claimed in this application pass. Required work remains: An independent verifier reconstructs the build relationship and rejects altered subjects or unknown builders.

**Original acceptance remains:** An independent verifier reconstructs the build relationship and rejects altered subjects or unknown builders.

### UC-M04.08 — Authenticated image admission

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone B

Prerequisites: UC-M04.05, UC-M04.07

No component acceptance claimed in this application pass. Required work remains: An intact but self-signed or unapproved image is rejected; signature policy failure never becomes a checksum-only pass.

**Original acceptance remains:** An intact but self-signed or unapproved image is rejected; signature policy failure never becomes a checksum-only pass.

### UC-M05.01 — Executable workload DAG planner

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M01.07, UC-M01.08, UC-M03.01

No component acceptance claimed in this application pass. Required work remains: A multi-step workload executes dependencies exactly in the required order and publishes explicit outputs.

**Original acceptance remains:** A multi-step workload executes dependencies exactly in the required order and publishes explicit outputs.

### UC-M05.02 — Resource-aware placement scheduler

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M03.05, UC-M05.01

No component acceptance claimed in this application pass. Required work remains: An infeasible workload is queued or refused; placement never violates a hard resource or ISA constraint.

**Original acceptance remains:** An infeasible workload is queued or refused; placement never violates a hard resource or ISA constraint.

### UC-M05.03 — Bounded queue and fairness control

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M05.02

No component acceptance claimed in this application pass. Required work remains: Overload produces bounded queues and explicit rejection while admitted tenants receive the chosen fairness guarantee.

**Original acceptance remains:** Overload produces bounded queues and explicit rejection while admitted tenants receive the chosen fairness guarantee.

### UC-M05.04 — Idempotent reconciliation controller

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M01.03, UC-M01.05, UC-M05.01

No component acceptance claimed in this application pass. Required work remains: Restarting the controller or redelivering a command neither duplicates instances nor loses an admitted workload.

**Original acceptance remains:** Restarting the controller or redelivering a command neither duplicates instances nor loses an admitted workload.

### UC-M05.05 — Workload readiness and liveness checks

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M03.06, UC-M05.04

No component acceptance claimed in this application pass. Required work remains: A booted but incorrect or stalled guest is not marked ready; probes have deadlines and output-size limits.

**Original acceptance remains:** A booted but incorrect or stalled guest is not marked ready; probes have deadlines and output-size limits.

### UC-M05.06 — Graceful stop and drain protocol

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M05.04, UC-M05.05

No component acceptance claimed in this application pass. Required work remains: Stop during active I/O either commits or records an interrupted operation without silently reporting completion.

**Original acceptance remains:** Stop during active I/O either commits or records an interrupted operation without silently reporting completion.

### UC-M05.07 — Safe restart and failure budget policy

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M05.05, UC-M05.06

No component acceptance claimed in this application pass. Required work remains: A crash loop cannot consume unbounded resources or repeatedly promote a known-bad image.

**Original acceptance remains:** A crash loop cannot consume unbounded resources or repeatedly promote a known-bad image.

### UC-M05.08 — Replica scaling and placement migration

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P2 · Milestone C

Prerequisites: UC-M05.02, UC-M05.06, UC-M05.07

No component acceptance claimed in this application pass. Required work remains: Scaling out or in respects application state semantics and does not lose accepted requests or bypass quotas.

**Original acceptance remains:** Scaling out or in respects application state semantics and does not lose accepted requests or bypass quotas.

### UC-M06.01 — Machine-stable management API

**PARTIAL_ADVANCE** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M01.02, UC-M05.04

New structured local command results and validation endpoint. No remote authenticated management service or complete legacy CLI/API parity.

**Original acceptance remains:** Contract tests exercise command/API parity and incompatible-version refusal without parsing human log text.

Related artifacts: `ship/unikernel/foundation_cli.py`, `ship/unikernel/cli.py`.

### UC-M06.02 — Operator and service authentication

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M06.01

No component acceptance claimed in this application pass. Required work remains: Unauthenticated and expired identities cannot load, seal, mount, read secrets or stop another workload.

**Original acceptance remains:** Unauthenticated and expired identities cannot load, seal, mount, read secrets or stop another workload.

### UC-M06.03 — Least-privilege authorization

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M06.02

No component acceptance claimed in this application pass. Required work remains: A read-only operator cannot escalate through an indirect command or optional argument.

**Original acceptance remains:** A read-only operator cannot escalate through an indirect command or optional argument.

### UC-M06.04 — Tenant and workspace isolation

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.03, UC-M06.03

No component acceptance claimed in this application pass. Required work remains: Cross-tenant name collisions, aliases and shared-cache references cannot expose mutable data.

**Original acceptance remains:** Cross-tenant name collisions, aliases and shared-cache references cannot expose mutable data.

### UC-M06.05 — Policy-as-code admission evaluator

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M03.08, UC-M04.08, UC-M06.03

No component acceptance claimed in this application pass. Required work remains: A denied policy leaves no child process or externally visible partial workload; policy evidence is recorded.

**Original acceptance remains:** A denied policy leaves no child process or externally visible partial workload; policy evidence is recorded.

### UC-M06.06 — Typed configuration and migration

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M01.04, UC-M06.05

No component acceptance claimed in this application pass. Required work remains: Invalid configuration is rejected atomically and an attempted downgrade cannot weaken an existing workload policy.

**Original acceptance remains:** Invalid configuration is rejected atomically and an attempted downgrade cannot weaken an existing workload policy.

### UC-M06.07 — Secret storage and injection boundary

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.07, UC-M06.04

No component acceptance claimed in this application pass. Required work remains: A redaction test finds no test secret in emitted artifacts, logs, snapshots or another tenant's state.

**Original acceptance remains:** A redaction test finds no test secret in emitted artifacts, logs, snapshots or another tenant's state.

### UC-M06.08 — Tamper-evident operator audit trail

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M06.02, UC-M06.03, UC-M06.05

No component acceptance claimed in this application pass. Required work remains: Changing or removing a recorded sensitive operation is detectable without trusting the same mutable workspace.

**Original acceptance remains:** Changing or removing a recorded sensitive operation is detectable without trusting the same mutable workspace.

### UC-M07.01 — Cross-resource durable transaction coordinator

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M01.03, UC-M01.05

Recoverable snapshots cover named managed files for serialized CLI consumers. Not simultaneous atomic filesystem visibility, hardware power-loss proof or rollback of arbitrary external side effects.

**Original acceptance remains:** Crash injection at every mutation step recovers a coherent old or new generation with no missing cargo.

Related artifacts: `ship/unikernel/transactions.py`, `ship/unikernel/cli.py`.

### UC-M07.02 — Checkpoint and history rollover

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone A

Prerequisites: UC-M07.01

No component acceptance claimed in this application pass. Required work remains: Long-running TIFF state continues after rollover and restores the same state as uninterrupted execution.

**Original acceptance remains:** Long-running TIFF state continues after rollover and restores the same state as uninterrupted execution.

### UC-M07.03 — Atomic multi-container tick commit

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M07.01, UC-M07.02

Selected local tick failures can restore managed berth/studio files through the command journal. No true per-node prepare protocol, guest checkpoint or independently verified full multi-container epoch qualification.

**Original acceptance remains:** Power-loss simulation between any two picture writes never leaves an apparently complete mixed-generation tick.

Related artifacts: `ship/unikernel/transactions.py`.

### UC-M07.04 — Strict state schema and decoder boundary

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M03.05, UC-M07.02

Ship JSON entry points reject duplicates/nonfinite numbers and bound size/depth. Embedded hull decoders are unchanged; no separate bounded decoder worker.

**Original acceptance remains:** Malformed metadata, dimensions, integer fields and nested structures are rejected inside a bounded decoder worker.

Related artifacts: `ship/unikernel/strictjson.py`.

### UC-M07.05 — Workspace capacity reservation

**PARTIAL_ADVANCE** · Source MISSING · P0 · Milestone A

Prerequisites: UC-M03.05, UC-M07.01

Conservative local free-space/retention preflight with disk-full fault tests. Not an OS space reservation or aggregate tenant capacity controller.

**Original acceptance remains:** A low-disk fault stops before destructive commit and preserves a usable recovery copy and clear error record.

Related artifacts: `ship/unikernel/transactions.py`, `ship/unikernel/artifacts.py`.

### UC-M07.06 — Reachability-based garbage collection

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone A

Prerequisites: UC-M04.05, UC-M07.01, UC-M07.05

No component acceptance claimed in this application pass. Required work remains: A concurrent deployment/restore cannot lose a referenced object; dry-run lists exactly the reclaimable bytes.

**Original acceptance remains:** A concurrent deployment/restore cannot lose a referenced object; dry-run lists exactly the reclaimable bytes.

### UC-M07.07 — Portable snapshots and state migrations

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone A

Prerequisites: UC-M02.08, UC-M06.07, UC-M07.02

No component acceptance claimed in this application pass. Required work remains: A snapshot restored on a supported clean host resumes with equivalent application state; incompatible ABI is refused.

**Original acceptance remains:** A snapshot restored on a supported clean host resumes with equivalent application state; incompatible ABI is refused.

### UC-M07.08 — Verified rollback and recovery commands

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone A

Prerequisites: UC-M07.01, UC-M07.03, UC-M07.07

Operator inspection and pending-journal rollback preserve originals and fence identity. Committed historical rollback, portable guest snapshots and general abandon/pruning are deliberately refused or absent.

**Original acceptance remains:** Automated restore returns registry, seals and mount state to a verified generation rather than only moving a directory.

Related artifacts: `ship/unikernel/transactions.py`, `ship/unikernel/foundation_cli.py`.

### UC-M08.01 — Typed guest-host IPC ABI

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M01.02, UC-M02.07, UC-M03.07

No component acceptance claimed in this application pass. Required work remains: Unknown operations, invalid handles and out-of-bounds buffers cannot reach arbitrary host functions.

**Original acceptance remains:** Unknown operations, invalid handles and out-of-bounds buffers cannot reach arbitrary host functions.

### UC-M08.02 — Message framing and versioned serialization

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M08.01

No component acceptance claimed in this application pass. Required work remains: Truncated, oversized, duplicate-field and mismatched-version messages are rejected without desynchronizing the channel.

**Original acceptance remains:** Truncated, oversized, duplicate-field and mismatched-version messages are rejected without desynchronizing the channel.

### UC-M08.03 — Backpressure and bounded channels

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.05, UC-M08.02

No component acceptance claimed in this application pass. Required work remains: Producer floods remain within a measured buffer budget and cannot deadlock unrelated workloads.

**Original acceptance remains:** Producer floods remain within a measured buffer budget and cannot deadlock unrelated workloads.

### UC-M08.04 — Ordering, idempotency and replay semantics

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M01.05, UC-M07.03, UC-M08.02

No component acceptance claimed in this application pass. Required work remains: Repeated or out-of-order messages cannot double-apply a committed external effect or overwrite newer state.

**Original acceptance remains:** Repeated or out-of-order messages cannot double-apply a committed external effect or overwrite newer state.

### UC-M08.05 — Deadlines and cancellation propagation

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M02.06, UC-M03.06, UC-M08.03

No component acceptance claimed in this application pass. Required work remains: Canceled work stops using resources within its specified bound and has a deterministic final disposition.

**Original acceptance remains:** Canceled work stops using resources within its specified bound and has a deterministic final disposition.

### UC-M08.06 — Shared-memory or buffer grant safety

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M06.04, UC-M08.01

No component acceptance claimed in this application pass. Required work remains: Revoked or cross-tenant grants cannot be used after stop, replacement or channel reset.

**Original acceptance remains:** Revoked or cross-tenant grants cannot be used after stop, replacement or channel reset.

### UC-M08.07 — Optional policy-controlled network stack

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone C

Prerequisites: UC-M02.07, UC-M03.04, UC-M06.05

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** The offline profile still has no network access; approved endpoints work and all other routes remain denied.

### UC-M08.08 — Optional service discovery and routing

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone C

Prerequisites: UC-M05.05, UC-M05.06, UC-M08.07

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** A stopped or replaced generation cannot receive newly routed requests after its endpoint is withdrawn.

### UC-M09.01 — Independent key lifecycle

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M04.08, UC-M06.03

No component acceptance claimed in this application pass. Required work remains: A revoked signer cannot admit new images; one compromised online role cannot mint a new trusted root.

**Original acceptance remains:** A revoked signer cannot admit new images; one compromised online role cannot mint a new trusted root.

### UC-M09.02 — Anti-rollback update metadata

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M09.01

No component acceptance claimed in this application pass. Required work remains: Older, expired or inconsistent metadata cannot silently replace a newer approved release.

**Original acceptance remains:** Older, expired or inconsistent metadata cannot silently replace a newer approved release.

### UC-M09.03 — Verified executable-cache reads

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M04.05, UC-M06.05, UC-M09.01

No component acceptance claimed in this application pass. Required work remains: Changing a cached adapter or native executable blocks execution even when the original hold ZIP still matches its pin.

**Original acceptance remains:** Changing a cached adapter or native executable blocks execution even when the original hold ZIP still matches its pin.

### UC-M09.04 — Image-state-policy binding

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M01.05, UC-M07.07, UC-M09.01

No component acceptance claimed in this application pass. Required work remains: State replay from a different image or tenant is rejected before guest execution.

**Original acceptance remains:** State replay from a different image or tenant is rejected before guest execution.

### UC-M09.05 — Proof and digest assurance hierarchy

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M01.07, UC-M04.04, UC-M06.05

Separate declared assurance classes and refuse complete/isolated promotion with skipped or absent prerequisites. Not independent signature, semantic or isolation certification.

**Original acceptance remains:** No promotion rule treats a deterministic hash witness as proof of arbitrary program correctness or authority.

Related artifacts: `ship/unikernel/contracts.py`, `ship/unikernel/gates.py`.

### UC-M09.06 — Native runtime memory-safety audit

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M02.08, UC-M03.02

No component acceptance claimed in this application pass. Required work remains: Adversarial image/bytecode corpora complete without sanitizer findings; each remaining finding has an explicit blocker.

**Original acceptance remains:** Adversarial image/bytecode corpora complete without sanitizer findings; each remaining finding has an explicit blocker.

### UC-M09.07 — Guest escape and side-channel assessment

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M03.03, UC-M03.04, UC-M03.05, UC-M09.06

No component acceptance claimed in this application pass. Required work remains: Independent tests and host configuration evidence support the declared tenant boundary; unsupported threats are clearly excluded.

**Original acceptance remains:** Independent tests and host configuration evidence support the declared tenant boundary; unsupported threats are clearly excluded.

### UC-M09.08 — Security advisory and dependency response

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M04.06, UC-M09.01, UC-M09.02

No component acceptance claimed in this application pass. Required work remains: A simulated vulnerable dependency can be located, blocked, rebuilt and rolled back without disabling unrelated workloads.

**Original acceptance remains:** A simulated vulnerable dependency can be located, blocked, rebuilt and rolled back without disabling unrelated workloads.

### UC-M10.01 — Structured bounded logs

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M03.06, UC-M06.07, UC-M07.05

Bounded stdout/stderr for the ship-owned helper runner. No complete redaction, audit anchoring, rotation or global logs budget.

**Original acceptance remains:** Log floods do not exhaust memory/disk and a bounded final failure record remains available.

Related artifacts: `ship/unikernel/supervisor.py`.

### UC-M10.02 — Resource and latency metrics

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M03.05, UC-M05.03

No component acceptance claimed in this application pass. Required work remains: Metrics reconcile with host observations and distinguish guest work from compiler, decoder and controller overhead.

**Original acceptance remains:** Metrics reconcile with host observations and distinguish guest work from compiler, decoder and controller overhead.

### UC-M10.03 — End-to-end execution traces

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M01.08, UC-M05.04, UC-M07.03

No component acceptance claimed in this application pass. Required work remains: One failed invocation can be traced to exact image, input generation, backend and commit disposition.

**Original acceptance remains:** One failed invocation can be traced to exact image, input generation, backend and commit disposition.

### UC-M10.04 — Unified live health view

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M05.05, UC-M10.02, UC-M10.03

No component acceptance claimed in this application pass. Required work remains: A stale or stopped workload cannot continue showing healthy merely because its last witness passed.

**Original acceptance remains:** A stale or stopped workload cannot continue showing healthy merely because its last witness passed.

### UC-M10.05 — Capacity and saturation alarms

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P0 · Milestone C

Prerequisites: UC-M07.02, UC-M07.05, UC-M10.02

No component acceptance claimed in this application pass. Required work remains: Controlled resource pressure triggers a visible actionable warning and preserves the stop/refusal policy.

**Original acceptance remains:** Controlled resource pressure triggers a visible actionable warning and preserves the stop/refusal policy.

### UC-M10.06 — Replay and interactive debugger

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M02.08, UC-M08.04, UC-M10.03

No component acceptance claimed in this application pass. Required work remains: A recorded deterministic failure reproduces with the same observable state and flags unrecorded nondeterminism.

**Original acceptance remains:** A recorded deterministic failure reproduces with the same observable state and flags unrecorded nondeterminism.

### UC-M10.07 — Crash dumps and support bundle export

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M06.07, UC-M07.07, UC-M10.01

No component acceptance claimed in this application pass. Required work remains: A support bundle is sufficient to reproduce a seeded failure and passes secret/content-scope checks.

**Original acceptance remains:** A support bundle is sufficient to reproduce a seeded failure and passes secret/content-scope checks.

### UC-M10.08 — Operator UI with explicit authority cues

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P2 · Milestone C

Prerequisites: UC-M06.01, UC-M06.03, UC-M07.08, UC-M10.04

No component acceptance claimed in this application pass. Required work remains: Destructive controls show scope and generation; UI status is derived from observed facts rather than animation or file presence.

**Original acceptance remains:** Destructive controls show scope and generation; UI status is derived from observed facts rather than animation or file presence.

### UC-M11.01 — Authenticated worker identity

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M06.02, UC-M09.01

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** Unknown/revoked workers cannot receive cargo, join scheduling or publish trusted results.

### UC-M11.02 — Secure inter-host transport

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M08.02, UC-M08.04, UC-M11.01

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** A remote endpoint cannot impersonate a worker or deliver oversized/replayed control messages.

### UC-M11.03 — Durable consensus control store

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M07.01, UC-M11.02

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** Leader loss and network partition preserve the specified single-writer safety and recovery/liveness assumptions.

### UC-M11.04 — Leases, fencing and ownership transfer

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M01.05, UC-M11.03

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** An isolated previous owner cannot mutate committed state after a new owner is activated.

### UC-M11.05 — Partition and failure-domain placement

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M05.02, UC-M11.04

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** Loss of one selected fault domain preserves the explicitly promised replicas and never double-commits state.

### UC-M11.06 — Distributed artifact and state replication

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M04.05, UC-M07.07, UC-M11.03

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** A worker resumes from independently verified objects after source-host loss; corrupt replicas are rejected.

### UC-M11.07 — Rolling upgrades and compatibility negotiation

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M01.02, UC-M07.08, UC-M11.05

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** Canary failure stops the rollout; incompatible state or protocol versions never silently interoperate.

### UC-M11.08 — Multi-host disaster-recovery qualification

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone D

Prerequisites: UC-M11.04, UC-M11.06, UC-M11.07

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** A documented drill meets chosen recovery objectives without trusting stale leaders or unsigned replacement artifacts.

### UC-M12.01 — Real operating-system CI matrix

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M03.08, UC-M04.01

Native evidence is Linux only. Windows launcher syntax/path checks are not native Windows or macOS qualification.

**Original acceptance remains:** Every supported platform has machine-recorded launch/build/verify results; simulated path checks do not count as OS execution.

Related artifacts: `docs/WORKFLOW_EXECUTION.md`.

### UC-M12.02 — Parser fuzzing campaign

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M07.04, UC-M08.02, UC-M09.06

No component acceptance claimed in this application pass. Required work remains: A budgeted campaign has reproducible seeds and no unexplained crashes, hangs, overreads or unbounded allocations.

**Original acceptance remains:** A budgeted campaign has reproducible seeds and no unexplained crashes, hangs, overreads or unbounded allocations.

### UC-M12.03 — State-machine and property-based tests

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M01.03, UC-M01.06, UC-M07.03

Seeded local state-transition/canonicalization and generation/recovery checks. Not exhaustive all-engine arithmetic, alias or multi-container model checking.

**Original acceptance remains:** Generated transitions preserve ownership, byte conservation, integrity and monotonic generation properties.

Related artifacts: `tests/test_foundation.py`.

### UC-M12.04 — Crash, disk-full and concurrency fault injection

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M07.01, UC-M07.05, UC-M07.08

Real disposable child-process exit at five managed-file boundaries plus injected write/ENOSPC/recovery failures. Not power-loss hardware testing or every inherited/native backend mutation.

**Original acceptance remains:** Recovery converges to a documented state without data loss or a false successful verdict across repeated trials.

Related artifacts: `tests/test_foundation.py`.

### UC-M12.05 — Performance and capacity qualification

**NOT_IMPLEMENTED_THIS_PASS** · Source MISSING · P1 · Milestone C

Prerequisites: UC-M04.02, UC-M10.02

No component acceptance claimed in this application pass. Required work remains: Published measurements include hardware, toolchain, sample count and failure rates; no estimated speedup is presented as measured.

**Original acceptance remains:** Published measurements include hardware, toolchain, sample count and failure rates; no estimated speedup is presented as measured.

### UC-M12.06 — Optional OCI packaging/runtime conformance

**NOT_APPLICABLE** · Source MISSING · P2 · Milestone C

Prerequisites: UC-M03.01, UC-M04.05, UC-M06.01

Outside the selected trusted-local development profile; not excluded from a future profile that selects this feature.

**Original acceptance remains:** OCI descriptors and chosen lifecycle contracts pass their conformance checks; unsupported OCI features are explicitly refused.

### UC-M12.07 — Authenticated portable installer and updater

**NOT_IMPLEMENTED_THIS_PASS** · Source PARTIAL · P1 · Milestone C

Prerequisites: UC-M07.08, UC-M09.02, UC-M12.01

No component acceptance claimed in this application pass. Required work remains: A clean install and interrupted upgrade on each supported OS preserve user cargo and restore an approved release.

**Original acceptance remains:** A clean install and interrupted upgrade on each supported OS preserve user cargo and restore an approved release.

### UC-M12.08 — Evidence-based release promotion and runbooks

**PARTIAL_ADVANCE** · Source PARTIAL · P0 · Milestone C

Prerequisites: UC-M09.05, UC-M09.07, UC-M12.01, UC-M12.02, UC-M12.03, UC-M12.04

Source-linked application ledger and explicit promotion blockers. No complete component or individual task is promoted; imported accounting is not execution evidence.

**Original acceptance remains:** No release is labeled operational or isolated while a required gate is skipped, untested or supported only by a declaration.

Related artifacts: `ship/unikernel/gates.py`, `ship/unikernel/workflow.py`, `docs/WORKFLOW_EXECUTION.md`.
