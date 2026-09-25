"""Automated backup + isolated restore verification (MC-039-05/06). Writes a JSON drill report."""
import argparse, json, os, shutil, sys, tempfile, time
import _path  # noqa: F401
from inv05_current_control_state_system.backup import create_backup, restore_backup
from inv05_current_control_state_system.wal import DurableStore, Keyring, Sealer


def drill(n_keys=500, seed_dir=None):
    work = tempfile.mkdtemp(prefix="inv05-drill-")
    data_s = Sealer(Keyring({"d1": os.urandom(32)}, "d1"))
    backup_s = Sealer(Keyring({"b1": os.urandom(32)}, "b1"))
    sign_key = os.urandom(32)
    src = DurableStore.open(os.path.join(work, "src"), sealer=data_s)
    for i in range(n_keys):
        src.store.put(f"k/{i:05d}", {"i": i})
    t0 = time.perf_counter()
    b = create_backup(src.store, os.path.join(work, "backups"), sealer=backup_s, sign_key=sign_key)
    t_backup = time.perf_counter() - t0
    t0 = time.perf_counter()
    dst = restore_backup(b["path"], os.path.join(work, "restored"), backup_sealer=backup_s, sign_key=sign_key,
                         data_sealer=data_s)
    t_restore = time.perf_counter() - t0
    same = src.store.snapshot().to_dict()["kvs"] == dst.store.snapshot().to_dict()["kvs"]
    rep = {"schema": "cstate.restore_drill/1", "keys": n_keys, "revision": b["revision"], "backup_s": t_backup,
           "restore_s": t_restore, "state_equal": same, "invariants": dst.store.check_invariants(),
           "watch_before_backup_refused": dst.store.compact_revision == b["revision"], "ok": same}
    src.close(); dst.close(); shutil.rmtree(work, ignore_errors=True)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--keys", type=int, default=500); ap.add_argument("--out")
    a = ap.parse_args()
    r = drill(a.keys)
    s = json.dumps(r, indent=2)
    if a.out:
        open(a.out, "w").write(s)
    print(s)
    sys.exit(0 if r["ok"] else 1)
