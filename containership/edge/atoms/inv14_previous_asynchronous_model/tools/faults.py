"""Fault-injection harness (component P2-26; C060, C089).

Scenarios (each returns observed vs expected):
  F1 clock_backward_jump    injected clock jumps back 100 s mid-wait -> wait still bounded
  F2 clock_forward_jump     injected clock jumps forward -> early timeout, no crash
  F3 audit_sink_loss        audit path removed mid-run -> PK_AUDIT_UNAVAILABLE, no leaked slots
  F4 signaller_stall        producer never signals -> timeout at the bound
  F5 dependency_loss        pk_core absent -> release verifier exits 2 (BLOCKED), never 0
  F6 process_kill           SIGKILL during a blocking poll after a checkpoint -> restart
                            restores counters, readiness is not restored, re-poll observes resource
  F7 corrupt_checkpoint     torn checkpoint on restart -> refused, safe defaults
  F8 control_plane_degraded invalid config pushed -> rejected, active config unchanged
Network partition / reconnect: not applicable to the in-memory primitive (no
network I/O); the boundary is recorded, not simulated.
"""
import json, os, shutil, signal, subprocess, sys, tempfile, textwrap, threading, time
import _path  # noqa
sys.path.insert(0, str(_path.PKG / "tests"))
from _support import make_service
import polling as P, checkpoint, config, admission


def f1():
    seq = iter([1000.0, 900.0] + [900.0] * 100000)
    ps = P.PollSet("o", clock=lambda: next(seq, 900.0))
    t = time.monotonic(); r = ps.poll([P.Pollable("x", "o")], timeout_ticks=40); el = time.monotonic() - t
    return {"timed_out": r["timed_out"], "elapsed_s": round(el, 4), "ok": r["timed_out"] and el < 0.5}


def f2():
    seq = iter([0.0, 10_000.0])
    ps = P.PollSet("o", clock=lambda: next(seq, 10_000.0))
    t = time.monotonic(); r = ps.poll([P.Pollable("x", "o")], timeout_ticks=1000); el = time.monotonic() - t
    return {"timed_out": r["timed_out"], "elapsed_s": round(el, 4), "ok": r["timed_out"] and el < 0.5}


def f3():
    svc, iss, _, tmp = make_service()
    o = "a/b/c"
    svc.poll(o, [P.Pollable("x", o)], timeout_ticks=1, token=iss.mint(o))
    shutil.rmtree(tmp)
    try:
        svc.poll(o, [P.Pollable("x", o)], timeout_ticks=1, token=iss.mint(o)); code = None
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
    snap = svc.admission.snapshot()
    return {"code": code, "active_after": snap["active"], "in_flight": svc.lifecycle.in_flight(),
            "ok": code == "PK_AUDIT_UNAVAILABLE" and snap["active"] == 0 and svc.lifecycle.in_flight() == 0}


def f4():
    t = time.monotonic(); r = P.PollSet("o").poll([P.Pollable("x", "o")], timeout_ticks=100); el = time.monotonic() - t
    return {"elapsed_s": round(el, 4), "ok": r["timed_out"] and 0.095 <= el < 0.5}


def f5():
    env = {k: v for k, v in os.environ.items() if k != "PK_CORE_PATH"}
    d = tempfile.mkdtemp(); shutil.copytree(_path.PKG, os.path.join(d, _path.PKG.name))
    r = subprocess.run([sys.executable, "-B", os.path.join(d, _path.PKG.name, "verify_release.py"), "--external-only"],
                       capture_output=True, text=True, env=env, cwd=d)
    shutil.rmtree(d)
    return {"exit": r.returncode, "blocked_msg": "RELEASE BLOCKED" in r.stderr, "ok": r.returncode == 2 and "RELEASE BLOCKED" in r.stderr}


CHILD = textwrap.dedent("""
    import sys, time; sys.path.insert(0, {pkg!r}); sys.dont_write_bytecode = True
    import polling as P, checkpoint
    ps = P.PollSet("o"); p = P.Pollable("x", "o"); p.signal()
    for _ in range(7): ps.poll([p], timeout_ticks=1)
    checkpoint.save({cp!r}, checkpoint.build(ps.metrics_snapshot(), "DEPRECATED", "4.3.0-base"))
    print("CHECKPOINTED", flush=True)
    ps.poll([P.Pollable("never", "o")], timeout_ticks=60000)
""")


def f6():
    d = tempfile.mkdtemp(); cp = os.path.join(d, "cp.json")
    pr = subprocess.Popen([sys.executable, "-B", "-c", CHILD.format(pkg=str(_path.PKG), cp=cp)], stdout=subprocess.PIPE, text=True)
    line = pr.stdout.readline().strip(); time.sleep(0.05)
    pr.send_signal(signal.SIGKILL); pr.wait(5)
    restored, err = checkpoint.restore_or_default(cp)
    p = P.Pollable("x", "o"); fresh_ready = p.is_ready(); p.signal()
    repoll = P.PollSet("o").poll([p], timeout_ticks=1)["ready"]
    shutil.rmtree(d)
    return {"child_reached_checkpoint": line == "CHECKPOINTED", "killed_rc": pr.returncode,
            "restored_polls_ready": restored["counters"]["polls_ready"] if restored else None,
            "readiness_persisted": restored["readiness_persisted"] if restored else None,
            "fresh_pollable_ready": fresh_ready, "repoll_ready": repoll,
            "ok": line == "CHECKPOINTED" and restored is not None and restored["counters"]["polls_ready"] == 7
                  and not fresh_ready and repoll == ["x"]}


def f7():
    d = tempfile.mkdtemp(); cp = os.path.join(d, "cp.json")
    checkpoint.save(cp, checkpoint.build({}, "DISABLED", "v")); raw = open(cp).read()
    open(cp, "w").write(raw[: len(raw) // 2])
    got, code = checkpoint.restore_or_default(cp); shutil.rmtree(d)
    return {"code": code, "ok": got is None and code == "PK_CHECKPOINT_CORRUPT"}


def f8():
    store = config.ConfigStore(config.BASE_CONFIG); before = store.active
    bad = json.loads(json.dumps(config.BASE_CONFIG)); bad["limits"]["max_pollables"] = 0; bad["provenance"]["version"] = "x"
    try:
        store.update(bad); code = None
    except Exception as e:
        code = getattr(e, "code", None)
    return {"code": code, "ok": code == "PK_CONFIG_LIMIT_RANGE" and store.active == before}


SCENARIOS = {"F1_clock_backward_jump": f1, "F2_clock_forward_jump": f2, "F3_audit_sink_loss": f3, "F4_signaller_stall": f4,
             "F5_dependency_loss": f5, "F6_process_kill": f6, "F7_corrupt_checkpoint": f7, "F8_control_plane_degraded": f8}


def run(only=None):
    out = {}
    for k, f in SCENARIOS.items():
        if only and k not in only:
            continue
        try:
            out[k] = f()
        except Exception as e:
            out[k] = {"ok": False, "harness_error": f"{type(e).__name__}: {e}"}
    out["network_partition"] = {"status": "NOT_APPLICABLE", "boundary": "INV-14 performs no network I/O; partition tolerance belongs to the telemetry collector, audit storage and runtime layers."}
    return out


if __name__ == "__main__":
    r = run(sys.argv[1:] or None); print(json.dumps(r, indent=1))
    raise SystemExit(0 if all(v.get("ok", True) for v in r.values() if isinstance(v, dict) and "status" not in v) else 1)
