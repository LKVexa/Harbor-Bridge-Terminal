# INV-71 security design (C023, C024, C039, C042-C048, INV71-X006, INV71-X007)

The reference implementations named here are executable semantics. The production mechanisms marked **PRODUCTION** do not exist in this repository and are what a certifying audit must see working on real hosts.

## 1. Authentication matrix (C023, C044)

| Caller → callee | Reference mechanism | PRODUCTION mechanism | Lifetime | Rotation / revocation |
|---|---|---|---|---|
| workload/scheduler → controller | HMAC capability token: aud, iss, sub, role, tenant, site, actions, exp, single-use nonce | SPIFFE-compatible X.509 SVID over mTLS plus a short-lived capability token | token ≤ 15 min | subject revocation list; nonce replay cache |
| operator / break-glass → controller | same, plus a second principal for two-person actions | SSO-backed operator identity plus hardware-backed break-glass | ≤ 15 min | immediate subject revocation |
| controller ↔ node agent | fencing epoch (in-process) | mTLS with node identity bound to attested measurements | cert ≤ 24 h | CA revocation and duplicate-identity detection |
| node → artifact store | signed manifest verification | registry mTLS plus asymmetric signature (cosign / HSM) | per release | manifest `serial` monotonic; digest revocation list |
| node → audit sink | MAC'd records and checkpoints | mTLS to a WORM sink; checkpoints signed by a node key held in a KMS/HSM | - | key rotation per key-lifecycle §4 |

Clock skew tolerance is 30 s. Tokens issued in the future beyond skew are rejected. Bootstrap trust roots are provisioned at node bootstrap (Day-0 runbook) and never shipped in images. Tests cover expired, revoked, wrong-audience, wrong-tenant, forged, replayed, clock-skewed and anonymous requests (`tests/test_control_security.py::AuthnTest`, `AuthzTest`).

## 2. Authorization (C024)

Capabilities, roles and two-person rules are in `docs/generated/AUTHZ.md`. Every decision is bound to the authenticated principal, tenant, site, requested action and policy version, and carries a reason code (`AUTHZ.*`). The control-plane ability to request guest work (`session.exec`) is separate from host device manipulation (`host.*`, node-helper only).

## 3. Host privilege inventory (C042, C043)

| Component | Identity | Capabilities retained | Devices / paths | Rationale |
|---|---|---|---|---|
| controller | dedicated non-root service user | none | none on nodes | control only |
| node agent | dedicated non-root user | none | reads cgroup/netns inventory | orchestration |
| node helper (privileged-minimal) | root in a separate unit, or CAP_NET_ADMIN + CAP_SYS_ADMIN only | CAP_NET_ADMIN (TAP/nftables/netns), CAP_SYS_ADMIN (jailer mount/chroot, cgroup delegation) | `/dev/kvm`, `/dev/net/tun`, `/srv/jailer`, `/sys/fs/cgroup/firecracker` | the only component that touches host devices |
| jailer → firecracker | per-session uid/gid ≥ 200000, new PID ns, chroot | none after exec | `/dev/kvm`, one TAP, two block files | one VM per jail |
| telemetry exporter | non-root | none | none | export only |

Ambient authority removed: no host mounts or devices (locked config fields), no debug console, Firecracker's default seccomp filters (never `--no-seccomp`), swap off for VMs (`memory.swap.max=0`), and no inherited secrets in env or argv (`tests/test_governance.py` scans the rendered argv and config).

## 4. Encryption and keys (C047)

| Path | In transit | At rest |
|---|---|---|
| control API, node RPC, policy distribution | TLS 1.3, mutual auth, AEAD suites only | - |
| artifact download | TLS 1.3 plus signature and digest verification | artifacts are public-integrity; confidentiality only if the guest image holds licensed content |
| audit / telemetry export | TLS 1.3 mutual | WORM sink encrypted with a per-environment KMS key |
| per-session overlay | - | **PRODUCTION**: dm-crypt with a per-session ephemeral key held only in node memory, destroyed at teardown (cryptographic erase, X006) |
| snapshots / base images | - | integrity by digest; no secrets are ever baked in (the build pipeline scans for them) |
| guest secrets | streamed per session from the secret provider | never persisted on the host |

