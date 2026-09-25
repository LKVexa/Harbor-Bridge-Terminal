# Constraint precedence (MC-011)

Evaluation order is fixed. Implementation: `production/policy_engine.py` plus the admission pipeline order in `service.py`.

1. **Non-overridable invariants** (in code, not configurable, and no rule can lift them):
   schema validity → authentication → organisation match → freeze/quarantine → RBAC
   (deny-overrides, default deny) → registry allow-list → digest pinning → signature by an approved,
   unrevoked, in-scope signer → attestation (when required) → audit-before-forward.
2. **Organisation rules** (`policy.rules`), ordered by class rank
   `security(0) > residency(1) > availability(2) > slo(3) > cost(4)`, then by `priority`
   (descending), then by `id`. This is a total order, so storage order and iteration order never matter
   (`PolicyEngineTest.test_deterministic` shuffles the rules 20 times).
3. **Exemptions** (`effect: exempt`) may suppress only rules of **equal or lower** class. An attempt
   to lift a higher-class rule is recorded in `exemption_refused` and has no effect
   (the fixture `COST-EXEMPT-RES` in `production/testing.py` is always refused).
4. **External policy (GAP-13)** can only add denials. An `allow` from GAP-13 never overrides a denial from steps 1–3.

RBAC composition: bindings apply at their scope and everything beneath it. **Any matching
deny beats any allow** at any level (`contractor` is allowed on `acme/payments` and denied on
`acme/payments/prod`). Delegation can't grant capabilities the grantor doesn't hold.

Emergency exceptions: the only emergency lever is `freeze`/`emergency_disable`, which is
restrictive. There is no emergency *allow*. Temporarily relaxing a rule goes through a new config
generation with N approvers (the audit trail records author, approvers and reason). A TTL on
config generations isn't implemented (debt D-05).

Every fired rule appears as a stable reason code (`ECP_POLICY_DENIED` with `details.rule`),
and the explain view shows `policy_local.order`, `fired`, `suppressed` and `exemption_refused`.
