"""INV-39 - Process sandbox tier.

5.1.0 adds the production enforcement path (``runtime.SandboxService`` over the
native Linux launcher in ``linux/``).  The dependency-free policy model is always
importable; ``pk_core`` integration is exposed when that framework is installed.
"""
from __future__ import annotations

__version__ = "5.1.0"

from .sandbox import (
    FORBIDDEN_CAPABILITIES,
    REQUIRED_NAMESPACES,
    SYSCALL_BUDGET,
    ProfileInvalid,
    ProfileNotApplied,
    Sandbox,
    SandboxProfile,
    SandboxStateError,
)

try:
    from .component import COMPONENT, ProcessSandboxTierComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as exc:
    if not (exc.name and (exc.name == "pk_core" or exc.name.startswith("pk_core."))):
        raise
    _PK_CORE_IMPORT_ERROR = exc
    COMPONENT = None
    ProcessSandboxTierComponent = None
    ELEMENT_ID = "INV-39"
    ELEMENT_NAME = "Process sandbox tier"

    def build_contract():
        raise RuntimeError("pk_core is required to build the INV-39 integration contract") from _PK_CORE_IMPORT_ERROR


from .errors import ERROR_CODES, OUTCOMES, SandboxError

__all__ = [
    "ERROR_CODES",
    "OUTCOMES",
    "SandboxError",
    "__version__",
    "COMPONENT",
    "ProcessSandboxTierComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "FORBIDDEN_CAPABILITIES",
    "REQUIRED_NAMESPACES",
    "SYSCALL_BUDGET",
    "ProfileInvalid",
    "ProfileNotApplied",
    "Sandbox",
    "SandboxProfile",
    "SandboxStateError",
]
