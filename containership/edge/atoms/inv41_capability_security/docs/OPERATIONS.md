# INV-41 operations: support, rollout, lifecycle, incidents, runbooks

Status: **written, not yet reviewed or accepted by an owning team** (BLOCKERS.json B-OWN-01, B-DEPLOY-01). Numbers marked PROPOSED need owner approval. Architecture: ADR-0001; requirements: docs/REQUIREMENTS.md.

## Support commitments and error budgets

* Support coverage: business hours of the owning team; SEV1 paging 24×7 once `incident_commander` is assigned (`OWNERS.json`).
* SLOs (PROPOSED): library mode — latency per `perf/slo.json`; service/bridge mode — 99.9 % monthly availability of authorization decisions, error budget 43 min/month.
* **Zero-tolerance (never budgeted):** any authorization widening, cross-authority acceptance, successful post-revocation use, secret leakage, audit-chain break. One occurrence = SEV1.
* Budget exhausted ⇒ feature freeze; only reliability/security changes ship until the rolling 30-day budget recovers.

## Failure taxonomy
<a id="failure-taxonomy"></a>

| Layer | Examples | Class | Detection | Allowed response |
|---|---|---|---|---|
| operation | invalid input, widening, forged/foreign ref | configuration/untrusted | error code, `inv41_uses_denied_total` | deny; never retry |
| process | crash, OOM, thread stall | transient/persistent | liveness, restart count | restart ⇒ new domains; re-bind |
| runtime | unsupported interpreter, bad entropy/HMAC | configuration | preflight | refuse start |
| container/VM/node | host loss, reboot | transient | orchestrator | reconstruct from signed config |
| network | partition, reorder, duplicate | transient/Byzantine | dependency health, circuit breaker | fail closed; bounded retry for reads |
| identity/policy/key/time | outage, stale, skew | transient/persistent | `set_dependency`, readiness | degraded; privileged work refused |
| telemetry/audit | sink outage, buffer full | transient | `buffered`, ALT-06 | mandatory audit ⇒ deny |
| control plane / config | bad or stale config | configuration/operator | `config.rejected`, ALT-07 | reject; keep last known good; rollback |
| overload | burst above capacity | overload | `inv41_overload_rejections_total` | early `Overloaded`; revocation priority lane |
| dependency (pk_core) | missing/unpinned | compatibility | estate gate | BLOCKED; production refuses |

Health thresholds (PROPOSED): readiness false if a required dependency is unavailable for >5 s or self-check has not passed; liveness false only in `failed`/`terminated`. Hysteresis: circuit breaker needs 2 consecutive successes to close.

## Staged rollout
<a id="rollout"></a>

dev → integration (estate gate) → staging → canary (5 % of workloads, ≥ 24 h observation) → phased production (25 % / 50 %, ≥ 24 h each) → full. Automatic abort triggers: any zero-tolerance event; deny-rate shift > 3× baseline; p99 latency > SLO for 15 min; error-rate > 1 %; memory > ceiling. Configuration/policy rolls out independently of code (signed config, monotonic version). Mixed versions allowed only within one MAJOR (contracts/SUPPORT_MATRIX.json).

**Emergency disable:** `Broker.quarantine()` freezes a domain (revocation remains available); `ConfigStore.rollback(operator_authorized=True)` restores last known good as a fresh domain.

## Version lifecycle and vulnerability response
<a id="vulnerability"></a>

* Supported lines: current MAJOR.MINOR and previous MINOR. Deprecation notice ≥ 180 days; security emergency may shorten to 30 days. EOL versions are refused for new production deployment by the release gate.
* Vulnerability SLA (PROPOSED): critical — ack 4 h, mitigation 24 h, patch 72 h; high — ack 1 business day, patch 7 days; medium — 30 days; low — next release. Coordinated disclosure after patch availability.
* Emergency revocation: rotate the config-signing key (`ConfigStore.revoke_key`), revoke subjects (`HmacTokenAdapter.revoked_subjects`), quarantine affected domains, publish a superseding release.
* Dependency intake: runtime is stdlib-only (GV003); track CPython security releases for the supported range.

## State reconstruction and backup
<a id="reconstruction"></a>

* Intentionally ephemeral, **never backed up**: authorities, seals, references, holders, membranes.
* Authoritative sources to reconstruct: signed configuration (policy), identity provider (principals), audit chain head (to anchor the new segment).
* Back up: signed configs + provenance, audit exports, evidence bundles, release manifests.
* Restore test: `tools/scale_soak.py` `scenario_restart` proves old references stay invalid and the new audit segment is anchored.
* Schema migration: `config.migrate` (INV41_CONFIG/0 → /1); re-sign after migration.

## Runbooks

