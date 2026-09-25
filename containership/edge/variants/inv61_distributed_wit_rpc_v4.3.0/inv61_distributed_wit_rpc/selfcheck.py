"""Post-install self check (bootstrap step): proves the installed runtime can
parse its reference WIT, run an authenticated loopback call over a real
socket, verify its audit chain and report its versions.  Exit 0 = healthy."""
from __future__ import annotations

import json
import secrets
import sys
import tempfile
from pathlib import Path

from . import __version__, codec, negotiation, security, state, transport
from .server import RpcService
from .wit_model import parse


def main() -> int:
    iface = parse((Path(__file__).with_name("wit") / "kv.wit").read_text())[0]
    d = Path(tempfile.mkdtemp(prefix="inv61-selfcheck-"))
    k = security.Key("selfcheck-k1", "selfcheck", secrets.token_bytes(32))
    ring = security.KeyRing(); ring.add(k)
    akey = secrets.token_bytes(32)
    audit = security.AuditLog(d / "audit.jsonl", akey)
    svc = RpcService(node_id="selfcheck", keyring=ring, audit=audit, state=state.StateStore(d / "state.json"),
                     policy=security.Policy([security.Grant("selfcheck", "default", iface.qualified, "echo")]))
    svc.export(iface, "echo", lambda b: b)
    srv = transport.RpcServer(svc).start()
    try:
        c = transport.RpcClient(*srv.address, k)
        r = c.call(iface, "echo", [[1, 2, 3]])
        c.close()
    finally:
        srv.close(); svc.close()
    ok = r["status"] == "ok" and r["value"] == [1, 2, 3] and security.AuditLog.verify(d / "audit.jsonl", akey)[0]
    print(json.dumps({"inv61": __version__, "protocol": list(negotiation.CURRENT), "interface_digest": iface.digest,
                      "python": sys.version.split()[0], "status": "pass" if ok else "fail"}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
