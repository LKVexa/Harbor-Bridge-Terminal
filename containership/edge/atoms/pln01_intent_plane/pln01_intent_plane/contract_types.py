"""Local, dependency-free contract types (MC-051).

When the ``pk_core`` monorepo package is installed its ``Contract``,
``Dependency`` and ``Slo`` types are used; otherwise these structurally
compatible stand-ins let the contract be built, serialized and tested
standalone.  They are not a re-implementation of pk_core's gate logic.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Dependency:
    element: str
    direction: str
    purpose: str
    required: bool = True


@dataclass(frozen=True)
class Slo:
    name: str
    objective: str
    error_budget: str


@dataclass(frozen=True)
class Contract:
    element: str
    name: str
    responsibility: str
    owns: list = field(default_factory=list)
    not_owns: list = field(default_factory=list)
    dependencies: list = field(default_factory=list)
    source_of_truth: str = ""
    assumptions: list = field(default_factory=list)
    boundaries: dict = field(default_factory=dict)
    mandatory: list = field(default_factory=list)
    optional: list = field(default_factory=list)
    non_goals: list = field(default_factory=list)
    interfaces: dict = field(default_factory=dict)
    threats: list = field(default_factory=list)
    failure_modes: list = field(default_factory=list)
    slos: list = field(default_factory=list)
    signals: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
