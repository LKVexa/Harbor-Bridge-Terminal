# GAP-12 Day-0 bootstrap runbook

Scope: first installation of GAP-12 v4.3.0 at a site. Roles are named by function; the
people who hold them are **not assigned** in this package (see `evidence/out/owners.json`).

## Preconditions
- CPython >= 3.10 on Linux (3.11 verified); optional `cryptography==46.0.7` for end-to-end AEAD.
- GAP-06 attestation verifier reachable (without it `TrustGate` fails closed: no path is trusted).
- At least two independent STUN servers and one TURN server with `secret://` credential references.
- Egress allow list covering exactly those servers (deny by default).

## Steps
1. Verify the artifact digest against `evidence/out/sbom.cdx.json` / `provenance.intoto.json` (note: provenance is UNSIGNED in this build).
2. Write the site overlay; run `ConfigManager.preview(env, site)` and resolve every reported problem.
3. Apply with `ConfigManager.apply(..., source=<change id>, author=<automation id>)`; record generation + digest.
4. Start the health server; `/readyz` must be 200 (dns, identity, keys up).
5. Run `python3 lab/scenarios.py` on a staging host (root) and archive `lab_results.json`.

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
