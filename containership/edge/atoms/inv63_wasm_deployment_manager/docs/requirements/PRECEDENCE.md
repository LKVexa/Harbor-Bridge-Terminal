# INV-63 Conflict Precedence

| Field | Value |
|---|---|
| Document ID | INV63-REQ-PRECEDENCE |
| INV-63 C-IDs covered | C019 (with C055) |
| Status | DRAFT — pending approval |
| Owner | Service owner (role) — UNASSIGNED |
| Reviewers | Security reviewer (role), Architecture reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when `service.PRECEDENCE` / `service._eligible` changes. |

## Rule
`service.py::PRECEDENCE = ("security", "residency", "consistency", "slo", "cost")`. A higher concern is never traded for a lower one.

| Rank | Concern | Mechanism in code |
|---|---|---|
| 1 | security | authn/authz, `ArtifactVerifier`, `Controls.check` (emergency disable, quarantine, freeze) before any action; `_eligible` removes `controls.quarantined_hosts` first |
| 2 | residency | `_eligible` keeps only hosts where `config.residency_labels[host] in body.residency`; none → `INV63-E-POLICY` at `set_desired` |
| 3 | consistency | journal-before-act (`desired_set` appended before in-memory update), epoch fencing, idempotency keys; rollouts refused offline |
| 4 | SLO | spread across labels (`manager.diff(spread=True)`), `max_unavailable`, make-before-break in `reconcile_ns` |
| 5 | cost | pack placement (`spread=False`) / fewest instances per host |

## Worked examples (host set from `tests/_support.py`: `h1:z1, h2:z2, h3:z3, h4:z1`; residency labels `h1,h2=eu`, `h3,h4=us`)

| # | Situation | Result | Code path |
|---|---|---|---|
| E1 | `count=2, residency=["eu"]` | placed only on `h1`,`h2` (zones z1,z2 — spread still satisfied) | `_eligible` → `manager.diff(eligible_hosts=[h1,h2])`; `test_service.py::SemanticsTest::test_precedence_residency_over_spread` |
| E2 | `residency=["mars"]`, `count=1` | rejected `INV63-E-POLICY` "no host satisfies residency/security constraints" | `op_set_desired` |
| E3 | `residency=["eu"]` and `h2` quarantined, `count=2` | eligible = `[h1]` → only one label; decision constraint note `"spread relaxed: residency/security precede SLO spread"`; both instances on `h1` | `_eligible` + `reconcile_ns` spread note |
| E4 | residency workload already running on a host that becomes ineligible (quarantined) | instance counted as stale and stopped; replacement started first on an eligible host (make-before-break) | `manager.diff` (`a[2] not in allowed`) |
| E5 | Lattice offline during a rollout request | rollout refused `INV63-E-CONTROL-PLANE-OFFLINE` rather than proceeding without observation (consistency > SLO) | `op_rollout` |
| E6 | Tenant frozen but a reconcile is due | no action (`INV63-E-FROZEN`); `tick()` skips it (security/operator control > SLO) | `Controls.check` |
| E7 | Quota vs SLO: request exceeds `tenant_quotas` | `INV63-E-QUOTA` — capacity policy is not relaxed to meet desired count | `op_set_desired` |

## Spread relaxation note
When `spread=True`, `count > 1` and eligible hosts span fewer than two labels, the placement proceeds on the available label(s) and the relaxation is recorded only in the decision record (`constraints.note`), visible via the `explain` op. It is not surfaced as an error, outcome or metric. If `eligible_hosts` becomes empty during reconcile, `manager.diff` raises `LookupError` → `INV63-E-PRECONDITION`.

Gap: "consistency" and "cost" have no explicit arbitration code; they are expressed through ordering of checks as listed above.
