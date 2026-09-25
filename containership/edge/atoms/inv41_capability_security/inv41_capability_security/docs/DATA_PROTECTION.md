# INV-41 data protection

Status: applicability matrix and in-repo controls implemented and tested; encryption/KMS are deployment prerequisites (BLOCKERS.json B-KEY-01). Architecture: ADR-0001.

## Classification

| Data | Class | Where it can exist | Control |
|---|---|---|---|
| Authority seal (32 B), reference token/signature | **secret, process-local** | memory only | never serialized (CT009), redacted (CT010/PR005), refused by audit (AU003) |
| Capability references | process-local security objects — **not** bearer credentials | memory only | non-serializable; bridge uses opaque handles |
| Policy / configuration | confidential | files, memory, backups | signed + digested; provenance |
| Config-signing, audit-sealing, transport keys | secret | KMS/HSM (deployment) | separate key per purpose (below) |
| Principal records | confidential | memory, audit (opaque) | canonical key only; opaque ids in telemetry |
| Audit events | confidential, integrity-critical | buffer, collector, archive | hash chain + HMAC; no secrets |
| Logs / metrics / traces | internal | backends | redaction, bounded labels |
| Release evidence | internal | CI artifacts | hashed in manifest |
| Crash dumps | may contain seals | host | **disable core dumps** (`ulimit -c 0` / WER off) for the broker process |

## Encryption applicability

| Path | Requirement |
|---|---|
| In-process calls | none (same address space) |
| Local IPC (bridge pipe to child) | relies on OS process isolation + pipe ACLs: the pipe is anonymous, inherited only by the child |
| Collector / identity / key / config distribution over network | TLS 1.3 (TLS 1.2 with AEAD suites only as fallback); no SSLv3/TLS1.0/1.1, no CBC/RC4/3DES/NULL/export |
| At rest: config, audit archive, evidence | AES-256-GCM (or platform disk encryption) with KMS-managed keys |

## Key management

Separate keys: config-signing, audit-sealing, release-signing, transport. ≥ 256-bit symmetric / P-256 or Ed25519 asymmetric. Rotation: 90 days (PROPOSED), overlapping window via key ids (`ConfigStore.trusted_keys`, `HmacTokenAdapter.keys`). Emergency rotation: `ConfigStore.revoke_key(key_id)`. Destruction via KMS scheduled deletion. Key ids and versions are recorded in config signatures and audit events. Unavailable/revoked key material ⇒ fail closed (CF002, ID003).

## Minimization and retention

Retention per class: docs/OPERATIONS.md §Telemetry policy. Redaction rules: `telemetry.REDACT_KEYS`, token-like pattern `[A-Za-z0-9_-]{40,}`; audit additionally refuses (not scrubs) forbidden keys.

## Verification

In repo: CT009, CT010, PR005, BT002, BT007, AU003, CF002, ID003 and mutants M08/M19. Deployment (blocked): TLS configuration tests, key rotation drills, at-rest encryption checks.
