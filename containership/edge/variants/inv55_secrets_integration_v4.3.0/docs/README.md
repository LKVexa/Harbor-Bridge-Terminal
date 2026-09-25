# INV-55 documentation index (4.3.0, Draft)

All documents are Draft and `PENDING-OWNER-APPROVAL`. Statements cite `file::symbol`; unimplemented items say NOT IMPLEMENTED.

## Architecture
- [ADR-0001 Vault provider](architecture/ADR-0001-vault-provider.md)
- [Deployment patterns](architecture/deployment-patterns.md)
- [Outcome semantics](architecture/outcome-semantics.md)
- [Lifecycle](architecture/lifecycle.md)
- [Compatibility policy](architecture/compatibility-policy.md)
- [Compatibility matrix](architecture/compatibility-matrix.md)
- [Quota and fairness](architecture/quota-fairness.md)
- [Disconnected policy](architecture/disconnected-policy.md)
- [Constraint precedence](architecture/constraint-precedence.md)
- [Interface limits](architecture/interface-limits.md)
- [Failure-mode catalog](architecture/failure-mode-catalog.md)
- [Crash/restart semantics](architecture/crash-restart-semantics.md)
- [Split-brain](architecture/split-brain.md)
- [Degraded mode](architecture/degraded-mode.md)
- [Failover](architecture/failover.md)

## Requirements
- [SRS](requirements/SRS.md) · [NFR](requirements/NFR.md) · [Master workflow](requirements/master-workflow.md)

## Security
- [Threat model](security/threat-model.md) · [Identity roles](security/identity-roles.md) · [Ambient authority](security/ambient-authority.md) · [Peer authentication](security/peer-authentication.md) · [Artifact provenance](security/artifact-provenance.md) · [Tenant isolation](security/tenant-isolation.md) · [Encryption](security/encryption.md) · [Dependency outage matrix](security/dependency-outage-matrix.md) · [Memory handling](security/memory-handling.md) · [Secret-name privacy](security/secret-name-privacy.md) · [Telemetry privacy](security/telemetry-privacy.md)

## Operations
- [Runbooks](operations/runbooks.md) · [Incident response](operations/incident-response.md) · [Backup/restore](operations/backup-restore.md) · [Rollout/rollback](operations/rollout-rollback.md) · [Dashboards and alerts](operations/dashboards-alerts.md) · [Troubleshooting](operations/troubleshooting.md) · [Observability](operations/observability.md)

## Governance
- [Ownership](governance/OWNERSHIP.md) · [SLO/support](governance/slo-support-policy.md) · [Patching/EOL](governance/patching-vuln-eol.md) · [Review process](governance/review-process.md) · [Waiver register](governance/waiver-register.md) · [Release policy](governance/release-policy.md)

## Performance
- [Capacity model](performance/capacity-model.md) · [Performance policy](performance/performance-policy.md) · [Power/thermal](performance/power-thermal.md)

## Root
- [CODEOWNERS](../CODEOWNERS) · [catalog-info.yaml](../catalog-info.yaml) · [SECURITY.md](../SECURITY.md) · [THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)
