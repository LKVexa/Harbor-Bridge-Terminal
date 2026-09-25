# Unikernel Containership — Missing Components Roadmap

**Baseline: UC-2.2.0. 96 implementation gaps in 12 workstreams.** Assessment date: September 21, 2026, America/Los_Angeles. Build evidence uses UTC timestamps.

## What completion means

The existing ship is a local Python management layer over four classical VM engines, sealed metadata/witness programs, a hull runtime and reversible TIFF state. The UC-2.2.0 repair improves local safety; it does not supply a native boot image, a hypervisor boundary, OS-enforced default-deny networking, tenant authentication or distributed consensus.

A true unikernel path must produce an application linked with selected operating-system functionality for a specified guest platform [S1, S2]. A guest-facing ABI and a host-facing runtime are distinct engineering surfaces [S3]. Production isolation additionally depends on host configuration, privilege and resource controls [S4]. Those distinctions drive this roadmap, not the names “container,” “VM,” “fabric” or “seal.”

**Recommended first vertical slice:** retain the Windows-friendly ship as the management plane; choose one library-OS/guest backend; port one supported native engine plus one small, nontrivial workload; build a real guest image; boot it in an isolated instance; verify its actual output; stop it; restore one checkpoint. Extend to the other engines only after this slice is measured. Do not start by putting the entire Python ship inside one image or by calling four local interpreter instances a distributed cluster.

## Milestones and priorities

A = dependable local control-plane foundation. B = one genuine bootable guest. C = isolated, operable single-host containership. D = optional multi-host federation. Workstreams are categories, not a mandatory serial waterfall; dependencies define the order.

P0 is a blocker for the relevant milestone, P1 makes the managed service dependable, and P2 is advanced/optional scope. `PARTIAL` means a related local mechanism exists but the stated acceptance test is not met. `MISSING` means no implementation of that component was identified in the audited ship. Both are backlog, not completed features. Optional networking, OCI and multi-host federation are not requirements for an offline first-guest release. Source labels support the architectural family; individual tasks and acceptance tests are engineering proposals derived from this audit, not quotations or claims of standards conformance.

## Priority implementation route

Begin with UC-M01.01–01.08, UC-M07.01/07.05/07.08 and UC-M12.03/12.04. In parallel, design UC-M02.01–02.08 and the build chain. Then implement UC-M03, UC-M04.08, UC-M05.01/05.04–05.07, UC-M06 security and UC-M09. The remaining C workstreams make the first guest an operable platform. UC-M11 stays disabled until a separate multi-host promotion gate is met.

Do not use `uc seal` to silence unexplained failures, treat the new local guards as an adversarial sandbox, or count metadata witness agreement as application correctness. The cryptographic hashes bind bytes; outside trust anchors and policy bind authority.



## Component index
| Workstream | IDs | Primary outcome |
|---|---|---|
| 01. Architecture and executable contracts | UC-M01.01–08 | Milestone A |
| 02. Bootable unikernel guest | UC-M02.01–08 | Milestone B |
| 03. Host isolation and supervision | UC-M03.01–08 | Milestone C |
| 04. Build and artifact production | UC-M04.01–08 | Milestone B |
| 05. Workload orchestration and scheduling | UC-M05.01–08 | Milestone C |
| 06. Control plane, identity and policy | UC-M06.01–08 | Milestone C |
| 07. Persistence, transactions and recovery | UC-M07.01–08 | Milestone A |
| 08. Guest communication and data plane | UC-M08.01–08 | Milestone C |
| 09. Trust, integrity and adversarial security | UC-M09.01–08 | Milestone C |
| 10. Observability and operator experience | UC-M10.01–08 | Milestone C |
| 11. Optional multi-host federation | UC-M11.01–08 | Milestone D |
| 12. Qualification, packaging and release | UC-M12.01–08 | Milestone C |

## 01. Architecture and executable contracts


Milestone **A**. Architectural basis: [S1], [S3].


### UC-M01.01 — Trust-boundary and capability model

**P0 · PARTIAL · core or selected profile**

Define operator, cargo author, guest, engine, hull and host trust boundaries. Keep control-plane permission, guest capability and proof status as separate fields.

**Acceptance:** A reviewed threat model maps every entry point to its actual enforcement boundary; no declaration is labeled enforcement.

**Dependencies:** None; foundational decision.


### UC-M01.02 — Versioned runtime and guest contracts

**P0 · PARTIAL · core or selected profile**

Specify boot, invoke, stop, inspect, snapshot and error contracts with strict required fields, extensions and version negotiation.

**Acceptance:** Contract tests reject unknown incompatible versions, duplicate fields and unsupported capabilities before mutation.

**Dependencies:** `UC-M01.01`


### UC-M01.03 — Lifecycle state machine

**P0 · PARTIAL · core or selected profile**

Separate desired and observed states: admitted, staged, built, booting, ready, running, draining, stopped, failed and quarantined.

**Acceptance:** Every transition has a durable reason and legal predecessor; failed readiness cannot produce a running status.

**Dependencies:** `UC-M01.02`


### UC-M01.04 — Canonical manifest and schema evolution

**P0 · PARTIAL · core or selected profile**

Extend checksum parsing to duplicate-key-safe JSON, schema migration, canonical encoding and non-ambiguous field semantics.

**Acceptance:** Equivalent manifests hash consistently; malicious duplicates and lossy downgrade migrations are rejected.

**Dependencies:** `UC-M01.02`


### UC-M01.05 — Stable workload identity and generations

