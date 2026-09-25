"""INV-11 WIT front end and production subsystem (dependency-free, stdlib only).

Layers (dependency order):  limits -> diagnostics -> source -> lexer -> ast ->
parser -> resolve -> normalize/typegraph -> compat -> schema/fingerprint ->
lifecycle/operations modules.  Nothing here imports ``pk_core``.
"""
from __future__ import annotations

WIT_FEATURE_LEVEL = "wit-2024-10 (wasm-tools 1.219.x grammar subset, see docs/GRAMMAR.md)"
POLICY_VERSION = "INV11-COMPAT-POLICY/1"
NORMALIZATION_VERSION = "INV11-NORM/1"
SCHEMA_VERSION = "PK_INTERFACE/1+PK_INTERFACE_DIFF/1"
TOOL_VERSION = "4.3.0"
