"""INV-11 - Interface contract language.

The structural model is dependency-free.  The ``pk_core``-backed component and
contract are imported lazily so compatibility tooling can operate without the
estate runtime being installed.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .interface_model import (
    ADDITIVE,
    BREAKING,
    COMPATIBLE,
    Func,
    Incompatible,
    Interface,
    check_link,
    classify,
)
from .metadata import ELEMENT_ID, ELEMENT_NAME


def __getattr__(name: str) -> object:
    if name in {"COMPONENT", "InterfaceContractLanguageComponent"}:
        from .component import COMPONENT, InterfaceContractLanguageComponent

        return {
            "COMPONENT": COMPONENT,
            "InterfaceContractLanguageComponent": InterfaceContractLanguageComponent,
        }[name]
    if name == "build_contract":
        from .contract import build

        return build
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "ADDITIVE",
    "COMPATIBLE",
    "BREAKING",
    "Func",
    "Interface",
    "Incompatible",
    "classify",
    "check_link",
    "COMPONENT",
    "InterfaceContractLanguageComponent",
    "build_contract",
]
