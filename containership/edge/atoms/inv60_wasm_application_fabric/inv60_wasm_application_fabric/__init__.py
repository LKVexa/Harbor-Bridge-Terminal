"""INV-60 - Wasm application fabric (master-applied component)."""

__version__ = "4.3.0"
from .component import COMPONENT, WasmApplicationFabricComponent
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
from .runtime import Lattice

__all__ = ["__version__", "COMPONENT", "WasmApplicationFabricComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract", "Lattice"]
