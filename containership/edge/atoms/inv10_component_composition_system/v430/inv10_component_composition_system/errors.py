"""Stable machine-readable error categories for INV-10 service layers (MC-01..MC-50).

All service-layer errors derive from :class:`CompositionError` so callers
handle one hierarchy. Codes are part of the public contract; never rename.
"""
from __future__ import annotations

from .composition import CompositionError


class DependencyUnavailable(CompositionError):
    code = "DEPENDENCY_UNAVAILABLE"


class DependencyIncompatible(CompositionError):
    code = "DEPENDENCY_INCOMPATIBLE"


class SchemaViolation(CompositionError):
    code = "SCHEMA_VIOLATION"


class PolicyRejected(CompositionError):
    code = "POLICY_REJECTED"


class Unauthenticated(CompositionError):
    code = "UNAUTHENTICATED"


class ProvenanceRejected(CompositionError):
    code = "PROVENANCE_REJECTED"


class ValidationRequired(CompositionError):
    code = "VALIDATION_REQUIRED"


class InterfaceIncompatible(CompositionError):
    code = "INTERFACE_INCOMPATIBLE"


class BoundaryViolation(CompositionError):
    code = "BOUNDARY_VIOLATION"


class ExternalUnavailable(CompositionError):
    code = "EXTERNAL_UNAVAILABLE"


class NotFound(CompositionError):
    code = "NOT_FOUND"


class Conflict(CompositionError):
    code = "CONFLICT"


class IntegrityError(CompositionError):
    code = "INTEGRITY_ERROR"


class Overloaded(CompositionError):
    code = "OVERLOADED"


class Frozen(CompositionError):
    code = "FROZEN"


class Quarantined(CompositionError):
    code = "QUARANTINED"


class WitParseError(CompositionError):
    code = "WIT_PARSE_ERROR"


ERROR_CODES = sorted(
    {c.code for c in CompositionError.__subclasses__()}
    | {"COMPOSITION_ERROR", "INVALID_COMPOSITION", "UNSATISFIED_IMPORT", "AMBIGUOUS_EXPORT",
       "COMPOSITION_CYCLE", "RESOURCE_LIMIT_EXCEEDED"}
)
