# Lifecycle state machines (M10) — generated from fabric/lifecycle.py

States — component: absent, staged, starting, running, degraded, stopping, stopped, failed, quarantined; host: unknown, joining, active, draining, suspect, lost, quarantined, removed; link: absent, granted, revoked, expired.

Any (state, event) pair not listed is **illegal** and returns `ILLEGAL_TRANSITION` without mutating state. Repeating an event whose target is the current state is an idempotent no-op. Mutations are serialized by the control-plane mutex and fenced by the lease epoch; every transition is persisted to the WAL before it is acknowledged, so a crash between WAL append and acknowledgement replays to the same state. After restart, links are reconstructed as `revoked` (fail closed).

| machine | from | event | to | side effect | emitted event |
|---|---|---|---|---|---|
| component | absent | stage | staged | artifact verified and pinned | `component.staged` |
| component | degraded | fail | failed | instance lost | `component.failed` |
| component | degraded | quarantine | quarantined | operator isolation | `component.quarantined` |
| component | degraded | recover | running | health restored | `component.running` |
| component | degraded | reschedule | starting | moved off lost host | `component.rescheduled` |
| component | degraded | stop | stopping | links revoked | `component.stopping` |
| component | failed | quarantine | quarantined | operator isolation | `component.quarantined` |
| component | failed | reschedule | starting | moved off lost host | `component.rescheduled` |
| component | failed | stage | staged | artifact verified and pinned | `component.staged` |
| component | quarantined | release | stopped | operator release | `component.released` |
| component | running | degrade | degraded | health below threshold | `component.degraded` |
| component | running | fail | failed | instance lost | `component.failed` |
| component | running | quarantine | quarantined | operator isolation | `component.quarantined` |
| component | running | reschedule | starting | moved off lost host | `component.rescheduled` |
| component | running | stop | stopping | links revoked | `component.stopping` |
| component | staged | quarantine | quarantined | operator isolation | `component.quarantined` |
| component | staged | start | starting | placement decided | `component.starting` |
| component | starting | fail | failed | start failed | `component.failed` |
| component | starting | quarantine | quarantined | operator isolation | `component.quarantined` |
| component | starting | ready | running | instance serving | `component.running` |
| component | stopped | quarantine | quarantined | operator isolation | `component.quarantined` |
| component | stopped | stage | staged | artifact verified and pinned | `component.staged` |
| component | stopping | stopped | stopped | instance released | `component.stopped` |
| host | active | declare_lost | lost | failover triggered | `host.lost` |
| host | active | drain | draining | no new placements | `host.draining` |
| host | active | miss | suspect | heartbeat missed | `host.suspect` |
| host | active | quarantine | quarantined | operator isolation | `host.quarantined` |
| host | draining | declare_lost | lost | failover triggered | `host.lost` |
| host | draining | miss | suspect | heartbeat missed | `host.suspect` |
| host | draining | quarantine | quarantined | operator isolation | `host.quarantined` |
| host | draining | remove | removed | membership removed | `host.removed` |
| host | joining | admit | active | added to placement pool | `host.active` |
| host | joining | quarantine | quarantined | operator isolation | `host.quarantined` |
| host | lost | join | joining | re-enrolment | `host.joining` |
| host | lost | remove | removed | membership removed | `host.removed` |
| host | quarantined | release | draining | operator release | `host.released` |
| host | suspect | declare_lost | lost | failover triggered | `host.lost` |
| host | suspect | heartbeat | active | suspicion cleared | `host.active` |
| host | suspect | quarantine | quarantined | operator isolation | `host.quarantined` |
| host | unknown | join | joining | identity verified | `host.joining` |
| link | absent | grant | granted | capability bound | `link.granted` |
| link | expired | grant | granted | capability bound | `link.granted` |
| link | granted | expire | expired | grant lifetime elapsed | `link.expired` |
| link | granted | revoke | revoked | capability withdrawn | `link.revoked` |
| link | revoked | grant | granted | capability bound | `link.granted` |
