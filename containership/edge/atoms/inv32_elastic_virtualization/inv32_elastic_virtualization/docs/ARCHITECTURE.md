# INV-32 Elastic Virtualization — Architecture (v4.3.0)

Status: implemented reference control plane on a deterministic provider. Production provider (HyperFlux) is
**BLOCKED** on an approved specification (ADR-0001). Nothing in this document authorises real hypervisor control.

## 1. Component map

| Module | Role | Workstream |
|---|---|---|
| `model.py` | v4.2.0 pure accounting/policy reference (unchanged; kept as the "reference path" optimisations may never bypass) | — |
| `adapters/base.py` | `HypervisorAdapter` boundary, `LiveGuest`, `Capabilities`, `HostCapacity`, lifecycle table, atomicity contract | 1 |
| `adapters/fake.py` | deterministic reference/fake provider with fault injection | 1, 10, 14 |
| `adapters/hyperflux.py` | fail-closed production shell; refuses construction until a spec digest is pinned | 1 |
| `controller.py` | production mutation pipeline, recovery/reconciliation, health, inventory, explain | 1, 4–10, 12, 18 |
| `validation.py`, `schemas/`, `conformance/` | external schemas, hardened decoder, conformance vectors | 3 |
| `errors.py` | stable codes, categories, outcomes, retry classes, `PK_ERROR/1` envelope | 3, 9, 10 |
| `authz.py` | principals, signed credentials, revocation, deny-by-default policy, break-glass | 4 |
| `config.py` | `PK_INV32_CONFIG/1`, layering, validation, two-phase activation, rollback, secret refs | 5 |
| `store.py` | WAL journal, expected state, segmented signed audit, anchors, backup/restore | 6 |
| `fencing.py` | leases, epochs/fencing tokens, per-guest serialization | 7 |
| `health.py` | readiness/liveness, watchdog, quarantine/freeze/emergency | 8, 10 |
| `resilience.py` | retry/backoff/jitter, retry budgets, circuit breaker, admission, rate limits | 9 |
| `quota.py` | tenant guarantees/caps/borrowing, reclaim order | 18 |
| `telemetry.py` | metrics, structured logs, W3C trace context, explain store, redaction, telemetry policy | 12 |
| `bootstrap.py` | `--check` preflight and idempotent bootstrap, JSON diagnostics, exit codes | 2, 5, 19 |
| `bench.py` | benchmark harness, SLO check, regression gate with waivers | 11 |
| `release.py` | SBOM, RTM checker, evidence manifest (sign/verify), waivers, production exit gate | 15, 16, 17, 20 |

## 2. Boundaries and trust

```
 INV-33 controller / PLN-05 / GAP-10 ──(PK_RESOURCE_ADJUSTMENT/2 over mTLS*)──▶ ElasticController
                                                                                   │  authn (signed credential)
   operators ──(credential + break-glass)──────────────────────────────────────▶   │  authz (deny by default)
                                                                                   ▼
             lease store ◀──epoch/fencing──  controller  ──journal/audit──▶ DurableStore (encrypted volume*)
                                                   │                            │ anchors
                                                   ▼                            ▼
                                    HypervisorAdapter ──(idempotency key, fencing token, expected version,
                                    (HyperFlux*)          incarnation, deadline)──▶ hypervisor ──▶ guest agent
```
`*` = deployment dependency not provided by this package (see RTM BLOCKED items).

Trust boundaries (each is a row in THREAT_MODEL.md): TB1 caller→controller; TB2 operator→controller;
TB3 controller→lease store; TB4 controller→state/audit store; TB5 controller→provider; TB6 provider→guest
agent (guest-reported data is untrusted and advisory); TB7 controller→telemetry/export; TB8 artifact
registry→node.

HyperFlux form factor (library / daemon / RPC / kernel / device) is undecided (ADR-0001). The adapter
interface is transport-neutral; `hyperflux.Transport.call(method, params, deadline)` is the seam.

## 3. Identity mapping

| Identity | Format | Maps to provider |
|---|---|---|
| host | schema `id` grammar `^[A-Za-z0-9][A-Za-z0-9._:-]{0,254}$` | lease resource; provider host handle (ADR-0001) |
| guest | same grammar | provider guest ID **plus** `incarnation` (unique per create/boot) — defeats ID reuse |
| tenant | same grammar | provider-reported owner tenant; must equal request tenant and registration |
| principal | `<kind>:<issuer>/<subject>` | not sent to provider |
| operation | `^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$` | provider idempotency key |
| controller | `controller_id` + lease `epoch` | provider fencing token |

## 4. Primitive semantics

| Primitive | Atomicity | On partial | Timeout |
|---|---|---|---|
| memory grow (hot-plug) | block-granular, may be partial | record confirmed `applied_mib`, outcome `partial_success` | UNKNOWN → journal + block guest until reconciled |
| memory reclaim (balloon) | cooperative, may be partial or refused | record confirmed value; refused → outcome `rejected`, memory unchanged | same |
| memory hot-unplug | optional capability (`feature_memory_hot_unplug`) | all-or-nothing per block | same |
| vCPU add/remove | all-or-nothing required | compensate back to `from`, outcome `rolled_back` (or `unknown_outcome` if compensation fails) | same |

Granularity: targets are aligned to `Capabilities.memory_block_mib` (down when growing, up when reclaiming),
never below the working-set floor or the provider-reported `non_balloonable_mib` (pinned/DMA/device). vCPU
removal never goes below `min_boot_vcpus`. NUMA-preserving vCPU placement is a provider capability flag
(`numa_preserving_vcpu`); when false, topology is the provider's responsibility and is recorded in the
compatibility matrix as a limitation.

Lifecycle: mutations are permitted only in `running`; `paused`, `suspended`, `migrating`, `snapshotting`,
`booting`, `shutting_down`, `crashed`, `stopped` reject with `guest_state_incompatible` (retry: conditional).

Cancellation: honoured before the provider call; after the call the controller waits for confirmation or
deadline (never abandons an in-flight provider mutation).

## 5. Allocatable memory

`usable = total − hypervisor_overhead − reserved_pools − fragmentation_loss` (all provider-confirmed);
`reserve = max(host_reserve_min_mib, ceil(usable × host_reserve_fraction))`;
`free = usable − reserve − Σ live guest memory − Σ in-flight growth reservations`.
If capacity is reported untrusted, or live allocation already exceeds `usable − reserve`, the controller
fails closed (`capacity_untrusted`).

## 6. Mutation pipeline

See the `controller.py` module docstring. Journal phases: `prepared → provider_requested →
provider_confirmed → state_committed → audit_committed`, plus terminal `failed`, `reconciled`, and `unknown`.
The response is sent only after `audit_committed` (fsync'd).

## 7. Reference-path preservation

`model.ElasticHost` is unchanged and still tested by `tests/test_model.py`; optimisations in the controller
(e.g. `verify_recent` on the hot path) are bounded by periodic full verification and readiness probes.
