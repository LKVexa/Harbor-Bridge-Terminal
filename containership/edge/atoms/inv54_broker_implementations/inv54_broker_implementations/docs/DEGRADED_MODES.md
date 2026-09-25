# Degraded-operation modes  (component 56)

| Mode | Trigger | Allowed | Forbidden | Exit |
|---|---|---|---|---|
| `dependency:<name>` | registered dependency probe false | publish/consume; results carry `Outcome.DEGRADED` + mode | nothing extra | probe true → READY |
| `drop_oldest` | backlog full with that policy | publish (oldest dropped, counted) | silent loss | backlog drains |
| quarantined | operator / incident | reads | writes | operator release |
| security outage | key/identity service down | nothing needing that service | **any** unauthenticated operation (fail closed) | service restored |
