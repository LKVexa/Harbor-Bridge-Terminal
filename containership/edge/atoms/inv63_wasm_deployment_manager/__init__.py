"""INV-63 - Wasm deployment manager."""

__version__ = "4.3.0"

__all__ = [
    "__version__",
    "COMPONENT",
    "WasmDeploymentManagerComponent",
    "Manager",
    "DesiredState",
    "AuditEvent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "DeploymentService",
    "DeploymentError",
    "ErrorCode",
    "Outcome",
]


def __getattr__(name):
    """Load the inventory framework lazily.

    Core manager logic remains importable/testable without ``pk_core`` while
    preserving the package-level API when the framework is installed.
    """
    if name in {"Manager", "DesiredState", "AuditEvent"}:
        from .manager import AuditEvent, DesiredState, Manager
        return {"Manager": Manager, "DesiredState": DesiredState, "AuditEvent": AuditEvent}[name]
    if name == "DeploymentService":
        from .service import DeploymentService
        return DeploymentService
    if name in {"DeploymentError", "ErrorCode", "Outcome"}:
        from . import errors
        return getattr(errors, name)
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    if name in {"COMPONENT", "WasmDeploymentManagerComponent"}:
        from .component import COMPONENT, WasmDeploymentManagerComponent
        return {"COMPONENT": COMPONENT, "WasmDeploymentManagerComponent": WasmDeploymentManagerComponent}[name]
    raise AttributeError(name)
