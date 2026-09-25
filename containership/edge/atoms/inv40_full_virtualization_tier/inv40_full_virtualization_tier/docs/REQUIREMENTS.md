# INV-40 SHALL-level requirements (INV-40-C011..C014, C017..C019)

Every SHALL names its test. "Test" = a non-skipped unittest in `tests/`.

## Function: maximum legacy compatibility / compliance isolation (C011)
| ID | Requirement | Test |
|---|---|---|
| FVT-R01 | The tier SHALL refuse to start any guest when the hardware virtualization primitive is unusable, and SHALL NOT offer software emulation. | `test_no_software_fallback`, `test_qemu_refuses_without_primitive`, `test_qemu_argv_is_kvm_only_and_full_model` |
| FVT-R02 | Every guest SHALL carry the complete baseline device model; extra devices are additive only. | `test_complete_device_model_required` (v4.2.0) |
| FVT-R03 | No concrete device instance SHALL be leased to two live guests. | `test_parallel_boots_one_winner_per_guest`, v4.2.0 lease race test |
| FVT-R04 | Resident footprint SHALL be measured, reported and refused above the ceiling, with no orphaned hypervisor on refusal. | `test_footprint_breach_leaves_no_orphan` |
| FVT-R05 | The tier SHALL make no assumption about guest-OS internals. | contract; no introspection code (review) |
| FVT-R06 | One tenant per guest; a principal SHALL act only on tenants its credential names. | `test_cross_tenant_denied_and_audited` |

## Functional requirements by deployment context (C012)
| Context | Requirement | Status |
|---|---|---|
| Datacenter | FVT-R01..R06 on a KVM host via `QemuKvmProvider` | implemented; hardware test BLOCKED (HW-KVM) |
| Cloud | Same contract through a cloud provider adapter (EC2 metal / nested) | NOT IMPLEMENTED — no adapter; recorded |
| Near-edge | Same, with `offline_mode` governing control-plane loss | implemented (config) |
| Far-edge | Tier MAY be unavailable (no primitive or power budget); SHALL report `ready=false` rather than degrade to emulation | implemented (probe) |

## Non-functional (C013)
| Quality | Target (PROPOSED — thresholds unapproved) |
|---|---|
| Boot latency | ≤ `boot_budget_ms` (8000); miss ⇒ `status=degraded`, never hidden |
| Isolation | zero guests without primitive; zero shared device instances (no error budget) |
| Durability | journal/audit/config writes fsync'd before acknowledgement |
| Consistency | one mutating controller per epoch (fencing) |
| Determinism | same config ⇒ same QEMU argv (`test_qemu_argv_*`) |
| Control-plane overhead | p99 create/boot ≤ 25 ms over FakeProvider (see `ci/bench_thresholds.json`) |

## Outcome semantics (C014)
| Outcome | Signal | Caller action |
|---|---|---|
| success | `status=ok` | none |
| degraded success | `status=degraded` (boot over budget) or health `dependencies.telemetry_sink_failures>0` | proceed; alert |
| partial success | not produced: create/boot are all-or-nothing (failed boot destroys the launched hypervisor) | — |
| retryable failure | `PK_FULL_VM_ERROR/1` with `class=retryable` | retry with backoff, same idempotency key |
| rejected | `class=rejected` | change request/credential/policy first |
| terminal failure | `class=terminal` | do not retry this request |

## Capacity, quotas, fairness (C017)
`max_concurrent_ops`, `max_queue` (shed with `PK_FULL_VM_OVERLOADED`), per-tenant `tenant_guest_quota` and `tenant_memory_quota_mib` (`PK_FULL_VM_QUOTA_EXCEEDED`). Fairness = hard per-tenant ceilings; no tenant can consume another's quota (`test_admission_shed_and_quota`, `test_parallel_creates_respect_quota`).

## Intermittent / absent connectivity (C018)
* Identity/key/time unavailable ⇒ fail closed, `PK_FULL_VM_TRUST_UNAVAILABLE` (retryable).
* Telemetry collector unavailable ⇒ degraded, operations continue, `telemetry_sink_failures` counted.
* Controller partition ⇒ stale epoch rejected on reconnection (`PK_FULL_VM_STALE_OWNER`).
* `offline_mode=serve_cached_readonly` is declared in the schema; only reads are permitted in that mode (reads are not yet separated — PARTIAL).

## Precedence when requirements conflict (C019)
1. **Security / isolation** (primitive, tenant, device exclusivity, integrity) — never traded.
2. **Residency / compliance** placement constraints (owned upstream by placement; this tier refuses rather than relocates).
3. **Correctness / durability** of state.
4. **SLOs** (boot budget, availability) — may degrade with explicit signal.
5. **Cost** — lowest precedence.
A conflict resolved by this order is recorded as a decision (`telemetry.Decisions`) with the rule applied.
