"""M31 - runnable node entrypoint (demo KV interface). Prints one JSON line with the
bound address once ready, then serves until stdin closes or SIGTERM.

    INV61_PSK=<hex> python tools/serve.py --peer svc-a --tenant t1 --key-id k1
"""
from __future__ import annotations
import argparse, json, os, signal, sys, threading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from wrpc import controls, node, ops, security, wit  # noqa: E402

DEMO_WIT = """package pk:kv@0.2.0;
interface store { get: func(k: string) -> option<u64>; put: func(k: string, v: u64); pid: func() -> u32; }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--peer", required=True)
    ap.add_argument("--tenant", required=True)
    ap.add_argument("--key-id", required=True)
    ap.add_argument("--config", help="JSON file layer")
    a = ap.parse_args()
    layers = [("file", json.load(open(a.config)))] if a.config else []
    store = ops.ConfigStore()
    store.activate(*layers)
    cfg = store.active
    kr = security.Keyring()
    kr.add(a.peer, ops.resolve_secret(cfg["psk_ref"]), 86400, key_id=a.key_id)
    data = {}
    impls = {("pk:kv/store", "get"): lambda k: data.get(k), ("pk:kv/store", "put"): lambda k, v: data.__setitem__(k, v),
             ("pk:kv/store", "pid"): lambda: os.getpid()}
    n = node.Node(cfg, kr, wit.parse(DEMO_WIT), impls, {a.peer: a.tenant},
                  controls.Authorizer([controls.Grant(a.tenant, a.peer, "pk:kv/store", "*")]),
                  log_sink=lambda line: print(line, file=sys.stderr, flush=True))
    host, port = n.start()
    print(json.dumps({"ready": True, "host": host, "port": port, "pid": os.getpid(),
                      "config_digest": store.provenance["digest"]}), flush=True)
    done = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: done.set())
    threading.Thread(target=lambda: (sys.stdin.read(), done.set()), daemon=True).start()
    done.wait()
    n.drain()
    n.stop()


if __name__ == "__main__":
    main()
