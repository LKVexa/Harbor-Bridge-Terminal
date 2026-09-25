# Incident response (INV30-GAP-067 · INV-30-C097)

| Sev | Definition | Page | Ack | Update cadence |
|---|---|---|---|---|
| SEV1 | Any zero-budget invariant violation or false hardware claim; audit ledger verify failure | 24×7 primary + owner + security | 15 min | 30 min |
| SEV2 | Availability SLO fast burn; service stalled; all minting failing | primary | 15 min | 1 h |
| SEV3 | Degraded (breaker open, telemetry down), slow burn | ticket | 1 business day | daily |
| SEV4 | Cosmetic / docs | ticket | — | — |

**Containment:** SEV1 → `ops disable` immediately (revokes every capability), preserve audit ledger + decision log,
snapshot config history. SEV2 → quarantine affected tenant(s) or service, rollback last change.
**Recovery:** fix → new release evidence → canary from 1 %. **Post-incident:** blameless review within 5 business
days; action items with owners and due dates in WAIVERS.json (tech-debt section) or the tracker.

## Telemetry leakage (sensitive data found in logs/metrics/traces)
SEV2 (SEV1 if key material). Stop the exporter, purge the affected retention window at the sink, rotate any exposed
key (restart ⇒ all handles invalidated), add the leaked field as a sentinel to `test_security.T-12`, ship a fix.

## Forensic evidence preservation
Before any restart: copy the audit ledger + anchored head, decision log export, `ops health` output, config
history (`ConfigStore`), rollout state + its audit ledger, `ops env` (hardware/attestation state), release evidence dir.
