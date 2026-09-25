"""M01 - explicit pk_core compatibility probe.

INV-61's contract/component layer imports these symbols from ``pk_core``. The
package is NOT in the supplied archive and its canonical source, version and
digest are unknown (see docs/DEPENDENCIES.md, status BLOCKED). This probe makes
that failure explicit and uniform instead of three silently skipped tests.
"""
from __future__ import annotations

import importlib

REQUIRED_SYMBOLS = {
    "pk_core.contract": ("Contract", "Dependency", "Slo"),
    "pk_core.checklist": ("ChecklistItem", "Finding"),
    "pk_core.component": ("Component",),
}
# Unknown until the owner names the canonical source; see docs/DEPENDENCIES.md.
REQUIRED_VERSION = None
REQUIRED_SHA256 = None


class PkCoreUnavailable(RuntimeError):
    pass


def probe() -> dict:
    """Return {module: [missing symbols]} (empty dict == compatible). Never returns
    silently on a missing package: raises PkCoreUnavailable naming what is required."""
    missing = {}
    for mod, names in REQUIRED_SYMBOLS.items():
        try:
            m = importlib.import_module(mod)
        except ModuleNotFoundError:
            raise PkCoreUnavailable(
                "pk_core is required for the INV-61 contract/component layer "
                f"(needs {sorted(REQUIRED_SYMBOLS)}; pinned version: {REQUIRED_VERSION or 'UNPINNED - source unknown'})"
            ) from None
        gaps = [n for n in names if not hasattr(m, n)]
        if gaps:
            missing[mod] = gaps
    return missing
