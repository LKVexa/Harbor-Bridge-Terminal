"""Shared deterministic fixtures for the INV-29 standalone suites (no pk_core)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inv29_hybrid_wasm_unikernel as pkg  # noqa: E402
from inv29_hybrid_wasm_unikernel import admission as adm  # noqa: E402
from inv29_hybrid_wasm_unikernel.model import HostImage, WasmModule  # noqa: E402

NOW = 1_790_000_000
ATTEST_KEY = "inv27-44-test-signer"
SIGN_KEY = "inv29-record-signer"
TENANT = "acme"


class Clock:
    def __init__(self, t=NOW):
        self.t = t

    def __call__(self):
        return self.t


def keyring():
    return adm.Keyring({ATTEST_KEY: b"A" * 32, SIGN_KEY: b"S" * 32})


def policy(**kw):
    kw.setdefault("allowed_tenants", frozenset({TENANT}))
    return adm.AdmissionPolicy(**kw)


def admitter(kr=None, pol=None, clock=None, **kw):
    kr = kr or keyring()
    return adm.Admitter(kr, pol or policy(), signing_key_id=SIGN_KEY, clock=clock or Clock(), **kw)


def request(kr, *, imports=("clock", "net-send"), exposes=("clock", "net-send", "net-recv"),
            tenant=TENANT, module_bytes=b"module-v1", host_bytes=b"host-v1", now=NOW, nonce=None,
            atts=None, sealed=True, hardened=True, **kw):
    md, hd = adm.digest_bytes(module_bytes), adm.digest_bytes(host_bytes)
    if atts is None:
        atts = (adm.issue_attestation(kr, ATTEST_KEY, "sealed", hd, now=now),
                adm.issue_attestation(kr, ATTEST_KEY, "hardened", md, now=now))
    return adm.AdmissionRequest(
        tenant=tenant,
        module=WasmModule("svc", frozenset(imports), hardened=hardened),
        host=HostImage("mirage-host", frozenset(exposes), sealed=sealed),
        module_digest=md, host_digest=hd, attestations=tuple(atts),
        nonce=nonce or adm.new_nonce(), **kw)
