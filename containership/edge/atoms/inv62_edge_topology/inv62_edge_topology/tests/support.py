"""Shared fixtures for the INV-62 production test suites (stdlib only)."""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from inv62_edge_topology.production import config as cfgmod  # noqa: E402
from inv62_edge_topology.production.client import Client  # noqa: E402
from inv62_edge_topology.production.service import TopologyService  # noqa: E402

TENANT = "tenant-a"
OTHER = "tenant-b"

SECRETS = {
    "secret://keys/k1": b"k1" * 20,
    "secret://keys/k2": b"k2" * 20,
    "secret://audit": b"au" * 20,
    "secret://state": b"st" * 20,
    "secret://cfgsign": b"cs" * 20,
}


class FakeClock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, s: float) -> None:
        self.t += s


def base_config(**over) -> dict:
    doc = {
        "schema_version": 1,
        "environment": "test",
        "cloud_node": "cloud",
        "secrets": {"token_keys": {"k1": "secret://keys/k1"}, "active_token_key": "k1", "audit_key": "secret://audit",
                    "state_key": "secret://state"},
        "security": {"audit_fsync": False},
        "admission": {"rate_per_s": 100000.0, "burst": 100000, "max_in_flight": 1000},
    }
    return cfgmod.deep_merge(cfgmod.compose(doc), over)


def make_service(state_dir=None, clock=None, **over) -> TopologyService:
    clock = clock or FakeClock()
    svc = TopologyService(cfgmod.StaticSecretProvider(SECRETS), state_dir=state_dir, clock=clock, mono=clock)
    svc.activate_config(base_config(**over), author="test", source="unit", expected_generation=None)
    return svc


def client(svc: TopologyService, role: str, tenant: str = TENANT, node: str | None = None, sleep=None) -> Client:
    return Client(svc.handle, tenant, lambda: svc.authn.issue(f"{role}-{node or 'x'}", role, [tenant], node=node),
                  sleep=sleep or (lambda s: None))


ESTATE = [
    {"kind": "add_node", "node": "cloud", "tier": "cloud", "caps": ["control", "gpu"], "residency": "eu"},
    {"kind": "add_node", "node": "r1", "tier": "region", "parent": "cloud", "residency": "eu"},
    {"kind": "add_node", "node": "s1-gw", "tier": "site", "site": "s1", "parent": "r1", "caps": ["cache", "coordinator"], "residency": "eu"},
    {"kind": "add_node", "node": "s1-gw2", "tier": "site", "site": "s1", "parent": "r1", "caps": ["coordinator"], "residency": "eu"},
    {"kind": "add_node", "node": "s1-d1", "tier": "device", "site": "s1", "parent": "s1-gw", "residency": "eu"},
    {"kind": "add_node", "node": "s1-d2", "tier": "device", "site": "s1", "parent": "s1-gw", "caps": ["gpu"], "residency": "eu"},
    {"kind": "connect", "a": "cloud", "b": "r1", "latency_ms": 20},
    {"kind": "connect", "a": "r1", "b": "s1-gw", "latency_ms": 60},
    {"kind": "connect", "a": "r1", "b": "s1-gw2", "latency_ms": 70},
    {"kind": "connect", "a": "s1-gw", "b": "s1-gw2", "latency_ms": 1},
    {"kind": "connect", "a": "s1-gw", "b": "s1-d1", "latency_ms": 2},
    {"kind": "connect", "a": "s1-gw", "b": "s1-d2", "latency_ms": 3},
]


def seeded(state_dir=None, clock=None, **over):
    svc = make_service(state_dir, clock, **over)
    feed = client(svc, "topology-feed")
    feed.apply(ESTATE)
    return svc, feed
