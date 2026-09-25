# INV-34 performance analysis (MC-041..MC-049)

Measured by `tools/perf.py`; numbers land in `governance/PERF_BASELINE.json` for the host that ran CI.

## Where time goes on the local path (MC-045)

| Hop | Copies / serialisations | Syscalls that dominate |
|---|---|---|
| HTTP body -> `json.loads` -> request dict | 1 parse | socket read |
| submit: store `load` (read+JSON parse+sha256 digest) | 1 read, 1 parse, 1 canonical dump for digest | `open`, `read`, `flock` |
| submit: CAS `update` (deepcopy, dump, digest, temp write, `fsync`, `os.replace`, dir `fsync`) | 1 deepcopy, 2 dumps | **two `fsync`s — the dominant cost** |
| audit append (canonical dump + HMAC + `fsync`) | 1 dump | one `fsync` |
| reconcile: lease acquire (1 CAS write) + live read + adapter call + journal commit (1 CAS write) | 2 store writes | 4-6 `fsync`s + adapter RTT |

A real Cloud Hypervisor call adds two Unix-socket round trips (`vm.info` before, `vm.resize`, `vm.info` after) — not measured here (no live VMM; B-LIVE-HV).

## Bounds (MC-046)

in-flight requests `AdmissionController.max_in_flight` (32), queue 128, idempotency 4096 entries/VM,
journal 1024 entries/VM (non-terminal entries never trimmed), request body 16 KiB, backend response 1 MiB,
cpulist 4 KiB, audit nonce table bounded by the credential skew window.

## Not characterised

power/thermal on edge nodes (MC-047, B-HW); fleet scale, soak, network hop latency (MC-059, B-FLEET).
Thresholds in `governance/THRESHOLDS.json` are PROPOSED; the regression gate reports `within_proposed`, never PASS.
