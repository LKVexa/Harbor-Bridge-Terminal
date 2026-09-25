# INV-17 Support, Vulnerability Response, Patch and EOL Policy

**Controls:** C094 (checklist §56); related C093 (§10).

**Status:** Proposed — all target values below are PROPOSED and not yet agreed. Owner: UNASSIGNED — owner to fill.

## 1. Support window (PROPOSED)

| Line | Status | Support |
|------|--------|---------|
| 4.3.x | Current | Full (features + fixes) |
| 4.2.x | Previous | Security and critical fixes for 6 months after 4.3.0 GA (PROPOSED) |
| < 4.2 | EOL | None |

Interface versions (`PROTOCOL_VERSIONS`) older than the supported package lines may be dropped from `control::SUPPORTED_VERSIONS` only at a major release.

## 2. Vulnerability intake

- Channel: private security contact — UNASSIGNED — owner to fill. Do not file vulnerabilities in public trackers.
- Acknowledge within 2 business days (PROPOSED).
- Triage with CVSS; record in governance/technical-debt.json or a private tracker.

## 3. Patch SLA (PROPOSED, from triage)

| Severity | Fix / mitigation available |
|----------|----------------------------|
| Critical | 7 days |
| High | 30 days |
| Medium | 90 days |
| Low | next minor |

Interim mitigations available in-product: `StreamRegistry.emergency_disable`, `quarantine`, capability revocation (`CapabilityAuthority.revoke`), key rotation (`KeyRing.rotate`).

## 4. Dependencies

Runtime is stdlib-only; `vendor/pk_core` 4.0.0 is vendored (certification adapter only). Vendored code is patched by re-vendoring; SBOM via tools/sbom.py.

## 5. EOL

EOL announced at least 90 days ahead (PROPOSED) in CHANGELOG.md. After EOL no fixes are issued.
