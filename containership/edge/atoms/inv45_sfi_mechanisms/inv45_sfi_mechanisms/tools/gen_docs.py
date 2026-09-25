"""Regenerate derived documents from their single sources of truth.

* docs/security/ERROR_CATALOG.md  <- production/errors.py registry
* schemas/ERROR_REGISTRY.pin      <- digest of (code, wire, category, retryable)

``--check`` exits 1 when a derived file is stale (used by CI); without it, files are written.
Changing the pin is a reviewed act: a code must never be reused for a new meaning.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from inv45_sfi_mechanisms.production import errors  # noqa: E402


def outputs() -> dict[Path, str]:
    rows = [[s.code, s.wire, s.category, s.retryable] for s in errors.REGISTRY.values()]
    pin = hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()
    return {ROOT / "docs/security/ERROR_CATALOG.md": errors.registry_markdown(),
            ROOT / "schemas/ERROR_REGISTRY.pin": pin + "\n"}


def main() -> int:
    check = "--check" in sys.argv
    stale = []
    for p, text in outputs().items():
        if check:
            if not p.exists() or p.read_text() != text:
                stale.append(str(p.relative_to(ROOT)))
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    if stale:
        print("stale derived files:", ", ".join(stale))
        return 1
    print("derived docs", "current" if check else "written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