**P1 · MISSING · core or selected profile**

Use immutable workload IDs and monotonic generations rather than directory names as authority across replacement and restore.

**Acceptance:** A stale process cannot write state or publish results for a replacement with the same display name.

**Dependencies:** `UC-M01.03`, `UC-M01.04`


### UC-M01.06 — Closed-world source and dependency inventory

**P0 · PARTIAL · core or selected profile**

Define which files are input, generated, excluded or runtime state; preserve an explicit rejection/exclusion ledger for every ingest.

**Acceptance:** Every original archive member is either hash-accounted cargo or has a documented policy disposition; no silently lost dependencies.

**Dependencies:** `UC-M01.04`


### UC-M01.07 — Application semantics versus witness contract

**P0 · PARTIAL · core or selected profile**

Distinguish sorting, metadata witnessing, dialect compilation and actual application execution. Define supported source languages and observable semantics.

**Acceptance:** A nontrivial application passes semantic input/output tests on its target; a row-sequence hash alone never satisfies execution.

**Dependencies:** `UC-M01.02`, `UC-M01.06`


### UC-M01.08 — Artifact and dependency graph

**P1 · MISSING · core or selected profile**

Represent source, compiler, runtime, configuration, guest image, state schema and evidence as a typed acyclic graph.

**Acceptance:** Changing any dependency invalidates exactly the affected images/evidence; cycles and missing dependencies are rejected.

**Dependencies:** `UC-M01.04`, `UC-M01.06`



## 02. Bootable unikernel guest


Milestone **B**. Architectural basis: [S1], [S2], [S3].


### UC-M02.01 — Chosen library-OS integration

**P0 · MISSING · core or selected profile**

Choose one initial target such as a selected Unikraft configuration or a Solo5-compatible library OS. Port one supported C engine/workload first, not all runtimes at once.

**Acceptance:** A clean build links the application and only required OS libraries into a guest image, not a host Python command.

**Dependencies:** `UC-M01.07`


### UC-M02.02 — Boot ABI and startup path

**P0 · MISSING · core or selected profile**

Implement the selected architecture entry point, boot information validation, stack setup and platform startup sequence.

**Acceptance:** The chosen VMM loads the image and reaches a guest-originated ready signal without a conventional guest OS boot.

**Dependencies:** `UC-M02.01`


### UC-M02.03 — Linker, image layout and permissions

**P0 · MISSING · core or selected profile**

Define executable sections, relocations, memory map, zero initialization, overflow bounds and supported image format.

**Acceptance:** Malformed images are rejected; executable and writable regions follow the selected platform protection policy.

**Dependencies:** `UC-M02.02`


### UC-M02.04 — Guest allocator and memory lifecycle

**P0 · MISSING · core or selected profile**

Provide bounded allocation, failure behavior, stack budgets and memory ownership appropriate to the linked runtime.

**Acceptance:** Memory exhaustion yields a documented failure without host escape or cross-guest corruption.

**Dependencies:** `UC-M02.03`


### UC-M02.05 — Guest execution loop and scheduling

**P0 · MISSING · core or selected profile**

Select cooperative, preemptive or run-to-completion semantics; implement required timers, interrupt handling and cancellation points.

**Acceptance:** A deliberately non-terminating workload can be stopped at the host boundary and cannot starve other guests.

**Dependencies:** `UC-M02.02`, `UC-M02.04`


### UC-M02.06 — Clock and entropy interfaces

**P0 · MISSING · core or selected profile**

Keep deterministic simulation time separate from real monotonic time and cryptographic randomness; validate boot-time availability.

**Acceptance:** Replay uses recorded inputs while security keys never derive from deterministic witness seeds or replay clocks.

**Dependencies:** `UC-M02.02`


### UC-M02.07 — Minimal console, block and transport drivers

**P0 · MISSING · core or selected profile**

Implement only devices needed by the first workload: bounded console, selected block device and optional transport with validated descriptors.

**Acceptance:** Malformed descriptors and unavailable devices fail safely; no unused device is exposed by default.

**Dependencies:** `UC-M02.02`, `UC-M02.04`


### UC-M02.08 — Guest ABI conformance and panic reporting

**P0 · MISSING · core or selected profile**

Build positive/negative ABI probes, panic records and source-mapped traces for the chosen image/runtime combination.

**Acceptance:** A boot-success artifact includes image digest, ABI version, workload output and intentionally induced panic evidence.

**Dependencies:** `UC-M02.03`, `UC-M02.05`, `UC-M02.06`, `UC-M02.07`



## 03. Host isolation and supervision


Milestone **C**. Architectural basis: [S3], [S4].


### UC-M03.01 — Pluggable execution backend boundary

**P0 · PARTIAL · core or selected profile**

Separate host-process adapters from actual guest backends; expose explicit isolation classes and capability negotiation.

**Acceptance:** An isolation-required workload cannot silently fall back to an in-process or ordinary subprocess adapter.

**Dependencies:** `UC-M01.02`, `UC-M02.08`


### UC-M03.02 — Real hypervisor or tender integration

**P0 · MISSING · core or selected profile**

Implement one supported backend that creates a separate guest instance from the built image and validates its boot configuration.

**Acceptance:** Two guest instances are independently booted, inspected and stopped; host-only VM interpreter runs cannot pass this gate.

**Dependencies:** `UC-M03.01`


### UC-M03.03 — Host process sandbox profile

**P0 · MISSING · core or selected profile**

