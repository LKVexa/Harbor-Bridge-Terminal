# INV-71 operations: rollout, runbooks, incidents, recovery, patching, reviews (C038, C040, C091-C099)

**Status:** PROPOSED procedures. None of them has been exercised against a production or production-equivalent environment, and no owner has reviewed them. Each step says what exists in this repository and what it assumes.

## 1. SLOs and support (C091)

The SLO table is in `docs/ARCHITECTURE.md` §6. Burn-rate policy (PROPOSED): page on a 14.4× burn over 1 h plus 5 min, ticket on a 6× burn over 6 h. An exhausted error budget pauses rollouts (§2). Zero-budget invariants (isolation, forbidden egress, teardown reported CLOSED while leaking) page as SEV1 on the first occurrence. Support hours: 24×7 for SEV1–2 and business hours for SEV3–4 (owner to confirm). Component-local SLOs cover teardown and audit durability. End-to-end SLOs cover create-to-ready and availability.

## 2. Staged rollout and rollback (C038, C092)

| Stage | Scope | Observation window | Pre-promotion gate |
|---|---|---|---|
| lab | qualified lab node | 24 h | full test suite + `tools/production_gate.py` evidence for the exact digest |
| canary | 1 node per site | 24 h | 0 security events; teardown verified 100%; p99 create within target; overhead within tolerance |
| 5% | per site | 24 h | same, plus no SLO burn alert |
| 25% → 100% | progressive | 24 h each | same |

Automatic rollback triggers: any zero-budget violation, crash loop (3 restarts in 10 min), startup regression over 20% versus baseline, failed health, or an incompatible config or artifact activation. Rollback re-activates the previous config generation (`ConfigStore.rollback`, tested) and the previous signed manifest serial, after verifying that its signatures are still valid and that its artifacts are not revoked. An operator-initiated rollback records cohort, reason and incident id, and needs two people for any security-sensitive downgrade (`rollback.execute` is two-person). Emergency disable (`emergency.disable`, one person, audited) is independent of the rollout system.

## 3. Runbooks (C096)

Every step lists its prerequisites, action, expected output and abort criteria. The commands shown are the reference tools. The production equivalents are marked TBD, because the node agent does not exist yet.

### Day 0: node bootstrap and qualification (C040)
1. **Qualify.** `python -c "from inv71_heavy_agent_sandbox.control.qualify import probe_local, qualify; print(qualify(probe_local(), '<profile>'))"`. Expected: `verdict: ADMIT`. Abort on REJECT.
2. **Verify artifacts.** Fetch the signed manifest and verify each artifact with `ManifestVerifier.verify_artifact`. Abort on any `ARTIFACT.*` error.
3. **Provision trust roots and node identity.** TBD (PKI). Abort if attestation fails.
4. **Configure the host.** cgroup delegation to `/sys/fs/cgroup/firecracker`, `/srv/jailer`, KSM off, core dumps off, nftables base table. TBD script. It must be idempotent: re-running converges.
5. **Activate config.** Stage the signed generation, then `activate` with every node participant preparing. Abort if any participant rejects.
6. **Register the node** with the controller. Readiness must report `READY`.
Resume after interruption: every step is idempotent. Re-run from step 1, and let `reconcile()` reap any partial resources before admitting work.

### Day 1: deploy
Canary selection, gates and rollback are in §2. Validate compatibility with `compat.check_skew` and `deployable()` before each cohort, and abort on `COMPAT.UNSUPPORTED_VERSION`.

### Day 2: operate
- **Drain a node:** `emergency_disable(scope="node")`. Wait for sessions to reach CLOSED or QUARANTINED, then patch, requalify and `emergency_enable` (two-person).
- **Patch the runtime or kernel:** see §5.
- **Policy or config rollout:** a signed generation plus two-person activation, cohort by cohort.
- **Certificate or key rotation:** TBD with the PKI. Stale credentials stop at their grace.
- **Degraded dependency:** `status()` shows `degraded_dependencies`. Security dependencies fail closed automatically.
- **Quarantine:** freeze (forensics) or quarantine the session or node, collect the audit stream and explain records, then release it for reaping (operator-only transition).

## 4. Incidents (C097)

| Severity | Triggers | Page | Acknowledge / mitigate |
|---|---|---|---|
| SEV1 | isolation breach, forbidden egress, artifact or signature compromise, unauthorized control action, audit tampering | primary + IC + security | 5 min / 1 h |
| SEV2 | teardown verification failures on more than one node, trust-dependency outage beyond grace, SLO fast burn | primary | 15 min / 4 h |
| SEV3 | single QUARANTINED session, degraded noncritical dependency | ticket | next business day |

Containment playbooks: disable new sessions (global, tenant or node), revoke the policy or artifact digest (`ManifestVerifier.revoked`), quarantine a node or site, cut egress by activating an empty-allowlist generation, drain, rotate credentials, and preserve evidence (audit stream plus anchors plus explain log). Re-entry: requalify the node, re-establish trust, and verify reconcile shows no orphans. Tabletop and live game days are BLOCKED until owners exist.

## 5. Patching, vulnerabilities, end of life (C094)

Patch SLAs (PROPOSED), measured from disclosure to fleet completion: critical 72 h, high 14 d, medium 30 d, low next release. Advisory sources: Firecracker security advisories, Linux kernel CVE feed, and the guest distro feed. Each maps to the manifest artifact class and SBOM component. Emergency path: rebuild, sign a new manifest serial (revoking the old digest), canary, then progressive rollout. Supported release lifetime is N and N-1, with 90 days' deprecation notice. After end of life, nodes refuse to start an unlisted combination (`deployable()`).

## 6. Backup, restore, reconstruction (C095)

| State | Strategy |
|---|---|
| session writable state | never backed up; sessions rebuild from the clean base snapshot |
| base images and snapshots | reconstructed from signed, pinned artifacts; the digest is verified before use |
| config generations and provenance | backed up (encrypted, immutable, residency-scoped) |
| audit streams and anchors | WORM sink; anchors replicated off-site |
| lease / ownership table | rebuilt by reconciliation; epochs from a durable counter |

Restore drills into an isolated environment are BLOCKED here.

## 7. Recurring reviews (C098)

`governance/review_schedule.json` lists cadence and scope: privileged access and break-glass use monthly, egress policy and artifact allowlist monthly, dependencies and advisories weekly, configuration drift daily (automated: the effective config digest against the approved generation), architecture and threat model quarterly. Reviewers must be independent of the change author. Findings go to `governance/waivers.json` or the tracker, with owner and due date.

## 8. Waivers and technical debt (C099)

`governance/waivers.json` is the register (schema in the file). The gate refuses any expired, ownerless or permanent waiver on a security invariant. The register is empty: nothing has been waived, and nobody exists who could approve a waiver.
