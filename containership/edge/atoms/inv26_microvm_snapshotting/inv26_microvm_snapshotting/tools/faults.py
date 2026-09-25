"""Fault-injection matrix (C051, C053, C057, C060, C089 partial).

Each scenario injects one fault (or a combination), then checks invariants:

  I1  no guest is Running without an acknowledged reseed
  I2  no snapshot is AVAILABLE unless its blob decrypts
  I3  a grant never commits more than one READY restore
  I4  after restart + reconcile there are no transient records and no orphan blobs
  I5  every refusal is a catalogued code (never SNAP_INTERNAL)

Crash-at-every-step: capture and restore are re-run with the metastore
raising after its k-th durable write (k = 1..N), a *new* service instance is
built over the same directories (process restart), ``reconcile()`` runs, and
I1-I4 are checked, then a fresh capture/restore must succeed.

``python -m inv26_microvm_snapshotting.tools.faults --out evidence/FAULTS.json``
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .. import crypto
from ..metastore import MetaStore


def invariants(r) -> list[str]:
    bad = []
    for vm, v in r.hv.vms.items():
        if v["state"] == "Running" and v.get("restored") and v["rng"] is None:
            bad.append(f"I1 guest {vm} running without reseed")
    for key, (gen, v) in r.meta.scan("snap/").items():
        if v["state"] == "AVAILABLE":
            try:
                blob = r.blobs.get(v["tenant"], v["snapshot_id"], v["generation"])
                crypto.open_envelope(blob, env=v["manifest"]["envelope"], ctx=r.svc._ctx(v), kms=r.kms)
            except Exception as exc:
                bad.append(f"I2 {v['snapshot_id']} AVAILABLE but unreadable ({type(exc).__name__})")
    return bad


def post_restart(r) -> list[str]:
    svc = r.build()
    rep = svc.reconcile()
    r.svc = svc
    bad = invariants(r)
    for key, (gen, v) in r.meta.scan("snap/").items():
        if v["state"] in ("CAPTURING", "CAPTURED", "VERIFYING", "DELETING"):
            bad.append(f"I4 transient snapshot {key} {v['state']}")
    for key, (gen, v) in r.meta.scan("grant/").items():
        if v["state"] in ("PENDING", "RESTORING", "RESEEDING"):
            bad.append(f"I4 transient grant {key}")
    live = {f"{v['snapshot_id']}.g{v['generation']}.blob" for _, (_, v) in r.meta.scan("snap/").items()
            if v["state"] in ("AVAILABLE", "QUARANTINED")}
    for name in r.blobs.list("t1"):
        if name not in live:
            bad.append(f"I4 orphan blob {name}")
    return bad


class CrashingMeta(MetaStore):
    def __init__(self, *a, crash_at: int = 0, **kw):
        super().__init__(*a, **kw)
        self.writes, self.crash_at = 0, crash_at

    def transact(self, *a, **kw):
        self.writes += 1
        if self.crash_at and self.writes == self.crash_at:
            raise SystemExit(f"injected crash at durable write {self.writes}")  # BaseException, like a kill
        return super().transact(*a, **kw)


def crash_matrix() -> list[dict]:
    from ..tests.harness import Rig
    out = []
    for op in ("capture", "restore"):
        for k in range(1, 12):
            r = Rig()
            snap = r.capture("base") if op == "restore" else None
            r.meta = CrashingMeta(r.root / "meta", clock=r.clock)
            r.cfgstore.meta = r.meta
            r.svc = r.build()
            r.meta.writes, r.meta.crash_at = 0, k
            crashed = False
            try:
                if op == "capture":
                    r.boot("k-src")
                    r.svc.handle("capture", r.token(), r.capture_req("c1", vm="k-src"))
                else:
                    g = r.grant(snap, vm="k-dst")
                    r.svc.handle("restore", r.token(), r.restore_req(snap, g, vm="k-dst"))
            except SystemExit:
                crashed = True
                r.hv.destroy("k-dst")  # a killed restore process takes its VMM child with it (jailer semantics)
            if not crashed:
                out.append({"op": op, "crash_at_write": k, "result": "no-crash (operation used fewer writes)"})
                break
            r.meta = MetaStore(r.root / "meta", clock=r.clock)
            r.cfgstore.meta = r.meta
            bad = post_restart(r)
            # service still works after recovery
            r.boot("k-src2")
            st, body = r.svc.handle("capture", r.token(), r.capture_req("after", vm="k-src2"))
            if st != 200:
                bad.append(f"post-recovery capture failed {body.get('code')}")
            else:
                st, body = r.restore(body, vm="k-after")
                if st != 200:
                    bad.append(f"post-recovery restore failed {body.get('code')}")
            out.append({"op": op, "crash_at_write": k, "violations": bad, "result": "PASS" if not bad else "FAIL"})
    return out


def dependency_matrix() -> list[dict]:
    from ..tests.harness import Rig
    scenarios = {
        "kms_down": lambda r: setattr(r.kms, "available", False),
        "storage_down": lambda r: setattr(r.blobs, "root", r.root / "nonexistent-ro") or
        (r.root / "blobs").chmod(0o000),
        "hypervisor_down": lambda r: setattr(r.hv, "available", False),
        "entropy_down": lambda r: setattr(r.entropy, "fail", True),
        "hypervisor_flaky_once": lambda r: setattr(r.hv, "fail_next", "resume"),
        "audit_sink_down": lambda r: setattr(r.audit, "_open", lambda p: (_ for _ in ()).throw(OSError("down"))),
        "kms_and_entropy_down": lambda r: (setattr(r.kms, "available", False), setattr(r.entropy, "fail", True)),
        "key_disabled": lambda r: r.kms.set_state("inv26-kek", 1, "disabled"),
    }
    out = []
    for name, inject in scenarios.items():
        r = Rig()
        snap = r.capture()
        inject(r)
        g = r.grant(snap)
        t0 = time.perf_counter()
        st, body = r.svc.handle("restore", r.token(), r.restore_req(snap, g, vm="vm-2"))
        ms = (time.perf_counter() - t0) * 1000
        (r.root / "blobs").chmod(0o700)
        # heal the dependencies before checking at-rest invariants (the checker needs KMS/storage)
        r.kms.available, r.hv.available = True, True
        r.blobs.root = r.root / "blobs"
        if name == "key_disabled":
            r.kms.set_state("inv26-kek", 1, "enabled")
        bad = invariants(r)
        if st != 200 and body.get("code") == "SNAP_INTERNAL":
            bad.append("I5 SNAP_INTERNAL")
        if st == 200 and name not in ("hypervisor_flaky_once", "audit_sink_down"):
            bad.append("restore succeeded despite a fail-closed dependency outage")
        # second use of the same grant must never commit a second restore (I3)
        st2, body2 = r.svc.handle("restore", r.token(), r.restore_req(snap, g, vm="vm-2"))
        if st == 200 and st2 == 200 and not body2.get("replayed"):
            bad.append("I3 grant committed twice")
        out.append({"scenario": name, "status": st, "code": body.get("code", "OK"), "ms": round(ms, 2),
                    "health_ready": r.svc.health()["ready"], "violations": bad,
                    "result": "PASS" if not bad else "FAIL"})
    return out


def breaker_and_retry() -> dict:
    from ..tests.harness import Rig
    r = Rig(cfg_over={"breaker": {"threshold": 3, "cooldown_ms": 100}, "retry": {"attempts": 1}})
    snap = r.capture()
    r.hv.available = False
    codes = [r.restore(snap, vm=f"b{i}")[1]["code"] for i in range(6)]
    r.hv.available = True
    time.sleep(0.12)
    st, _ = r.restore(snap, vm="b-ok")
    return {"codes_while_down": codes, "opened": "SNAP_CIRCUIT_OPEN" in codes,
            "recovered_after_cooldown": st == 200,
            "result": "PASS" if "SNAP_CIRCUIT_OPEN" in codes and st == 200 else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    t0 = time.time()
    res = {"schema": "PK_SNAPSHOT_FAULTS/1", "crash_matrix": crash_matrix(), "dependencies": dependency_matrix(),
           "breaker": breaker_and_retry()}
    rows = res["crash_matrix"] + res["dependencies"] + [res["breaker"]]
    res["result"] = "PASS" if all(r.get("result") in ("PASS",) or r.get("result", "").startswith("no-crash")
                                  for r in rows) else "FAIL"
    res["seconds"] = round(time.time() - t0, 2)
    txt = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt + "\n")
    print(json.dumps({"result": res["result"], "crash_cases": len(res["crash_matrix"]),
                      "dependency_cases": len(res["dependencies"]), "seconds": res["seconds"]}))
    if res["result"] != "PASS":
        print(txt, file=sys.stderr)
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
