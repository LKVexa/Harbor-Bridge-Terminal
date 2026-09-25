# GAP-04 Threat Model and Data Classification

**Version:** 1.0 (GAP-04 4.3.0) · **Status:** proposed — requires security-owner review (waiver W-009) · **Controls:** C01-001, C02-001, C04-001, C05-001, C06-001, C14-001, C15-001/006/007, C16-001, C35-006, C46-001

## 1. Assets
| Asset | Why it matters | Where it lives |
|---|---|---|
| Autonomy authority (signed lease, capability set, authority epoch) | Defines what a site may do alone | `state.lease` inside journal frames (AES-256-GCM) |
| Verified policy bundle + rollback floor | Governs every offline decision | journal frames |
| Offline decision log | Accountability; reconciliation input | `decision` frames (WAL) |
| Audit chain head / MAC key | Proves the log is complete and unmodified | `journal.wal` chain; `keys.json` audit key |
| Data-encryption keys | Confidentiality of state at rest | `keys.json` (0600) or a `KeyProvider` (TPM/KMS seam) |
| Trusted-time high-water mark | Prevents lease extension by rewinding time | `clock` frames + state |
| Controller generation | Fencing token against stale/duplicate instances | `generation.json` + every frame |

## 2. Trust anchors and cryptographic assumptions
* Trust anchors are the Ed25519 public keys in a `PK_TRUST_BUNDLE/1`, each restricted to purposes (`lease`, `policy`, `time`, `heartbeat`, `grant`, `quarantine`, `config`). A key authorized for one purpose cannot sign another (test `test_T_C35_signature_malleability_and_key_confusion`).
* Bundle versions never go backwards (`trust_min_version` persisted); a node never replaces its stored bundle with an older one.
* Profile `PK_CRYPTO/1`: Ed25519 (no negotiation), AES-256-GCM (96-bit random nonce, AAD binds sequence + key id), HMAC-SHA-256, SHA-256. Library: `cryptography` 46.0.7 (OpenSSL backend). **Not FIPS-validated** (W-005).
* Canonical encoding `PK_CANON/1`: sorted keys, no whitespace, integers only (|n| ≤ 2^53−1), NFC strings required, duplicate keys rejected, 64 KiB / depth-16 limits.

## 3. Attacker capabilities considered
| # | Attacker | Capability | Primary controls | Tests |
|---|---|---|---|---|
| A1 | Network peer | Inject/replay/forge leases, policies, heartbeats, grants | Signatures, purpose-bound keys, nonce challenge, lease-id/fingerprint replay set, authority epoch | `test_p0_lease_policy`, `test_T_C35_*`, `test_T_C10_spoof_and_replay` |
| A2 | Network | Fake a partition to escape policy | Partition only narrows authority; tier schedule; lease expiry is absolute | `test_T_C32_long_partition_to_expiry` |
| A3 | Network | Fake reachability to trigger renewal/early reconnect | Signed challenge/response heartbeats with hysteresis; renewal only via new signed lease | `test_T_C35_spoofed_reachability_cannot_end_partition` |
| A4 | Local user / root on the node | Rewind RTC, restore VM snapshot | Trusted-time HWM, fail closed on rollback; reboot without trusted anchor = no authority | `test_p0_durability.TrustedTime` |
| A5 | Local root | Edit/delete/reorder journal frames | CRC + hash chain + HMAC (key not derivable from journal) | `test_T_C04_*`, `test_T_C35_journal_tampering_detected_on_open` |
| A6 | Local root | Run a second controller instance | Exclusive OS lock + persisted generation fencing; downstream `FencingValidator` | `test_T_C16_*`, `test_T_C33_duplicate_controllers_fenced_across_processes` |
| A7 | Compromised caller | Escalate beyond lease/tier/capability | Intersection of lease capabilities × tier × policy × PLN-07 grant; overrides can only narrow | `test_T_C35_privilege_escalation_blocked`, `test_T_C12_*` |
| A8 | Any caller | Exhaust memory/disk/queue | Bounded inputs, admission control, journal budget + reserve, emergency freeze | `test_T_C20_*`, `test_T_C30_*`, `test_T_C35_exhaustion_bounded` |
| A9 | Supply chain | Tamper release artifact / SBOM | Reproducible zip, SHA256SUMS + Ed25519 signature, SBOM/provenance cross-checks | `test_T_C45_C46_reproducible_signed_release` |

## 4. Residual risks (explicit, not mitigated in 4.3.0)
* **R1 Whole-disk rollback offline.** If an attacker with root restores an entire older disk image (journal **and** keys together) while the site stays partitioned, the older HWM and log are internally consistent and cannot be detected locally. Detection happens on reconnect (authority epoch, reconciliation audit head vs. last acknowledged head upstream). Hardware monotonic counters (TPM NV) would close this; tracked as W-012.
* **R2 Keys beside data.** The reference `FileKeyProvider` stores keys in the state directory (0600). Theft of the whole disk reveals state. Production must use a TPM/KMS-backed `KeyProvider` (W-005).
* **R3 Tail truncation.** Removing whole frames from the *end* of the journal is indistinguishable from a crash before those appends. Upstream comparison of the exported head closes this at reconnect.
* **R4 Multi-host split brain.** Fencing is per state directory/host. Two hosts with separate disks claiming the same site require control-plane-issued generations (W-011).
* **R5 Reference adapters.** GAP-01/05/12/13 and PLN-07 were exercised through in-package reference implementations only (W-002).

## 5. Data classification (C15-006/007, C03-019, C27-008)
| Data | Class | At rest | In logs | Retention |
|---|---|---|---|---|
| Decision records (subject, kind, bindings) | Confidential | Encrypted (AES-GCM) | subject hashed (`h:`), ids allowed | until reconciled + archive policy |
| Lease/policy/trust documents | Confidential (integrity-critical) | Encrypted | fingerprints/digests only | current + history in archive |
| Signatures, nonces, tokens, keys | Secret | keys: 0600 file / KeyProvider | always `<redacted>` | key lifetime |
| Health/metrics | Internal | n/a | n/a | backend policy |
| Archived journal segments | Confidential | Encrypted (frames) | n/a | per legal hold; chain anchors kept |

## 6. Trusted time (C02)
Priority: (1) control-plane signed `PK_TIME_TOKEN/1` bound to a fresh nonce; (2) an authenticated NTS/Roughtime adapter calling `anchor_trusted`; (3) RTC **only if** `clock.allow_rtc_after_reboot` is enabled, at reduced confidence which caps authority at `freeze`. Holdover = monotonic extrapolation from the last anchor. Integer UTC seconds only, so DST/timezone/leap-second presentation never reaches safety logic. Jumps beyond `max_drift_s` and any value below `HWM − tolerance` fail closed with `GAP04-E0300`.

## 7. Issuer responsibilities (C01-018)
The control-plane issuer must: keep signing keys in an HSM; issue leases ≤ `lease.max_lifetime_s`; increment `authority_epoch` on every revocation event; publish trust bundles with increasing `bundle_version`; on key compromise, publish a bundle marking the key `revoked` and raise the epoch. Maximum tolerated verification outage for a site = remaining lease time.
