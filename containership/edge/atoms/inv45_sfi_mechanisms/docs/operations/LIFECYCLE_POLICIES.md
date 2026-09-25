# Patching, vulnerability response, EOL, backup/restore, recurring reviews (C094, C095, C098)

## Patching and vulnerability response (C094)

| Severity (CVSS / impact) | Triage | Fix released | Deployed |
|---|---|---|---|
| Critical (escape, verifier bypass, key exposure) | 24 h | 7 days | 7 days |
| High | 3 days | 30 days | 30 days |
| Medium | 7 days | 90 days | next release |
| Low | 30 days | best effort | next release |

Scope includes dependencies: Node/V8 (engine CVEs are treated as this component's CVEs because isolation
depends on them), CPython, `cryptography`. Disclosure: private report to the security owner alias
(`SECURITY.md` §Reporting); coordinated disclosure after fix. Dependency updates follow the ADR upgrade
procedure; `constraints.txt` is reviewed monthly (REVIEWS below).

**Supported lifetime / EOL:** each minor release is supported for 12 months or until two newer minors ship,
whichever is later; EOL is announced 90 days ahead; after EOL no security fixes. Engine majors follow the
upstream Node LTS EOL dates.

These SLAs are **proposed** and have not been exercised (no incident has occurred); owner UNASSIGNED.

## State inventory, backup, restore, migration (C095)

| State | Durable? | Backup | Restore / reconstruction |
|---|---|---|---|
| Config generations + CURRENT | yes | copy `config/` (immutable files + pointer) | restore dir; `GenerationStore.recover()` validates every generation by digest |
| Quarantine + anti-rollback floors (`state/state.json`) | yes | copy `state/` | restore **before** taking traffic; a node without floors could accept a rollback — floors can also be reconstructed as max(version) from audit `load` events |
| Audit log | yes | ship to SIEM continuously; export checkpoints | append-only; verify with checkpoint after restore |
| Keys / trust roots | external | secret store backup | rotate on doubt |
| Replay cache, verify cache, instances, explain records | no (ephemeral) | — | rebuilt; descriptors outstanding at crash are burned only if consumed |

RPO: config/state = last successful atomic write; audit = spool contents (≤ 10 000 events) if the host is
lost before shipping. RTO: day-0 steps 4–5 (< 5 min on the baseline host). Restore drills: **not yet run**
(open).

Migration: schema ids are explicit; a future `PK_SFI_STATE/2` ships with a one-way migration tool and keeps
the `/1` reader for one minor release.

## Recurring reviews (C098)

| Review | Cadence | Inputs | Output |
|---|---|---|---|
| Access (grants, operators, IdP subjects) | quarterly | IdP export, audit `authz.decision` denials | removed grants, ticket per finding |
| Policy (profile, allowlists, limits) | quarterly and on any `profile.*` change | config generations diff | ADR if pinned items change |
| Dependency (Node, CPython, cryptography, pk_core) | monthly | advisories, constraints.txt | patch per SLA |
| Configuration drift | monthly | active digest vs release base | rollback or reviewed generation |
| Architecture + threat model | semi-annually and on triggers (engine/loader/CPU/boundary change) | ADR, THREAT_MODEL | updated docs, waiver renewals |
| Waiver register | monthly | WAIVERS.md | expiries renewed or closed |

Each review is recorded as an entry in `release/reviews.jsonl` (schema: date, review, reviewers, findings,
tickets). **No review has been performed yet**; the file starts empty. Findings feed WAIVERS.md.
