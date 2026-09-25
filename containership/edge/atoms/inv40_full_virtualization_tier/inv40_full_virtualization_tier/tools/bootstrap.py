"""Deterministic day-0 bootstrap: empty node -> validated config -> probe -> health (INV-40-C040)."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
from fvt import identity  # noqa: E402
from fvt.provider import FakeProvider, QemuKvmProvider  # noqa: E402
from fvt.service import FullVmService  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--site", default="unassigned-site")
    ap.add_argument("--env", default="dev", choices=["dev", "test", "staging", "prod"])
    ap.add_argument("--config", help="site/env overlay JSON")
    ap.add_argument("--fake-provider", action="store_true", help="non-production test lane")
    a = ap.parse_args(argv)
    overlay = json.loads(pathlib.Path(a.config).read_text()) if a.config else {}
    overlay.update({"site": a.site, "environment": a.env})
    prov = FakeProvider() if a.fake_provider else QemuKvmProvider()
    # keys are supplied by the KMS binding in production; bootstrap only needs the health path
    svc = FullVmService(provider=prov, keys=identity.KeyProvider({}), state_dir=a.state_dir, config=overlay)
    h = svc.health()
    print(json.dumps(h, indent=1, sort_keys=True))
    return 0 if h["ready"] else 3


if __name__ == "__main__":
    sys.exit(main())
