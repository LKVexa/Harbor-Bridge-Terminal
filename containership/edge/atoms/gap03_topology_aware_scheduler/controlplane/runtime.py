"""Runtime wiring for health (MC-018) from the live control-plane objects.

``build_health`` turns the real coordination, stores, degraded policy, controls, config and adapters into
readiness checks + deep diagnostics, and publishes control / generation-lag gauges."""
from __future__ import annotations

from .. import __version__
from .health import Health


def build_health(*, coordinator, ledger, topology, audit, trust_ready, degraded, controls, config, inventory=None,
                 journal=None, metrics=None, clock=None) -> Health:
    def lease():
        return coordinator.is_leader(), "leader" if coordinator.is_leader() else "not_leader"

    def stores():
        bad = [s.KIND for s in (ledger, topology) if s.read_only or s.pending_migration]
        return not bad, ",".join(bad) or "writable"

    def audit_ok():
        return not audit._store.read_only, "writable" if not audit._store.read_only else "read_only"

    def identity():
        return trust_ready(), "trust store loaded"

    def commit_allowed():
        d = degraded.decide("commit")
        return d["allowed"], d.get("reason", "ok")

    def info():
        backlog = 0
        if journal is not None:
            backlog = sum(1 for t in journal.state["txns"].values() if t["state"] not in ("COMMITTED", "ABORTED"))
        ctl = controls.summary(privileged=False)
        lag = {}
        if inventory is not None:
            lag["gap02"] = max(0, topology.generation - inventory.snapshot_meta()["max_generation"])
        if metrics is not None:
            modes: dict = {}
            for c in ctl:
                modes[c["mode"]] = modes.get(c["mode"], 0) + 1
            for m, n in modes.items():
                metrics.set("gap03_active_controls", n, mode=m)
            for src, v in lag.items():
                metrics.set("gap03_generation_lag", v, source=src)
        return {"version": __version__, "schemas": ["PK_TOPOLOGY/1.1", "PK_LOCALITY_COST/1.0", "PK_FAIR_SHARE/1.0"],
                "config_generation": config.current.generation, "config_digest": config.current.digest,
                "topology_generation": topology.generation, "ledger_revision": ledger.state["revision"],
                "coordination": coordinator.status(), "degraded": degraded.health(), "controls": ctl,
                "pending_migrations": [s.KIND for s in (ledger, topology) if s.pending_migration],
                "reconciliation_backlog": backlog, "generation_lag": lag}

    return Health(checks={"lease": lease, "stores": stores, "audit": audit_ok, "identity": identity,
                          "commit_policy": commit_allowed}, info=info, metrics=metrics)
