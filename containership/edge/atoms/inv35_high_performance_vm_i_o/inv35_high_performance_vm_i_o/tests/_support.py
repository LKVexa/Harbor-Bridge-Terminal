"""Shared fixtures for the v4.3.0 suites (no external dependencies)."""
from __future__ import annotations

import importlib
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(PKG_DIR.parent) not in sys.path:
    sys.path.insert(0, str(PKG_DIR.parent))

pkg = importlib.import_module(PKG_DIR.name)
rt = importlib.import_module(PKG_DIR.name + ".runtime")
errors = importlib.import_module(PKG_DIR.name + ".runtime.errors")
config = importlib.import_module(PKG_DIR.name + ".runtime.config")
lifecycle = importlib.import_module(PKG_DIR.name + ".runtime.lifecycle")
security = importlib.import_module(PKG_DIR.name + ".runtime.security")
policy = importlib.import_module(PKG_DIR.name + ".runtime.policy")
telemetry = importlib.import_module(PKG_DIR.name + ".runtime.telemetry")
health = importlib.import_module(PKG_DIR.name + ".runtime.health")
release = importlib.import_module(PKG_DIR.name + ".runtime.release")
schema_check = importlib.import_module(PKG_DIR.name + ".runtime.schema_check")
wire = importlib.import_module(PKG_DIR.name + ".runtime.wire")

Descriptor, MemoryRegion, VirtQueue = pkg.Descriptor, pkg.MemoryRegion, pkg.VirtQueue
Inv35Error, State, DegradedMode = rt.Inv35Error, rt.State, rt.DegradedMode

REGION = (MemoryRegion(0x10000, 0x10000),)
CTL = {"register_memory", "lifecycle", "configure", "quarantine", "read_status"}
BULK = {"submit", "complete"}


def schema(rel: str) -> dict:
    import json
    return json.loads((PKG_DIR / "schemas" / rel).read_text(encoding="utf-8"))


class FakeClock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def stack(tenant: str = "t1", queues: tuple[str, ...] = ("q0",), **cfg_env):
    """A runtime with registered queues plus control and bulk tokens."""
    r = rt.Runtime()
    if cfg_env:
        r.config.apply(*config.build(environment=cfg_env, source="test", author="test"))
        r._rebuild_policy()
    cp, dp = rt.ControlPlane(r), rt.Datapath(r)
    ctl = r.authority.mint("controller", tenant, set(queues), CTL)
    bulk = r.authority.mint("vmm", tenant, set(queues), BULK)
    for q in queues:
        cp.register_queue(ctl, tenant=tenant, queue=q, regions=REGION)
    return r, cp, dp, ctl, bulk


def one(i: int = 0, addr: int = 0x10000, length: int = 64, nxt=None):
    return {i: Descriptor(i, addr, length, nxt)}
