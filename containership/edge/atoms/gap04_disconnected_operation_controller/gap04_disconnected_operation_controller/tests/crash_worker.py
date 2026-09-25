"""Child process for crash qualification. Prints 'ACK <request_id> <decision_id>' only after
decide() returns (i.e. after the WAL fsync). Parent kills it / crashpoints exit it."""
import json, os, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _util import node, T  # noqa
d = pathlib.Path(sys.argv[1]); phase = sys.argv[2]; n_dec = int(sys.argv[3])
cp = T.ControlPlane(); cp.seed = bytes.fromhex(os.environ["CP_SEED"]); cp.pub = os.environ["CP_PUB"]
n, cp, m = node(d, cp=cp)
m.t = float(os.environ.get("MONO", "1000"))
if phase == "setup":
    T.bring_up(n, cp, m)
    T.go_dark(n, m)
    print("READY", flush=True)
elif phase == "decide":
    n.clock.anchor_trusted(n.clock.hwm)
    start = int(os.environ.get("START", "0"))
    for i in range(start, start + n_dec):
        rid = f"req-{i:08d}"
        r = n.decide("restart", f"ns/w{i}", rid)
        print("ACK", rid, r["decision_id"], flush=True)
elif phase == "reconcile":
    n.clock.anchor_trusted(n.clock.hwm)
    os.environ["NOOP"] = "1"
    T.come_back(n, cp, m)
    if n.controller.partitioned_since is None:
        print("ALREADY_RECONCILED", flush=True)
    else:
        rec = n.reconnect()
        print("RECONCILED", rec["decision_count"], flush=True)
print("DONE", flush=True)
