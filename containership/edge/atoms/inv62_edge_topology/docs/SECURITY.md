# Security design (MC-013, MC-014, MC-029, MC-033 .. MC-039)

## Authentication (PKT1)
`PKT1.<kid>.<b64url claims>.<b64url HMAC-SHA256>`; claims `sub, role, tenants[], aud="inv62", iat, exp, nonce, node?`.
Verification: key id must be active or verify-only (revoked → reject); constant-time MAC compare; audience;
lifetime ≤ 900 s; ±30 s skew; explicit tenants (no `*`); subject not revoked. Mutating operations spend the nonce
(single use) after admission. Credentials are minted by an issuer sidecar holding the active key
(`Authenticator.issue` is that reference implementation). Node/peer authentication: node-agent credentials bind
`node`, and lease operations require the bound node to equal the candidate. **Artifact authentication** is by
release manifest digest + signature (`tools/release.py verify`), and configuration authentication by optional
HMAC signature (`require_signed_config`).

## Authorisation (default deny)
| Role | Permissions |
|---|---|
| topology-feed (GAP-02/12) | graph.write, graph.read |
| scheduler (GAP-03) | nearest.resolve, graph.read, partition.read |
| node-agent | partition.read, partition.lease (own node only) |
| disconnected-controller (GAP-04) | partition.read, nearest.resolve |
| operator | graph.read, partition.read, admin.freeze, admin.quarantine, config.activate |
| auditor | audit.read, graph.read, diag.sensitive |

No role holds every permission (tested). Unmapped operations are denied. Denials are audited.

## Least privilege / ambient authority
The component opens only: its `state_dir` (read/write), the secret root (read, `0600` enforced on POSIX), and
nothing else. No subprocesses, no network clients, no device access in the runtime package (the release tools
are build-time only). Secrets are referenced as `secret://…` and never stored in config, logs, audit or errors.

## Encryption and key rotation
* Transport confidentiality: lattice mTLS (outside this component; MC-021).
* Message authenticity: PKT1 HMAC. Rotation: `KeyRing.add(new)` → `rotate_to(new)` (old becomes verify-only) →
  after max credential lifetime (900 s) `retire_verify_only()`; revoked keys fail immediately. Keys are never
  overwritten.
* At rest: WAL/snapshot MAC (HKDF-style derivation from `state_key`); optional AES-256-GCM (`encrypt_at_rest`)
  which fails closed if unavailable or if plaintext state is found. State-key rotation: `export_state()` with
  old key, restart with new key and `import_state()` + `checkpoint()` (documented in RUNBOOKS).

## Outage semantics (fail closed)
Key service, policy service, trusted time, secret provider unavailable → `TOPO.DEPENDENCY_UNAVAILABLE`,
readiness false, no mutation accepted. State store write failures open a circuit breaker.

## Audit trail
`audit.jsonl`: HMAC-SHA256 per record + SHA-256 chain + sequence; `audit.verify(records, key,
expected_head=…)` detects edit, delete, reorder, insert and truncation (when the head is anchored externally,
e.g. exported to the SIEM each hour). Events: config.activated, graph.applied, election.granted, admin.*,
security.denied.
