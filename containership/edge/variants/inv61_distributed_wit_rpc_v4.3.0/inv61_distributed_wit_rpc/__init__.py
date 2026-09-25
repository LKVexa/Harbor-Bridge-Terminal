"""INV-61 - Distributed WIT RPC.

The protocol runtime (rpc, codec, wit_model, negotiation, security, resilience,
config, observability, state, server, transport) is stdlib-only.  The
``pk_core`` inventory/gating integration (component.py, contract.py) is an
optional extra: it is imported lazily and fails with a clear, versioned error
when absent (M01) instead of breaking the protocol runtime.
"""

__version__ = "4.3.0"
PK_CORE_REQUIREMENT = "pk_core==4.0.*"  # pin recorded in pyproject.toml [project.optional-dependencies].gate

__all__ = ["__version__", "PK_CORE_REQUIREMENT", "COMPONENT", "DistributedWitRpcComponent",
           "ELEMENT_ID", "ELEMENT_NAME", "build_contract", "require_pk_core"]

ELEMENT_ID = "INV-61"
ELEMENT_NAME = "Distributed WIT RPC"


def require_pk_core():
    """Import pk_core or raise an actionable error naming the required pin."""
    try:
        import pk_core  # noqa: F401
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            f"INV-61 gate integration requires {PK_CORE_REQUIREMENT}; install the 'gate' extra "
            "or set PK_CORE_PATH. The protocol runtime does not need it.") from None
    for sym in ("contract.Contract", "contract.Dependency", "contract.Slo",
                "checklist.ChecklistItem", "checklist.Finding", "component.Component"):
        mod, name = sym.split(".")
        m = __import__(f"pk_core.{mod}", fromlist=[name])
        if not hasattr(m, name):
            raise ImportError(f"pk_core is missing required symbol {sym} (need {PK_CORE_REQUIREMENT})")
    return pk_core


def __getattr__(name):
    if name in ("COMPONENT", "DistributedWitRpcComponent"):
        require_pk_core()
        from . import component
        return getattr(component, name)
    if name == "build_contract":
        require_pk_core()
        from .contract import build
        return build
    raise AttributeError(name)
