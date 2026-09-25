"""INV-61 - Distributed WIT RPC (master-applied component)."""

__version__ = "4.3.0"
from .component import COMPONENT, DistributedWitRpcComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["__version__", "COMPONENT", "DistributedWitRpcComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
