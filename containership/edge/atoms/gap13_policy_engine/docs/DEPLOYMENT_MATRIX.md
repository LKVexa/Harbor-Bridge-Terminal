# Deployment-pattern support matrix (G13-MC-045)

| Pattern | Status | Notes |
|---|---|---|
| Cloud / datacenter, library in-process | **Supported** | Python ≥3.10; `cryptography` required for verification. |
| Cloud / datacenter, `/v1` service behind TLS sidecar | **Supported** | Bind 127.0.0.1; mTLS/TLS at sidecar; one service per worker process. |
| Near-edge site, intermittently connected | **Supported** | File/HTTPS distribution, LKG cache in `state_dir`, staleness modes; `FREEZE_LAST_KNOWN_GOOD` only with approved waiver. |
| Far-edge constrained node | **Conditional** | Functionally supported; power/thermal impact unmeasured (G13-MC-033 BLOCKED). |
| Multi-writer shared `state_dir` across hosts (NFS/SMB) | **Unsupported** | Atomic rename semantics not guaranteed; use per-host state dirs. |
| Exposing `/v1` directly on a public interface without TLS | **Unsupported** | Transport has no built-in TLS by design. |
| Windows / macOS hosts | **Declared, unverified** | Stdlib-only, `os.replace`, spawn-safe; CI rows pending (waiver W-004). |
