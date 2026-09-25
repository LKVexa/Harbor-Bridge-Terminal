# Constraint precedence (INV30-GAP-013 · INV-30-C019) — implemented in `policy.py`

1. **Capability invariant** (unwaivable) › 2. **Security** › 3. **Residency** › 4. **Hardware requirement** › 5. **SLO** › 6. **Cost** › 7. **Convenience**

Examples: an SLO breach never justifies serving on the model a workload that required hardware (4 › 5); a cost
saving never justifies disabling authentication (2 › 6); residency forbids failing over to a site in another
jurisdiction even if that site has CHERI hardware (3 › 4). The losing constraint is recorded in the decision log.
Waivers (WAIVERS.json) may never target class 1.
