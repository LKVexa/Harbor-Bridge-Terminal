# INV-34 Architecture Decision — ACPI CPU Hot-Plug Control Path

## Decision

INV-34 represents **conventional VM CPU scaling through ACPI CPU hot-plug**. The repository implements the control-plane policy and reconciliation state model; hypervisor-specific execution is an adapter boundary.

This corrects the pre-5.0.0 scope drift, where INV-34 implemented x86 instruction-feature matching even though `CHECKLIST.json` identifies the source function as conventional VM CPU scaling and explicitly names ACPI hot-plug.

## State model

For each VM the controller tracks:

- `observed_vcpus`: independently observed online count.
- `desired_vcpus`: accepted expansion target.
- `max_vcpus`: VM/configured ceiling.
- `host_capacity_vcpus`: currently discovered host ceiling.
- ACPI/hot-plug capability flags.
- administrative expansion enable/disable state.
- monotonically increasing `generation` for stale-write detection.

Legal transitions are monotonic. A request may leave desired count unchanged (`noop`) or increase it (`accepted`). Backend observation may remain unchanged or increase toward desired. Any decrease is rejected as outside the INV-34 hot-add path.

## Request semantics

A request is accepted only when:

- identifiers and integer bounds are valid;
- optional expected generation equals the current generation;
- target is not lower than current desired count;
- target is not above the VM maximum;
- target is not above current discovered host capacity;
- an actual increase is administratively enabled;
- both hypervisor ACPI hot-plug and guest hot-plug support are present.

Idempotency keys are stored in a bounded LRU-style replay cache. Exact replays return the original result; a reused key with different parameters fails with `IDEMPOTENCY_CONFLICT`.

## External adapter boundary

A production reconciler must consume accepted desired targets, issue the appropriate hypervisor action, observe guest/hypervisor CPU-online state, and call `record_observation`. The adapter must not translate “request submitted” into “CPU online.” Partial progress is valid and represented by `pending_vcpus > 0`.

## Failure semantics

Failures are explicit subclasses of `ExpansionError`, each carrying a stable machine-readable code, retryability flag, and structured context. Capacity discovery failure and backend execution are intentionally not fabricated inside this reference package; they belong to external adapters and are listed in `MISSING_COMPONENTS.md`.

## Concurrency

Per-VM controller state is guarded by `threading.RLock`. Generation checks protect against stale external writers. Duplicate request races using the same idempotency key resolve to one state change and one replayed result.
