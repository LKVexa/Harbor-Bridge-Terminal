# INV-72 security notes

Owners: `ops/OWNERS.md`. Threat model: `ops/THREAT_MODEL.md`. Boundaries: `ops/BOUNDARIES.md`.
Identities and least privilege: `ops/IDENTITY_INVENTORY.json`.

## Guarantees provided in this archive

* Isolation: partitions by explicit opt-in only; whole devices exclusive per reservation; atomic,
  fenced reservation (C046 — matching layer only).
* Authentication of callers (HMAC tokens, replay cache, bounded TTL) and of inventory sources
  (digest + HMAC, monotonic generation) (C044).
* Capability authorization with tenant scope; no capability implies another (C024, C042).
* Fail-closed behaviour when identity/key service, inventory or configuration are unavailable (C048).
* Tamper-evident audit and journal (SHA-256 chain, HMAC when keyed; external head anchor) (C049).
* Secrets never enter configuration; logs/audit/explain are redacted; tenant ids pseudonymised in
  telemetry (C039, C075).

## Not provided here (waived, not claimed)

* Execution, memory, network and side-channel isolation of co-resident workloads — host/GAP-11 (W-003).
* Asymmetric artifact signatures and provenance attestations; at-rest encryption and key rotation (W-004).
* Pinned passthrough / inference / driver stack (W-003).

## Key handling

INV-72 receives keys only through the host `KeyProvider`; it never persists them. Rotation = the host
returns the new key for a principal; tokens signed with the old key then fail. The in-process demo key
used by `tools/bootstrap.py` is for bootstrap tests only and is refused for production by review.
