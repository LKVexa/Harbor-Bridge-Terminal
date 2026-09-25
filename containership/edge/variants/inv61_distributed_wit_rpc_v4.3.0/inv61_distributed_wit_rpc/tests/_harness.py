"""Shared fixtures for the INV-61 4.3.0 suites (stdlib only)."""
from __future__ import annotations

import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib  # noqa: E402

pkg = importlib.import_module(PKG_DIR.name)
codec = importlib.import_module(PKG_DIR.name + ".codec")
wit_model = importlib.import_module(PKG_DIR.name + ".wit_model")
security = importlib.import_module(PKG_DIR.name + ".security")
server = importlib.import_module(PKG_DIR.name + ".server")
transport = importlib.import_module(PKG_DIR.name + ".transport")
resilience = importlib.import_module(PKG_DIR.name + ".resilience")
observability = importlib.import_module(PKG_DIR.name + ".observability")
state = importlib.import_module(PKG_DIR.name + ".state")
negotiation = importlib.import_module(PKG_DIR.name + ".negotiation")
config = importlib.import_module(PKG_DIR.name + ".config")
rpc = importlib.import_module(PKG_DIR.name + ".rpc")

KV = wit_model.parse((PKG_DIR / "wit" / "kv.wit").read_text())[0]


def key(principal: str = "client-a", kid: str | None = None) -> "security.Key":
    return security.Key(kid or f"{principal}-k1", principal, secrets.token_bytes(32))


class Fixture:
    """A fully-wired service with a KV implementation, keys and policy."""

    def __init__(self, tmp: str | None = None, *, grants=None, clock_ms=None, **svc_kw):
        self.tmp = pathlib.Path(tmp or tempfile.mkdtemp(prefix="inv61-"))
        self.ring = security.KeyRing()
        self.ckey = key("client-a")
        self.ring.add(self.ckey)
        self.policy = security.Policy(grants if grants is not None else [
            security.Grant("client-a", "default", KV.qualified, "*")])
        kf = self.tmp / "audit.key"
        if not kf.exists():
            kf.write_bytes(secrets.token_bytes(32))
        self.audit_key = kf.read_bytes()
        self.audit = security.AuditLog(self.tmp / "audit.jsonl", self.audit_key, fsync=False)
        self.logs: list[str] = []
        self.logger = observability.StructuredLogger("node-1", sink=self.logs.append)
        kw = dict(node_id="node-1", keyring=self.ring, policy=self.policy, audit=self.audit,
                  logger=self.logger, state=state.StateStore(self.tmp / "state.json"))
        if clock_ms is not None:
            kw["clock_ms"] = clock_ms
        kw.update(svc_kw)
        self.svc = server.RpcService(**kw)
        self.data: dict[str, int] = {}
        self.calls = {"put": 0}

        def put(e, mode):
            self.calls["put"] += 1
            self.data[e["key"]] = e["value"]
            return ("ok", None)

        def slow(ms, cancel=None):
            end = time.monotonic() + ms / 1000
            while time.monotonic() < end:
                if cancel is not None and cancel.cancelled:
                    return False
                time.sleep(0.002)
            return True

        self.svc.export(KV, "get", lambda k: self.data.get(k))
        self.svc.export(KV, "put", put, mutating=True)
        self.svc.export(KV, "scan", lambda p, n: [{"key": k, "value": v, "tags": []}
                                                  for k, v in sorted(self.data.items()) if k.startswith(p)][:n])
        self.svc.export(KV, "echo", lambda b: b)
        self.svc.export(KV, "slow", slow, wants_cancel=True)
        self.svc.export(KV, "boom", lambda: 1 / 0)
        self.svc.acquire_ownership("kv/store", ttl_s=60)
        time.sleep(0.002)  # frames issued in the boot millisecond are refused by design

    def envelope(self, func: str, args: list, *, key_=None, nonce=None, issued_ms=None,
                 deadline_ms=None, version=None, fp=None, idem=None, tenant="default", trace=None):
        k = key_ or self.ckey
        f = KV.funcs[func]
        now = int(time.time() * 1000) if issued_ms is None else issued_ms
        env = {"request_id": secrets.token_hex(8), "sender": k.principal, "tenant": tenant,
               "nonce": nonce or secrets.token_hex(16), "issued_ms": now,
               "deadline_ms": deadline_ms if deadline_ms is not None else now + 5000,
               "interface": KV.qualified, "version": version or KV.version, "function": func,
               "fp": fp or rpc.fingerprint(f.param_types(), f.result_types()),
               "idempotency_key": idem, "traceparent": trace,
               "args": codec.encode(("tuple", tuple(KV.resolve(t) for _, t in f.params)), args),
               "key_id": "", "mac": b""}
        return security.sign(env, k)

    def call(self, env, tls_peer=None) -> dict:
        body = codec.encode(codec.REQUEST_ENVELOPE, env)
        return codec.decode(codec.RESPONSE_ENVELOPE, self.svc.handle(body, tls_peer=tls_peer))


def make_pki(d: pathlib.Path, names=("node-1", "client-a", "mallory")) -> dict:
    """Throwaway CA + leaf certs (CN=name, SAN=localhost,127.0.0.1) via openssl."""
    if shutil.which("openssl") is None:
        raise RuntimeError("openssl CLI required for TLS tests")
    run = lambda *a: subprocess.run(a, cwd=d, check=True, capture_output=True)
    run("openssl", "req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
        "-keyout", "ca.key", "-out", "ca.pem", "-days", "2", "-subj", "/CN=inv61-test-ca")
    out = {"ca": str(d / "ca.pem")}
    for n in names:
        (d / f"{n}.ext").write_text("subjectAltName=DNS:localhost,IP:127.0.0.1\n")
        run("openssl", "req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes",
            "-keyout", f"{n}.key", "-out", f"{n}.csr", "-subj", f"/CN={n}")
        run("openssl", "x509", "-req", "-in", f"{n}.csr", "-CA", "ca.pem", "-CAkey", "ca.key",
            "-CAcreateserial", "-out", f"{n}.pem", "-days", "2", "-extfile", f"{n}.ext")
        out[n] = (str(d / f"{n}.pem"), str(d / f"{n}.key"))
    return out
