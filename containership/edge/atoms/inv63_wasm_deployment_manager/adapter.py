"""Lattice adapters: the downstream boundary to INV-60 / Wadm (INV-63-C021, C030, C031).

* :class:`LatticeAdapter` - the protocol the service depends on.
* :class:`InMemoryLattice` - conformance fixture with fault injection
  (start failures, partitions, latency) used by integration/fault tests.
* :class:`WadmAdapter` - renders desired state as a Wadm OAM application
  manifest (``core.oam.dev/v1beta1`` + ``spreadscaler`` trait) and hands it to an
  injected transport.  The transport (NATS / ``wash app deploy``) is NOT bundled:
  a live Wadm is an external, pinned dependency (see ``pins.json``); without it
  the adapter reports ``DEPENDENCY_UNAVAILABLE`` and the gate reports BLOCKED.
"""
from __future__ import annotations

import json
import pathlib
from collections import Counter
from typing import Any, Callable, Protocol

from .errors import DeploymentError, ErrorCode

Instance = tuple[str, str, str]
PINS = json.loads((pathlib.Path(__file__).resolve().parent / "pins.json").read_text())


class LatticeAdapter(Protocol):
    def ping(self) -> bool: ...
    def list_instances(self) -> list[Instance]: ...
    def start(self, inst: Instance) -> None: ...
    def stop(self, inst: Instance) -> None: ...
    def healthy(self, inst: Instance) -> bool: ...


class InMemoryLattice:
    def __init__(self, hosts: dict[str, str]):
        self.hosts = dict(hosts)
        self.running: list[Instance] = []
        self.fail_start: set[tuple[str, str]] = set()   # (component, version) that crash on start
        self.fail_hosts: set[str] = set()
        self.partitioned = False
        self.unhealthy_versions: set[tuple[str, str]] = set()
        self.calls: Counter[str] = Counter()

    def _net(self) -> None:
        if self.partitioned:
            raise DeploymentError(ErrorCode.CONTROL_PLANE_OFFLINE, "lattice unreachable")

    def ping(self) -> bool:
        self.calls["ping"] += 1
        return not self.partitioned

    def list_instances(self) -> list[Instance]:
        self._net()
        self.calls["list"] += 1
        return list(self.running)

    def start(self, inst: Instance) -> None:
        self._net()
        self.calls["start"] += 1
        if inst[2] not in self.hosts:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, f"unknown host {inst[2]}")
        if (inst[0], inst[1]) in self.fail_start or inst[2] in self.fail_hosts:
            raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"start failed for {inst}")
        self.running.append(inst)

    def stop(self, inst: Instance) -> None:
        self._net()
        self.calls["stop"] += 1
        if inst in self.running:
            self.running.remove(inst)

    def healthy(self, inst: Instance) -> bool:
        return inst in self.running and (inst[0], inst[1]) not in self.unhealthy_versions

    def capabilities(self) -> set[str]:
        return {"wasi-p2", "component-model"}


def wadm_manifest(tenant: str, component: str, version: str, count: int, image: str,
                  spread_labels: list[str] | None = None) -> dict[str, Any]:
    """Render a Wadm OAM manifest for one component (pinned spec in pins.json)."""
    spread = [{"name": f"{lbl}", "requirements": {"zone": lbl}, "weight": 100 // max(1, len(spread_labels or [1]))}
              for lbl in (spread_labels or [])]
    return {
        "apiVersion": PINS["wadm"]["oam_api_version"],
        "kind": "Application",
        "metadata": {"name": f"{tenant}-{component}".replace("/", "-")[:63],
                     "annotations": {"version": version, "inv63.tenant": tenant}},
        "spec": {"components": [{
            "name": component, "type": "component",
            "properties": {"image": image},
            "traits": [{"type": "spreadscaler", "properties": {"instances": count, "spread": spread}}],
        }]},
    }


class WadmAdapter:
    def __init__(self, transport: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None):
        self.transport = transport

    def _send(self, op: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.transport is None:
            raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE,
                                  f"no Wadm transport configured (pinned wadm {PINS['wadm']['version']})")
        return self.transport(op, payload)

    def ping(self) -> bool:
        try:
            return bool(self._send("ping", {}).get("ok"))
        except DeploymentError:
            return False

    def deploy(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return self._send("deploy", manifest)

    # LatticeAdapter protocol -------------------------------------------------
    def list_instances(self) -> list[Instance]:
        out = self._send("list", {}).get("instances", [])
        return [tuple(i) for i in out if isinstance(i, (list, tuple)) and len(i) == 3]

    def start(self, inst: Instance) -> None:
        r = self._send("start", {"component": inst[0], "version": inst[1], "host": inst[2]})
        if not r.get("ok"):
            raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"wadm start failed: {r.get('error', '?')}"[:200])

    def stop(self, inst: Instance) -> None:
        r = self._send("stop", {"component": inst[0], "version": inst[1], "host": inst[2]})
        if not r.get("ok"):
            raise DeploymentError(ErrorCode.DEPENDENCY_UNAVAILABLE, f"wadm stop failed: {r.get('error', '?')}"[:200])

    def healthy(self, inst: Instance) -> bool:
        try:
            return bool(self._send("health", {"component": inst[0], "version": inst[1], "host": inst[2]}).get("ok"))
        except DeploymentError:
            return False

    def capabilities(self) -> set[str]:
        try:
            return set(self._send("capabilities", {}).get("capabilities", []))
        except DeploymentError:
            return set()
