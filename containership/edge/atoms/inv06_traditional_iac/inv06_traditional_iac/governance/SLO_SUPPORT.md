# Production Support and SLO Commitment (MC-070) and Tail-Latency Thresholds (MC-052)

Status: **Draft — estate commitments require owner sign-off.** Release-blocking *reference* thresholds are enforced by `release.check_slos`.

| SLI | Reference threshold (release-blocking) | Proposed estate SLO |
|---|---|---|
| plan p99 @ 1 000 resources | ≤ 0.25 s | ≤ 2 s |
| apply (engine) p99 @ 1 000 | ≤ 0.25 s | ≤ 2 s excluding provider time |
| drift p99 @ 1 000 | ≤ 0.25 s | ≤ 2 s |
| backend commit p99 @ 1 000 | ≤ 1.0 s | ≤ 3 s |
| control-plane availability | — | 99.9 % monthly (error budget 43 m) |
| state durability | — | no committed revision lost (RPO 0 on host; backup RPO 1 h) |

Support hours, response targets and escalation: _owner to set_ (see `OWNERS.yaml`). Proposed: Sev1 15 min 24×7, Sev2 1 h business hours, Sev3 next business day.
