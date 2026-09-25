# INV-45 runbooks — day-0 / day-1 / day-2, rollout, incident (C040, C092, C096, C097)

All commands run from the directory that contains `inv45_sfi_mechanisms/`. Every step has a check; stop at
the first failed check. Ownership of each procedure: `OWNERSHIP.md` (roles UNASSIGNED — bind before use).

## Day-0: bootstrap an empty node (C040)

1. Install pinned dependencies: `python -m pip install -c inv45_sfi_mechanisms/constraints.txt cryptography`
   and Node 22 LTS. **Check:** `python -m inv45_sfi_mechanisms.production.cli preflight` exits 0.
2. Provision secrets in the secret store and export references only:
   `INV45_SEAL_KEY`, `INV45_IDP_KEY` (≥ 32 random bytes each). **Check:** nothing secret appears in config.
3. Write the base config (release-reviewed) and validate it:
   `python -m inv45_sfi_mechanisms.production.cli config-validate base.json`. Record the printed digest.
4. Create the state root (`config/`, `state/`, `audit/`) on a local filesystem with atomic rename
   (A-21), mode 0700, owned by the service user.
5. Start the service; activate generation 1 via `activate_config` (author, source, change id).
   **Check:** `health().status == "ready"`, `config_generation == 1`, digest matches step 3.
6. Run the smoke: `python -m unittest inv45_sfi_mechanisms.tests.integration.test_engine_e2e`.
7. Export the audit checkpoint (`AuditLog.checkpoint()`) to the SIEM.

Deterministic: same pinned artifacts + same base config ⇒ same config digest and profile digest.

## Day-1: deploy a new release (canary → staged → full) (C092)

| Stage | Traffic | Duration | Promote when | Abort when |
|---|---|---|---|---|
| 0 pre-flight | 0 | — | CI + `tools/release.py --verify` PASS; perf gate not FAIL (or approved waiver) | any gate FAIL |
| 1 canary | 1 node, ≤ 5 % tenants | ≥ 1 h | error rate ≤ baseline, no `SFI_INTERNAL_INVARIANT`, verify p95 ≤ 1.5× | any invariant/security error, health not ready, p95 > 2× |
| 2 staged | 25 % nodes | ≥ 4 h | as stage 1 | as stage 1 |
| 3 full | 100 % | — | — | — |

Mixed versions during rollout are safe because descriptors bind `config_sha256`/`profile_sha256`: a
descriptor sealed on one node version is refused by another whose profile/config differs (tenants resubmit).
Nodes must not share a state root across versions (C058).

**Rollback (automatic triggers):** stage abort criteria above, or health `degraded` > 10 min on canary.
**Rollback (operator):** redeploy previous release artifact (digest from `release/MANIFEST.json`); then
`rollback_config(token, to_generation=N, reason=...)`. Measured config rollback time in tests: < 50 ms
(local); release rollback time depends on the deployment system — **not yet measured** (open).

## Emergency disable

* Tenant: `quarantine(op_token, "tenant", "<tenant>", "disable", "<reason>")` — stops new loads and
  execution for that tenant immediately, running handles are stopped.
* Global: requires two humans: `quarantine(op1, "global", "*", "disable", "<reason>", second_token=op2)`.
  **Check:** `health().status == "quarantined"`. Survives restart (durable state).
* Release: `release(...)` with the same authority rules.

## Day-2 operations (C096)

* **Every change** (contract, code, policy): full CI, perf gate, re-verify fixtures, compare audit
  checkpoint continuity.
* **Key rotation:** CRYPTO_POLICY.md §Key lifecycle.
* **Config change:** stage → validate (`config-validate`) → `activate_config` with `expected_current`
  (CAS) → watch health 10 min → keep previous generation number for rollback.
* **Stale activation lock (FM12):** confirm no activation process is alive (`ps`), check that
  `CURRENT` points at a valid generation (`GenerationStore.recover()` returns `active-ok`), then remove
  `<root>/config/.activate.lock`. Record an audit note.
* **Controller takeover (FM10):** stop the old controller; start the new one with `force=True` ownership
  takeover; verify the old one now fails writes (fenced).
* **Audit verification:** `cli audit-verify <root>/audit/audit.jsonl --checkpoint SEQ:HASH` daily against
  the SIEM checkpoint.
* **Troubleshooting:** every rejection returns a `decision_id`; `explainer.explain(decision_id)` shows the
  deciding constraint, inputs (digests), policy generation and topology.

## Incident response (C097)

Severity model (objective triggers):

| Sev | Trigger | Page | Response target |
|---|---|---|---|
| SEV-0 | confirmed memory/control-flow escape, verifier bypass, unauthorized execution, sealing-key compromise | primary + secondary on-call + security owner, immediately | contain ≤ 15 min |
| SEV-1 | cross-tenant impact suspected; `SFI_AUDIT_TAMPERED`; `SFI_INTERNAL_INVARIANT` in production | primary on-call + security owner | contain ≤ 1 h |
| SEV-2 | service unavailable / sustained `dependency_stale` / perf gate regression in production | primary on-call | ≤ 4 h |
| SEV-3 | degraded non-critical dependency, single-tenant rejections | ticket | next business day |

Steps: (1) **contain** — tenant or global disable (dual authorization for global); revoke keys if key
compromise; (2) **preserve evidence** — copy audit log + checkpoint, config generations, state root,
decision records, engine job inputs if retained by the caller; (3) **eradicate/recover** — patch, new
release through the gates, rotate keys, re-verify all artifacts under the new profile; (4) **release**
quarantine with the same authority; (5) **post-incident review** within 5 business days, feeding
WAIVERS.md and THREAT_MODEL.md.

Escalation targets are team aliases in `OWNERSHIP.md` (currently UNASSIGNED placeholders). The quarterly
paging drill required by C009/C097 has **not** been run.
