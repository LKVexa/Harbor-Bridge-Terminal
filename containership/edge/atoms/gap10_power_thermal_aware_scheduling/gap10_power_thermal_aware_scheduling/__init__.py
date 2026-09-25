"""GAP-10 - Power/thermal-aware scheduling (master-applied component)."""

__version__ = "4.3.0"

try:  # the pk_core estate is optional; the kernel and production layer are stdlib-only
    from .component import COMPONENT, PowerThermalAwareSchedulingComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if _exc.name != "pk_core" and not str(_exc.name or "").startswith("pk_core"):
        raise
    COMPONENT = PowerThermalAwareSchedulingComponent = build_contract = None
    ELEMENT_ID, ELEMENT_NAME = "GAP-10", "Power/thermal-aware scheduling"
from .model import DEFAULT_POLICY, PolicyError, PowerThermalPolicy, ThermalState

__all__ = [
    "__version__",
    "COMPONENT",
    "PowerThermalAwareSchedulingComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "DEFAULT_POLICY",
    "PolicyError",
    "PowerThermalPolicy",
    "ThermalState",
]
