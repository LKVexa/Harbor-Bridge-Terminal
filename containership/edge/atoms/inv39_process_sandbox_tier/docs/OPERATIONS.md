# Operations runbooks (MC-095, MC-097..MC-101)

## Day 0 — install on an empty node
1. `sh tools/bootstrap.sh` → prints the feature probe; exits 2 if seccomp/NNP/user namespaces are missing.
2. Provision the node key into the secret store; set `node_key_ref`.
3. Activate config: `ConfigStore(dir).activate(cfg, actor=<you>, source=<git sha>)`.
4. Confirm `SandboxService.status()["ready"] is True`; record `config_digest` and `release_digest`.

## Day 1 — first workloads
Launch with `posix-minimal` or a GAP-13-issued profile. Verify the returned PK_SANDBOX_APPLIED/2 with `EvidenceVerifier`. Watch `inv39_sandbox_starts_total{outcome}`.

## Day 2 — routine
* Config change: overlay (tighten-only) → canary → promote; `rollback(actor, reason)` at any time.
* Weekly: `verify_chain_file(audit)` and compare the head with the externally stored copy.
* Release upgrade: build with `tools/build_release.py`, run `ci/ci.sh`, `tools/exit_gate.py` must say GO.

## Canary / staged rollout (MC-095)
Stages: 1 node → 5 % → 25 % → 100 %, 30 min soak each. Promotion requires: 0 `E_INTERNAL`, 0 escaped probes on the canary, launch p99 within NFR, no new `E_NOT_APPLIED`. Rollback: `ConfigStore.rollback` (config) or redeploy previous artifact by digest (release). Emergency disable: quarantine the node id (`Quarantine.set(..., target=<node_id>)`) → all new launches refused. **Status: procedure only; no fleet orchestrator in this repository.**

## Incident (MC-100)
| SEV | Example | Page | First action |
|---|---|---|---|
| 1 | escape probe ESCAPED in prod, evidence forgery | owner + security immediately | quarantine node(s); preserve audit chain + head |
| 2 | E_NOT_APPLIED spike, attestation failures | owner 30 min | quarantine affected tenant/profile; rollback config |
| 3 | overload / quota exhaustion | on-call | raise ceilings only via approved config change |
Containment → evidence capture (`audit.jsonl`, `status()`, metrics) → recovery (rollback/re-launch) → review within 5 business days.

## Vulnerability response and EOL (MC-097)
Kernel CVEs reachable through allowed syscalls: assess against the profile allow-lists within 24 h (critical) / 7 d (high); tighten profiles or quarantine. Supported release lines: current + previous minor; EOL announced 90 days ahead. Advisory channel and SLA owner: _UNASSIGNED_.

## Backup / restore (MC-098)
State to back up: config `history.jsonl` + `active.json`, `audit.jsonl` + externally stored head hash, node key (in the secret store, not here). Restore: copy files back, `ConfigStore(dir)` recovers the active version, `AuditChain(path)` refuses to open a tampered chain. Evidence records are reconstructible only from the audit chain digests, not re-signable.

## Recurring reviews (MC-101)
Quarterly: access grants (Authorizer roles), profile allow-lists vs. workload needs, dependency matrix, exception register expiry, ADR validity. Owner: _UNASSIGNED_.
