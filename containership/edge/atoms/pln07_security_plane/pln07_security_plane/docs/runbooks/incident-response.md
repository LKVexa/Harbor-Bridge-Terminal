# Incident response (MC-69)

**Triggers:** a grant accepted that should be denied; key compromise; audit or revocation chain break; horizon breach at many sites; S1 outage.

1. **Contain (≤ 15 min).** Freeze the scope: plane, tenant, subject or site (`/admin/freeze`). Freezing fails closed.
2. **Key compromise.** `revoke_key(kid)` on every verifier. Rotate. Re-issue from a clean issuer. Every grant signed by that kid stops verifying.
3. **Grant compromise.** `revoke` the highest compromised ancestor. Descendants die with it. Confirm acks from every site.
4. **Evidence.** Snapshot `/healthz`, audit events (hash chain), revocation log `head`, config provenance. Hash the snapshot into the incident record.
5. **Eradicate and recover.** Fix, run the gate, canary, thaw with security-lead approval.
6. **Review within 5 business days.** Timeline, root cause, new tests (threat suite), waiver/ledger updates.
