# Exceptions, waivers, technical debt, deprecations (INV30-GAP-014 · INV-30-C099)
Machine-readable register: `../WAIVERS.json`. Rules: every entry has an owner, created date and expiry ≤ 90 days;
class `capability-invariant` can never be waived; expired waivers fail the release gate; the register is reviewed
monthly (REVIEW_PROCESS.md). **No waivers are approved in 4.3.0** — open items are recorded as blockers/tech debt.
