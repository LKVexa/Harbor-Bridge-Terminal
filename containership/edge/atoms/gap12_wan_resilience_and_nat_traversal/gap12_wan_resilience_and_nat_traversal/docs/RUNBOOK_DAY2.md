# GAP-12 Day-2 operations runbook

Scope: steady-state operation, drills and re-certification. Roles are named by function; the
people who hold them are **not assigned** in this package (see `evidence/out/owners.json`).

## Preconditions
- CPython >= 3.10 on Linux (3.11 verified); optional `cryptography==46.0.7` for end-to-end AEAD.
- GAP-06 attestation verifier reachable (without it `TrustGate` fails closed: no path is trusted).
- At least two independent STUN servers and one TURN server with `secret://` credential references.
- Egress allow list covering exactly those servers (deny by default).

## Diagnostics
- `/readyz` detail names the blocking dependency. `Controller.explain(peer)` gives the decision trail.
- `stun.discover()` reason: NET_UDP_BLOCKED / DNS_* / DEP_MALFORMED / DEP_INCONSISTENT.

## Decision points
- UDP blocked at the site: keep relay-over-UDP disabled, rely on TCP/TLS fallback (TURN over TCP is UNSUPPORTED in this build).
- `DEP_INCONSISTENT` across STUN servers: expect symmetric NAT; pre-warm relay.

## Rollback
- `ConfigManager.rollback(author=...)`; kill switch control disabling the new mechanism; remove the package.

## Escalation
- Escalate (do not retry) on AUTH_* reasons, DNS_MISMATCH, or audit-chain verification failure.

## Evidence to retain
- Config activation record, readiness output, lab results, audit log head hash.

## Day-2 specifics
- Watch alerts: G12EstablishBurn*, G12RetryStorm, G12RelaySaturation, G12DnsFailure, G12TraversalRegression, G12SecurityEvent.
- Monthly: partition/reconnect drill; rotate TURN secrets (overlap then retire); verify audit chain.
- On every implementation or policy change: re-run `ops/ci.sh` and archive `evidence/out/`.
