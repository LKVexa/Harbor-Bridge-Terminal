"""Small dependency-free GAP-02 smoke test."""
from __future__ import annotations

import json

from . import __version__, discover


def main() -> int:
    inventory, report = discover("gap02-selftest", 1)
    result = {
        "version": __version__,
        "inventory_schema": inventory.to_dict()["schema"],
        "report": report.for_consumer(1),
        "diagnostics": report.diagnostics,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
