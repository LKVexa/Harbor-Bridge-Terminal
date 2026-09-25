"""Load the audited v4.2.0 allocator by file path.

The parent package's ``__init__`` imports ``pk_core`` (absent from the supplied
archive), so the overlay never imports ``gap11_accelerator_scheduling`` itself; it
binds the byte-identical ``allocator.py`` beside it directly.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ALLOCATOR_PATH = Path(__file__).resolve().parents[1] / "allocator.py"
_NAME = "gap11_v420_allocator"
if _NAME in sys.modules:
    allocator = sys.modules[_NAME]
else:
    _spec = importlib.util.spec_from_file_location(_NAME, ALLOCATOR_PATH)
    if _spec is None or _spec.loader is None:  # pragma: no cover
        raise ImportError(f"cannot load {ALLOCATOR_PATH}")
    allocator = importlib.util.module_from_spec(_spec)
    sys.modules[_NAME] = allocator
    _spec.loader.exec_module(allocator)
