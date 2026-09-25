"""INV-69 - Agentic workload layer.

The hardened runtime is importable with only the Python standard library.
Integration with ``pk_core`` is loaded lazily when conformance symbols are used.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .runtime import Agent, ToolSpec, TOOLS
from .errors import AgentError
from .governed import GovernedRuntime

__all__ = [
    "__version__",
    "Agent",
    "ToolSpec",
    "TOOLS",
    "AgentError",
    "GovernedRuntime",
    "COMPONENT",
    "AgenticWorkloadLayerComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]


def __getattr__(name: str):
    if name in {"COMPONENT", "AgenticWorkloadLayerComponent"}:
        try:
            from .component import COMPONENT, AgenticWorkloadLayerComponent
        except ModuleNotFoundError as exc:
            if exc.name == "pk_core" or (exc.name and exc.name.startswith("pk_core.")):
                raise RuntimeError(
                    "pk_core is required for the conformance component; "
                    "the standalone runtime remains available as inv69_agentic_workload_layer.Agent"
                ) from exc
            raise
        return {"COMPONENT": COMPONENT, "AgenticWorkloadLayerComponent": AgenticWorkloadLayerComponent}[name]

    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        try:
            from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
        except ModuleNotFoundError as exc:
            if exc.name == "pk_core" or (exc.name and exc.name.startswith("pk_core.")):
                raise RuntimeError("pk_core is required to build the INV-69 conformance contract") from exc
            raise
        return {
            "ELEMENT_ID": ELEMENT_ID,
            "ELEMENT_NAME": ELEMENT_NAME,
            "build_contract": build_contract,
        }[name]
    raise AttributeError(name)
