"""INV-64 - Application model.

The untrusted-input manifest API is intentionally importable without the
external ``pk_core`` integration framework. Integration objects are loaded only
when their names are requested.
"""
from __future__ import annotations

from importlib import import_module

__version__ = "4.3.0"

from .manifest import (
    DuplicateKeyError,
    ManifestDepthError,
    ManifestTooLargeError,
    ManifestValidationError,
    ValidationIssue,
    canonical,
    canonical_document,
    parse_manifest_json,
    validate,
    validate_issues,
)

_INTEGRATION_EXPORTS = {
    "COMPONENT",
    "ApplicationModelComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
}


def __getattr__(name: str):
    if name not in _INTEGRATION_EXPORTS:
        raise AttributeError(name)
    try:
        if name in {"COMPONENT", "ApplicationModelComponent"}:
            module = import_module(".component", __name__)
            value = getattr(module, name)
        else:
            module = import_module(".contract", __name__)
            mapping = {
                "ELEMENT_ID": "ELEMENT_ID",
                "ELEMENT_NAME": "ELEMENT_NAME",
                "build_contract": "build",
            }
            value = getattr(module, mapping[name])
    except ModuleNotFoundError as exc:
        if exc.name == "pk_core" or (exc.name and exc.name.startswith("pk_core.")):
            raise ModuleNotFoundError(
                f"{name} requires the external pk_core integration dependency; "
                "set PK_CORE_PATH or make pk_core importable"
            ) from exc
        raise
    globals()[name] = value
    return value


__all__ = [
    "__version__",
    "COMPONENT",
    "ApplicationModelComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "DuplicateKeyError",
    "ManifestDepthError",
    "ManifestTooLargeError",
    "ManifestValidationError",
    "ValidationIssue",
    "validate",
    "validate_issues",
    "parse_manifest_json",
    "canonical",
    "canonical_document",
]