Constrain the VMM/tender with the selected OS mechanisms: user identity, syscall policy, filesystem access and process isolation.

**Acceptance:** An adversarial guest cannot access unrelated host files or make forbidden host operations through exposed devices.

**Dependencies:** `UC-M03.02`


### UC-M03.04 — Enforced default-deny networking

**P0 · MISSING · core or selected profile**

Translate NETWORK=deny into absent devices and/or enforced host filtering. Explicitly isolate the host control-plane and metadata endpoints.

**Acceptance:** A guest traffic probe demonstrates denied egress and lateral access; policy text alone is not evidence.

**Dependencies:** `UC-M03.03`


### UC-M03.05 — CPU, memory, I/O and process quotas

**P0 · MISSING · core or selected profile**

Apply aggregate per-workload and per-tenant limits, including compiler children, decoder workers and inherited processes.

**Acceptance:** Memory, fork, log and I/O flood probes remain inside quota and preserve another guest's health.

**Dependencies:** `UC-M03.03`


### UC-M03.06 — Supervisor, watchdog and child-tree cleanup

**P0 · PARTIAL · core or selected profile**

Track each child by generation, enforce deadlines, bound stdout/stderr, kill the complete tree and reap zombies.

**Acceptance:** Timeout and parent crash leave no executable orphan; failure reason and last bounded log survive.

**Dependencies:** `UC-M03.01`, `UC-M03.05`


### UC-M03.07 — Privilege-separated resource broker

**P0 · MISSING · core or selected profile**

Concentrate privileged device/network operations in a small authenticated broker instead of the entire ship process.

**Acceptance:** Unprivileged ship operation succeeds with only narrowly scoped broker requests; arbitrary paths and commands are denied.

**Dependencies:** `UC-M03.03`


### UC-M03.08 — Host capability and isolation evidence

**P0 · PARTIAL · core or selected profile**

Expand doctor from informational checks to exercised backend capability probes, patch policy and immutable run-time evidence.

**Acceptance:** Admission records the selected backend and verified constraints; unavailable virtualization blocks rather than degrades security.

**Dependencies:** `UC-M03.02`, `UC-M03.04`, `UC-M03.05`



## 04. Build and artifact production


Milestone **B**. Architectural basis: [S1], [S5], [S7].


### UC-M04.01 — Locked toolchain and dependency closure

**P0 · PARTIAL · core or selected profile**

Pin compiler, linker, libraries, engine sources and runtime artifacts with offline-usable checksums and origins.

**Acceptance:** Build works from an explicit dependency cache without implicit PATH/download substitutions; missing inputs are refused.

**Dependencies:** `UC-M01.08`


### UC-M04.02 — Hermetic and reproducible build recipe

**P0 · MISSING · core or selected profile**

Normalize timestamps, environment, source paths and generated metadata while separating nondeterministic build evidence.

**Acceptance:** Two isolated clean builders produce matching declared image digests or a precisely documented reproducibility boundary.

**Dependencies:** `UC-M04.01`


### UC-M04.03 — Sandboxed build workers

**P0 · MISSING · core or selected profile**

Treat compilers, build hooks and imported project tooling as untrusted execution with disposable roots and quotas.

**Acceptance:** A hostile build cannot read operator secrets, contact unapproved endpoints or persist outside its workspace.

**Dependencies:** `UC-M03.03`, `UC-M03.05`, `UC-M04.01`


### UC-M04.04 — Semantic translation validation

**P0 · PARTIAL · core or selected profile**

Compare source semantics, intermediate representation and native results across supported dialects; bound lowering sizes and arithmetic.

**Acceptance:** Generated and hand-written semantic test programs agree under edge cases; unsupported features are refused explicitly.

**Dependencies:** `UC-M01.07`, `UC-M02.08`


### UC-M04.05 — Immutable content-addressed image store

**P0 · MISSING · core or selected profile**

Address images and dependency blobs by digest, verify reads, publish atomically and separate source from executable outputs.

**Acceptance:** Interrupted publication exposes no partial image; a modified blob is rejected even when its filename matches.

**Dependencies:** `UC-M01.04`, `UC-M04.02`


### UC-M04.06 — Software bill of materials and license inventory

**P1 · PARTIAL · core or selected profile**

Produce machine-readable component/version/source/license records for the guest, host, bundled hull and hold.

**Acceptance:** Every linked or shipped runtime dependency maps to a source/version/license and a reviewable provenance record.

**Dependencies:** `UC-M04.01`, `UC-M04.05`


### UC-M04.07 — Build provenance attestations

**P0 · PARTIAL · core or selected profile**

Bind image digest to inputs, build recipe, builder identity and observed tests; use SLSA concepts without claiming an unassessed level.

**Acceptance:** An independent verifier reconstructs the build relationship and rejects altered subjects or unknown builders.

**Dependencies:** `UC-M04.02`, `UC-M04.05`


### UC-M04.08 — Authenticated image admission

**P0 · PARTIAL · core or selected profile**

Verify release signatures against operator-established trust roots before build, mount or execution; disable implicit trust enrollment for untrusted cargo.

**Acceptance:** An intact but self-signed or unapproved image is rejected; signature policy failure never becomes a checksum-only pass.

**Dependencies:** `UC-M04.05`, `UC-M04.07`



## 05. Workload orchestration and scheduling


Milestone **C**. Architectural basis: [S6].


### UC-M05.01 — Executable workload DAG planner

**P0 · MISSING · core or selected profile**

Convert declared entry points and dependency edges into actual invocations, not merely script placement into folders.

