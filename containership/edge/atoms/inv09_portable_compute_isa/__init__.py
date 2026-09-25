"""INV-09 - Portable compute ISA (master-applied component)."""

__version__ = "4.3.0"

try:  # pk_core is a workspace dependency (M45); the prod/ boundary does not need it
    from .component import COMPONENT, PortableComputeIsaComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on workspace layout
    if _exc.name != "pk_core" and not str(_exc.name).startswith("pk_core."):
        raise
    COMPONENT = PortableComputeIsaComponent = build_contract = None  # type: ignore[assignment]
    ELEMENT_ID, ELEMENT_NAME = "INV-09", "Portable compute ISA"

__all__ = ["__version__", "COMPONENT", "PortableComputeIsaComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
