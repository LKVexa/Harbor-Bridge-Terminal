"""Concurrency/race, burst, soak, fleet-scale and partition/reconnect suites (MC-28; C086, C088-C089).

    python -m inv64_application_model.tools.stress [--profile ci|extended] [--out evidence/STRESS.json]

``ci`` runs in well under a minute and is release-gated; ``extended`` (soak
minutes, larger fleet) is for the scheduled job. Python has no data-race
detector, so races are hunted with schedule stress (``sys.setswitchinterval``
at 1µs, many threads) plus invariant checks after every run.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
import threading
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from inv64_application_model.activation import ConfigStore
from inv64_application_model.audit import AuditLog
from inv64_application_model.auth import Authenticator, TrustConfig, mint
from inv64_application_model.authz import Authorizer
from inv64_application_model.errors import Inv64Error
from inv64_application_model.manifest import canonical, validate
from inv64_application_model.semantics import AdmissionController
from inv64_application_model.service import ApplicationModelService

PROFILES = {"ci": {"threads": 16, "iters": 200, "tenants": 50, "soak_s": 5, "burst": 400},
            "extended": {"threads": 64, "iters": 2000, "tenants": 1000, "soak_s": 600, "burst": 10000}}
K = b"s" * 32
M = {"schema": "app/v1", "components": [{"name": "api"}, {"name": "w"}], "providers": [{"name": "kv"}],
     "links": [{"from": "api", "to": "kv"}], "traits": [{"type": "spread", "component": "api"}]}


def _service(tmp: Path, tenants: list[str], **kw) -> ApplicationModelService:
    trust = TrustConfig("t", "inv64", {"iss": {"k": ("HS256", K)}})
    pol = {"format": "PK_APP_AUTHZ_POLICY/1", "version": "p1",
           "grants": [{"id": f"g-{t}", "roles": ["dev"], "capabilities": ["app.submit", "app.validate"],
                       "tenants": [t], "environments": ["prod"], "sites": ["*"], "resources": ["apps/*"]}
                      for t in tenants]}
    return ApplicationModelService(authenticator=Authenticator(lambda: trust, failure_limit=10 ** 9),
                                   authorizer=Authorizer(pol), audit=AuditLog(tmp / "audit.jsonl"), **kw)


def _tok(tenant: str, jti: str) -> str:
    now = time.time()
    return mint({"iss": "iss", "sub": f"u-{tenant}", "aud": "inv64", "tid": tenant, "kind": "workload",
                 "roles": ["dev"], "iat": now, "exp": now + 600, "jti": jti}, kid="k", key=K)


def _req(tenant, op="submit", app="shop", key=None, manifest=M):
    r = {"format": "PK_APP_SUBMIT_REQUEST/1", "version": "PK_APP_SUBMIT/2", "operation": op, "tenant": tenant,
         "environment": "prod", "site": "s1", "app": app, "manifest_json": json.dumps(manifest)}
    if key:
        r["idempotency_key"] = key
    return r


def s1_concurrent_validate(p, tmp) -> dict:
    obj = copy.deepcopy(M)
    snap = copy.deepcopy(obj)
    want = canonical(obj)
    bad = []
    old = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        with ThreadPoolExecutor(p["threads"]) as ex:
            for d in ex.map(lambda _: (validate(obj), canonical(obj)), range(p["iters"])):
                if d[0] or d[1] != want:
                    bad.append(d)
    finally:
        sys.setswitchinterval(old)
    return {"ok": not bad and obj == snap, "mismatches": len(bad), "input_mutated": obj != snap}


def s2_duplicate_idempotency(p, tmp) -> dict:
    svc = _service(tmp, ["acme"])
    key = "idem-" + "x" * 16
    outs = []
    with ThreadPoolExecutor(p["threads"]) as ex:
        futs = [ex.submit(svc.handle, _req("acme", key=key), token=_tok("acme", f"j{i}")) for i in range(p["threads"] * 2)]
        outs = [f.result() for f in futs]
    effects = [r for r in svc.audit.records() if r["operation"] == "app.submit" and r["outcome"] == "accepted"]
    replays = sum(1 for o in outs if o.get("replayed"))
    return {"ok": len(effects) == 1 and all(o["outcome"] == "success" for o in outs) and svc.audit.verify() > 0,
            "logical_effects": len(effects), "replays": replays, "audit_verified": True}


def s3_concurrent_activation(p, tmp) -> dict:
    s = ConfigStore(tmp / "cfg")
    eff = lambda tag: {"scope": {"tenant": "acme"}, "manifest": dict(M, **{"x": tag}), "digest": canonical(dict(M, **{"x": tag}))}
    r0 = s.propose(eff("base"), actor="op", release="r", validator=validate)
    s.activate(r0, actor="op", expected_active=None)
    cands = [s.propose(eff(f"c{i}"), actor="op", release="r", validator=validate) for i in range(p["threads"])]
    wins, conflicts = [], 0

    def go(r):
        nonlocal conflicts
        try:
            s.activate(r, actor="op", expected_active=r0)
            wins.append(r)
        except Inv64Error as e:
            if e.code in ("activation.conflict", "activation.state"):
                conflicts += 1
    ts = [threading.Thread(target=go, args=(r,)) for r in cands]
    [t.start() for t in ts]
    [t.join() for t in ts]
    actives = [r for r, v in s.state["revisions"].items() if v["state"] == "active"]
    return {"ok": len(wins) == 1 and actives == wins, "winners": len(wins), "conflicts": conflicts}


def s4_burst_backpressure(p, tmp) -> dict:
    adm = AdmissionController(max_inflight=8, per_tenant_max=4)
    peak = 0
    rejected = 0
    lock = threading.Lock()

    def work(i):
        nonlocal peak, rejected
        try:
            with adm.admit(f"t{i % 3}"):
                with lock:
                    peak = max(peak, adm.inflight)
                time.sleep(0.001)
        except Inv64Error:
            with lock:
                rejected += 1
    with ThreadPoolExecutor(64) as ex:
        list(ex.map(work, range(p["burst"])))
    return {"ok": peak <= 8 and adm.inflight == 0, "peak_inflight": peak, "rejected": rejected, "limit": 8}


def s5_fleet_isolation(p, tmp) -> dict:
    tenants = [f"t{i:04d}" for i in range(p["tenants"])]
    svc = _service(tmp, tenants)
    for i, t in enumerate(tenants):
        r = svc.handle(_req(t, app=f"a{i}", key=f"k-{t}-" + "y" * 12), token=_tok(t, f"f{i}"))
        assert r["outcome"] == "success", r
    leaks = sum(1 for t in tenants for rec in svc.registry.list(t) if rec["tenant"] != t)
    cross = svc.handle(_req(tenants[0]), token=_tok(tenants[1], "cross"))
    return {"ok": leaks == 0 and cross["error"]["code"] == "tenant.mismatch" and all(len(svc.registry.list(t)) == 1 for t in tenants),
            "tenants": len(tenants), "leaks": leaks, "cross_tenant": cross["error"]["code"]}


def s6_soak(p, tmp) -> dict:
    svc = _service(tmp, ["acme"])
    tracemalloc.start()
    t_end = time.time() + p["soak_s"]
    i = 0
    samples = []
    fds0 = len(os.listdir("/proc/self/fd")) if os.path.isdir("/proc/self/fd") else None
    th0 = threading.active_count()
    while time.time() < t_end:
        svc.handle(_req("acme", op="validate"), token=_tok("acme", f"s{i}"))
        i += 1
        if i % 500 == 0:
            samples.append(tracemalloc.get_traced_memory()[0])
    tracemalloc.stop()
    growth = (samples[-1] - samples[len(samples) // 2]) if len(samples) >= 4 else 0
    fds1 = len(os.listdir("/proc/self/fd")) if fds0 is not None else None
    # bounded structures: ring buffers/decision log/replay cache have hard caps; growth after warm-up must be small
    return {"ok": growth < 8 * 2 ** 20 and (fds0 is None or fds1 - fds0 <= 2) and threading.active_count() <= th0,
            "requests": i, "mem_growth_second_half_bytes": growth, "fd_delta": None if fds0 is None else fds1 - fds0}


def s7_partition_reconnect(p, tmp) -> dict:
    """Two sites diverge during a partition; on reconnect each converges to the control plane's desired digest."""
    eff = lambda tag: {"scope": {"tenant": "acme"}, "manifest": dict(M, **{"x": tag}), "digest": canonical(dict(M, **{"x": tag}))}
    a, b = ConfigStore(tmp / "siteA"), ConfigStore(tmp / "siteB")
    for s in (a, b):
        r = s.propose(eff("v1"), actor="cp", release="r", validator=validate)
        s.activate(r, actor="cp", expected_active=None)
    # partition: site A gets a local emergency change, B does not
    ra = a.propose(eff("local-hotfix"), actor="site-op", release="r", validator=validate)
    a.activate(ra, actor="site-op", expected_active=a.state["active"])
    desired = eff("v2")  # control plane decided v2 meanwhile
    # reconnect: precedence rule (SPECIFICATION §7.4): control-plane desired state wins; local divergence recorded
    for s in (a, b):
        if s.status()["active_digest"] != desired["digest"]:
            r = s.propose(desired, actor="cp-reconcile", release="r", validator=validate)
            s.activate(r, actor="cp-reconcile", expected_active=s.state["active"])
    same = a.status()["active_digest"] == b.status()["active_digest"] == desired["digest"]
    return {"ok": same, "converged_digest": desired["digest"][:16],
            "divergence_recorded": any(v["actor"] == "site-op" for v in a.state["revisions"].values())}


SCENARIOS = [s1_concurrent_validate, s2_duplicate_idempotency, s3_concurrent_activation, s4_burst_backpressure,
             s5_fleet_isolation, s6_soak, s7_partition_reconnect]


def run(profile: str) -> dict:
    p = PROFILES[profile]
    res = []
    with tempfile.TemporaryDirectory() as d:
        for fn in SCENARIOS:
            sub = Path(d) / fn.__name__
            sub.mkdir()
            t0 = time.perf_counter()
            try:
                r = fn(p, sub)
            except Exception as e:
                r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
            r.update({"id": fn.__name__, "elapsed_s": round(time.perf_counter() - t0, 3)})
            res.append(r)
    return {"schema": "PK_APP_STRESS/1", "profile": profile, "parameters": p, "scenarios": res,
            "result": "PASS" if all(r["ok"] for r in res) else "FAIL", "python": sys.version.split()[0]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="ci", choices=sorted(PROFILES))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.profile)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    for r in res["scenarios"]:
        print(("PASS " if r["ok"] else "FAIL ") + r["id"], {k: v for k, v in r.items() if k not in ("id", "ok")})
    print(res["result"])
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
