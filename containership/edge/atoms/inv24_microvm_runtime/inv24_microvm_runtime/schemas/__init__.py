"""Typed external schemas (MC-013) and a dependency-free validator."""
from .validator import load_schema, validate, SCHEMA_FILES

__all__ = ["load_schema", "validate", "SCHEMA_FILES"]
