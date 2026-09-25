# Patching, vulnerability-response and EOL SLAs (MC-072)

Status: **PROPOSED**. The owner must approve these targets (ops/DECISIONS.json).

| Event | Target |
|---|---|
| Critical advisory against a registered toolchain version | Refuse it in production automatically (`advisory_block_severity=high`), within the feed-refresh interval (≤ 2 days). Emergency-disable within 4 h of human confirmation |
| High advisory | Same automatic refusal. Patched version registered, reviewed and certified within 7 days, or an approved waiver with expiry ≤ 30 days |
| Medium/low advisory | Tracked. Patched within 30/90 days |
| Vulnerability in INV-28 itself | Acknowledge within 2 business days. Critical fix or mitigation within 7 days, high within 30 days |
| Toolchain EOL | Set `eol_date` as soon as upstream announces it. The entry becomes unselectable automatically on that date. Workloads get migrated before it |
| Security review freshness | Per entry (`review.interval_days`, default 180). An overdue review makes the entry unselectable in production |
| INV-28 release support | Only the latest minor (4.3.x) gets fixes |
