# Supported Platforms and Cross-Version Compatibility

## Platform matrix

| OS / kernel | Arch | Python | Service manager | Runtime adapters | Status |
|---|---|---|---|---|---|
| Linux ≥ 5.10 (Ubuntu 22.04/24.04, Debian 12) | x86_64 | 3.10–3.13 | systemd ≥ 249 | process (shipped), fake | **Supported** — tested in this build on 3.11; CI matrix defined |
| Linux ≥ 5.10 | aarch64 | 3.10–3.13 | systemd ≥ 249 | process, fake | **Supported (CI matrix; not executed in this build)** |
| Linux, non-systemd (OpenRC, s6) | any | 3.10+ | — | process | Best effort: no watchdog/notify integration |
| macOS | any | 3.10+ | — | process | Development only |
| Windows | any | any | — | — | **Unsupported** (UNIX socket, process groups) |
| Any | any | < 3.10 | — | — | **Unsupported** |
| wasmtime / Firecracker / unikernel runtimes | — | — | — | adapters not shipped | **Unsupported until EXC-004 closes** |

## Version compatibility

- **Wire schemas.** `PK_NODE_LIFECYCLE/1`, `PK_DRAIN/1`, `PK_NODE_HEALTH/1`. Within `/1`, only optional fields are added; consumers MUST ignore unknown response fields (fixture `compat_forward_status_additive_field`). Requests may carry `x-extensions`. A `/2` request to a `/1` supervisor is rejected with `E_BAD_REQUEST` (fixture `invalid_request_schema_v2`).
- **v4.x callers → v5.0.0.** v4.x had no wire protocol (in-process Python only). In-process callers of `NodeSupervisor` keep working unchanged. Networked callers must sign requests (breaking by design).
- **`PK_DRAIN/1` additions in v5.** `active`, `unproven_reclaim`, `kill_after`, `forced` (additive).
- **Persisted state.** schema 1 (v4.x style, no drain intent/cordon ack) migrates forward to 2 on load. Downgrade across a schema bump is not supported: restore the pre-upgrade backup (RUNBOOKS RB-12).
- **Adjacent components.** Scheduler must send `cordon_ack` carrying the cordon `generation` (new in v5; older schedulers simply leave `cordon_ack_overdue` counting and are otherwise unaffected). Health reporters must be registered in `signals.json`.
