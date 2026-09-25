# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Shared test fixtures: a fully wired service with signed-request helper."""
import time
import uuid

from ..authz import Authenticator, MintingAuthority
from ..config import load
from ..service import CapabilityService

KEY_A = b"A" * 32
KEY_B = b"B" * 32
MINT_KEY = b"M" * 32


def make_service(**cfg_over):
    cfg = load("datacenter", extra=cfg_over or None)
    auth = Authenticator()
    auth.register("ctl-a", KEY_A, {"mint", "derive", "access", "invalidate", "describe"}, {"tenant-a"})
    auth.register("ctl-b", KEY_B, {"derive", "access"}, {"tenant-b"})
    svc = CapabilityService(cfg, authenticator=auth, authority=MintingAuthority(MINT_KEY))
    return svc


def signed(action, body, principal="ctl-a", key=KEY_A, ts=None, nonce=None):
    ts = time.time() if ts is None else ts
    nonce = nonce or uuid.uuid4().hex
    return {"principal": principal, "ts": ts, "nonce": nonce,
            "mac": Authenticator.request_mac(key, principal, action, body, ts, nonce)}


def mint(svc, tenant="tenant-a", base=0x1000, length=0x1000, perms=("read", "write"), **kw):
    b = {"schema": "PK_CAPABILITY/1", "op": "mint", "tenant": tenant, "base": base, "length": length,
         "permissions": list(perms), **kw}
    return svc.mint(b, signed("mint", b))


def access(svc, handle, address, size=8, op="read", tenant="tenant-a", principal="ctl-a", key=KEY_A):
    b = {"schema": "PK_CAPABILITY_ACCESS/1", "handle": handle, "tenant": tenant, "address": address,
         "size": size, "operation": op}
    return svc.access(b, signed("access", b, principal, key))


def derive(svc, handle, base, length, perms=None, tenant="tenant-a", **kw):
    b = {"schema": "PK_CAPABILITY/1", "op": "derive", "tenant": tenant, "handle": handle, "base": base,
         "length": length, **kw}
    if perms is not None:
        b["permissions"] = list(perms)
    return svc.derive(b, signed("derive", b))


def invalidate(svc, handle, tenant="tenant-a"):
    b = {"schema": "PK_CAPABILITY/1", "op": "invalidate", "tenant": tenant, "handle": handle}
    return svc.invalidate(b, signed("invalidate", b))
