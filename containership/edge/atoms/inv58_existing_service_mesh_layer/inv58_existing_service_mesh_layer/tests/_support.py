"""Shared fixtures for the INV-58 v4.3.0 dependency-free suites."""
from __future__ import annotations

import pathlib
import sys
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))
PKG = PKG_DIR.name

import importlib

pkg = importlib.import_module(PKG)
authz = importlib.import_module(PKG + ".authz")
audit = importlib.import_module(PKG + ".audit")
config = importlib.import_module(PKG + ".config")
errors = importlib.import_module(PKG + ".errors")
integrity = importlib.import_module(PKG + ".integrity")
mesh = importlib.import_module(PKG + ".mesh_logic")
resilience = importlib.import_module(PKG + ".resilience")
secret_refs = importlib.import_module(PKG + ".secret_refs")
service = importlib.import_module(PKG + ".service")
telemetry = importlib.import_module(PKG + ".telemetry")

KEYS = {
    "inv58/audit": b"A" * 32,
    "inv58/token": b"T" * 32,
    "inv58/artifact": b"R" * 32,
}


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


class KMS:
    """Test double for the key service; can be switched off."""

    def __init__(self):
        self.up = True
        self.keys = dict(KEYS)

    def __call__(self, name: str) -> bytes:
        if not self.up:
            raise ConnectionError("kms down")
        return self.keys[name]


def base_config(**over):
    doc = {
        "version": "1",
        "tenants": ["alpha", "beta"],
        "meshed_destinations": ["payments", "orders"],
        "spiffe_bindings": {
            "runtime:node/n1": {"actor_type": "node", "roles": ["mesh-node"], "tenants": ["alpha", "beta"]},
            "runtime:ns/alpha/sa/controller": {"actor_type": "controller", "roles": ["mesh-controller"]},
            "runtime:ns/beta/sa/controller": {"actor_type": "controller", "roles": ["mesh-controller"]},
        },
    }
    doc.update(over)
    return config.compose(doc)


NONCE = [0]


def token(clock: Clock, *, sub="alice", typ="operator", roles=("mesh-operator",), tenant=None, tenants=(),
          ttl=300, aud="inv58", key=KEYS["inv58/token"], iat=None, nonce=None):
    NONCE[0] += 1
    iat = int(clock()) if iat is None else iat
    claims = {"sub": sub, "typ": typ, "roles": list(roles), "aud": aud, "iat": iat, "exp": iat + ttl,
              "nonce": nonce or f"n{NONCE[0]}-{time.perf_counter_ns()}", "tenants": list(tenants)}
    if tenant:
        claims["tenant"] = tenant
    return {"token": authz.Authenticator.mint(key, claims)}


def san(path: str, td: str = "estate.local") -> dict:
    return {"san": f"spiffe://{td}/{path}"}


NODE = san("node/n1")
CTRL_A = san("ns/alpha/sa/controller")
CTRL_B = san("ns/beta/sa/controller")


def make_service(clock: Clock | None = None, kms: KMS | None = None, cfg=None, **kw):
    clock = clock or Clock()
    kms = kms or KMS()
    svc = service.MeshLayerService(resolver=secret_refs.SecretResolver({"kms": kms}), clock=clock, **kw)
    svc.bootstrap(cfg or base_config(), author="bootstrap@test", source="tests")
    return svc, clock, kms


def publisher(clock):
    return token(clock, sub="ci-bot", typ="ci", roles=("config-publisher",))


def operator(clock, **kw):
    return token(clock, sub="op", typ="operator", roles=("mesh-operator",), tenants=("alpha", "beta"), **kw)


def auditor(clock):
    return token(clock, sub="aud", typ="auditor", roles=("security-auditor",), tenants=("alpha", "beta"))
