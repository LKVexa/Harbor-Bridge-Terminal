import pathlib
import sys
PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR) not in sys.path:
    sys.path.insert(0, str(PKG_DIR))
import secrets  # noqa: E402
from fvt import identity  # noqa: E402

KEY = b"k" * 32
DIGEST = "sha256:" + "a" * 64


def keys():
    return identity.KeyProvider({"k1": KEY})


def tok(kp, tenants=("t1",), ops=("create", "boot", "stop", "destroy", "read", "quarantine"), kind="service", **kw):
    return identity.issue(kp, "k1", sub=kw.pop("sub", "svc-a"), kind=kind, tenants=list(tenants), ops=list(ops),
                          nonce=secrets.token_hex(8), **kw)


def req(name="g1", tenant="t1", mem=1024, key=None, **kw):
    d = {"schema": "PK_FULL_VM/1", "name": name, "tenant": tenant, "memory_mib": mem,
         "image_digest": DIGEST, "idempotency_key": key or secrets.token_hex(6)}
    d.update(kw)
    return d
