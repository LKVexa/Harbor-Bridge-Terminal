"""Shared test helpers.  Tests tag the checklist items they evidence in the first line of
their docstring as ``items: MC01-002 MC01-012``; ``evidence/run_evidence.py`` collects
those tags together with each test's real pass/fail/skip result."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PKG = "gap05_state_replication_consistency_model"


def record_observation(item: str, data: dict) -> None:
    """Append a measured observation for the evidence runner (no-op outside it)."""
    import json
    import os
    path = os.environ.get("GAP05_OBSERVATIONS")
    if path:
        with open(path, "a") as fh:
            fh.write(json.dumps({"item": item, **data}) + "\n")
