# INV-34 Threat Model

## Protected assets

Host CPU capacity, VM resource entitlement, authoritative desired CPU state, observed guest CPU state, request identity, and the integrity of CPU-expansion decisions.

## Trust boundaries

The caller/control plane, capability-discovery source, INV-34 controller, hypervisor adapter, hypervisor, guest kernel/agent, and telemetry/audit pipeline are separate trust boundaries.

## Threats and current controls

| Threat | Repository control | Remaining production control |
|---|---|---|
| Unauthorized resource expansion | No ambient network/filesystem authority in pure logic; explicit enable flag | Caller authentication/authorization and quota policy |
| Stale controller overwrite | `expected_generation` / `STALE_GENERATION` | Durable compare-and-swap in shared state store |
| Replay/key confusion | Bounded idempotency cache; parameter conflict rejection | Durable cross-process idempotency store |
| Resource exhaustion | Target, identifier and replay-cache bounds; VM/host ceilings | Fleet quotas, admission control, rate limits |
| False completion | desired and observed counts separated | Signed/authenticated backend observations where required |
| Unsupported hot-plug | hypervisor/guest capability gates | Certified compatibility probe and adapter |
| CPU hot-unplug risk | shrink and observation regression rejected | Separate, explicitly designed hot-unplug subsystem if ever needed |
| Tampered dependency/artifact | None in this ZIP | Provenance/signature verification and dependency policy |
| Audit log tampering | None in this ZIP | Append-only/tamper-evident security event sink |
| Hypervisor/guest escape or side channel | Outside pure controller | Hypervisor hardening and security certification |

## Safe degradation

A missing hot-plug capability, disabled expansion, stale generation, invalid input, or capacity overrun fails closed. Loss of the external backend should leave `desired_vcpus > observed_vcpus` rather than fabricate convergence. Operators must reconcile after dependency recovery.