**Acceptance:** A multi-step workload executes dependencies exactly in the required order and publishes explicit outputs.

**Dependencies:** `UC-M01.07`, `UC-M01.08`, `UC-M03.01`


### UC-M05.02 — Resource-aware placement scheduler

**P1 · PARTIAL · core or selected profile**

Replace heuristic complexity-only routing with measured capacity, ISA compatibility, memory bounds and isolation requirements.

**Acceptance:** An infeasible workload is queued or refused; placement never violates a hard resource or ISA constraint.

**Dependencies:** `UC-M03.05`, `UC-M05.01`


### UC-M05.03 — Bounded queue and fairness control

**P1 · MISSING · core or selected profile**

Implement priority, starvation prevention, backpressure and queue-capacity limits with durable work identifiers.

**Acceptance:** Overload produces bounded queues and explicit rejection while admitted tenants receive the chosen fairness guarantee.

**Dependencies:** `UC-M05.02`


### UC-M05.04 — Idempotent reconciliation controller

**P0 · MISSING · core or selected profile**

Continuously reconcile desired state to observed instances through generation-scoped idempotent operations.

**Acceptance:** Restarting the controller or redelivering a command neither duplicates instances nor loses an admitted workload.

**Dependencies:** `UC-M01.03`, `UC-M01.05`, `UC-M05.01`


### UC-M05.05 — Workload readiness and liveness checks

**P0 · PARTIAL · core or selected profile**

Separate successful build, boot, ready service, live process, completed invocation and correct application output.

**Acceptance:** A booted but incorrect or stalled guest is not marked ready; probes have deadlines and output-size limits.

**Dependencies:** `UC-M03.06`, `UC-M05.04`


### UC-M05.06 — Graceful stop and drain protocol

**P0 · MISSING · core or selected profile**

Stop admission, drain accepted work, flush state within a bound, then terminate and preserve a definitive exit reason.

**Acceptance:** Stop during active I/O either commits or records an interrupted operation without silently reporting completion.

**Dependencies:** `UC-M05.04`, `UC-M05.05`


### UC-M05.07 — Safe restart and failure budget policy

**P1 · MISSING · core or selected profile**

Define retryable versus permanent failures, exponential backoff, restart ceilings and quarantine for deterministic crashes.

**Acceptance:** A crash loop cannot consume unbounded resources or repeatedly promote a known-bad image.

**Dependencies:** `UC-M05.05`, `UC-M05.06`


### UC-M05.08 — Replica scaling and placement migration

**P2 · MISSING · core or selected profile**

Add explicit stateless/stateful scaling semantics, allocation reservations and drain-before-replace behavior.

**Acceptance:** Scaling out or in respects application state semantics and does not lose accepted requests or bypass quotas.

**Dependencies:** `UC-M05.02`, `UC-M05.06`, `UC-M05.07`



## 06. Control plane, identity and policy


Milestone **C**. Architectural basis: [S4], [S6].


### UC-M06.01 — Machine-stable management API

**P1 · PARTIAL · core or selected profile**

Provide versioned structured operations and errors; keep CLI presentation separate from machine contracts and long-running job IDs.

**Acceptance:** Contract tests exercise command/API parity and incompatible-version refusal without parsing human log text.

**Dependencies:** `UC-M01.02`, `UC-M05.04`


### UC-M06.02 — Operator and service authentication

**P0 · MISSING · core or selected profile**

Authenticate local broker clients and any remote control endpoints; design offline identity provisioning first.

**Acceptance:** Unauthenticated and expired identities cannot load, seal, mount, read secrets or stop another workload.

**Dependencies:** `UC-M06.01`


### UC-M06.03 — Least-privilege authorization

**P0 · MISSING · core or selected profile**

Define distinct permissions for read, build, execute, seal, sign, trust enrollment and destructive lifecycle actions.

**Acceptance:** A read-only operator cannot escalate through an indirect command or optional argument.

**Dependencies:** `UC-M06.02`


### UC-M06.04 — Tenant and workspace isolation

**P0 · MISSING · core or selected profile**

Separate state roots, credentials, image references, quotas and backend instances by tenant identity.

**Acceptance:** Cross-tenant name collisions, aliases and shared-cache references cannot expose mutable data.

**Dependencies:** `UC-M03.03`, `UC-M06.03`


### UC-M06.05 — Policy-as-code admission evaluator

**P0 · PARTIAL · core or selected profile**

Evaluate signed provenance, runtime class, resource budgets, device access and network requirements before any executable action.

**Acceptance:** A denied policy leaves no child process or externally visible partial workload; policy evidence is recorded.

**Dependencies:** `UC-M03.08`, `UC-M04.08`, `UC-M06.03`


### UC-M06.06 — Typed configuration and migration

**P1 · PARTIAL · core or selected profile**

Specify configuration schemas, precedence, secret references, defaults and generation-aware updates; reject unknown sensitive fields.

**Acceptance:** Invalid configuration is rejected atomically and an attempted downgrade cannot weaken an existing workload policy.

**Dependencies:** `UC-M01.04`, `UC-M06.05`


### UC-M06.07 — Secret storage and injection boundary

**P0 · MISSING · core or selected profile**

Keep secrets out of cargo, TIFFs, manifests, process arguments and public logs; supply scoped short-lived handles at runtime.

**Acceptance:** A redaction test finds no test secret in emitted artifacts, logs, snapshots or another tenant's state.

**Dependencies:** `UC-M03.07`, `UC-M06.04`


