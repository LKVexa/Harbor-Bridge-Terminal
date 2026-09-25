# Interface / boundary inventory (MC-012)

| # | Boundary | Kind | Direction | Owner module | Trust | Limits | Schema / contract |
|---|---|---|---|---|---|---|---|
| B1 | PLN-04 admission request | in-process API (future RPC) | in | `admission/controller.py` | untrusted caller, token-authenticated | queue depth, per-tenant depth, deadline ≤600 s | `PK_MICROVM_ADMISSION/1` |
| B2 | Create/boot/lifecycle records | API out | out | `runtime.py` | trusted | bounded fields | `PK_MICROVM*/1` |
| B3 | Firecracker REST API | HTTP/1.1 over Unix socket | out | `adapters/firecracker.py` | VMM trusted-after-verify | 64 KiB responses, per-call timeout, whitelisted paths/fields | Firecracker OpenAPI (pinned version) |
| B4 | VMM process | fork/exec, argv only | out | `supervision/vmm_process.py` | verified binary | 64 KiB stdout/stderr capture, ready/stop timeouts | argv |
| B5 | Jailer | fork/exec | out | `security/isolation.py` | verified binary, root | cgroup memory/cpu/pids | jailer CLI |
| B6 | `/dev/kvm` | ioctl | out | `virtualization/kvm.py` | host kernel | 2 s preflight deadline | KVM API 12 |
| B7 | Block backing files | filesystem | out | `devices/specs.py` | tenant data | 512-aligned, ≤1 TiB, no symlinks, tenant root | `PK_MICROVM_DEVICE/1` |
| B8 | TAP / netns | kernel netdev | out | `devices/specs.py`, isolation | host | ≤4 NICs, exclusive ownership | — |
| B9 | vsock UDS | Unix socket | both | `devices/specs.py` | guest untrusted | CID range, ≤100-byte path | — |
| B10 | Snapshot store | filesystem | both | `snapshot/store.py` | integrity-checked | digests, epoch, tenant binding | `PK_MICROVM_SNAPSHOT/1` |
| B11 | Config store | filesystem | in | `config/loader.py` | operator | narrow-only overlays | `PK_MICROVM_CONFIG/1` |
| B12 | Key provider (KMS/HSM) | provider API | in | `security/keys.py` | trusted | ≥32-byte keys | `KeyProvider` protocol |
| B13 | Audit log | append-only file | out | `security/audit.py` | tamper-evident | 8 KiB/record | JSONL chain |
| B14 | Metrics scrape | Prometheus text | out | `observability/metrics.py` | read-only | 1000 series/metric | exposition format |
| B15 | Logs | JSON lines | out | `observability/logging.py` | read-only | 16 KiB/line | `PK_MICROVM_LOG/1` |
| B16 | Trace context | W3C traceparent | both | `observability/tracing.py` | untrusted header | strict parse | W3C |
| B17 | Health/readiness | API out | out | `resilience/health.py` | read-only | 1 s/probe | `PK_MICROVM_HEALTH/1` |
| B18 | Operator controls | API in | in | `resilience/controls.py` | operator token | capability-gated | — |
| B19 | Guest metadata (MMDS) | — | — | not exposed | — | disabled (optional in contract, not implemented) | — |
| B20 | INV-35 datapath | provider protocol | both | `io/datapath.py` | optional peer | ≤16 regions, ≤1024 queue, ≤1 MiB descriptor | `Datapath` protocol |
