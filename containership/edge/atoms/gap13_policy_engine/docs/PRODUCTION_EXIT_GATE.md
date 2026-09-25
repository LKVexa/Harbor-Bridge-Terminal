# Production-exit gate (G13-MC-050)

`python -m gap13_policy_engine.release_gate --profile production` writes `evidence/<release>/gate_production.json`, integrity-linked to the certification manifest digest and artifact digests.

The production profile adds, on top of the `rc` (engineering regression) profile:
* every component in `COMPONENT_STATUS.json` is `DONE` or covered by an **approved, unexpired** waiver;
* no role in `docs/OWNERS.yaml` is `UNASSIGNED`;
* ADR-001 status is `Accepted`;
* all Priority-0 components are `DONE` (waivers not accepted for P0 unless governance explicitly permits).

Verdicts: `GO`, `CONDITIONAL_GO` (only approved waivers outstanding), `NO_GO`. The gate never self-approves; acceptance is recorded by the reviewers named in OWNERS.yaml by changing component status to `DONE` in a reviewed commit.
