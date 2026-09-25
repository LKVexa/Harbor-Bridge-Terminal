"""M10 - authoritative lifecycle state machines (component, host, link).

Transition tables are data: (state, event) -> (next_state, side_effect, event_name).
Anything not in the table is an ILLEGAL_TRANSITION. Repeated requests that land
on the state they would produce are idempotent no-ops (M10 idempotency rule).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import FabricError

COMPONENT_STATES = ("absent", "staged", "starting", "running", "degraded", "stopping",
                    "stopped", "failed", "quarantined")
HOST_STATES = ("unknown", "joining", "active", "draining", "suspect", "lost", "quarantined", "removed")
LINK_STATES = ("absent", "granted", "revoked", "expired")

COMPONENT_TABLE = {
    ("absent", "stage"): ("staged", "artifact verified and pinned", "component.staged"),
    ("stopped", "stage"): ("staged", "artifact verified and pinned", "component.staged"),
    ("failed", "stage"): ("staged", "artifact verified and pinned", "component.staged"),
    ("staged", "start"): ("starting", "placement decided", "component.starting"),
    ("starting", "ready"): ("running", "instance serving", "component.running"),
    ("starting", "fail"): ("failed", "start failed", "component.failed"),
    ("running", "degrade"): ("degraded", "health below threshold", "component.degraded"),
    ("degraded", "recover"): ("running", "health restored", "component.running"),
    ("running", "stop"): ("stopping", "links revoked", "component.stopping"),
    ("degraded", "stop"): ("stopping", "links revoked", "component.stopping"),
    ("stopping", "stopped"): ("stopped", "instance released", "component.stopped"),
    ("running", "fail"): ("failed", "instance lost", "component.failed"),
    ("degraded", "fail"): ("failed", "instance lost", "component.failed"),
    ("running", "reschedule"): ("starting", "moved off lost host", "component.rescheduled"),
    ("degraded", "reschedule"): ("starting", "moved off lost host", "component.rescheduled"),
    ("failed", "reschedule"): ("starting", "moved off lost host", "component.rescheduled"),
    **{(s, "quarantine"): ("quarantined", "operator isolation", "component.quarantined")
       for s in ("staged", "starting", "running", "degraded", "failed", "stopped")},
    ("quarantined", "release"): ("stopped", "operator release", "component.released"),
}
HOST_TABLE = {
    ("unknown", "join"): ("joining", "identity verified", "host.joining"),
    ("joining", "admit"): ("active", "added to placement pool", "host.active"),
    ("active", "drain"): ("draining", "no new placements", "host.draining"),
    ("active", "miss"): ("suspect", "heartbeat missed", "host.suspect"),
    ("draining", "miss"): ("suspect", "heartbeat missed", "host.suspect"),
    ("suspect", "heartbeat"): ("active", "suspicion cleared", "host.active"),
    ("suspect", "declare_lost"): ("lost", "failover triggered", "host.lost"),
    ("active", "declare_lost"): ("lost", "failover triggered", "host.lost"),
    ("draining", "declare_lost"): ("lost", "failover triggered", "host.lost"),
    ("draining", "remove"): ("removed", "membership removed", "host.removed"),
    ("lost", "remove"): ("removed", "membership removed", "host.removed"),
    ("lost", "join"): ("joining", "re-enrolment", "host.joining"),
    **{(s, "quarantine"): ("quarantined", "operator isolation", "host.quarantined")
       for s in ("joining", "active", "draining", "suspect")},
    ("quarantined", "release"): ("draining", "operator release", "host.released"),
}
LINK_TABLE = {
    ("absent", "grant"): ("granted", "capability bound", "link.granted"),
    ("revoked", "grant"): ("granted", "capability bound", "link.granted"),
    ("expired", "grant"): ("granted", "capability bound", "link.granted"),
    ("granted", "revoke"): ("revoked", "capability withdrawn", "link.revoked"),
    ("granted", "expire"): ("expired", "grant lifetime elapsed", "link.expired"),
}
TERMINAL = {"removed"}


@dataclass
class StateMachine:
    name: str
    table: dict
    states: tuple
    state: str
    history: list = field(default_factory=list)

    def fire(self, event: str) -> tuple[str, str]:
        key = (self.state, event)
        if key not in self.table:
            # idempotent repeat: event already produced current state
            for (src, ev), (dst, _, _) in self.table.items():
                if ev == event and dst == self.state and self.state not in TERMINAL:
                    return self.state, "noop"
            raise FabricError("ILLEGAL_TRANSITION", f"{self.name}: {event!r} not allowed from {self.state!r}",
                              detail={"state": self.state, "event": event})
        nxt, _effect, emitted = self.table[key]
        self.history.append((self.state, event, nxt))
        self.state = nxt
        return nxt, emitted

    def allowed(self) -> list[str]:
        return sorted({ev for (src, ev) in self.table if src == self.state})


def component_machine(name: str, state: str = "absent") -> StateMachine:
    return StateMachine(name, COMPONENT_TABLE, COMPONENT_STATES, state)


def host_machine(name: str, state: str = "unknown") -> StateMachine:
    return StateMachine(name, HOST_TABLE, HOST_STATES, state)


def link_machine(name: str, state: str = "absent") -> StateMachine:
    return StateMachine(name, LINK_TABLE, LINK_STATES, state)


def validate_tables() -> list[str]:
    """Static checks: every state used is declared and every declared state is reachable."""
    problems = []
    for label, table, states, start in (("component", COMPONENT_TABLE, COMPONENT_STATES, "absent"),
                                         ("host", HOST_TABLE, HOST_STATES, "unknown"),
                                         ("link", LINK_TABLE, LINK_STATES, "absent")):
        for (s, _), (d, _, _) in table.items():
            for x in (s, d):
                if x not in states:
                    problems.append(f"{label}: undeclared state {x}")
        reach, frontier = {start}, [start]
        while frontier:
            cur = frontier.pop()
            for (s, _), (d, _, _) in table.items():
                if s == cur and d not in reach:
                    reach.add(d)
                    frontier.append(d)
        for s in states:
            if s not in reach:
                problems.append(f"{label}: unreachable state {s}")
    return problems


def transition_table_markdown() -> str:
    rows = ["| machine | from | event | to | side effect | emitted event |", "|---|---|---|---|---|---|"]
    for label, table in (("component", COMPONENT_TABLE), ("host", HOST_TABLE), ("link", LINK_TABLE)):
        for (s, e), (d, eff, ev) in sorted(table.items()):
            rows.append(f"| {label} | {s} | {e} | {d} | {eff} | `{ev}` |")
    return "\n".join(rows)
