# Incident response (MC-038; C097)

Page `inv27-oncall`, then escalate per `ops/OWNERS.json`. The contact details are unassigned
(W-OWNERS).

<a id="seal-bypass"></a>
## SEV-1: suspected seal bypass (an image ran that should not have)
1. **Contain:** `quarantine(image_ref=<digest>)` for the image, and for the tenant if needed. If the
   cause is unknown, use `disable()`.
2. **Preserve:** `AuditLog.export()` and record the head `(seq, hash)` out of band. Copy the journal
   and the decision records for the digest.
3. **Diagnose:** `explain()` the admission. Re-run `admission.admit` offline on the same bytes,
   manifest and envelope with the current version. Compare the seal fields (`parser`, `verifier`,
   `config_revision`, `provenance_key`).
4. **Remediate:** revoke the key in the trust root if provenance was abused. Patch the parser or
   profile, and add a fixture reproducing the bypass to `tests/fixtures`.
5. **Review:** a post-incident review within 5 working days, and a threat-model update.

## SEV-2: trust root stale or VMM unavailable
Admission is fail-closed and running instances are unaffected. Restore the dependency and confirm
`health().ready`.

## SEV-3: shedding or latency
Follow the runbook sections on overload and latency.

Drills have not been run yet (W-DRILLS).
