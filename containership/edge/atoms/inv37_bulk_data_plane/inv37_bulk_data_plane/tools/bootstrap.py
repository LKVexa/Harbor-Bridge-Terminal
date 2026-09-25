"""Deterministic bootstrap: empty node -> healthy INV-37 (C040).  Exit codes:
0 healthy, 2 fatal preflight, 3 activation/health failure."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))


def main(argv=None) -> int:
    pkg = __import__(HERE.name)
    C, S = pkg.config, pkg.security
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--site")
    ap.add_argument("--env")
    ap.add_argument("--node")
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--author", default="bootstrap")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    caps = pkg.shm_transport.probe()
    layers = [("profile", C.load_file(a.profile, layer="profile"))]
    for name in ("site", "env", "node"):
        if getattr(a, name):
            layers.append((name, C.load_file(getattr(a, name), layer=name)))
    layers.append(("bootstrap", C.load_layer({"security": {"key_file": a.key_file},
                                              "checkpoint": {"directory": a.state_dir}}, layer="bootstrap")))
    mgr = C.ConfigManager(probe=caps, history_path=Path(a.state_dir) / "config-history.json")
    cand = mgr.build(layers, author=a.author, source=a.profile)
    out = {"digest": cand.digest, "findings": [vars(f) for f in cand.findings], "effective": C.redacted(cand.effective),
           "capabilities": caps}
    if not cand.admission_allowed:
        print(json.dumps({"status": "fatal", **out}, indent=1, default=str))
        return 2
    if a.dry_run:
        print(json.dumps({"status": "dry_run_ok", **out}, indent=1, default=str))
        return 0
    ring = S.KeyRing.from_file(a.key_file)
    holder = {}

    def health_check(cfg):
        dp = pkg.BulkDataPlane(cfg, keyring=ring, caps=caps)
        dp.recover()
        holder["dp"] = dp
        return dp.health()["ready"]

    try:
        mgr.activate(cand, health_check=health_check)
    except pkg.BulkDataPlaneError as exc:
        print(json.dumps({"status": "activation_failed", "error": exc.as_dict(), **out}, indent=1, default=str))
        return 3
    print(json.dumps({"status": "healthy", "health": holder["dp"].health(), **out}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
