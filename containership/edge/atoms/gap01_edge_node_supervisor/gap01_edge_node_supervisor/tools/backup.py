"""Scheduled backup with retention (38): python -m ...tools.backup STATE_DIR DEST_DIR [--keep N]
Verifies each archive restores to a loadable store before pruning old ones."""
from __future__ import annotations

import argparse
import datetime
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from gap01_edge_node_supervisor.store import StateStore  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("state_dir"); ap.add_argument("dest"); ap.add_argument("--keep", type=int, default=14)
    a = ap.parse_args(argv)
    dest = pathlib.Path(a.dest); dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arc = StateStore(a.state_dir, fsync=False).backup(dest / f"gap01-{stamp}.tgz")
    with tempfile.TemporaryDirectory() as t:  # prove restorability
        StateStore.restore(arc, t)
        StateStore(t, fsync=False).load()
    olds = sorted(dest.glob("gap01-*.tgz"))[:-a.keep]
    for o in olds:
        o.unlink()
    print(f"backup {arc.name} verified; pruned {len(olds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
