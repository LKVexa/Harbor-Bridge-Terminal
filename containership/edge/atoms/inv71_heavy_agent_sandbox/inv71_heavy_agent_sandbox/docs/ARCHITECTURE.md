# INV-71 architecture, interfaces and semantics (C012-C014, C018, C019, C021-C023, C025, C027)

Normative requirements are in `docs/generated/REQUIREMENTS.md` (from `governance/requirements.json`). This document gives the boundary inventory, data flow, semantics and policies those requirements rely on.

## 1. Boundary inventory (C021)

| # | Boundary | Protocol / object | Direction | Trust | Caller → callee identity | Data class | Timeout | Size limit | Owner |
|---|---|---|---|---|---|---|---|---|---|
| B1 | Workload API (INV-69 → controller) | HTTPS/gRPC, `PK_HEAVYBOX_SESSION/2` | in | untrusted caller until authenticated | workload/scheduler token → controller | tenant metadata | per `docs/generated/OPERATIONS.md` | 4 KiB token, 64 allowlist entries | service owner |
| B2 | Controller → node agent | mTLS RPC with fencing epoch | out | authenticated peer | controller identity → node identity | session plan | 15 s create | 256 KiB config | runtime owner |
| B3 | Node agent → jailer | exec argv (`runtime_plan.Plan.jailer_argv`) | local | privileged helper | node-helper uid | plan | 10 s | argv only | runtime owner |
| B4 | Jailer → Firecracker | chroot, `--config-file`, `--no-api` | local | confined | per-session uid/gid | VM config | 10 s | - | runtime owner |
| B5 | Firecracker → `/dev/kvm` | ioctl | local | kernel | jailed uid | guest memory | - | - | host-platform owner |
| B6 | Guest ↔ VMM devices | virtio-block (ro rootfs, rw overlay), virtio-net | guest-controlled bytes | **untrusted** | guest | arbitrary | - | rate limited | runtime owner |
| B7 | TAP ↔ host netns ↔ nftables | L3 packets | out | **untrusted source** | guest | arbitrary | - | net_mbps / pps | network owner |
| B8 | Trusted resolver | DNS over the node's resolver | out | trusted | node | names | 0.5 s | 8 CNAMEs | network owner |
| B9 | Artifact store | HTTPS + signed manifest | in | authenticated publisher | registry → node | executables | 60 s | per artifact | release authority |
| B10 | Policy / config distribution | signed config generations | in | authenticated | policy service → controller/node | policy | 2 s | 256 KiB | security owner |
| B11 | Audit sink (GAP-09) | append-only JSONL + anchored checkpoints | out | authenticated sink | node → sink | security events | 5 s | spool 64 MiB | security owner |
| B12 | Metrics / logs / traces (GAP-09) | Prometheus text, JSON logs, W3C traceparent | out | authenticated | node → collector | operational | - | bounded labels | SRE owner |
| B13 | Operator / break-glass | authenticated API | in | privileged | operator token (+ approver) | control | - | - | service owner |
| B14 | Snapshot provider (INV-26) | clean base digest | in | trusted | INV-26 → node | image | 5 s | - | runtime owner |
| B15 | Console / vsock | **disabled** (`console=off`, no vsock device in plan) | - | - | - | - | - | - | runtime owner |

Host objects the runtime touches (C021-IMP-03): `/srv/jailer/firecracker/<slug>/root` (chroot), `/var/run/netns/<slug>`, `tap<slug>` (≤15 chars), `/sys/fs/cgroup/firecracker/<slug>`, nftables table `inet <slug>`, and the overlay file inside the chroot. These are exactly `Plan.owned`, and `reconcile()` checks them at teardown.

## 2. Data flow: where untrusted bytes cross (C021-IMP-04)

```mermaid
flowchart LR
  W[Workload / INV-69] -- token + JSON (B1) --> C[Controller]
  C -- plan + epoch (B2) --> N[Node agent]
  N -- argv (B3) --> J[Jailer] --> F[Firecracker VMM]
  F <-- virtio (B6, UNTRUSTED) --> G[Guest]
  G -- packets (B7, UNTRUSTED) --> T[TAP / netns] --> X[nftables default-drop]
  C -- resolve (B8) --> R[Trusted resolver]
  C -- capability tuple --> X
  N -- audit (B11) --> A[(Audit sink + anchors)]
  P[Policy/config (B10)] --> C
  S[Artifact store (B9)] -- verified by digest --> N
```

The parsers that see untrusted bytes are the token decoder, the config parser, `canonicalize_host`, `normalize_path`, the traceparent parser, and in production the Firecracker virtio device model. `tools/fuzz.py` covers the first five.

Undeclared boundaries fail review: an implementation that adds a channel not listed above must update this table and the ADR (C021-IMP-05). `tests/test_governance.py` checks that the plan enables no vsock or console.

