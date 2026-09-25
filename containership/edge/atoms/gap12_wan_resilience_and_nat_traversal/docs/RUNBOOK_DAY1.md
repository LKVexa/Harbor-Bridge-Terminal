# GAP-12 Day-1 deployment runbook

Scope: rolling a GAP-12 release through the fleet with `wan.rollout.Rollout`. Roles are named by function; the
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

## Day-1 specifics
- Run the compatibility check (PK_PATH_STATE/1, PK_BACKOFF/1, PK_RELAY_ACCOUNTING/1 unchanged) before stage 1.
- Stages 1 % / 10 % / 50 % / 100 %; promotion only with >= 50 samples and every criterion met for the soak period.
- Any breach (error rate, p95 establishment, relay ratio) rolls back automatically.
