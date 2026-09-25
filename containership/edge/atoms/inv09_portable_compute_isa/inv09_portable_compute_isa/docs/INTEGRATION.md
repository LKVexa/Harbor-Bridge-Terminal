# INV-09 integration contracts: M17–M19, M21, M23–M26

## M17/M18 Host imports and WASI
`PK_HOST_IMPORT_CONTRACT/1` (`schemas/`). Deny by default. The shipped contract knows a small WASI
preview1 subset; filesystem/sockets are intentionally absent. Tenants extend the contract via change
control; each rule names an import class and optionally a registered feature it implies.

## M19 Component Model / WIT — **not implemented**
Component binaries (layer 1, version `0x0d 0x00 0x01 0x00`) are refused with `BAD_VERSION`. A WIT
validator is optional in the checklist and remains OPEN.

## M21 Runtime/validator compatibility matrix
The bundle's `engines` block is the machine-readable matrix. The shipped entry `reference-engine` is a
**placeholder** — production must replace it with real engine builds certified by GAP-15. Until then
M21 is BLOCKED.

## M23 Policy-engine integration (GAP-13)
The policy engine selects `profile` per environment and supplies the signed bundle. The gate consumes
only signed bundles; the profile name in the request must exist in the active bundle, else `refuse`.

## M24 Runtime-hardening handoff (INV-44)
The engine receives an `AdmissionTicket` (bytes, digest, profile, engine, epoch, attestation). The engine
MUST: execute only `ticket.module_bytes`; apply fuel metering and the call-depth/memory limits of the
profile; refuse tickets whose epoch is not current (`Gate.execute` enforces this in-process).

## M25 Artifact provenance — PARTIAL
Module identity (`sha256:` digest) is the join key for provenance systems. Verifying SLSA/in-toto
provenance statements before validation is not implemented.

## M26 Tenant isolation — PARTIAL
Validation is pure and per-request; cache keys include profile, contract revision and manifest digest.
Open item: tenant id in the cache key (side-channel, see THREAT_MODEL M28).