## 3. Outcome semantics (C014)

The outcomes are `SUCCESS`, `PARTIAL`, `DEGRADED`, `RETRYABLE_FAILURE`, `TERMINAL_FAILURE` and `SECURITY_REJECTED`, and every error code carries one (`docs/generated/ERROR_CODES.md`).

| Operation | Partial effects possible? | Mandatory compensation before returning |
|---|---|---|
| create | yes (admission, lease, host resources) | release admission, reap resources, and FAILED→REAPING. A failed create leaves no session and no reservation (tested). |
| egress decide | no | - |
| teardown | yes (some resources gone) | none are hidden. Leaks go to QUARANTINED and are never reported CLOSED. |
| config activate | no (generation switch) | the previous generation stays active |

READY postconditions: the guest digest equals the base digest, the lease is held at the current epoch, the plan is rendered and the audit record is durable. VERIFIED postconditions: the guest state is empty, no owned host resource is observed, and the teardown/2 record is written.

## 4. Behavior with intermittent or absent network (C018)

| Unreachable | Allowed | Refused |
|---|---|---|
| control plane (site partition) | existing sessions continue within the profile's offline grace; local teardown | new sessions after grace; any policy change |
| DNS / resolver | connections already bound by a capability until it expires | every new egress decision (`POLICY.DESTINATION_UNVERIFIED`) |
| identity / policy / keys | cached validity within grace (300 / 300 / 600 s) | new trust decisions after grace |
| attestation, trusted time, artifact verification | nothing new | all new trust decisions, immediately |
| audit sink | actions whose audit record fits the local spool | actions once the spool is full (`AUDIT.SINK_UNAVAILABLE`) |
| telemetry / dashboards / secondary registry | everything (DEGRADED) | - |

On reconnect: flush the spool, re-anchor checkpoints, refresh policy/identity, reconcile leases (stale epochs are fenced), and reap orphans found by `reconcile()`. A revocation that happened while offline takes effect at refresh, and grace bounds the exposure.

## 5. Constraint precedence (C019)

The order is deterministic and implemented in `config.precedence_decide`: authentication > artifact integrity > isolation > residency > egress policy > teardown verification > tenant policy > capacity > SLO > cost. The first six never yield to anything below them. SLO and cost pressure can only produce `ADMIT_DEGRADED`, never a relaxed security check. A missing input counts as not satisfied, so it fails closed. A change to this order needs security and legal review and a new config generation.

## 6. Non-functional requirements (C013, PROPOSED)

| Objective | Target | Budget |
|---|---|---|
| Session isolation violations | 0 | none (zero-budget invariant) |
| Forbidden-egress connections | 0 | none |
| Teardown verification failures reported as CLOSED | 0 | none |
| Availability of create (per site, 30-day) | 99.9% | 43 min / 30 d |
| create-to-ready warm / cold | p50 125 / 800 ms; p95 200 / 1500 ms; p99 250 / 2500 ms; hard timeout 2 s / 10 s | 1% may exceed p99 |
| teardown verified | p99 ≤ 1 s, hard timeout 45 s | - |
| audit durability | no acknowledged action without a durable record | none |
| policy propagation | p99 ≤ 5 s | - |

Determinism: policy evaluation, precedence and config merge are pure functions of versioned inputs, so the same inputs give the same decision and reason code on every site. Measurement: 30-day rolling windows, per site, then aggregated. Planned maintenance is excluded only when announced 72 h ahead. Clock source: the node's monotonic clock for latency and a disciplined UTC clock for audit timestamps. A latency budget never authorizes weakening isolation.

## 7. Timeouts, cancellation, idempotency, backpressure (C025)

Deadlines and retry classes are listed in `docs/generated/OPERATIONS.md`. create, snapshot restore, policy fetch, exec and artifact fetch can be cancelled. Cancelling create compensates as in §3, and the caller sees the final state by retrying with the same idempotency key. stop and teardown cannot be cancelled. Idempotency keys are scoped per tenant and deduplicated for a 1 h window, and reusing a key with a different body is rejected. Backpressure: admission rejects with `CAPACITY.ADMISSION_REJECTED` (429, retryable, full-jitter backoff). The reserve slice (10%) keeps teardown and containment possible. Retries cannot amplify an outage because denials are never retried, attempts and elapsed time are capped, and breakers open on dependency failure.

## 8. Mixed versions (C027)

See `docs/generated/COMPATIBILITY.md`. Handshake: the peer sends its surface versions and requested and required features. The controller refuses versions outside N-1..N, refuses any required feature it cannot interpret, and silently drops optional features the older side cannot interpret. Rolling-upgrade order: schemas (additive) → controller → node agents → guest image ABI (the major must match the node). Downgrade: allowed only to a version that reads every record the newer version wrote. `/2` records reduce to `/1` for egress (tested). Snapshot format majors never downgrade.
