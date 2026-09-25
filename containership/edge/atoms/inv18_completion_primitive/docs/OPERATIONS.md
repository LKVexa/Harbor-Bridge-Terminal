# INV-18 operations, release and governance (C091–C098)

All `sh runbook` blocks are executed verbatim by tests/test_release.py::RunbookTest from
the directory that contains the package, with `$PY` set to the Python interpreter and
`$EVID` to a scratch evidence directory. If a block stops working, CI fails.

## SLO policy

| SLO | SLI (numerator / denominator) | Objective | Window | Error budget |
|---|---|---|---|---|
| at most once [S] | `inv18_invariant_violations_total` + futures observed resolved twice / futures created | 0 | rolling 30 d | **none** — any event is SEV1 |
| no orphans [S] | abandoned futures whose receiver did not get FUTURE_ABANDONED / abandoned futures | 0 | rolling 30 d | none |
| resolution latency [S, revised P] | resolutions with latency ≤ 800 µs (governed) / resolutions | ≥ 99 % | rolling 30 d | 1 % |

The source SLO "p99 under 1 µs" is not achievable in CPython (W-C062); the revised
objective is PROPOSED until the owner approves it. Burn-rate alerts: 14.4× over 1 h
(page), 6× over 6 h (ticket). Budget exhausted ⇒ feature freeze for INV-18 until the
budget recovers; only reliability fixes ship. SLO reporting owner: operational_owner
(VACANT ⇒ primary_technical_owner). Support: business hours (OWNERS.json `after_hours`).
Severity response commitments: OWNERS.json `response_targets_minutes`. Measurement
source: C072 metrics (`python -m inv18_completion_primitive slo-report`).

## Rollout (C092)

Pre-production: `gate` must be `GO` (or `CONDITIONAL_GO` with accepted conditions).
Canary: one process / 1 % of workers for 24 h; exit signals: zero invariant violations,
A1–A9 silent, p99 within threshold. Stages: 1 % → 10 % → 50 % → 100 %, each ≥ 4 h.
Automatic halt: any SEV1/SEV2 alert. Rollback: redeploy the previous sealed artifact
(digest in the previous `RELEASE_EVIDENCE.json`) and its config revision.
Emergency disable: `Runtime.disable(admin, mode="freeze")` in the host, or removal of
INV-18 from the registry package (pk_core reports a reduced element count).
Operator authorization: holder of the AdminCap = operational_owner. Rollout status is
recorded as audit events (`config.activate`, `component.disable`).

```sh runbook
$PY -m inv18_completion_primitive drill canary --evidence-dir "$EVID"
$PY -m inv18_completion_primitive drill rollback --evidence-dir "$EVID"
$PY -m inv18_completion_primitive drill disable --evidence-dir "$EVID"
```

## Supported-version matrix (C093)

`conformance/COMPAT_MATRIX.json` is canonical (INV-18 releases × Python × pk_core ×
contract versions × adjacent contracts; supported / deprecated / unsupported).
`python tools/compat_matrix.py` executes the supported Python versions available on
the host and writes `conformance/COMPAT_RESULTS.json`; the gate reads it.

## Maintenance policy (C094)

Severity: critical (exploitable isolation/at-most-once break), high, medium, low.
Patch SLAs: critical 72 h, high 14 d, ordinary defects next minor. Intake: private
report to the security_owner (VACANT ⇒ approving_authority); dependency advisories
checked on every review (REVIEWS.json `vulnerabilities`, 30 d). Emergency release:
patch branch → full gate → canary shortened to 1 h. Supported lifetime: the latest two
minor releases; EOL notice 90 days; unsupported versions receive no fixes and the gate
refuses to certify them. Backports: critical/high only. Events are recorded in CHANGELOG.

## Backup / restore / reconstruction (C095)

