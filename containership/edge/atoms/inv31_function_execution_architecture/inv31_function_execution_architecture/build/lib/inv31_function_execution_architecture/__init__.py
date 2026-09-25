"""INV-31 - Function execution architecture (master-applied component)."""

__version__ = "4.3.0"

from .pkcompat import PK_CORE_STATUS, require_pk_core

if PK_CORE_STATUS["available"] and PK_CORE_STATUS["compatible"]:
    from .component import COMPONENT, FunctionExecutionArchitectureComponent
else:  # pk_core absent/incompatible: runtime + boundary stay usable, gate is refused
    COMPONENT = None
    FunctionExecutionArchitectureComponent = None
ELEMENT_ID = "INV-31"
ELEMENT_NAME = "Function execution architecture"


def build_contract():
    """Return the pk_core Contract; raises FrameworkUnavailable without pk_core."""
    require_pk_core()
    from .contract import build
    return build()


from .runtime import (
    CONCURRENCY_LIMIT,
    MAX_AGE,
    MAX_POOL_INSTANCES,
    ConcurrencyExceeded,
    FunctionPool,
    Instance,
    InstanceDestroyed,
    InstanceExpired,
    PoolCapacityExceeded,
)

__all__ = [
    "__version__",
    "PK_CORE_STATUS",
    "require_pk_core",
    "COMPONENT",
    "FunctionExecutionArchitectureComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "CONCURRENCY_LIMIT",
    "MAX_AGE",
    "MAX_POOL_INSTANCES",
    "ConcurrencyExceeded",
    "PoolCapacityExceeded",
    "InstanceDestroyed",
    "InstanceExpired",
    "Instance",
    "FunctionPool",
]
