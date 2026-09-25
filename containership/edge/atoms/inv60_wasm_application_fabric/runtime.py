"""Dependency-free reference runtime for INV-60.

This module intentionally has no ``pk_core`` dependency so the lattice's safety
properties can be unit-tested in isolation from the conformance framework.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable


class DigestMismatch(ValueError):
    """Stored artifact bytes do not match their content-addressed reference."""


class NotLinked(PermissionError):
    """A component attempted to use a capability without an active link."""


class UnknownArtifact(LookupError):
    """An artifact reference is not present in the registry."""


class AlreadyRunning(RuntimeError):
    """A component name is already bound to a running instance."""


class InvalidConfiguration(ValueError):
    """Runtime configuration violates a lattice invariant."""


def _name(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidConfiguration(f"{field_name} must be a non-empty string")
    return value


@dataclass
class Lattice:
    """Small deterministic model of a Wasm application fabric lattice.

    It models content-addressed artifacts, host membership, component placement,
    run-time capability links, routing and failover. Mutating operations validate
    all preconditions before changing state so rejected operations are atomic.
    """

    hosts: list[str]
    registry: dict[str, bytes] = field(default_factory=dict)  # ref -> immutable bytes
    instances: dict[str, str] = field(default_factory=dict)  # component -> host
    links: dict[tuple[str, str], Callable[..., Any]] = field(default_factory=dict)
    failovers: int = 0

    def __post_init__(self) -> None:
        # Copy caller-owned state and reject ambiguous membership.
        self.hosts = list(self.hosts)
        if any(not isinstance(h, str) or not h.strip() for h in self.hosts):
            raise InvalidConfiguration("hosts must contain only non-empty strings")
        if len(set(self.hosts)) != len(self.hosts):
            raise InvalidConfiguration("host names must be unique")
        self.registry = {str(ref): bytes(data) for ref, data in self.registry.items()}
        self.instances = dict(self.instances)
        self.links = dict(self.links)
        if self.failovers < 0:
            raise InvalidConfiguration("failovers cannot be negative")
        if any(host not in self.hosts for host in self.instances.values()):
            raise InvalidConfiguration("every instance must reference a live host")

    def add_host(self, host: str) -> None:
        host = _name(host, "host")
        if host in self.hosts:
            raise InvalidConfiguration(f"host {host!r} already exists")
        self.hosts.append(host)

    def push(self, data: bytes | bytearray | memoryview) -> str:
        if not isinstance(data, (bytes, bytearray, memoryview)):
            raise TypeError("artifact data must be bytes-like")
        immutable = bytes(data)
        ref = "sha256:" + hashlib.sha256(immutable).hexdigest()
        self.registry[ref] = immutable
        return ref

    def start(self, component: str, ref: str) -> str:
        component = _name(component, "component")
        ref = _name(ref, "ref")
        if component in self.instances:
            raise AlreadyRunning(f"{component!r} is already running on {self.instances[component]!r}")
        if ref not in self.registry:
            raise UnknownArtifact(f"{component}: no artifact {ref!r} in registry")
        if not self.hosts:
            raise LookupError(f"{component}: no hosts available")
        data = self.registry[ref]
        actual = "sha256:" + hashlib.sha256(data).hexdigest()
        if actual != ref:
            raise DigestMismatch(f"{component}: registry bytes do not match {ref[:19]}...")
        host = self.hosts[len(self.instances) % len(self.hosts)]
        self.instances[component] = host
        return host

    def stop(self, component: str) -> str:
        component = _name(component, "component")
        if component not in self.instances:
            raise LookupError(f"{component!r} not running")
        host = self.instances.pop(component)
        # Links are runtime authority; revoke them when the workload stops.
        for key in [key for key in self.links if key[0] == component]:
            del self.links[key]
        return host

    def link(self, component: str, name: str, provider: Callable[..., Any]) -> None:
        component = _name(component, "component")
        name = _name(name, "link name")
        if component not in self.instances:
            raise LookupError(f"{component!r} not running")
        if not callable(provider):
            raise TypeError("provider must be callable")
        self.links[(component, name)] = provider

    def unlink(self, component: str, name: str) -> None:
        component = _name(component, "component")
        name = _name(name, "link name")
        key = (component, name)
        if key not in self.links:
            raise NotLinked(f"{component} has no link {name!r}")
        del self.links[key]

    def call(self, component: str, name: str, *args: Any) -> Any:
        component = _name(component, "component")
        name = _name(name, "link name")
        host = self.instances.get(component)
        if host is None:
            raise LookupError(f"{component} not running")
        if host not in self.hosts:
            raise LookupError(f"{component} is assigned to unavailable host {host!r}")
        provider = self.links.get((component, name))
        if provider is None:
            raise NotLinked(f"{component} has no link {name!r}")
        return provider(*args)

    def lose_host(self, host: str) -> list[str]:
        host = _name(host, "host")
        if host not in self.hosts:
            raise LookupError(f"unknown host {host!r}")

        moved = [component for component, assigned in self.instances.items() if assigned == host]
        survivors = [candidate for candidate in self.hosts if candidate != host]
        if moved and not survivors:
            raise LookupError(f"losing {host!r} leaves no survivor to reschedule onto")

        # Commit only after every refusal condition has been checked.
        self.hosts = survivors
        for index, component in enumerate(moved):
            self.instances[component] = survivors[index % len(survivors)]
        self.failovers += len(moved)
        return moved
