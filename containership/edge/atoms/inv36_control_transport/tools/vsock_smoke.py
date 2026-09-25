"""Real AF_VSOCK smoke test (MC-03.035/.041, MC-15.009).

Exercises the kernel vsock path available on this machine:

* socket creation, bounded buffer sizing, bind/listen on VMADDR_CID_ANY;
* port-collision detection;
* connect to the host CID with a deadline and typed failure classification;
* optional end-to-end exchange when ``--peer-cid``/``--peer-port`` reach a
  listening INV-36 peer (a certified VM row), or when vsock loopback
  (``vsock_loopback``) is loaded so CID 1 is reachable.

``end_to_end`` is true only if a full PK_CTRL_HS/1 + frame exchange crossed a
real vsock connection.  Kernel-path checks alone never certify a row.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import threading

from .. import vsock
from ..stream import Connection, StreamError, StreamUnavailable


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=15036)
    ap.add_argument("--peer-cid", type=int)
    ap.add_argument("--peer-port", type=int, default=vsock.DEFAULT_PORT)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res: dict = {"schema": "inv36.vsock-smoke/1", "platform": vsock.platform_support(), "checks": {},
                 "end_to_end": False}
    ok = True

    def rec(name: str, passed: bool, detail: str) -> None:
        nonlocal ok
        res["checks"][name] = {"pass": passed, "detail": detail[:200]}
        ok = ok and passed

    if not vsock.available():
        rec("available", False, "AF_VSOCK unavailable")
    else:
        lst = None
        try:
            lst = vsock.VsockListener(port=a.port).open()
            rec("bind_listen", True, f"bound CID_ANY:{a.port}")
            try:
                vsock.VsockListener(port=a.port).open()
                rec("port_collision_detected", False, "second bind unexpectedly succeeded")
            except StreamUnavailable as exc:
                rec("port_collision_detected", True, exc.code.name)
            rec("accept_timeout_bounded", lst.accept(timeout=0.05) is None, "accept returned within deadline")
        except StreamError as exc:
            rec("bind_listen", False, f"{exc.code.name}: {exc}")
        try:
            vsock.vsock_connect(vsock.VMADDR_CID_HOST, 1, timeout=0.5).close()
            rec("host_connect_classified", True, "connected to host (unexpected but valid)")
        except StreamError as exc:
            rec("host_connect_classified", True, f"typed failure {exc.code.name}")
        # end-to-end via loopback or an explicit peer
        target = (a.peer_cid, a.peer_port) if a.peer_cid is not None else (vsock.VMADDR_CID_LOCAL, a.port)
        try:
            from ..messages import ControlMessage
            from ..testing import World
            w = World()
            srv = w.endpoint("vsock:srv", "host_agent", "t1",
                             handlers={"HEARTBEAT": lambda p, m: ControlMessage.of("HEARTBEAT", "t1", b"pong")})
            cli = w.endpoint("vsock:cli", "guest_agent", "t1")
            box: dict = {}
            if a.peer_cid is None and lst is not None:
                def serve():
                    got = lst.accept(timeout=2.0)
                    if got:
                        ch = srv.accept(Connection(got[0], read_timeout=2), source=f"vsock:{got[1][0]}")
                        ch.serve_one()
                        box["served"] = True
                t = threading.Thread(target=serve, daemon=True)
                t.start()
            s = vsock.vsock_connect(target[0], target[1], timeout=1.0)
            ch = cli.connect(Connection(s, read_timeout=2), source=f"vsock:{target[0]}")
            ch.send(ControlMessage.of("HEARTBEAT", "t1", b"ping"))
            reply = ch.receive()
            res["end_to_end"] = reply.body == b"pong"
            rec("end_to_end_exchange", res["end_to_end"], f"exchanged with CID {target[0]}")
        except StreamError as exc:
            res["checks"]["end_to_end_exchange"] = {"pass": None, "detail": f"not reachable: {exc.code.name} "
                                                    "(load vsock_loopback or pass --peer-cid on a certified row)"}
        if lst:
            lst.close()
    passed = [k for k, v in res["checks"].items() if v["pass"]]
    res["summary"] = f"kernel checks passed: {', '.join(passed)}; end_to_end={res['end_to_end']}"
    res["ok"] = ok
    text = json.dumps(res, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
