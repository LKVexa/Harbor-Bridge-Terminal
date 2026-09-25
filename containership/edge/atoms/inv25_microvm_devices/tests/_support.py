"""Shared test fixtures: put the package's parent on sys.path, deterministic keys and tokens."""
import itertools
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib
pkg = importlib.import_module(PKG_DIR.name)
from importlib import import_module as _im
model = _im(PKG_DIR.name + ".model")
errors = _im(PKG_DIR.name + ".errors")
authz = _im(PKG_DIR.name + ".authz")
audit = _im(PKG_DIR.name + ".audit")
store = _im(PKG_DIR.name + ".store")
provenance = _im(PKG_DIR.name + ".provenance")
compat = _im(PKG_DIR.name + ".compat")
schemavalidate = _im(PKG_DIR.name + ".schemavalidate")

TEST_KEY = b"inv25-test-only-key-never-use-in-production"
AUD = "inv25-control-plane"
ISS = "test-issuer"
_n = itertools.count()


class Clock:
    def __init__(self, t=1_800_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


def verifier(clock=None):
    return authz.Verifier(audience=AUD, keys={"k1": (ISS, TEST_KEY)}, clock=clock or Clock())


def token(v, sub, caps, envs=("prod",), bg=False, ttl=300, **kw):
    return authz.mint_token(kw.pop("key", TEST_KEY), key_id=kw.pop("kid", "k1"), issuer=kw.pop("iss", ISS),
                            subject=sub, audience=kw.pop("aud", AUD), capabilities=caps, environments=envs,
                            ttl=ttl, nonce=f"n{next(_n)}", now=kw.pop("now", v.clock()), break_glass=bg)


ALL = ["catalogue.register", "catalogue.replace", "catalogue.widen", "catalogue.activate", "catalogue.rollback"]


def spec(name="virtio-net", version="1.0", regs=("status",)):
    return model.DeviceSpec(name, "paravirtual", version, frozenset(regs), "required by guest", "sec-team")


def schema(name):
    import json
    return json.loads((PKG_DIR / "schemas" / name).read_text())
