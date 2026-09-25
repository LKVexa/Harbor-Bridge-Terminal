"""MC-29: typed adapter contracts for GAP-01 / GAP-02 / GAP-07 / PLN-07 / SCH-01.

These are the *interfaces* this subsystem calls or is called through, plus
in-memory reference peers used by contract tests.  Real peer services are not
in this archive, so integration against production-equivalent peers is BLOCKED.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class SupervisorPort(Protocol):          # GAP-01 (peer)
    def cordon(self, cmd: dict) -> bool: ...
    def may_report_ready(self, node: str) -> bool: ...


class CapabilityReportPort(Protocol):    # GAP-02 (downstream)
    def sign_capability_report(self, node: str, report: bytes) -> bytes: ...


class SigningPort(Protocol):             # GAP-07 (upstream)
    def trust_store_version(self) -> str: ...


class GrantPort(Protocol):               # PLN-07 (downstream)
    def may_grant(self, node: str) -> bool: ...


class PlacementPort(Protocol):           # SCH-01 (downstream)
    def exclude(self, cmd: dict) -> bool: ...
    def candidates(self, nodes: list) -> list: ...


@dataclass
class ReferencePeers:
    """One object implementing every peer port against a level lookup."""
    level_of: callable
    cordoned: set = field(default_factory=set)

    def cordon(self, cmd):
        self.cordoned.add(cmd["node"])
        return True

    def exclude(self, cmd):
        self.cordoned.add(cmd["node"])
        return True

    def may_report_ready(self, node):
        return node not in self.cordoned and self.level_of(node) != "untrusted"

    def may_grant(self, node):
        return self.may_report_ready(node)

    def candidates(self, nodes):
        return [n for n in nodes if self.may_report_ready(n)]

    def trust_store_version(self):
        return "anchors-v1"
