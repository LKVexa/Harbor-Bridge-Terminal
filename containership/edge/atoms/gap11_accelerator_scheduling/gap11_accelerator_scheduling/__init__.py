"""GAP-11 - Accelerator scheduling (master-applied component)."""

__version__ = "4.2.0"
from .component import COMPONENT, AcceleratorSchedulingComponent
from .allocator import Accelerator, AcceleratorPool, AllocationLease, PartitionSpec
from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract

__all__ = ["__version__", "COMPONENT", "AcceleratorSchedulingComponent", "Accelerator", "AcceleratorPool", "AllocationLease", "PartitionSpec", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