### UC-M06.08 — Tamper-evident operator audit trail

**P1 · PARTIAL · core or selected profile**

Record actor, command, policy decision, generation and outcome in an append-only independently anchored audit stream.

**Acceptance:** Changing or removing a recorded sensitive operation is detectable without trusting the same mutable workspace.

**Dependencies:** `UC-M06.02`, `UC-M06.03`, `UC-M06.05`



## 07. Persistence, transactions and recovery


Milestone **A**. Architectural basis: [S5], [S8].


### UC-M07.01 — Cross-resource durable transaction coordinator

**P0 · PARTIAL · core or selected profile**

Extend staging/journals to berth, bill of lading, ship seals, hull mounts and runtime state with explicit commit/recovery semantics.

**Acceptance:** Crash injection at every mutation step recovers a coherent old or new generation with no missing cargo.

**Dependencies:** `UC-M01.03`, `UC-M01.05`


### UC-M07.02 — Checkpoint and history rollover

**P0 · MISSING · core or selected profile**

Turn the 512-page stop guard into validated immutable checkpoints, bounded history segments and an explicit restore index.

**Acceptance:** Long-running TIFF state continues after rollover and restores the same state as uninterrupted execution.

**Dependencies:** `UC-M07.01`


### UC-M07.03 — Atomic multi-container tick commit

**P0 · PARTIAL · core or selected profile**

Commit all participating node, fabric and hull results under one epoch or persist an explicit partial-tick record and recovery plan.

**Acceptance:** Power-loss simulation between any two picture writes never leaves an apparently complete mixed-generation tick.

**Dependencies:** `UC-M07.01`, `UC-M07.02`


### UC-M07.04 — Strict state schema and decoder boundary

**P0 · PARTIAL · core or selected profile**

Apply bounded schema validation to every TIFF/JSON/blob entry point, including embedded hull decoders, previews and import paths.

**Acceptance:** Malformed metadata, dimensions, integer fields and nested structures are rejected inside a bounded decoder worker.

**Dependencies:** `UC-M03.05`, `UC-M07.02`


### UC-M07.05 — Workspace capacity reservation

**P0 · MISSING · core or selected profile**

Reserve space for staging, image growth and backups before mutation; enforce minimum free-space thresholds and aggregate quotas.

**Acceptance:** A low-disk fault stops before destructive commit and preserves a usable recovery copy and clear error record.

**Dependencies:** `UC-M03.05`, `UC-M07.01`


### UC-M07.06 — Reachability-based garbage collection

**P1 · MISSING · core or selected profile**

Track references from active generations, snapshots and retained backups; quarantine then remove only unreferenced artifacts.

**Acceptance:** A concurrent deployment/restore cannot lose a referenced object; dry-run lists exactly the reclaimable bytes.

**Dependencies:** `UC-M04.05`, `UC-M07.01`, `UC-M07.05`


### UC-M07.07 — Portable snapshots and state migrations

**P1 · MISSING · core or selected profile**

Define snapshot format, engine/ABI compatibility, encrypted secret handling and schema migration with validation before restore.

**Acceptance:** A snapshot restored on a supported clean host resumes with equivalent application state; incompatible ABI is refused.

**Dependencies:** `UC-M02.08`, `UC-M06.07`, `UC-M07.02`


### UC-M07.08 — Verified rollback and recovery commands

**P0 · PARTIAL · core or selected profile**

Provide operator-facing inspect, restore and abandon commands for retained backups and transaction journals, with generation checks.

**Acceptance:** Automated restore returns registry, seals and mount state to a verified generation rather than only moving a directory.

**Dependencies:** `UC-M07.01`, `UC-M07.03`, `UC-M07.07`



## 08. Guest communication and data plane


Milestone **C**. Architectural basis: [S1], [S3], [S4].


### UC-M08.01 — Typed guest-host IPC ABI

**P0 · MISSING · core or selected profile**

Define request/response buffers, handles, errors and ownership across the actual guest boundary; default to local transport.

**Acceptance:** Unknown operations, invalid handles and out-of-bounds buffers cannot reach arbitrary host functions.

**Dependencies:** `UC-M01.02`, `UC-M02.07`, `UC-M03.07`


### UC-M08.02 — Message framing and versioned serialization

**P0 · MISSING · core or selected profile**

Specify maximum lengths, canonical field encodings, numeric bounds, checksums and compatibility handling for every frame.

**Acceptance:** Truncated, oversized, duplicate-field and mismatched-version messages are rejected without desynchronizing the channel.

**Dependencies:** `UC-M08.01`


### UC-M08.03 — Backpressure and bounded channels

**P0 · MISSING · core or selected profile**

Use bounded queues, byte budgets, flow control and nonblocking cancellation instead of unbounded message accumulation.

**Acceptance:** Producer floods remain within a measured buffer budget and cannot deadlock unrelated workloads.

**Dependencies:** `UC-M03.05`, `UC-M08.02`


### UC-M08.04 — Ordering, idempotency and replay semantics

**P0 · PARTIAL · core or selected profile**

Assign request IDs and epochs; state at-most-once/at-least-once behavior and deduplicate side effects where needed.

**Acceptance:** Repeated or out-of-order messages cannot double-apply a committed external effect or overwrite newer state.

**Dependencies:** `UC-M01.05`, `UC-M07.03`, `UC-M08.02`


### UC-M08.05 — Deadlines and cancellation propagation

**P0 · MISSING · core or selected profile**

