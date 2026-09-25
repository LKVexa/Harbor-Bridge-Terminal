"""INV-54 - Broker implementations (master-applied component)."""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-54"
ELEMENT_NAME = "Broker implementations"

from .brokers import FanoutBroker, PartitionedLog
from .errors import BrokerError, Outcome


def build_contract():
    """Build the pk_core contract lazily so broker primitives remain standalone."""
    from .contract import build

    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "BrokerImplementationsComponent"}:
        from .component import COMPONENT, BrokerImplementationsComponent

        return {"COMPONENT": COMPONENT, "BrokerImplementationsComponent": BrokerImplementationsComponent}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "BrokerImplementationsComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "FanoutBroker",
    "PartitionedLog",
    "build_contract",
    "BrokerError",
    "Outcome",
]
