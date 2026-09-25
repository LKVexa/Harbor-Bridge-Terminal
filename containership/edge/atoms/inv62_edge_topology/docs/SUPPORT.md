# Support commitments (MC-080) — DRAFT, not in force

These commitments take effect only when an accountable owner accepts them in `OWNERSHIP.md`.
| Item | Proposed commitment |
|---|---|
| Support hours | SEV1/SEV2 24×7 on-call; SEV3/4 business hours (owning team's region) |
| Response | per `INCIDENT_RESPONSE.md` ack targets |
| SLOs | reachability: zero routes across down links (no budget); partition continuity: lease grantable within 5 s (1 %); resolution: engine p99 < 1 ms (1 %) |
| Error budget policy | budget exhausted → freeze feature releases for the component until restored |
| Supported versions | latest minor of the current major, plus previous minor for 180 days |
| Channels | ticket queue + page alias (TBD by owner) |
