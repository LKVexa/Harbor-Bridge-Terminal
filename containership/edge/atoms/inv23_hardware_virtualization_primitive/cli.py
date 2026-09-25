"""``inv23-probe``: print the host probe report / claim diagnostics as JSON."""

from __future__ import annotations

import argparse
import json
import sys

from .probe import Prober
from .schema import validate_probe_report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="inv23-probe")
    ap.add_argument("--status", action="store_true", help="also print claim-provider status (no secrets)")
    a = ap.parse_args(argv)
    p = Prober(cache_ttl_s=0)
    r = p.probe()
    rep = validate_probe_report(r.to_report())
    out = {"probe": rep, "diagnostics": {"last_success": p.telemetry.last_success, "last_failure_reason": p.telemetry.last_failure_reason}}
    if a.status:
        from .ownership import default_provider

        out["ownership"] = default_provider().status()
    json.dump(out, sys.stdout, indent=1)
    print()
    return 0 if r.state == "usable" else 3


if __name__ == "__main__":
    sys.exit(main())