Carry deadlines across scheduler, guest IPC and storage operations using suitable monotonic clocks.

**Acceptance:** Canceled work stops using resources within its specified bound and has a deterministic final disposition.

**Dependencies:** `UC-M02.06`, `UC-M03.06`, `UC-M08.03`


### UC-M08.06 — Shared-memory or buffer grant safety

**P1 · MISSING · core or selected profile**

Where zero-copy is selected, validate grant lifetime, size, direction and revocation; otherwise keep bounded copied buffers.

**Acceptance:** Revoked or cross-tenant grants cannot be used after stop, replacement or channel reset.

**Dependencies:** `UC-M06.04`, `UC-M08.01`


### UC-M08.07 — Optional policy-controlled network stack

**P2 · MISSING · optional feature**

For networked workloads only, add the selected virtual NIC, IP stack, TLS, DNS behavior and explicitly granted ingress/egress policy.

**Acceptance:** The offline profile still has no network access; approved endpoints work and all other routes remain denied.

**Dependencies:** `UC-M02.07`, `UC-M03.04`, `UC-M06.05`


### UC-M08.08 — Optional service discovery and routing

**P2 · MISSING · optional feature**

For multi-service deployments, publish authenticated generation-aware endpoints with readiness, expiry and withdrawal.

**Acceptance:** A stopped or replaced generation cannot receive newly routed requests after its endpoint is withdrawn.

**Dependencies:** `UC-M05.05`, `UC-M05.06`, `UC-M08.07`



## 09. Trust, integrity and adversarial security


Milestone **C**. Architectural basis: [S4], [S7], [S8].


### UC-M09.01 — Independent key lifecycle

**P0 · MISSING · core or selected profile**

Separate development, build, release and operator trust keys; support rotation, revocation, offline roots and scoped enrollment.

**Acceptance:** A revoked signer cannot admit new images; one compromised online role cannot mint a new trusted root.

**Dependencies:** `UC-M04.08`, `UC-M06.03`


### UC-M09.02 — Anti-rollback update metadata

**P0 · MISSING · core or selected profile**

Use authenticated versioned update metadata and a trustworthy expiry/version policy suitable for offline distribution.

**Acceptance:** Older, expired or inconsistent metadata cannot silently replace a newer approved release.

**Dependencies:** `UC-M09.01`


### UC-M09.03 — Verified executable-cache reads

**P0 · PARTIAL · core or selected profile**

Verify cached engine source, libraries and executables against the approved dependency graph immediately before use; protect mutable roots.

**Acceptance:** Changing a cached adapter or native executable blocks execution even when the original hold ZIP still matches its pin.

**Dependencies:** `UC-M04.05`, `UC-M06.05`, `UC-M09.01`


### UC-M09.04 — Image-state-policy binding

**P0 · PARTIAL · core or selected profile**

Bind state to exact image, ABI, configuration, policy, tenant and generation instead of a name or accumulator alone.

**Acceptance:** State replay from a different image or tenant is rejected before guest execution.

**Dependencies:** `UC-M01.05`, `UC-M07.07`, `UC-M09.01`


### UC-M09.05 — Proof and digest assurance hierarchy

**P0 · PARTIAL · core or selected profile**

Label byte integrity, signature authenticity, witness agreement, semantic correctness and isolation evidence separately.

**Acceptance:** No promotion rule treats a deterministic hash witness as proof of arbitrary program correctness or authority.

**Dependencies:** `UC-M01.07`, `UC-M04.04`, `UC-M06.05`


### UC-M09.06 — Native runtime memory-safety audit

**P0 · MISSING · core or selected profile**

Review and fuzz the actual C engines, image loaders, device handlers and interpreters with sanitizers and hardened builds.

**Acceptance:** Adversarial image/bytecode corpora complete without sanitizer findings; each remaining finding has an explicit blocker.

**Dependencies:** `UC-M02.08`, `UC-M03.02`


### UC-M09.07 — Guest escape and side-channel assessment

**P0 · MISSING · core or selected profile**

Exercise host boundary attacks and document the chosen hardware/shared-resource threat model rather than asserting absolute isolation.

**Acceptance:** Independent tests and host configuration evidence support the declared tenant boundary; unsupported threats are clearly excluded.

**Dependencies:** `UC-M03.03`, `UC-M03.04`, `UC-M03.05`, `UC-M09.06`


### UC-M09.08 — Security advisory and dependency response

**P1 · MISSING · core or selected profile**

Maintain reviewed component inventories, update policy, affected-image discovery and a revocation/rebuild workflow.

**Acceptance:** A simulated vulnerable dependency can be located, blocked, rebuilt and rolled back without disabling unrelated workloads.

**Dependencies:** `UC-M04.06`, `UC-M09.01`, `UC-M09.02`



## 10. Observability and operator experience


Milestone **C**. Architectural basis: [S4].


### UC-M10.01 — Structured bounded logs

**P0 · PARTIAL · core or selected profile**

Bound stdout, stderr, event logs and retained audit records; classify data and redact secrets at emission.

**Acceptance:** Log floods do not exhaust memory/disk and a bounded final failure record remains available.

**Dependencies:** `UC-M03.06`, `UC-M06.07`, `UC-M07.05`


### UC-M10.02 — Resource and latency metrics

**P1 · MISSING · core or selected profile**

Measure actual boot, queue, execution, memory, I/O and storage costs per image/generation with bounded label cardinality.

**Acceptance:** Metrics reconcile with host observations and distinguish guest work from compiler, decoder and controller overhead.

