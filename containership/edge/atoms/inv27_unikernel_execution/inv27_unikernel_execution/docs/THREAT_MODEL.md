# INV-27 threat model (MC-042; C041)

**Assets:** host kernel and VMM process, co-tenant guests, trust root, audit/journal integrity, and
the seal claim itself.

**Trust boundary:** image bytes, manifest, envelope, caller token and tenant name are all
**untrusted input**. Only the trust root (loaded from the host secret store) and the site config
(applied with provenance) are trusted.

| ID | Adversary / threat | Control (code) | Test |
|---|---|---|---|
| T-01 | Image claims a seal it lacks (malicious tenant, compromised toolchain) | facts derived from bytes (`image/facts.py`); manifest must equal facts (A10) | `test_seal.CallerClaimsAreNotEvidence` |
| T-02 | Dynamic loading reintroduces code | PT_INTERP/DT_NEEDED (A5), `dlopen` family (A8) | `test_seal.SealBreakers` |
| T-03 | Process creation/exec | fork/clone/execve/posix_spawn/system symbols (A8), SAS proof (A9) | `SealBreakers` |
| T-04 | Debug build ships a shell/ptrace/gdb stub | DEBUG vocabulary (A8) | `SealBreakers` (uk_ptrace) |
| T-05 | Syscall-set drift manifest↔binary | A10 symmetric difference | `CallerClaimsAreNotEvidence` |
| T-06 | Image swapped between verify and exec (TOCTOU) | `ImageBlob` single object, 0400 private file, re-hash before exec | `test_service.Boot` (DIGEST line) |
| T-07 | Supply-chain: forged/replayed provenance | Ed25519 + subject digest binding + builder/toolchain allow-list + key validity/revocation | `test_seal.Signatures`, `Identity` |
| T-08 | Parser DoS / memory corruption (hostile ELF) | bounds, overflow checks, count limits, work budget | `test_parser.Adversarial`, `Fuzz` |
| T-09 | Control-plane abuse (forged/replayed caller) | HMAC tokens, TTL ≤ 15 min, single-use nonce, capabilities, tenant scope | `test_service.Auth` |
| T-10 | Cross-tenant network/device/storage | deny-by-default `IsolationPlan`, per-tenant bridges, no passthrough vocabulary, read-only volumes by digest | `test_seal.Isolation` |
| T-11 | **Residual:** raw `syscall`/`svc` instruction inlined without a named handler | *not detected by symbol analysis.* Mitigated by accepting only toolchain profiles whose syscall path is the named shim, plus the VMM seccomp sandbox (`-sandbox …spawn=deny`). | open: needs a disassembly pass or VMM hypercall filter evidence (W-VMM) |
| T-12 | W+X segment enables JIT-style code injection | B2 / `UK_SEAL_WX` | `SealBreakers` (uk_wx) |
| T-13 | Guest escape into VMM then fork/exec | QEMU `-sandbox on,spawn=deny,elevateprivileges=deny` | argv test; real proof W-VMM |
| T-14 | Stale/compromised trust root | max-age fail-closed, per-key validity + revocation, version in every decision | `Signatures.test_stale_trust_root_fails_closed` |
| T-15 | Log/audit tampering, secret leakage | hash-chained audit with external head anchor, redaction, tenant pseudonyms | `Durability`, `Diagnostics` |
| T-16 | Split-brain double start | idempotency key per tenant, fencing tokens | `Controls`, `Concurrency` |
| T-17 | Symbol stripping to evade detection | stripped ⇒ `UK_SEAL_NO_EVIDENCE` unless verified attestation | `test_stripped_image_admitted_only_with_enabled_and_verified_attestation` |

Review cadence: every 90 days and on every new toolchain profile (ops/REVIEWS.json). Not yet
reviewed (W-OWNERS, W-APPROVALS).