Runtime future state is intentionally non-durable and **not reconstructable** (it has
no meaning after the process is gone). Back up: `config/*.json` (with the repository),
release evidence (`conformance/RELEASE_EVIDENCE.json`, `evidence/`), audit exports (host
sink). Restore = check out the release tag, verify digests, re-run bootstrap. Config
migration: bump `schema_version`, provide a migration function, keep N-1 readable for one
minor. Schema migration: new major wire schema alongside the old. Rollback across a
migration: the previous release reads its own config revision. RPO/RTO: config/evidence
RPO = last commit; RTO = bootstrap time (< 1 min, measured by the bootstrap report).

```sh runbook
$PY -m inv18_completion_primitive bootstrap --evidence-dir "$EVID"
$PY -m inv18_completion_primitive verify-install
```

## Runbooks (C096)

### RB-D0 — day 0 (bootstrap)

1. Prerequisites: CPython ≥ 3.10 (`bootstrap` checks), no third-party packages.
2. Clean bootstrap, dependency verification, configuration check, smoke tests,
   pk_core registration check (reports BLOCKED today), conformance preflight:

```sh runbook
$PY -m inv18_completion_primitive bootstrap --evidence-dir "$EVID"
$PY -m inv18_completion_primitive validate-config inv18_completion_primitive/config/prod.json
$PY -m inv18_completion_primitive conformance
```

### RB-D1 — day 1 (deployment)

```sh runbook
$PY -m inv18_completion_primitive status --config inv18_completion_primitive/config/staging.json
$PY -m inv18_completion_primitive drill canary --evidence-dir "$EVID"
```
Health/SLO checks: `status` must show `ready: true`; canary drill must report `pass`.
Rollback: `drill rollback` demonstrates the procedure; in production redeploy the
previous artifact (see Rollout).

### RB-D2 — day 2 (operation)

- **RB-D2-1 monitoring**: dashboards/inv18_dashboard.json; alerts A1–A9.
- **RB-D2-2 diagnostics**: `explain` shows why the component is degraded.
- **RB-D2-3 routine upgrade**: gate → canary → stages.
- **RB-D2-4 capacity review**: compare `outstanding` and memory with docs/PERFORMANCE.md capacity model.
- **RB-D2-5 evidence verification**.

```sh runbook
$PY -m inv18_completion_primitive explain
$PY -m inv18_completion_primitive faults --evidence-dir "$EVID"
$PY -m inv18_completion_primitive slo-report
$PY inv18_completion_primitive/tools/verify.py inv18_completion_primitive
```

## Incident management (C097)

| SEV | INV-18 examples | Page? | Initial response |
|---|---|---|---|
| SEV1 | invariant violation (double resolution/take), cross-tenant access, evidence corruption | yes | 15 min |
| SEV2 | SLO burn, saturation of process limit, auth attack burst | yes (business hours) | 60 min |
| SEV3 | abnormal abandonment, producer defects, release-gate failure | no | 1 business day |
| SEV4 | policy rejections, informational | no | best effort |

Roles: incident commander = approving_authority until an on-call exists; technical
escalation and security escalation per OWNERS.json tiers.

### INC-1 invariant violation
Contain: `disable(mode="freeze")`. Preserve evidence: export `rt.audit.events`,
`rt.decisions.records`, metrics snapshot. Recover: roll back to the last GO artifact.
Decide rollback when the violation reproduces on the current artifact but not the previous.

### INC-2 SLO burn
Check `explain` for SOFT_LIMIT_EXCEEDED/STALLED_FUTURES; distinguish producer slowness from
primitive latency via resolution vs receive histograms.

### INC-3 security event
Security escalation (tier 3). Revoke keys (`KeyRing.revoke`), disable the tenant scope,
preserve the audit chain and verify it.

### INC-4 producer defects
Double resolutions/abandonments are caller defects; notify the producing team with
decision records (RESOLVE_REJECTED / ABANDON_TRANSITION).

Communication: status note to consumers of INV-18 within the response target; post-incident
review within 5 business days recorded in REVIEWS.json `incidents`. Tabletop exercise:
**not yet conducted** (needs human participants) — the gate reports condition `TABLETOP_PENDING`.

## Recurring reviews (C098)

governance/REVIEWS.json holds cadences, the critical set, and records. A critical
review overdue beyond its cadence blocks the gate; a review counts only with a human
`completed_by`.
