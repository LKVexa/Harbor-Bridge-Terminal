"""Operational drills: rollout/rollback, emergency disable, backup/restore, alerts (MC-28, MC-34, MC-37, MC-38).

    python -m inv68_resource_packing.tools.drills [--out evidence/]

Writes:

* ``ROLLBACK_DRILL.json`` -- a candidate configuration that degrades efficiency
  is rolled out under ``ops/ROLLOUT_POLICY.json``; the controller must abort at
  the first stage whose signals breach a threshold and the configuration store
  must be back on the baseline digest, with the rollback audited.  A healthy
  candidate must promote through every stage.
* ``EMERGENCY_DISABLE.json`` -- freeze under load, verify refusal + state
  preservation + audit, unfreeze, verify recovery (runbook section 6).
* ``BACKUP_RESTORE.json`` -- export, destroy, restore, verify identical digest
  and identical packing decisions; tampered bundle refused (MC-37).
* ``ALERTS.json`` -- every rule in ``ops/alerts.json`` must fire on its own
  synthetic window and stay silent on a healthy window, and the healthy
  window must raise nothing (MC-28; C080).
"""
from __future__ import annotations

import argparse
import json
import random
import shutil
import tempfile
from pathlib import Path

from .common import PKG, write

from inv68_resource_packing.audit import AuditLog  # noqa: E402
from inv68_resource_packing.auth import Authorizer, mint  # noqa: E402
from inv68_resource_packing.config import ConfigStore, compose, defaults  # noqa: E402
from inv68_resource_packing.errors import PackError  # noqa: E402
from inv68_resource_packing.packing import lower_bound, pack_detailed  # noqa: E402
from inv68_resource_packing.rollout import RolloutController  # noqa: E402
from inv68_resource_packing.service import PackingService  # noqa: E402

KEY = {"k": b"d" * 32}


def _signals(cfg, seed: int) -> dict:
    """Synthetic canary signals derived from *real* packing under ``cfg``."""
    rng = random.Random(seed)
    ratios = []
    for _ in range(40):
        work = [{"name": f"w{i}", "cpu": rng.choice([.5, 1, 2, 4]), "mem": rng.choice([1, 2, 4, 8, 16])}
                for i in range(rng.randint(50, 300))]
        res = pack_detailed(work, 16, 64, cfg.headroom, cfg.cpu_overcommit)
        # efficiency is judged against the *baseline policy's* bound: that is what capacity planning bought
        ratios.append(len(res.hosts) / lower_bound(work, 16, 64, 0.1, 1.5, placeable_only=True))
    return {"requests": 1000, "error_rate": 0.001, "p99_ms": 8.0, "efficiency_ratio": sum(ratios) / len(ratios),
            "mem_overcommit_hosts": 0}


def rollback_drill(tmp: Path) -> dict:
    policy = json.loads((PKG / "ops" / "ROLLOUT_POLICY.json").read_text())
    audit = AuditLog(tmp / "audit.jsonl")
    store = ConfigStore(tmp / "cfg", audit=audit)
    base = defaults()
    store.activate(base, actor="bootstrap", epoch=1)
    baseline = _signals(base, 1)
    # healthy candidate: tighter queue only
    good = compose(base.document, ("candidate-good", {"config_version": "1.1.0", "limits": {"max_queue": 16}}))
    store.activate(good, actor="release", epoch=1, expected_digest=base.digest)
    ctl = RolloutController(policy, store=store, actor="rollout")
    while ctl.state == "in_progress":
        ctl.step(_signals(good, 2), baseline)
    healthy = {"state": ctl.state, "history": ctl.history, "active": store.active().digest == good.digest}
    # bad candidate: headroom 0.35 wastes hosts -> efficiency breach
    bad = compose(good.document, ("candidate-bad", {"config_version": "1.2.0", "headroom": 0.35}))
    store.activate(bad, actor="release", epoch=1, expected_digest=good.digest)
    ctl2 = RolloutController(policy, store=store, actor="rollout")
    import time as _t
    sig = _signals(bad, 3)
    t0 = _t.perf_counter()
    while ctl2.state == "in_progress":
        ctl2.step(sig, baseline)
    rollback_s = _t.perf_counter() - t0
    rolled_back_to_good = store.active().digest == good.digest
    ops = [r["operation"] for r in audit.records()]
    # safety: any memory overcommit aborts immediately regardless of other signals
    ctl3 = RolloutController(policy)
    ctl3.step(dict(_signals(good, 4), mem_overcommit_hosts=1), baseline)
    ctl4 = RolloutController(policy)
    ctl4.step(dict(_signals(good, 5), ready=False), baseline)
    ok = (healthy["state"] == "complete" and healthy["active"] and ctl2.state == "aborted" and rolled_back_to_good
          and "config.rollback" in ops and ctl3.state == "aborted" and ctl4.state == "aborted" and audit.verify() > 0)
    return {"schema": "PK_PACK_ROLLBACK_DRILL/1", "result": "PASS" if ok else "FAIL",
            "healthy_candidate": healthy, "bad_candidate": {"state": ctl2.state, "history": ctl2.history,
                                                            "rolled_back_to": good.digest[:12],
                                                            "rolled_back_ok": rolled_back_to_good},
            "overcommit_candidate": {"state": ctl3.state, "history": ctl3.history},
            "unready_candidate": {"state": ctl4.state, "history": ctl4.history},
            "audited_rollback": "config.rollback" in ops, "rollback_seconds_measured": round(rollback_s, 4), "rehearsal": "automated, synthetic signals from real packing"}