### Day-0 bootstrap
1. `python -m inv41_capability_security.preflight <profile>` → expect `"ok": true`; on false, stop (see failing check).
2. `python -m inv41_capability_security.selfcheck` and with `-O` → expect `"passing": true`.
3. Load signed config: `ConfigStore(trusted_keys=...).activate(cfg)` → expect `config.activated`; on `ConfigRejected` fix and re-sign; never bypass.
4. Start `Broker(authority, audit=AuditChain(key))`, set `selfcheck_passed=True` after step 2, check `health()["ready"]`.
5. Rollback: stop the process; nothing persistent was changed.

### Day-1
Monitoring via DASH-01; routine config change = new signed version through canary; key rotation = add new key id, activate a config signed by it, then `revoke_key(old)`; dependency upgrade = new CPython patch through the compat matrix; capacity review monthly against `evidence/bench.json`.

### Day-2 troubleshooting
<a id="runbook-cross-authority"></a>
**Cross-authority attempt (ALT-01, SEV1):** find the correlation id in the reason ledger (`Broker.explain`), identify the component that received a foreign reference, quarantine the receiving domain, preserve audit export, open an incident.
<a id="runbook-forgery"></a>
**Forgery / invalid references (ALT-02):** check for code constructing objects via reflection; if in an isolated child, terminate the session (`close_session`).
<a id="runbook-deny-shift"></a>
**Deny-rate shift (ALT-03):** compare config digest in reason records before/after; roll back config if a recent activation correlates.
<a id="runbook-allow-shift"></a>
**Allow-rate shift (ALT-04, SEV1 candidate):** treat as possible policy widening; diff the active policy against the previous config; quarantine if unexplained.
<a id="runbook-auth-failures"></a>
**Authentication failures (ALT-05):** check issuer/audience config and clock skew; check for replay (nonce errors) and credential revocation.
<a id="runbook-audit"></a>
**Audit failure (ALT-06):** run `audit.verify_chain` on the export with the expected head; if invalid, preserve evidence and escalate SEV1; if sink outage, restore the collector — mandatory audit is already denying.
<a id="runbook-config-rollback"></a>
**Config rollback (ALT-07):** confirm the operator identity on the rollback event; verify the restored digest; open a change review.
<a id="runbook-degraded"></a>
**Degraded (ALT-08):** read `health()["dependencies"]`; restore the dependency; the broker returns to ready automatically.
<a id="runbook-overload"></a>
**Overload (ALT-09):** confirm with `inv41_overload_rejections_total`; scale out or raise `max_concurrent_checks` via signed config within the profile ceiling.
<a id="runbook-perf-regression"></a>
**Performance regression (ALT-10):** re-run `tools/bench.py` on the reference environment; bisect; a waiver needs the release approver.

## Incident management
<a id="incident"></a>

Severities per `OWNERS.json` escalation (SEV1 examples: authorization bypass, cross-authority acceptance, post-revocation use, signing-key compromise). Roles: incident commander, security lead, communications, scribe. Containment for suspected forgery/policy/domain/key compromise: quarantine affected domains → revoke membranes → rotate signing key → block the release line → preserve audit export and evidence bundle (hash recorded). Post-incident review within 5 business days with tracked corrective actions linked to requirement IDs. The audit chain is the tamper-evident timeline.

## Recurring reviews
<a id="recurring-reviews"></a>

| Review | Cadence | Owner |
|---|---|---|
| Access/ownership (OWNERS.json, CODEOWNERS) | 90 days | accountable_owner |
| Policy/configuration | 90 days | policy_approver |
| Dependency/SBOM/vulnerability | 30 days | technical_owner |
| Threat model / ADR | 180 days or on security-sensitive change | security_approver |
| Compatibility / EOL | each release | release_approver |
| Performance/capacity, alert quality (noise, false positives) | 90 days | technical_owner |

## Telemetry policy
<a id="telemetry-policy"></a>

| Class | Purpose | Allowed | Prohibited | Sampling | Retention |
|---|---|---|---|---|---|
| Security audit | forensics, compliance | event type, outcome, reason, opaque ids, config digest, version | seals, tokens, signatures, keys, payloads | none | 1 year (PROPOSED) |
| Operational logs | diagnosis | INV41_LOG/1 fields, redacted | as above; raw principal names | successes 1/N, failures never sampled | 30 days |
| Metrics | SLOs, capacity | registered names, bounded labels | raw user/resource ids as labels | n/a | 13 months aggregated |
| Traces | latency correlation | span name, op, status, duration | policy contents, identities | head-based 1–10 % | 7 days |

Export destinations are deployment-defined over authenticated encryption (B-KEY-01). Diagnostic escalation must not bypass these rules: elevated debug requires an operator grant with automatic expiry and is itself audited. Residency: each profile keeps telemetry in its region; far-edge buffers locally and uploads in region.

## Isolation policy
Adversarial or untrusted code MUST NOT run in the broker process. Semi-trusted code runs through `isolation.run_isolated` + `CapabilityBridge`. Fully adversarial workloads are blocked until B-ISO-01 (WVR-001).
