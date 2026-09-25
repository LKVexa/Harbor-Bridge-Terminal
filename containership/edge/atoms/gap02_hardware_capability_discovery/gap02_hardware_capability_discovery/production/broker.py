"""GAP02-MC-18 — Probe privilege broker / least-privilege isolation.

The broker is a separate process (deploy it under a dedicated service identity
with only the device ACLs it needs; the reporter runs unprivileged). It accepts
exactly one JSON request on stdin and serves only operations in ``OPERATIONS``
— fixed paths / fixed argv, bounded output. No caller-controlled paths, no
shell. The client authorises via ``AuthzPolicy`` (``probe.deep``) *before*
spawning, and the broker re-checks the op allow-list itself.

    python -m gap02_hardware_capability_discovery.production.broker < request.json
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

from .errors import Code, Gap02Error

MAX_OUT = 65_536
_DEV = re.compile(r"^(nvme\d+n\d+|sd[a-z]{1,2})$")

# op -> (kind, spec, parameter validator)
OPERATIONS: dict[str, tuple[str, Any, Any]] = {
    "efi.secureboot": ("file", "/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c", None),
    "smart.health": ("argv", ("/usr/sbin/smartctl", "-H", "-j", "/dev/{dev}"), _DEV),
    "ethtool.features": ("argv", ("/usr/sbin/ethtool", "-k", "{dev}"), re.compile(r"^[a-z][a-z0-9]{1,14}$")),
}


def handle(req: dict) -> dict:
    op = req.get("op")
    if op not in OPERATIONS:
        return {"ok": False, "code": Code.POLICY_DENIED.value}
    kind, spec, validator = OPERATIONS[op]
    dev = req.get("dev")
    if validator is not None and (not isinstance(dev, str) or not validator.fullmatch(dev)):
        return {"ok": False, "code": Code.CONFIG_INVALID.value}
    if validator is None and dev is not None:
        return {"ok": False, "code": Code.CONFIG_INVALID.value}
    try:
        if kind == "file":
            with open(spec, "rb") as f:
                data = f.read(64)
            return {"ok": True, "hex": data.hex()}
        argv = [a.format(dev=dev) for a in spec]
        if not os.path.isfile(argv[0]):
            return {"ok": False, "code": Code.PROBE_UNAVAILABLE.value}
        cp = subprocess.run(argv, capture_output=True, text=True, timeout=5, shell=False,
                            stdin=subprocess.DEVNULL, env={"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"})
        return {"ok": True, "rc": cp.returncode, "out": cp.stdout[:MAX_OUT]}
    except PermissionError:
        return {"ok": False, "code": Code.PRIVILEGE_DENIED.value}
    except subprocess.TimeoutExpired:
        return {"ok": False, "code": Code.TIMEOUT.value}
    except OSError:
        return {"ok": False, "code": Code.PROBE_UNAVAILABLE.value}


class BrokerClient:
    def __init__(self, authz, principal: str, argv: tuple[str, ...] | None = None, timeout: float = 8.0):
        self.authz, self.principal, self.timeout = authz, principal, timeout
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # -I: isolated mode (ignores env vars, user site, cwd); package root injected explicitly
        self.argv = argv or (sys.executable, "-I", "-c",
                             f"import sys;sys.path.insert(0,{root!r});"
                             "from gap02_hardware_capability_discovery.production import broker;"
                             "raise SystemExit(broker.main())")

    def call(self, op: str, dev: str | None = None) -> dict:
        self.authz.require(self.principal, "probe.deep")
        req = json.dumps({"op": op, "dev": dev})
        env = {"PATH": "/usr/bin:/bin"}
        try:
            cp = subprocess.run(list(self.argv), input=req, capture_output=True, text=True,
                                timeout=self.timeout, shell=False, cwd="/", env=env)
        except subprocess.TimeoutExpired as e:
            raise Gap02Error(Code.TIMEOUT, "broker") from e
        try:
            return json.loads(cp.stdout[:MAX_OUT * 2])
        except ValueError as e:
            raise Gap02Error(Code.MALFORMED_RESPONSE, "broker reply") from e


def main() -> int:
    try:
        req = json.loads(sys.stdin.read(4096))
        if not isinstance(req, dict):
            raise ValueError
    except ValueError:
        print(json.dumps({"ok": False, "code": Code.MALFORMED_RESPONSE.value}))
        return 2
    print(json.dumps(handle(req)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
