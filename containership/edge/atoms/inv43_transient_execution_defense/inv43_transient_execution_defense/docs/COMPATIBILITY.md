# Compatibility and version negotiation (items 20, 43)

## Interface versions
| Contract | Versions | Negotiation |
|---|---|---|
| `PK_MITIGATIONS` | 1, 2 | `Accept-Schema: PK_MITIGATIONS/2, PK_MITIGATIONS/1`. No header → v1 (4.2.x behaviour). A node with `not_affected` statuses cannot be rendered as v1 → `406 schema_version_unrepresentable` (never a silent rewrite). |
| `PK_COTENANCY` | 1 | additive optional `decision_id` in 4.3.0 |
| `PK_ERROR` | 1 | `code` enum widened additively in 4.3.0 — **consumers MUST treat unknown codes as refusals** |
| `PK_READBACK` | 1 | new in 4.3.0 |
| `PK_ATTESTED_READBACK` | 1 | new in 4.3.0 |
| `INV43_POLICY`, `INV43_CONFIG` | 1 | new in 4.3.0 |

Forward-compatibility rule for readers: unknown fields are ignored; an unknown **status** value is read as `unknown` (`negotiation.read_status_forward_compatible`).

Breaking change in 4.3.0 for Python callers: none for the 4.2.x API (`MitigationState.report()` default is still v1). New status `not_affected` is only produced by the collector path.

## Platform compatibility matrix
| Platform | Evidence | Status |
|---|---|---|
| Linux 6.x x86-64 cloud sandbox (captured 2026-09-22) | real sysfs capture in `tests/fixtures/kernel_strings.json` + `evidence/host_readback.json` | classified; spectre_v2 read back as `inactive` (BHI: Vulnerable) |
| Linux 4.15 / 5.4 / 5.15 / 6.1 / 6.8, arm64 6.6 | documented string formats (not lab captures) | classifier total over all strings |
| Hypervisors (KVM/Xen/Hyper-V/Firecracker host view) | none | **BLOCKED** — needs lab |
| Providers (AWS/GCP/Azure/bare metal) | none | **BLOCKED** — needs lab |
| Python 3.10 – 3.13 | CI declaration in pyproject; executed on 3.11.15 only | partial |