def emergency_disable(tmp: Path) -> dict:
    audit = AuditLog(tmp / "audit.jsonl")
    store = ConfigStore(tmp / "cfg", audit=audit)
    store.activate(defaults(), actor="bootstrap", epoch=1)
    svc = PackingService(store, Authorizer(KEY), audit)
    sch = lambda: mint(KEY["k"], kid="k", sub="sch", kind="workload-scheduler", tenants=["t"], caps=["pack:submit"])
    op = lambda: mint(KEY["k"], kid="k", sub="oncall", kind="operator", tenants=["*"], caps=["control:freeze"])
    body = {"tenant": "t", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": [{"name": "a", "cpu": 1, "mem": 1}]}
    before = svc.pack(dict(body), sch())["outcome"]
    svc.freeze(op(), "DRILL: emergency disable rehearsal")
    try:
        svc.pack(dict(body), sch())
        during = "OK"
    except PackError as e:
        during = e.code
    status = svc.status()["state"]
    digest_kept = store.active() is not None
    svc.unfreeze(op(), "DRILL complete")
    after = svc.pack(dict(body), sch())["outcome"]
    ops = [r["operation"] for r in audit.records()]
    ok = (before == "success" and during == "FROZEN" and status == "frozen" and digest_kept and after == "success"
          and {"control.freeze", "control.unfreeze"} <= set(ops))
    return {"schema": "PK_PACK_EMERGENCY_DISABLE/1", "result": "PASS" if ok else "FAIL", "before": before,
            "during": during, "status_during": status, "state_preserved": digest_kept, "after": after,
            "audited": {"control.freeze", "control.unfreeze"} <= set(ops)}


def backup_restore(tmp: Path) -> dict:
    audit = AuditLog(tmp / "a" / "audit.jsonl")
    store = ConfigStore(tmp / "a" / "cfg", audit=audit)
    store.activate(defaults(), actor="bootstrap", epoch=1)
    store.activate(compose(defaults().document, ("site", {"headroom": 0.15, "config_version": "1.0.1"})),
                   actor="release", epoch=1)
    bundle_path = tmp / "backup.json"
    bundle_path.write_text(json.dumps(store.export()))
    want = store.active().digest
    shutil.rmtree(tmp / "a" / "cfg")  # disaster
    import time as _t
    t0 = _t.perf_counter()
    restored = ConfigStore.restore(tmp / "b" / "cfg", json.loads(bundle_path.read_text()))
    rto_s = _t.perf_counter() - t0
    same = restored.active().digest == want
    history_same = len(restored.history()) == 2
    work = [{"name": f"w{i}", "cpu": 1 + i % 3, "mem": 2 + i % 7} for i in range(200)]
    cfg = restored.active()
    decisions = pack_detailed(work, 16, 64, cfg.headroom, cfg.cpu_overcommit).to_dict()
    decisions2 = pack_detailed(work, 16, 64, 0.15, 1.5).to_dict()
    tampered = json.loads(bundle_path.read_text())
    k = next(iter(tampered["snapshots"]))
    tampered["snapshots"][k]["cpu_overcommit"] = 4.0
    try:
        ConfigStore.restore(tmp / "c" / "cfg", tampered)
        tamper = "accepted"
    except PackError as e:
        tamper = e.code
    ok = same and history_same and decisions == decisions2 and tamper == "CONFIG_INVALID" and rto_s < 60
    return {"schema": "PK_PACK_BACKUP_RESTORE/1", "result": "PASS" if ok else "FAIL",
            "authoritative_state": ["cfg/snapshots/*.json", "cfg/journal.jsonl", "cfg/ACTIVE", "audit ledger + anchor"],
            "reconstructible_state": ["placements (recomputed from request + config digest + capacity snapshot)",
                                      "idempotency cache", "metrics", "admission counters", "freeze flag (re-assert from audit)"],
            "rpo_target": "last committed activation", "rpo_measured": "0 activations lost (journal length preserved)",
            "rto_target_s": 60, "rto_measured_s": round(rto_s, 4), "rto_met": rto_s < 60,
            "restored_digest_matches": same, "journal_preserved": history_same,
            "identical_decisions_after_restore": decisions == decisions2, "tampered_bundle": tamper}


def alerts() -> dict:
    rules = json.loads((PKG / "ops" / "alerts.json").read_text())["rules"]
    healthy = {"code_rate": {"OK": 0.999}, "latency_p99_ms": 8, "gauges": {"inv68_mem_overcommit_hosts": 0,
               "inv68_efficiency_ratio": 1.03}, "counters": {"inv68_audit_dropped_total": 0}}

    def fires(rule, window) -> bool:
        w = rule["when"]
        if "code_rate" in w:
            return any(window["code_rate"].get(c, 0.0) > thr for c, thr in w["code_rate"].items())
        if "latency_p99_ms" in w:
            return window["latency_p99_ms"] > w["latency_p99_ms"]
        if "gauge" in w:
            return window["gauges"].get(w["gauge"], 0) > rule["threshold"]
        if "counter" in w:
            return window["counters"].get(w["counter"], 0) > rule["threshold"]
        return False

    def trigger(rule) -> dict:
        w = json.loads(json.dumps(healthy))
        when = rule["when"]
        if "code_rate" in when:
            c, thr = next(iter(when["code_rate"].items()))
            w["code_rate"][c] = thr + 0.01
        elif "latency_p99_ms" in when:
            w["latency_p99_ms"] = when["latency_p99_ms"] * 2
        elif "gauge" in when:
            w["gauges"][when["gauge"]] = rule["threshold"] + 1
        elif "counter" in when:
            w["counters"][when["counter"]] = rule["threshold"] + 1
        return w
    rows = []
    for r in rules:
        own = fires(r, trigger(r))
        quiet = not fires(r, healthy)
        others = sorted({o["class"] for o in rules if o is not r and fires(o, trigger(r))})
        rows.append({"id": r["id"], "class": r["class"], "fires_on_own_window": own, "silent_when_healthy": quiet,
                     "co_firing_classes": others})
    classes = {r["class"] for r in rules}
    required = {"load", "degradation", "policy_rejection", "dependency_failure", "attack", "software_defect"}
    ok = all(r["fires_on_own_window"] and r["silent_when_healthy"] for r in rows) and required <= classes
    return {"schema": "PK_PACK_ALERTS_CHECK/1", "result": "PASS" if ok else "FAIL", "rules": rows,
            "required_classes_present": sorted(required & classes), "missing_classes": sorted(required - classes)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    results = {}
    for name, fn in (("ROLLBACK_DRILL", rollback_drill), ("EMERGENCY_DISABLE", emergency_disable),
                     ("BACKUP_RESTORE", backup_restore)):
        with tempfile.TemporaryDirectory() as tmp:
            try:
                doc = fn(Path(tmp))
            except Exception as exc:  # noqa: BLE001
                doc = {"schema": f"PK_PACK_{name}/1", "result": "FAIL", "exception": f"{type(exc).__name__}: {exc}"}
        write(out / f"{name}.json", doc)
        results[name] = doc["result"]
    doc = alerts()
    write(out / "ALERTS.json", doc)
    results["ALERTS"] = doc["result"]
    print(results)
    return 0 if all(v == "PASS" for v in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
