# Lifecycle state machine  (C015 · components 06, 58)

States: `created → configured → starting → ready ⇄ degraded → draining → stopped`, plus `quarantined` (writes frozen, reads allowed) and `failed`. The legal-transition table is `lifecycle.TRANSITIONS`; any other transition raises `INV54-E0601`. Tests prove every state is reachable and illegal jumps are refused.

| State | Writes | Reads | Entered by |
|---|---|---|---|
| ready | yes | yes | start with healthy deps; recovery from degraded |
| degraded | yes (results flagged `degraded`) | yes | dependency probe failure (`BrokerService.reevaluate`) |
| draining | no | yes | operator drain / rollout |
| quarantined | no (`INV54-E0602`) | yes | incident response; per-tenant quarantine also available |
| stopped / failed | no | no | stop / unrecoverable fault |

Every transition emits a structured log, a metric and an audit event.
