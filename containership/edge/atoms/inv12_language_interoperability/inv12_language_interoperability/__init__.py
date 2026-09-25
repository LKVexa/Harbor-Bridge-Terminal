"""INV-12 - Language interoperability (master-applied component).

The ``canon`` sub-package (the canonical interop engine) is stdlib-only.  The
``pk_core``-bound component, contract and legacy reference API are imported
lazily, so ``import inv12_language_interoperability.canon`` works even where the
parent framework is absent; accessing ``COMPONENT`` and friends still requires
``pk_core`` exactly as in 4.2.0.
"""

__version__ = "4.3.0"

_COMPONENT_NAMES = (
    "COMPONENT", "CANONICAL_TYPES", "LANGUAGE_TYPES", "SUPPORTED_LANGUAGES", "CanonicalValue",
    "CanonicalizationError", "LanguageInteroperabilityComponent", "OutOfRange", "OwnershipError",
    "Unrepresentable", "check_mapping", "lift", "lower",
)
_CONTRACT_NAMES = {"ELEMENT_ID": "ELEMENT_ID", "ELEMENT_NAME": "ELEMENT_NAME", "build_contract": "build"}

__all__ = ["__version__", *_COMPONENT_NAMES, *_CONTRACT_NAMES]


def __getattr__(name):
    if name in _COMPONENT_NAMES:
        from . import component
        return getattr(component, name)
    if name in _CONTRACT_NAMES:
        from . import contract
        return getattr(contract, _CONTRACT_NAMES[name])
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
