"""Shared end-to-end harness (component 29): builds a full GAP-09 -> GAP-10 ->
scheduler/elasticity stack with deterministic clock and keys."""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))

from gap10_power_thermal_aware_scheduling.production.clock import ManualClock, TrustedClock  # noqa: E402
from gap10_power_thermal_aware_scheduling.production.controller import Gap10Controller  # noqa: E402
from gap10_power_thermal_aware_scheduling.production.coordination import LeaseManager  # noqa: E402
from gap10_power_thermal_aware_scheduling.production.enforcement import (  # noqa: E402
    CeilingView, ElasticityEnforcementAdapter, ReferenceElasticity, ReferenceScheduler,
    SchedulerEnforcementAdapter)
from gap10_power_thermal_aware_scheduling.production.keys import KeyRing  # noqa: E402
from gap10_power_thermal_aware_scheduling.production.observability import AuditSink  # noqa: E402
from gap10_power_thermal_aware_scheduling.production.policy_service import PolicyService, policy_to_dict, sign_bundle  # noqa: E402
from gap10_power_thermal_aware_scheduling.production.store import FileStateStore  # noqa: E402
from gap10_power_thermal_aware_scheduling.model import PowerThermalPolicy  # noqa: E402

SECRET = lambda tag: (tag * 64).encode()[:48]  # noqa: E731 - deterministic test secrets only
SCOPE = "dub/prod"


def keyring() -> KeyRing:
    kr = KeyRing()
    kr.add("gap09-k1", "gap09-reporter", SECRET("a"), {"telemetry.publish"}, scopes=("edge-*",))
    kr.add("author-k1", "alice", SECRET("b"), {"policy.author"}, scopes=("dub/*",))
    kr.add("approver-k1", "bob", SECRET("c"), {"policy.approve-relax"}, scopes=("dub/*",))
    kr.add("self-approver", "alice", SECRET("d"), {"policy.approve-relax"}, scopes=("dub/*",))
    kr.add("ops-k1", "oncall", SECRET("e"), {"control.operate", "control.release"})
    kr.add("rogue-k1", "rogue", SECRET("f"), {"telemetry.publish"}, scopes=("other-*",))
    return kr


class Stack:
    def __init__(self, tmp: str | None = None, controller_id="ctl-a", nodes=("edge-001", "edge-002"), capacity=100):
        self.tmp = tmp or tempfile.mkdtemp(prefix="gap10-")
        self.mc = ManualClock(1000.0)
        self.clock = TrustedClock(wall=self.mc.wall, mono=self.mc.mono)
        self.clock.sync()
        self.kr = keyring()
        self.audit = AuditSink(os.path.join(self.tmp, "audit.jsonl"))
        self.store = FileStateStore(os.path.join(self.tmp, "state"))
        self.leases = LeaseManager(ttl_s=30.0)
        self.policies = PolicyService(self.kr, self.audit)
        b = sign_bundle(self.kr, SCOPE, policy_to_dict(PowerThermalPolicy()), None, "author-k1")
        rev = self.policies.submit(b, now=self.clock.now())
        self.policies.activate(SCOPE, rev.revision_id, actor="alice", now=self.clock.now())
        from gap10_power_thermal_aware_scheduling.production.calibration import CalibrationInventory, HardwareProfile
        self.calibration = CalibrationInventory()
        self.calibration.register(HardwareProfile("edge-x86-v1", 105.0, 115.0, 200.0, 250.0, "li-ion", 500.0, "fan",
                                                  90.0, ("cpu",), "cal-2026-09", "hw-lab"))
        for n in nodes:
            self.calibration.assign(n, "edge-x86-v1")
        self.ctl = self.controller(controller_id)
        self.ctl.acquire()
        for n in nodes:
            self.ctl.register(n, scope=SCOPE, site="dub")
        self.view = CeilingView()
        self.sched = ReferenceScheduler()
        self.capacity = {n: capacity for n in nodes}
        self.adapter = SchedulerEnforcementAdapter(self.sched, self.view, self.capacity, metrics=self.ctl.metrics)
        self.elastic = ReferenceElasticity()
        self.elastic_adapter = ElasticityEnforcementAdapter(self.elastic, self.view, {"pool": list(nodes)}, self.capacity)
        self.seq = {}

    def controller(self, cid):
        return Gap10Controller(cid, "shard-0", self.kr, self.store, self.leases, self.policies,
                               clock=self.clock, audit=self.audit, calibration=self.calibration)

    def envelope(self, node="edge-001", temp=40.0, *, key="gap09-k1", seq=None, observed_at=None, power=None,
                 budget=None, battery=None, attestation="hardware", sensors=None, tamper=False):
        s = self.seq.get(node, 0) + 1 if seq is None else seq
        self.seq[node] = max(self.seq.get(node, 0), s)
        payload = {"node": node, "site": "dub", "seq": s,
                   "observed_at": self.clock.now() if observed_at is None else observed_at,
                   "sensors": sensors if sensors is not None else [{"sensor_id": "cpu0", "kind": "cpu", "temperature_c": temp}]}
        if power is not None:
            payload["power_draw_watts"] = power
        if budget is not None:
            payload["power_budget_watts"] = budget
        if battery is not None:
            payload["battery_fraction"] = battery
        sig = self._raw_sign(key, node, payload)
        if tamper:
            payload = dict(payload, sensors=[{"sensor_id": "cpu0", "kind": "cpu", "temperature_c": 20.0}])
        return {"schema": "PK_TELEMETRY_ENVELOPE/1", "key_id": key, "signature": sig, "attestation": attestation,
                "correlation_id": f"c-{node}-{s}", "payload": payload}

    def _raw_sign(self, key, node, payload):
        """Sign like a (possibly misbehaving) reporter holding ``key``: bypasses the
        keyring's own scope guard so the *verifier* is what gets tested."""
        import hashlib, hmac
        from gap10_power_thermal_aware_scheduling.production.keys import canonical
        entry = self.kr._keys[key]
        return hmac.new(entry.secret, canonical(["telemetry.publish", node, payload]), hashlib.sha256).hexdigest()

    def send(self, node="edge-001", temp=40.0, publish=True, **kw):
        d = self.ctl.ingest(self.envelope(node, temp, **kw))
        if publish:
            self.view.publish(d)
            self.adapter.apply(node, self.clock.now())
        return d
