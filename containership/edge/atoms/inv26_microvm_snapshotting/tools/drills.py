"""Operational drills with machine-readable evidence (C038, C059, C080, C092, C095, C097 partial).

  rollback        activate a bad-but-valid config (restore budget regression), detect via the
                  alert rule, roll back to the previous revision, verify service restored; timed.
  emergency       emergency disable -> readiness false + all capture/restore refused -> enable.
  backup_restore  export metadata (checksummed), destroy the node's metadata dir, import into a
                  fresh dir, prove every snapshot restores and consumed grants stay consumed.
  key_rotation    rotate the KEK, rewrap every DEK, disable the old version, prove restores work.
  alerts          drive four traffic classes (ordinary, attack, dependency outage, defect) and
                  show the alert rules in ops/alerts.json separate them.

``python -m inv26_microvm_snapshotting.tools.drills --out evidence/DRILLS.json``
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def drill_rollback() -> dict:
    from ..tests.harness import Rig
    r = Rig()
    snap = r.capture()
    t0 = time.perf_counter()
    rev0, doc = r.cfgstore.active()
    bad = copy.deepcopy(doc)
    bad["admission"]["max_inflight"] = 1
    bad["admission"]["per_tenant"] = 1
    bad["admission"]["max_queue"] = 0
    bad["admission"]["tenant_burst"] = 1.0
    bad["admission"]["tenant_rate_per_s"] = 0.01
    r.cfgstore.activate(bad, author="release-bot", source="drill:bad-canary", approval_ref="DRILL-1",
                        expect_revision=rev0)
    r.svc.reload_config()
    codes = [r.restore(snap, vm=f"d{i}")[1].get("code", "OK") for i in range(5)]
    alert = sum(c == "SNAP_OVERLOADED" for c in codes) / len(codes) > 0.5  # INV26-OverloadRatio
    detected_ms = (time.perf_counter() - t0) * 1000
    if alert:
        r.cfgstore.rollback(to_revision=rev0, author="oncall", reason="drill: overload ratio alert")
        r.svc.reload_config()
    after = r.restore(snap, vm="d-after")[0]
    hist = r.cfgstore.history()
    return {"drill": "rollback", "alert_fired": alert, "codes_during_bad_config": codes,
            "post_rollback_status": after, "revisions": [h["revision"] for h in hist],
            "rollback_source": hist[-1]["source"], "time_to_recover_ms": round((time.perf_counter() - t0) * 1000, 2),
            "detect_ms": round(detected_ms, 2), "audit_chain_records": r.audit.verify(),
            "result": "PASS" if alert and after == 200 and hist[-1]["previous_revision"] == rev0 + 1 else "FAIL"}


def drill_emergency() -> dict:
    from ..tests.harness import Rig
    r = Rig()
    snap = r.capture()
    adm = r.admin_token()
    r.svc.handle("disable", adm, {"reason": "drill"})
    h = r.svc.health()
    refused = [r.restore(snap, vm="e1")[1].get("code"), r.svc.handle("capture", r.token(), r.capture_req("e2"))[1]["code"]]
    r.svc.handle("enable", adm, {})
    ok = r.restore(snap, vm="e3")[0]
    return {"drill": "emergency_disable", "ready_while_disabled": h["ready"], "refusals": refused,
            "post_enable_status": ok,
            "result": "PASS" if not h["ready"] and refused == ["SNAP_DISABLED", "SNAP_DISABLED"] and ok == 200 else "FAIL"}


def drill_backup_restore() -> dict:
    from ..metastore import MetaStore
    from ..tests.harness import Rig
    r = Rig()
    snaps = [r.capture(f"b{i}") for i in range(3)]
    g_used = r.grant(snaps[0], vm="x1")
    r.restore(snaps[0], grant=g_used, vm="x1")
    backup = r.meta.export()
    shutil.rmtree(r.root / "meta")  # node metadata lost
    r.meta = MetaStore.import_backup(r.root / "meta2", backup)
    r.cfgstore.meta = r.meta
    r.svc = r.build()
    statuses = [r.restore(s, vm=f"y{i}")[0] for i, s in enumerate(snaps)]
    replay = r.svc.handle("restore", r.token(), r.restore_req(snaps[0], g_used, vm="x1"))[1].get("code")
    tampered = dict(backup, seq=backup["seq"] + 1)
    try:
        MetaStore.import_backup(r.root / "meta3", tampered)
        tamper_refused = False
    except Exception:
        tamper_refused = True
    return {"drill": "backup_restore", "records": len(backup["records"]), "restores_after_import": statuses,
            "consumed_grant_after_import": replay, "tampered_backup_refused": tamper_refused,
            "result": "PASS" if statuses == [200] * 3 and replay == "SNAP_GRANT_REPLAYED" and tamper_refused else "FAIL"}


def drill_key_rotation() -> dict:
    from ..tests.harness import Rig
    r = Rig()
    snaps = [r.capture(f"k{i}") for i in range(3)]
    new_v = r.kms.rotate("inv26-kek")
    rep = r.svc.rewrap_all()
    r.kms.set_state("inv26-kek", 1, "disabled")
    statuses = []
    for i, s in enumerate(snaps):
        cur = r.meta.get(f"snap/{s['snapshot_id']}")[1]
        s = dict(s, manifest_sha256=cur["manifest_sha256"])  # control plane re-reads the manifest digest
        statuses.append(r.restore(s, vm=f"r{i}")[0])
    stale = r.restore(snaps[0], vm="r-stale")[1].get("code")  # grant over the pre-rotation digest
    return {"drill": "key_rotation", "new_version": new_v, "rewrapped": rep["rewrapped"],
            "restores_with_old_version_disabled": statuses, "grant_for_pre_rotation_manifest": stale,
            "result": "PASS" if statuses == [200] * 3 and stale == "SNAP_GRANT_INVALID" else "FAIL"}


def evaluate_alerts(rules: list[dict], m) -> list[str]:
    fired = []
    for rule in rules:
        total = m.total("inv26_requests_total") or 1
        codes = {}
        for row in m.snapshot()["counters"]:
            if row["name"] == "inv26_requests_total":
                codes[row["labels"].get("code")] = codes.get(row["labels"].get("code"), 0) + row["value"]
        share = sum(codes.get(c, 0) for c in rule["codes"]) / total
        if share >= rule["threshold_ratio"] and sum(codes.get(c, 0) for c in rule["codes"]) >= rule["min_events"]:
            fired.append(rule["alert"])
    return sorted(fired)


def drill_alerts() -> dict:
    from ..tests.harness import Rig
    rules = json.loads((PKG / "ops" / "alerts.json").read_text())["rules"]
    out = {}

    def fresh():
        r = Rig()
        return r, r.capture()

    r, s = fresh()  # ordinary load
    for i in range(10):
        r.restore(s, vm=f"o{i}")
    out["ordinary"] = evaluate_alerts(rules, r.metrics)
    r, s = fresh()  # attack: cross-tenant probing + replay
    for i in range(10):
        g = r.grant(s, tenant="t9")
        r.svc.handle("restore", r.token(tenant="t9"), r.restore_req(s, g, tenant="t9", vm=f"a{i}"))
    out["attack"] = evaluate_alerts(rules, r.metrics)
    r, s = fresh()  # dependency outage
    r.kms.available = False
    for i in range(10):
        r.restore(s, vm=f"k{i}")
    out["dependency_outage"] = evaluate_alerts(rules, r.metrics)
    r, s = fresh()  # software defect
    r.svc._restore = lambda *a, **k: 1 / 0
    for i in range(10):
        r.restore(s, vm=f"d{i}")
    out["defect"] = evaluate_alerts(rules, r.metrics)
    distinct = len({tuple(v) for v in out.values()}) == 4 and out["ordinary"] == []
    return {"drill": "alerts", "fired_by_class": out, "classes_distinguished": distinct,
            "result": "PASS" if distinct else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    drills = [drill_rollback(), drill_emergency(), drill_backup_restore(), drill_key_rotation(), drill_alerts()]
    res = {"schema": "PK_SNAPSHOT_DRILLS/1", "drills": drills,
           "not_performed": ["human escalation/paging drill (C009, C097): no on-call route exists",
                             "canary on a real fleet (C092): no fleet",
                             "rollback between two real releases (C038): single release exists"],
           "result": "PASS" if all(d["result"] == "PASS" for d in drills) else "FAIL"}
    txt = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt + "\n")
    print(json.dumps({"result": res["result"], **{d["drill"]: d["result"] for d in drills}}))
    if res["result"] != "PASS":
        print(txt, file=sys.stderr)
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
