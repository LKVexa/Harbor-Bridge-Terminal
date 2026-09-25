# Security policy (MC-53 draft)

**Supported versions:** 5.0.x (reference implementation — not authorised for production trust decisions).

**Reporting a vulnerability:** a reporting channel has **not been designated**. Until the owning organisation assigns one (see `governance/OWNERS.json`), do not publish vulnerability details; contact the repository owner privately.

**Proposed coordinated-disclosure timeline:** acknowledge within 3 business days; triage within 10; fix or mitigation for Critical within 30 days, High within 90; public advisory after fix availability or at 90 days, whichever first; embargo extensions only by mutual agreement. Duplicate reports are credited to the first reporter.

**Scope notes:** the software attester in `mc/simulator.py` is test-only and intentionally insecure; reports about it are out of scope.