**Dependencies:** `UC-M03.05`, `UC-M05.03`


### UC-M10.03 — End-to-end execution traces

**P1 · PARTIAL · core or selected profile**

Correlate source/admission/build/boot/invocation/state commit IDs with bounded trace retention.

**Acceptance:** One failed invocation can be traced to exact image, input generation, backend and commit disposition.

**Dependencies:** `UC-M01.08`, `UC-M05.04`, `UC-M07.03`


### UC-M10.04 — Unified live health view

**P1 · PARTIAL · core or selected profile**

Present boot/readiness/liveness/evidence status separately with last-progress age, current phase and actual blocked reason.

**Acceptance:** A stale or stopped workload cannot continue showing healthy merely because its last witness passed.

**Dependencies:** `UC-M05.05`, `UC-M10.02`, `UC-M10.03`


### UC-M10.05 — Capacity and saturation alarms

**P0 · MISSING · core or selected profile**

Report disk, memory, queue and history-limit pressure before admission or state advancement runs out of capacity.

**Acceptance:** Controlled resource pressure triggers a visible actionable warning and preserves the stop/refusal policy.

**Dependencies:** `UC-M07.02`, `UC-M07.05`, `UC-M10.02`


### UC-M10.06 — Replay and interactive debugger

**P1 · PARTIAL · core or selected profile**

Retain source maps and bounded deterministic inputs for guest stepping and reproduction; distinguish simulation from real-time I/O.

**Acceptance:** A recorded deterministic failure reproduces with the same observable state and flags unrecorded nondeterminism.

**Dependencies:** `UC-M02.08`, `UC-M08.04`, `UC-M10.03`


### UC-M10.07 — Crash dumps and support bundle export

**P1 · MISSING · core or selected profile**

Export versioned redacted state, logs, hashes and host capability evidence without keys, user cargo leakage or unbounded archives.

**Acceptance:** A support bundle is sufficient to reproduce a seeded failure and passes secret/content-scope checks.

**Dependencies:** `UC-M06.07`, `UC-M07.07`, `UC-M10.01`


### UC-M10.08 — Operator UI with explicit authority cues

**P2 · MISSING · core or selected profile**

Build a small management view over the stable API: inspect, stage, run, stop, recover and review evidence; retain CLI parity.

**Acceptance:** Destructive controls show scope and generation; UI status is derived from observed facts rather than animation or file presence.

**Dependencies:** `UC-M06.01`, `UC-M06.03`, `UC-M07.08`, `UC-M10.04`



## 11. Optional multi-host federation


Milestone **D**. Architectural basis: [S4], [S6].


### UC-M11.01 — Authenticated worker identity

**P2 · MISSING · optional multi host**

Only for multi-host scope: provision unique worker identities, enrollment policy and revocation independent of display names.

**Acceptance:** Unknown/revoked workers cannot receive cargo, join scheduling or publish trusted results.

**Dependencies:** `UC-M06.02`, `UC-M09.01`


### UC-M11.02 — Secure inter-host transport

**P2 · MISSING · optional multi host**

Add authenticated encrypted bounded RPC and explicit cross-machine authorization; the offline profile must stay blocked.

**Acceptance:** A remote endpoint cannot impersonate a worker or deliver oversized/replayed control messages.

**Dependencies:** `UC-M08.02`, `UC-M08.04`, `UC-M11.01`


### UC-M11.03 — Durable consensus control store

**P2 · MISSING · optional multi host**

Choose and specify a real consensus protocol and failure model for desired state; local ALLREDUCE witness agreement is not consensus.

**Acceptance:** Leader loss and network partition preserve the specified single-writer safety and recovery/liveness assumptions.

**Dependencies:** `UC-M07.01`, `UC-M11.02`


### UC-M11.04 — Leases, fencing and ownership transfer

**P2 · MISSING · optional multi host**

Use epochs/fencing tokens to prevent old workers from committing after ownership moves or leases expire.

**Acceptance:** An isolated previous owner cannot mutate committed state after a new owner is activated.

**Dependencies:** `UC-M01.05`, `UC-M11.03`


### UC-M11.05 — Partition and failure-domain placement

**P2 · MISSING · optional multi host**

Model independent hosts/zones and partial connectivity; avoid treating four interpreters on one host as four fault domains.

**Acceptance:** Loss of one selected fault domain preserves the explicitly promised replicas and never double-commits state.

**Dependencies:** `UC-M05.02`, `UC-M11.04`


### UC-M11.06 — Distributed artifact and state replication

**P2 · MISSING · optional multi host**

Replicate immutable objects with digest validation and define consistency and placement rules for mutable state.

**Acceptance:** A worker resumes from independently verified objects after source-host loss; corrupt replicas are rejected.

**Dependencies:** `UC-M04.05`, `UC-M07.07`, `UC-M11.03`


### UC-M11.07 — Rolling upgrades and compatibility negotiation

**P2 · MISSING · optional multi host**

Support mixed worker/image/ABI versions during controlled rollouts with admission and rollback gates.

**Acceptance:** Canary failure stops the rollout; incompatible state or protocol versions never silently interoperate.

**Dependencies:** `UC-M01.02`, `UC-M07.08`, `UC-M11.05`


### UC-M11.08 — Multi-host disaster-recovery qualification

**P2 · MISSING · optional multi host**

Test full controller/worker loss, restored identity and data, split brain and lost update metadata in the declared topology.

**Acceptance:** A documented drill meets chosen recovery objectives without trusting stale leaders or unsigned replacement artifacts.

