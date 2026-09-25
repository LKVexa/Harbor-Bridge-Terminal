# Operations, release and governance (INV-40-C091..C099)

## SLOs and error budgets (C091) — PROPOSED
| SLO | Objective | Budget |
|---|---|---|
| Primitive requirement | 0 guests without primitive | none |
| Device exclusivity | 0 shared device instances | none |
| Footprint honesty | 100 % guests at measured VmRSS | none |
| Boot within budget | 95 % of boots ≤ 8 s over 28 d | 5 % |
| API availability (non-shed) | 99.9 % over 28 d | 43 min |
Support commitment: UNASSIGNED (needs an owner).

## Rollout, rollback, emergency disable (C092)
1. Canary: one host, `environment=staging`, 24 h, alerts FVT-A01..A10 silent.
2. Staged: 10 % → 50 % → 100 % of hosts, each stage gated by `tools/ci.py` evidence + gate re-run.
3. Rollback: config via `ConfigStore.rollback`; package via previous signed artifact digest.
4. Emergency disable: `quarantine(<human admin token>, "tier", reason)` → ready=false, new boots refused, running guests untouched unless guest-scoped quarantine is applied.

## Supported-version matrix (C093)
| Dependency | Supported | Verified here |
|---|---|---|
| CPython | 3.10, 3.11, 3.12 | 3.11.15 (cloud) |
| Linux KVM | any with `/dev/kvm` | **not verified** |
| QEMU | ≥ 7.2 (`-accel kvm`, `-sandbox`, q35) | **not verified** — pin pending (C031) |
| pk_core | UNPINNED | absent |
| Protocol majors | PK_FULL_VM*/1 | tests |

## Patching / vulnerability response / EOL (C094) — PROPOSED
Critical CVE in QEMU/KVM/this package: fix or mitigate ≤ 72 h; high ≤ 14 d; medium ≤ 90 d. Each minor supported ≥ 12 months after the next minor. Owner UNASSIGNED.

## Backup / restore / reconstruction (C095)
State = `state_dir`. Backup: `Journal.export(dest)` (compacted snapshot) + copy `audit.jsonl` + `config/`. Restore: `Journal.restore(backup, path)` refuses a torn backup; start the service → `recover()` reconciles. Tested in `test_torn_tail_corrupt_middle_compact_backup`. Guest disks are out of scope (immutable images by digest).

## Runbooks (C096)
* **Day 0:** `tools/bootstrap.py --state-dir … --site … --env …` → exit 0 only when ready.
* **Day 1:** `python tools/ci.py` → evidence; `python -m fvt.gate`-equivalent via `tools/ci.py --gate`; NO_GO blocks rollout.
* **Day 2:** watch alerts; rotate keys (`KeyProvider.rotate`, then revoke old kid after max token TTL 1 h); compact journal weekly; verify audit chain daily (`AuditLog.verify`) and export `audit_head` off-host.

## Incidents (C097)
SEV1 isolation breach / primitive bypass / audit chain failure → page security owner, quarantine tier, preserve `state_dir` read-only, verify audit chain, rotate keys. SEV2 tier unavailable → on-call; check breaker, trust services, primitive. SEV3 degraded → ticket. Escalation intervals in `docs/OWNERS.md`. **No drill has been run.**

## Recurring reviews (C098) — PROPOSED cadence
Access (token issuers, admin holders): monthly. Policy/config diff: each activation + quarterly. Dependencies (QEMU, kernel, CPython): monthly. Architecture (ADR-0001): semi-annually. None has occurred yet.

## Exceptions register (C099)
`governance/EXCEPTIONS.json` — every entry has owner, expiry, and reason; the gate refuses expired or unapproved waivers.
