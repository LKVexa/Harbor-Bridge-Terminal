"""Fault-injection scenario catalog with recovery evidence (MC-20; C051-C060).

    python -m inv64_application_model.tools.faults [--out evidence/FAULTS.json]

Each scenario injects one fault from FMEA.md, observes the system through its
public API only, and records: scenario id, FMEA row, injected fault, expected
and observed behaviour, recovery time, and PASS/FAIL. Recovery objectives are
release-blocking (``RTO_S``). Scenarios use temp directories and fake clocks, so
the run is deterministic and needs no network.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from inv64_application_model.activation import ConfigStore, SimulatedCrash
from inv64_application_model.adjacent import AdjacentError, Faults, default_adjacent
from inv64_application_model.audit import AuditLog, AuditUnavailable
from inv64_application_model.auth import Authenticator, TrustConfig, TrustUnavailable, mint
from inv64_application_model.authz import Authorizer
from inv64_application_model.errors import Inv64Error
from inv64_application_model.manifest import canonical, validate
from inv64_application_model.semantics import Deadline

RTO_S = 1.0
GOOD = {"schema": "app/v1", "components": [{"name": "api"}], "providers": [{"name": "kv"}],
        "links": [{"from": "api", "to": "kv"}], "traits": []}


class FakeClock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _eff(m, tag="") -> dict:
    m = dict(m, **({"x-tag": tag} if tag else {}))
    return {"format": "PK_APP_EFFECTIVE_CONFIG/1", "scope": {"tenant": "acme", "environment": "prod", "site": "s1"},
            "manifest": m, "digest": canonical(m)}


def scenario(fn):
    fn.scenario = True
    return fn


@scenario
def f01_adjacent_latency_exceeds_deadline(tmp: Path) -> dict:
    clk = FakeClock()
    adj = default_adjacent(inv63=Faults(latency_s=5.0))
    adj.inv63.sleep = clk.sleep
    d = Deadline.for_operation("activate", 2_000, clock=clk)
    try:
        adj.handoff(GOOD, tenant="acme", correlation_id="c", traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01", deadline=d)
        observed = "handoff succeeded"
    except Inv64Error as e:
        observed = e.code
    partial = bool(adj.inv65.bound.get("acme"))
    return {"fmea": "FM-ADJ-1", "fault": "INV-63 latency 5s vs 2s deadline", "expected": "deadline.exceeded, providers unbound",
            "observed": f"{observed}, providers bound={partial}", "pass": observed == "deadline.exceeded" and not partial}


@scenario
def f02_adjacent_unavailable(tmp: Path) -> dict:
    adj = default_adjacent(inv66=Faults(unavailable=True))
    try:
        adj.handoff(GOOD, tenant="acme", correlation_id="c", traceparent="t")
        obs = "ok"
    except Inv64Error as e:
        obs = e.code
    return {"fmea": "FM-ADJ-2", "fault": "INV-66 connection refused", "expected": "admission.overloaded (retryable), nothing deployed",
            "observed": obs, "pass": obs == "admission.overloaded" and not adj.inv63.deployed}


@scenario
def f03_adjacent_malformed(tmp: Path) -> dict:
    adj = default_adjacent(inv63=Faults(malformed=True))
    try:
        adj.handoff(GOOD, tenant="acme", correlation_id="c", traceparent="t")
        obs = "ok"
    except Inv64Error as e:
        obs = e.code
    return {"fmea": "FM-ADJ-3", "fault": "INV-63 malformed response", "expected": "internal, providers unbound",
            "observed": obs, "pass": obs == "internal" and not adj.inv65.bound.get("acme")}


@scenario
def f04_adjacent_version_mismatch(tmp: Path) -> dict:
    adj = default_adjacent(inv65=Faults(version=3))
    try:
        adj.handoff(GOOD, tenant="acme", correlation_id="c", traceparent="t")
        obs = "ok"
    except Inv64Error as e:
        obs = e.code
    return {"fmea": "FM-ADJ-4", "fault": "INV-65 advertises unsupported contract v3", "expected": "version.unsupported before any call",
            "observed": obs, "pass": obs == "version.unsupported" and not adj.inv10.calls}


def _crash(tmp: Path, phase: str) -> dict:
    root = tmp / f"store-{phase}"
    s = ConfigStore(root)
    r1 = s.propose(_eff(GOOD), actor="op", release="r", validator=validate)
    s.activate(r1, actor="op", expected_active=None)
    r2 = s.propose(_eff(GOOD, "v2"), actor="op", release="r", validator=validate)
    s.crash_at = phase
    try:
        s.activate(r2, actor="op", expected_active=r1)
    except SimulatedCrash:
        pass
    t0 = time.perf_counter()
    s2 = ConfigStore(root)  # "restart"
    rto = time.perf_counter() - t0
    want = r1 if phase == "prepare" else r2
    return {"fault": f"process kill after {phase.upper()} journaled", "expected": f"active={want}",
            "observed": f"active={s2.state['active']} recovery={s2.recovery}", "recovery_s": round(rto, 4),
            "pass": s2.state["active"] == want and s2.state["pending"] is None and rto < RTO_S}


@scenario
def f05_crash_after_prepare(tmp: Path) -> dict:
    return {"fmea": "FM-CFG-1", **_crash(tmp, "prepare")}


@scenario
def f06_crash_after_commit(tmp: Path) -> dict:
    return {"fmea": "FM-CFG-2", **_crash(tmp, "commit")}


@scenario
def f07_audit_sink_outage(tmp: Path) -> dict:
    class Broken:
        def __init__(self):
            self.fail = True

        def __call__(self, p):
            if self.fail:
                raise OSError("disk full")
            return p.open("a", encoding="utf-8")
    op = Broken()
    log = AuditLog(tmp / "a.jsonl", opener=op, buffer_limit=3)
    for i in range(5):
        log.append("x", actor="a", outcome="ok")
    crit_refused = False
    try:
        log.append("activation.commit", actor="a", outcome="ok", fail_closed=True)
    except AuditUnavailable:
        crit_refused = True
    op.fail = False
    log.append("x", actor="a", outcome="ok")
    n = log.verify()
    loss = [r for r in log.records() if r["operation"] == "audit.loss"]
    return {"fmea": "FM-AUD-1", "fault": "audit sink raises OSError", "expected": "bounded buffer, drops counted+chained, critical op refused",
            "observed": f"dropped={log.dropped} loss_records={len(loss)} critical_refused={crit_refused} verified={n}",
            "pass": log.dropped == 2 and len(loss) == 1 and loss[0]["detail"]["dropped"] == 2 and crit_refused}


@scenario
def f08_identity_service_outage(tmp: Path) -> dict:
    clk = FakeClock()
    K = b"k" * 32
    up = {"on": True}

    def src():
        if not up["on"]:
            raise TrustUnavailable()
        return TrustConfig("t1", "inv64", {"iss": {"k": ("HS256", K)}})
    a = Authenticator(src, clock=clk, cache_ttl_s=300)
    tok = lambda j: mint({"iss": "iss", "sub": "s", "aud": "inv64", "tid": "acme", "kind": "human", "iat": clk(),
                          "exp": clk() + 600, "jti": j}, kid="k", key=K)
    a.authenticate(tok("1"))
    up["on"] = False
    clk.t += 100
    cached_ok = a.authenticate(tok("2")).subject == "s"
    clk.t += 400
    try:
        a.authenticate(tok("3"))
        stale = "accepted"
    except Inv64Error as e:
        stale = e.code
    return {"fmea": "FM-TRUST-1", "fault": "trust source unavailable", "expected": "cached keys verify within TTL; auth.trust_unavailable after",
            "observed": f"within_ttl={cached_ok} after_ttl={stale}", "pass": cached_ok and stale == "auth.trust_unavailable"}


@scenario
def f09_clock_skew(tmp: Path) -> dict:
    clk = FakeClock()
    K = b"k" * 32
    a = Authenticator(lambda: TrustConfig("t1", "inv64", {"iss": {"k": ("HS256", K)}}, clock_skew_s=60), clock=clk)
    t = mint({"iss": "iss", "sub": "s", "aud": "inv64", "tid": "acme", "kind": "human", "iat": clk() + 300,
              "nbf": clk() + 300, "exp": clk() + 900, "jti": "x"}, kid="k", key=K)
    try:
        a.authenticate(t)
        obs = "accepted"
    except Inv64Error as e:
        obs = e.code
    return {"fmea": "FM-TIME-1", "fault": "issuer clock 300s ahead (skew allowance 60s)", "expected": "auth.not_yet_valid",
            "observed": obs, "pass": obs == "auth.not_yet_valid"}


@scenario
def f10_policy_service_outage(tmp: Path) -> dict:
    az = Authorizer()
    from inv64_application_model.auth import Principal
    p = Principal("s", "acme", "human", ("dev",), "iss", "j", 0)
    d = az.decide(p, "app.submit", tenant="acme", environment="prod", site="s1", resource="apps/x")
    try:
        az.activate({"format": "PK_APP_AUTHZ_POLICY/1", "version": "bad", "grants": "oops"})
        bad = "accepted"
    except Exception as e:
        bad = type(e).__name__
    return {"fmea": "FM-POL-1", "fault": "no verified policy / corrupt policy", "expected": "deny (authz.policy_invalid); corrupt policy rejected",
            "observed": f"{d.code}; {bad}", "pass": (not d.allowed) and d.code == "authz.policy_invalid" and bad == "PolicyError"}


@scenario
def f11_crash_loop_quarantine(tmp: Path) -> dict:
    s = ConfigStore(tmp / "loop")
    r1 = s.propose(_eff(GOOD), actor="op", release="r", validator=validate)
    s.activate(r1, actor="op", expected_active=None)
    bad = _eff(GOOD, "bad")
    r2 = s.propose(bad, actor="op", release="r", validator=validate)
    s.activate(r2, actor="op", expected_active=r1, health_probe=lambda e: False)
    try:
        s.propose(bad, actor="op", release="r", validator=validate)
        again = "accepted"
    except Inv64Error as e:
        again = e.code
    return {"fmea": "FM-CFG-3", "fault": "candidate fails health after commit (crash loop)", "expected": "auto rollback + quarantine; retry refused",
            "observed": f"active={s.state['active']} retry={again}", "pass": s.state["active"] == r1 and again == "activation.quarantined"}


@scenario
def f12_duplicate_after_restart(tmp: Path) -> dict:
    root = tmp / "dup"
    s = ConfigStore(root)
    r1 = s.propose(_eff(GOOD), actor="op", release="r", validator=validate)
    s.activate(r1, actor="op", expected_active=None)
    s2 = ConfigStore(root)  # restart; caller retries the same activation request
    try:
        s2.activate(r1, actor="op", expected_active=None)
        obs = "applied twice"
    except Inv64Error as e:
        obs = e.code
    return {"fmea": "FM-CFG-4", "fault": "client retries activation after server restart", "expected": "activation.conflict (CAS), single effect",
            "observed": obs, "pass": obs == "activation.conflict"}


@scenario
def f13_corrupt_state_snapshot(tmp: Path) -> dict:
    root = tmp / "corrupt"
    s = ConfigStore(root)
    r1 = s.propose(_eff(GOOD), actor="op", release="r", validator=validate)
    s.activate(r1, actor="op", expected_active=None)
    (root / "state.json").write_text("{not json", encoding="utf-8")
    try:
        ConfigStore(root)
        obs = "started on corrupt state"
    except ValueError as e:
        obs = type(e).__name__
    return {"fmea": "FM-CFG-5", "fault": "state snapshot corrupted on disk", "expected": "refuse to start (fail safe); restore from backup (BACKUP_RESTORE.md)",
            "observed": obs, "pass": obs == "JSONDecodeError"}


def run() -> dict:
    out = []
    with tempfile.TemporaryDirectory() as d:
        for name, fn in sorted(globals().items()):
            if callable(fn) and getattr(fn, "scenario", False):
                sub = Path(d) / name
                sub.mkdir()
                t0 = time.perf_counter()
                try:
                    r = fn(sub)
                except Exception as e:  # a scenario crash is itself a failure
                    r = {"fault": name, "observed": f"scenario crashed: {type(e).__name__}: {e}", "pass": False}
                r.update({"id": name, "elapsed_s": round(time.perf_counter() - t0, 4)})
                out.append(r)
    ok = all(r["pass"] for r in out)
    return {"schema": "PK_APP_FAULTS/1", "rto_objective_s": RTO_S, "scenarios": out,
            "passed": sum(r["pass"] for r in out), "total": len(out), "result": "PASS" if ok else "FAIL"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run()
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    for r in res["scenarios"]:
        print(("PASS " if r["pass"] else "FAIL ") + r["id"] + " :: " + r["observed"])
    print(res["result"], f"{res['passed']}/{res['total']}")
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