Key lifecycle: keys are generated in a KMS/HSM and scoped per environment (and per tenant where residency requires). Rotation is 90 days for service keys and 24 h for node certificates; revocation propagates within the stale-trust grace. Keys are backed up only for audit-verification keys. Compromise response: revoke, rotate, re-anchor audit checkpoints, and requalify affected nodes. Live rotation is to be tested in production-equivalent staging (BLOCKED here).

## 5. Secrets (C039)

Short-lived secrets are delivered only to the component that needs them. Guest secrets are separate from host and control-plane secrets, and the guest never sees node identity, signing, registry or telemetry credentials. Redaction happens at write: `audit_log.redact()` replaces any field whose name marks secret material, and error records never include raw exception messages. If the secret provider is unavailable, new sessions that need secrets fail closed and existing sessions keep their already-delivered secret until it expires.

## 6. Failure policy for trust dependencies (C048)

Implemented in `resilience.DependencyHealth` (see `docs/generated/OPERATIONS.md`). Inability to verify a new artifact, identity or policy is a hard deny for new trust decisions. Clock loss: without trusted time, no new token or certificate validation succeeds (grace 0). Audit ordering uses sequence numbers, not wall time. Anti-replay uses nonces, not timestamps alone.

## 7. Residual-data guarantees (INV71-X006)

Threat surfaces: guest RAM, host VMM memory, swap, page cache, KSM/dedup, huge pages, writable overlays, discard/TRIM, image caches, crash dumps and hibernation.

| Surface | Control | Status |
|---|---|---|
| guest RAM reuse | KVM hands guests zeroed anonymous pages (kernel semantics); must be validated per supported kernel | BLOCKED: needs a host |
| swap | `memory.swap.max=0` for every VM cgroup (rendered in plan) | rendered and tested |
| KSM / cross-tenant dedup | KSM disabled on nodes (`/sys/kernel/mm/ksm/run=0`) in qualification | specified; qualification check to be added on a real host |
| writable overlay | fresh per session, never reused; dm-crypt ephemeral key for cryptographic erase | specified; the plan never reuses an overlay path (distinct slugs, tested) |
| page cache of overlays | overlay files unlinked and dropped at teardown; reconcile proves absence | reconcile tested on fixtures only |
| core dumps | disabled for jailer/firecracker (`RLIMIT_CORE=0`, `fs.suid_dumpable=0`) | specified |
| snapshots / build pipeline | secret scan on rootfs build; snapshots taken from clean boot only | specified |
| Python reference model | clearing containers does not zeroize memory | documented limit |

What cannot be proven absolutely (hardware remanence, firmware, cache side channels) needs an explicit, owner-signed residual-risk acceptance in `governance/waivers.json`. None exists.

## 8. Egress destination enforcement (INV71-X007)

Policy is host-based with IP binding. The controller resolves allowlisted names through a trusted resolver (never the guest's). Every CNAME hop must itself be allowlisted, with a chain of at most 8. Every resolved address must be outside loopback, private, link-local (including 169.254.169.254, fd00:ec2::254 and 100.100.100.200), CGNAT, multicast, reserved, unspecified and IPv4-mapped/NAT64 forms of those. A `DestinationCapability` (HMAC over sid, requested and canonical name, address, port, protocol, policy version and expiry) is then issued, and the enforcement point opens only that exact tuple. That removes the time-of-check/time-of-use gap. TTLs are clamped to 1–300 s, and an expired answer is re-resolved and re-checked, which defeats rebinding. A resolver failure denies, and stale answers are never served. IDNA, trailing dots, case, zone IDs (rejected), literal IPs (allowlisted explicitly), URLs and host:port (rejected) are all handled. Redirects, proxy CONNECT and SNI/Host mismatch are out of scope for L3 enforcement: a production L7 proxy must re-run `decide()` per redirect target and compare SNI to the capability's canonical name. Every decision is logged as `PK_HEAVYBOX_EGRESS/2` with requested name, canonical name, resolved addresses, selected address, policy version and reason.
