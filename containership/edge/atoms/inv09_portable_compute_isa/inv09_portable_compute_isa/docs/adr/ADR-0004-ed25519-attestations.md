# ADR-0004: Ed25519 attestations over canonical JSON with full binding set
Status: accepted. The attestation binds digest, profile, bundle revision+epoch, host-contract revision,
engine, validator version, limits revision, features, expiry and nonce. HMAC was rejected (verifiers
would hold signing capability). Dependency: `cryptography` (no unsigned fallback).
