# Patch & end-of-life policy (INV-38-C094)

- **Patch cadence:** app code + Python/native deps monthly; `pk_core`, backend
  libraries, OS/kernel, drivers, NIC firmware, build tooling on vendor cadence.
- **Vulnerability response:** intake → triage owner → severity/exploitability →
  acknowledge/remediate SLAs; emergency criteria for actively exploited or
  DMA/isolation-critical issues with expedited qualification.
- **Blocking:** vulnerable/unsupported driver/firmware versions are blocked by
  preflight (`platform/preflight.py`) and compatibility policy.
- **EOL:** support sunset dates, migration guidance, artifact retention and
  post-EOL security-fix policy. Delayed remediation requires a time-bounded waiver
  (`governance/WAIVERS.json`). **Status:** `DONE`.
