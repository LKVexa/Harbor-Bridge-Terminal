# Incident response and escalation (C097)

| Sev | Entry criteria | First response | Update cadence |
|---|---|---|---|
| SEV1 | Forbidden/unreviewed device attachable in production; audit chain broken; signing key compromise | 15 min | 30 min |
| SEV2 | Unauthorized surface widening detected; activation/rollback failing; catalogue blocking all deploys | 1 h | 2 h |
| SEV3 | Single environment degraded; dependency (policy/audit sink) unavailable with mutations halted | 1 business day | daily |
| SEV4 | Non-urgent defect, documentation gap | best effort | weekly |

Targets are PROPOSED pending owner approval (W-0001).

## Chain
1. First responder: `@inv25-maintainers` on-call (rota PENDING).
2. Backup: secondary maintainer.
3. Security escalation: `@inv25-security` — mandatory for SEV1/SEV2 and any security-sensitive audit event.
4. Incident command: accountable owner `@inv25-owners` for SEV1.

## Playbooks
- **Deployment blocked by the catalogue:** read the `PK_DEVICE_ERROR/1` code. `INV25_UNAUTHORIZED`/`FORBIDDEN_*`
  are policy outcomes — escalate to the owner for a reviewed catalogue change, never bypass.
  `INV25_DEPENDENCY_UNAVAILABLE` → restore the dependency; the last-known-good catalogue keeps serving reads.
- **Unauthorized surface growth:** `surface.widened` event not linked to an approved activation →
  SEV2; `emergency_disable` the device (break-glass), verify audit chain (`AuditLog.verify_file`),
  roll back to the prior known-good digest (`store.rollback`), preserve evidence.
- **Audit chain break:** SEV1; freeze mutations (mutations already fail closed if the sink is down).

Evidence locations: incident ticket (system PENDING), `audit.jsonl`, activation history. Never paste tokens or keys.
