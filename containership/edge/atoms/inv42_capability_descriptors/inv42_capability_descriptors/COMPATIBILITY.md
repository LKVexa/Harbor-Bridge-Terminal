# Compatibility — INV-42 Capability descriptors

## Protocols

| Schema | Status | Behavior |
|---|---|---|
| `PK_DESCRIPTOR/2` | Current | Authenticated descriptor; strict field set; accepted by `DescriptorTable.from_wire()` |
| `PK_DESCRIPTOR/1` | Rejected | Legacy unauthenticated descriptor; intentionally rejected because knowledge of table id/number/type could forge authority |
| `PK_DESCRIPTOR_CLOSE/2` | Current | Close receipt for an authenticated descriptor |
| `PK_DESCRIPTOR_TABLE_STATUS/1` | Current | Non-secret health/counter snapshot (unchanged in 4.3.0) |
| `PK_DESCRIPTOR_EVENT/1` | New in 4.3.0 | Redacted observer event |
| `PK_DESCRIPTOR_DELEGATION/1` | New in 4.3.0 | Delegation record, versioned separately from the wire format |
| `PK_DESCRIPTOR_TRANSPORT/1` | New in 4.3.0 | TLS 1.3 mutual-TLS framing |

There is no transparent v1-to-v2 upgrade because a v1 payload lacks an authentication tag. The issuing table must mint a new v2 descriptor from the underlying live resource.

## Runtime

`pyproject.toml` enforces `requires-python >=3.10,<3.14`. The 4.3.0 remediation was run under CPython 3.11.15 on x86_64 Linux.

The CI matrix (`.github/workflows/ci.yml`) covers:

- **OS / architecture:** Ubuntu x86_64, Ubuntu arm64, Windows and macOS arm64.
- **Python:** 3.10 through 3.13.

Run evidence from that matrix is still pending (W-006). The support windows are defined in `VULNERABILITY_POLICY.md`.
