# Compatibility - INV-36 5.1.0

Machine-readable source of truth: `compat/matrix.json` (this page summarises it; update both together).

## Runtime

| Dimension | Supported | Tier |
|---|---|---|
| Python | 3.11, 3.12, 3.13 (CPython) | certified-target |
| cryptography | `>=46.0.4,<47` | certified-target |
| Architectures | x86_64, aarch64 | certified-target (no row certified yet) |
| OS | Linux (guest >= 5.10 with `vmw_vsock_virtio_transport`, host >= 5.10 with `vhost_vsock`) | certified-target |
| Windows (Hyper-V sockets), macOS (Virtualization.framework) | - | unsupported |
| pk_core | `>=4.0.0,<5.0.0`, certification only (`[estate]` extra) | pending estate confirmation |

Prerequisites: `/dev/vsock` readable by the agent user (guest), VMM vsock device with guest CID >= 3, `/dev/vhost-vsock` owned by the VMM (host), port 5036 free, no root or CAP_NET_ADMIN.

## Protocols

| Interface | Version | Status |
|---|---|---|
| Stream framing | `PK_CTRL_STREAM/1` | current (new in 5.1.0) |
| Session establishment | `PK_CTRL_HS/1` | current (new in 5.1.0) |
| Control session | `PK_CTRL_SESSION/2` | current |
| Control frame | `PK_CTRL_FRAME/2` | current (unchanged) |
| Control message envelope | `PK_CTRL_MSG/1` | current (new in 5.1.0) |
| Opaque relay | `PK_CTRL_RELAY/1` | current |
| `PK_CTRL_FRAME/1`, `PK_CTRL_SESSION/1` | 4.x | unsupported - rejected at the stream preamble |

## Peer versions

| A | B | Result |
|---|---|---|
| 5.1.x | 5.1.x | interoperate (golden fixtures) |
| 5.1.x | 5.0.x | **do not interoperate** - 5.0 has no stream/handshake layer; 5.1 rejects at the preamble |
| 5.x | 4.x | do not interoperate |

Maximum supported skew: same major protocol, current and previous INV-36 minor release. Rolling upgrade across 5.0 -> 5.1 requires a per-pool drain (see `docs/RELEASE.md`).

## Platform certification rows

| Row | Hypervisor | Arch | Mandatory | Status |
|---|---|---|---|---|
| R1 | Firecracker >= 1.7 | x86_64 | yes | NOT_RUN |
| R2 | QEMU/KVM >= 8.2 | x86_64 | yes | NOT_RUN |
| R3 | QEMU/KVM >= 8.2 | aarch64 | yes | NOT_RUN |
| R4 | Cloud Hypervisor >= 38 | x86_64 | no | NOT_RUN |
| R5 | authoring sandbox microVM (Linux 6.18) | x86_64 | no | KERNEL_PATH_ONLY (bind/listen/collision/typed connect failure; no end-to-end peer) |

Certification requires every mandatory row PASS (or an approved waiver; W-001 is only proposed).

## API changes from 5.0.0

Additive: `stream`, `handshake`, `messages`, `policy`, `config`, `health`, `recovery`, `quarantine`, `audit_log`, `observability`, `endpoint`, `vsock`, `errors`, `gate`, `audit` modules. `Session`, `Relay` and the transport exceptions are unchanged, except that transport exceptions now also subclass `errors.Inv36Error` (still `ValueError`) and carry `.code`. Building a `Session` directly from a caller-supplied secret is deprecated for production (use `ControlEndpoint`, which derives it from PK_CTRL_HS/1).