**Dependencies:** `UC-M11.04`, `UC-M11.06`, `UC-M11.07`



## 12. Qualification, packaging and release


Milestone **C**. Architectural basis: [S5], [S6], [S7], [S8].


### UC-M12.01 — Real operating-system CI matrix

**P0 · PARTIAL · core or selected profile**

Run native Windows, Linux and any claimed macOS environments, including spaces, long roots, NTFS reparse points and no-toolchain hosts.

**Acceptance:** Every supported platform has machine-recorded launch/build/verify results; simulated path checks do not count as OS execution.

**Dependencies:** `UC-M03.08`, `UC-M04.01`


### UC-M12.02 — Parser fuzzing campaign

**P0 · PARTIAL · core or selected profile**

Fuzz archive, manifest, image, TIFF, bytecode and IPC parsers inside resource-limited workers with a retained corpus.

**Acceptance:** A budgeted campaign has reproducible seeds and no unexplained crashes, hangs, overreads or unbounded allocations.

**Dependencies:** `UC-M07.04`, `UC-M08.02`, `UC-M09.06`


### UC-M12.03 — State-machine and property-based tests

**P0 · PARTIAL · core or selected profile**

Extend example regressions to generated legal/illegal lifecycle sequences, alias invariants and arithmetic edge cases.

**Acceptance:** Generated transitions preserve ownership, byte conservation, integrity and monotonic generation properties.

**Dependencies:** `UC-M01.03`, `UC-M01.06`, `UC-M07.03`


### UC-M12.04 — Crash, disk-full and concurrency fault injection

**P0 · PARTIAL · core or selected profile**

Inject process termination, partial writes, ENOSPC, permission changes and competing operators at every commit boundary.

**Acceptance:** Recovery converges to a documented state without data loss or a false successful verdict across repeated trials.

**Dependencies:** `UC-M07.01`, `UC-M07.05`, `UC-M07.08`


### UC-M12.05 — Performance and capacity qualification

**P1 · MISSING · core or selected profile**

Benchmark boot, workload throughput, tail latency, peak RSS and long-run TIFF/checkpoint growth against explicit baselines.

**Acceptance:** Published measurements include hardware, toolchain, sample count and failure rates; no estimated speedup is presented as measured.

**Dependencies:** `UC-M04.02`, `UC-M10.02`


### UC-M12.06 — Optional OCI packaging/runtime conformance

**P2 · MISSING · optional feature**

When OCI compatibility is selected, map guest images and lifecycle to specific pinned specification versions rather than merely adopting container names.

**Acceptance:** OCI descriptors and chosen lifecycle contracts pass their conformance checks; unsupported OCI features are explicitly refused.

**Dependencies:** `UC-M03.01`, `UC-M04.05`, `UC-M06.01`


### UC-M12.07 — Authenticated portable installer and updater

**P1 · PARTIAL · core or selected profile**

Package short-path launchers, dependency checks, rollback and signed update metadata without silently overwriting user state.

**Acceptance:** A clean install and interrupted upgrade on each supported OS preserve user cargo and restore an approved release.

**Dependencies:** `UC-M07.08`, `UC-M09.02`, `UC-M12.01`


### UC-M12.08 — Evidence-based release promotion and runbooks

**P0 · PARTIAL · core or selected profile**

Define mandatory, optional and not-applicable gates; publish test scope, failures, residual risks and operator recovery procedures.

**Acceptance:** No release is labeled operational or isolated while a required gate is skipped, untested or supported only by a declaration.

**Dependencies:** `UC-M09.05`, `UC-M09.07`, `UC-M12.01`, `UC-M12.02`, `UC-M12.03`, `UC-M12.04`



## Primary references

Reviewed during the audit. No upstream software was installed or integrated merely by citing it. Versions/backend choices must be pinned and requalified during implementation.


**[S1] Unikraft architecture** — https://unikraft.org/docs/internals/architecture

Architectural basis: Modular library-OS APIs, selected platform targets and linked guest binaries.


**[S2] MirageOS** — https://mirage.io/

Architectural basis: Standalone specialized guest images and library-OS runtime integration.


**[S3] Solo5 execution environment** — https://github.com/Solo5/solo5

Architectural basis: Guest-facing ABI, host-facing tenders and isolation boundaries.


**[S4] Firecracker production host setup** — https://github.com/firecracker-microvm/firecracker/blob/main/docs/prod-host-setup.md

Architectural basis: Hardware isolation plus host-side privileges, syscall, network and resource policies.


**[S5] OCI image specification** — https://github.com/opencontainers/image-spec

Architectural basis: Content-addressed descriptors, image metadata and interoperable packaging.


**[S6] OCI runtime specification** — https://github.com/opencontainers/runtime-spec

Architectural basis: Runtime lifecycle and configuration contracts; interoperability is optional here.


**[S7] SLSA v1.2** — https://slsa.dev/spec/v1.2/

Architectural basis: Build/source assurance tracks and independently verifiable provenance.


**[S8] The Update Framework specification** — https://theupdateframework.github.io/specification/latest/

Architectural basis: Trusted update metadata, role separation, version/expiration and rollback defenses.


## Promotion evidence

A completed component needs code, an executable test, observed evidence, a negative test, documented residual risk and a stable identifier in the release inventory. A checked checkbox, mock response, existing source filename, locally generated signature or self-resealed manifest is not independent promotion evidence. This roadmap is deliberately separate from the UC-2.2.0 completed-fix ledger.
