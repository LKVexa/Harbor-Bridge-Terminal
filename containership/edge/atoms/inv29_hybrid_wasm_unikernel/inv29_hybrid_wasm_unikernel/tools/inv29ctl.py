"""Operator CLI for INV-29 (MC064 rollback, MC065 emergency disable, MC066 backup/restore,
MC040 ledger verification, MC041 gate).

  python tools/inv29ctl.py status   --state DIR
  python tools/inv29ctl.py disable  --state DIR --reason "SEV1-1234" --actor oncall
  python tools/inv29ctl.py enable   --state DIR --actor oncall
  python tools/inv29ctl.py backup   --state DIR --out FILE
  python tools/inv29ctl.py restore  --state DIR --src FILE
  python tools/inv29ctl.py rollback --to-evidence conformance/evidence_ledger.jsonl --seq N
  python tools/inv29ctl.py verify-ledger [PATH]
"""
import argparse
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))
from inv29_hybrid_wasm_unikernel import evidence as E  # noqa: E402
from inv29_hybrid_wasm_unikernel import lifecycle as L  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(prog="inv29ctl")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "disable", "enable", "backup", "restore"):
        p = sub.add_parser(name)
        p.add_argument("--state", required=True)
        p.add_argument("--actor", default="operator")
        if name == "disable":
            p.add_argument("--reason", required=True)
        if name == "backup":
            p.add_argument("--out", required=True)
        if name == "restore":
            p.add_argument("--src", required=True)
    rb = sub.add_parser("rollback")
    rb.add_argument("--to-evidence", required=True)
    rb.add_argument("--seq", type=int, required=True)
    vl = sub.add_parser("verify-ledger")
    vl.add_argument("path", nargs="?", default=str(PKG / "conformance" / "evidence_ledger.jsonl"))
    vl.add_argument("--gate", default=str(PKG / "conformance" / "PK_GATE_RESULTS.json"),
                    help="gate artifact whose recorded ledger anchor must still be reachable")
    a = ap.parse_args(argv)

    if a.cmd == "verify-ledger":
        gp = pathlib.Path(a.gate)
        min_entries = json.loads(gp.read_text()).get("evidence_ledger_entries", 0) if gp.exists() else 0
        print(json.dumps(E.Ledger(pathlib.Path(a.path)).verify(min_entries=min_entries)))
        return 0
    if a.cmd == "rollback":
        # Rollback target = a previously sealed evidence entry (README day-2 contract).
        led = E.Ledger(pathlib.Path(a.to_evidence))
        led.verify()
        entries = [json.loads(l) for l in pathlib.Path(a.to_evidence).read_text().splitlines() if l.strip()]
        target = next((e for e in entries if e["seq"] == a.seq), None)
        if target is None or target["kind"] != "release-manifest":
            print("refused: rollback target must be an intact release-manifest entry", file=sys.stderr)
            return 2
        print(json.dumps({"rollback_to": target["body"], "entry_hash": target["hash"],
                          "next": "redeploy the artifact whose digests match rollback_to, then run reconcile"}))
        return 0
    state = pathlib.Path(a.state)
    ctl = L.ControlFile(state / "control.json")
    if a.cmd == "status":
        store = L.Store(state / "store")
        print(json.dumps({"control": ctl.read(), "compositions": len(store.ids())}))
    elif a.cmd == "disable":
        print(json.dumps(ctl.write(a.reason, a.actor)))
    elif a.cmd == "enable":
        print(json.dumps(ctl.write(None, a.actor)))
    elif a.cmd == "backup":
        print(json.dumps(L.Store(state / "store").backup(a.out)))
    elif a.cmd == "restore":
        print(json.dumps(L.Store(state / "store").restore(a.src)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
