"""Executable runbook (component P2-33).  State dir holds lifecycle.json,
checkpoint.json and audit.jsonl.  Commands: status | disable | rollback |
transition STATE | verify-audit.  The audit key is read from INV14_AUDIT_KEY_HEX
(>=32 bytes); it is never printed."""
import argparse, json, os, sys
import _path  # noqa
import lifecycle, audit, checkpoint, core_probe


def _key():
    h = os.environ.get("INV14_AUDIT_KEY_HEX", "")
    try:
        k = bytes.fromhex(h)
    except ValueError:
        k = b""
    if len(k) < 32:
        print(json.dumps({"ok": False, "code": "PK_AUDIT_WEAK_KEY"})); sys.exit(2)
    return k


def _load_lc(state):
    p = os.path.join(state, "lifecycle.json")
    s = json.load(open(p))["state"] if os.path.exists(p) else "DEPRECATED"
    return lifecycle.Lifecycle(s)


def _save_lc(state, lc):
    json.dump({"state": lc.state}, open(os.path.join(state, "lifecycle.json"), "w"))


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--state", required=True)
    sub = ap.add_subparsers(dest="c", required=True)
    sub.add_parser("status"); sub.add_parser("verify-audit")
    for n in ("disable", "rollback"):
        s = sub.add_parser(n); s.add_argument("--actor", required=True); s.add_argument("--reason", required=True)
    t = sub.add_parser("transition"); t.add_argument("to"); t.add_argument("--actor", required=True); t.add_argument("--reason", required=True)
    a = ap.parse_args(argv); os.makedirs(a.state, exist_ok=True)
    lc = _load_lc(a.state)
    sink_path = os.path.join(a.state, "audit.jsonl")
    if a.c == "status":
        cp, err = checkpoint.restore_or_default(os.path.join(a.state, "checkpoint.json"))
        pr = core_probe.probe()
        out = {"version": "4.3.0", "lifecycle": lc.state, "pk_core": pr["code"], "checkpoint_error": err,
               "readiness_persisted": cp["readiness_persisted"] if cp else False}
    elif a.c == "verify-audit":
        out = audit.verify_chain(sink_path, _key()) if os.path.exists(sink_path) else {"ok": True, "count": 0}
    else:
        sink = audit.AuditSink(sink_path, _key())
        try:
            if a.c == "disable":
                rec = lc.emergency_disable(actor=a.actor, reason=a.reason, drain_seconds=0)
            elif a.c == "rollback":
                rec = lc.transition("DEPRECATED", actor=a.actor, reason=a.reason)
            else:
                rec = lc.transition(a.to, actor=a.actor, reason=a.reason)
        except lifecycle.LifecycleError as e:
            print(json.dumps({"ok": False, "code": e.code})); return 2
        sink.append("lifecycle.transition", correlation_id="runbook", details={"to": lc.state, "actor": a.actor})
        _save_lc(a.state, lc); out = {"ok": True, "state": lc.state, "record": {k: rec[k] for k in rec if k != "at"}}
    print(json.dumps(out, sort_keys=True)); return 0 if out.get("ok", True) else 2


if __name__ == "__main__":
    sys.exit(main())
