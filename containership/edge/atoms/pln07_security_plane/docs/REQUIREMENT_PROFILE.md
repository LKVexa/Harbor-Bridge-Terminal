# Deployment requirement profiles (MC-60)

| Profile | Signing | Time | Revocation horizon | Attestation | Notes |
|---|---|---|---|---|---|
| Cloud | Ed25519 via KMS | 3 NTP/PTP sources, quorum 2 | 60 s | workload identity | full telemetry |
| Datacenter | Ed25519 via HSM | 2 sources, quorum 2 | 120 s | TPM | |
| Near-edge | Ed25519, pinned trust root | 2 sources, quorum 1, rollback 2 s | 300 s | TPM | spans sampled 0.1 |
| Far-edge | Ed25519, pinned trust root | local RTC + GNSS, quorum 1 | = grant TTL (≤ lease) | TPM/SEV | short TTL grants; power/thermal pending (MC-37) |

Config overlays per profile go through `ConfigStore.activate(base, env_overlay, site_overlay)`; overlays can only tighten `require_signatures` / `require_v2`.
