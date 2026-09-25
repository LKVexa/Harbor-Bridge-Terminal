# Constraint precedence policy (MC-011)

Document ID `INV66-PREC` · v1.0.0 · normative. Evaluation is deterministic and short-circuit-free for reporting (all applicable violations are returned), but *precedence* decides the outcome:

1. **Security invariants (never overridden):** authentication → explicit deny → freeze/quarantine → capability → schema/limits → provenance (registry, digest pin, signer key, signature, attestations).
2. **Organisation policy (GAP-13)** — only consulted when (1) passed; unavailability fails closed.
3. **Residency / environment:** request environment must equal the instance environment; tenant/lattice scope must be inside the org.
4. **Availability / SLO:** bulkhead and quotas may *delay* (retryable errors) but never convert a denial into an admission.
5. **Cost / optimisation:** optional behaviours (batching, per-tenant tuning) must not change any decision in 1–4.

Conflicts between two rules in the same tier resolve toward **deny**. A waiver can relax tiers 3–5 only, must be in `governance/WAIVERS.json` with an expiry, and is visible in `explain`.
