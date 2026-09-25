"""Standalone INV-61 node serving the reference ``inv61:kv/store`` interface.

Used by the two-process / network-namespace tests, the benchmark and the
bootstrap smoke check::

    python -m inv61_distributed_wit_rpc.demo_node --keyring keys.json \
        --audit-key-file audit.key --workdir ./run --port-file port.txt \
        [--tls-cert c.pem --tls-key k.pem --tls-ca ca.pem]
"""
from __future__ import annotations

import argparse
import pathlib
import signal
import sys
import threading

from . import observability, security, state, transport
from .server import RpcService
from .wit_model import parse

WIT = pathlib.Path(__file__).with_name("wit") / "kv.wit"


def build(args) -> tuple[RpcService, transport.RpcServer]:
    iface = parse(WIT.read_text())[0]
    ring = security.KeyRing.from_env_file(args.keyring)
    grants = [security.Grant(p, "default", iface.qualified, "*") for p in args.allow]
    work = pathlib.Path(args.workdir)
    work.mkdir(parents=True, exist_ok=True)
    audit = security.AuditLog(work / "audit.jsonl", pathlib.Path(args.audit_key_file).read_bytes().strip())
    svc = RpcService(node_id=args.node_id, keyring=ring, policy=security.Policy(grants), audit=audit,
                     logger=observability.StructuredLogger(args.node_id, sink=lambda l: print(l, file=sys.stderr)),
                     state=state.StateStore(work / "state.json"))
    data: dict[str, int] = {}
    svc.export(iface, "get", lambda k: data.get(k))

    def put(e, mode):
        data[e["key"]] = e["value"]
        return ("ok", None)
    svc.export(iface, "put", put, mutating=True)
    svc.export(iface, "scan", lambda p, n: [{"key": k, "value": v, "tags": []}
                                            for k, v in sorted(data.items()) if k.startswith(p)][:n])
    svc.export(iface, "echo", lambda b: b)
    svc.export(iface, "slow", lambda ms: threading.Event().wait(ms / 1000) or True)
    svc.export(iface, "boom", lambda: 1 / 0)
    svc.acquire_ownership("kv/store", ttl_s=3600)
    tls = None
    if args.tls_cert:
        tls = transport.server_tls_context(args.tls_cert, args.tls_key, args.tls_ca)
    srv = transport.RpcServer(svc, args.host, args.port, tls=tls, require_tls=bool(args.tls_cert))
    return svc, srv


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyring", required=True)
    ap.add_argument("--audit-key-file", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--node-id", default="node-1")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--port-file")
    ap.add_argument("--allow", action="append", default=["client-a"])
    ap.add_argument("--tls-cert"); ap.add_argument("--tls-key"); ap.add_argument("--tls-ca")
    args = ap.parse_args(argv)
    svc, srv = build(args)
    srv.start()
    if args.port_file:
        pathlib.Path(args.port_file).write_text(str(srv.address[1]))
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    stop.wait()
    ok = srv.drain(timeout_s=10)
    svc.close()
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
