"""INV-12 canonical interop engine (stdlib only; no pk_core dependency).

Sub-modules map one-to-one onto the missing-components checklist; see
``docs/TRACEABILITY.md``.
"""
from .errors import ENVELOPE_SCHEMA, ERROR_CODES, InteropError
from .types import Interface, load, load_interface, parse_type, type_hash
from .values import Err, Ok, Some, Variant
from .validate import validate
from .layout import alignment, decode, encode, flatten, flatten_signature, size
from .registry import PROFILE_DIGEST, PROFILE_ID, PROFILE_VERSION, REGISTRY

ENGINE_VERSION = "4.3.0"

__all__ = [
    "ENGINE_VERSION", "ENVELOPE_SCHEMA", "ERROR_CODES", "InteropError", "Interface", "load",
    "load_interface", "parse_type", "type_hash", "Err", "Ok", "Some", "Variant", "validate",
    "alignment", "decode", "encode", "flatten", "flatten_signature", "size", "PROFILE_DIGEST",
    "PROFILE_ID", "PROFILE_VERSION", "REGISTRY",
]
