"""Runtime compatibility test-matrix generation (component 34).

Reads the supported-version manifest and derives the required cells:
full cartesian coverage across *high*-criticality dimensions, pairwise
coverage (greedy all-pairs) for the rest. Every cell starts as a visible
coverage gap until fresh evidence exists (MC-34-06, MC-34-09).
"""
from __future__ import annotations

import itertools
import json


def load_manifest(path: str) -> dict:
    return json.load(open(path))


def generate(manifest: dict) -> list:
    dims = manifest["matrix_dimensions"]
    high = sorted(k for k, v in dims.items() if v["criticality"] == "high")
    low = sorted(k for k, v in dims.items() if v["criticality"] != "high")
    base = [dict(zip(high, combo)) for combo in itertools.product(*(dims[k]["values"] for k in high))]
    if not low:
        return base
    # pairwise over low dims, cycled across the high-criticality base cells
    pairs_needed = {(a, va, b, vb) for a, b in itertools.combinations(low, 2)
                    for va in dims[a]["values"] for vb in dims[b]["values"]}
    low_rows = []
    for combo in itertools.product(*(dims[k]["values"] for k in low)):
        row = dict(zip(low, combo))
        covers = {(a, row[a], b, row[b]) for a, b in itertools.combinations(low, 2)}
        if covers & pairs_needed or not low_rows:
            low_rows.append(row)
            pairs_needed -= covers
        if not pairs_needed:
            break
    if len(low) == 1:
        low_rows = [{low[0]: v} for v in dims[low[0]]["values"]]
    return [{**b, **low_rows[i % len(low_rows)]} for i, b in enumerate(base)] + \
           [{**base[0], **r} for r in low_rows[1:]]


def coverage(cells: list, tested: set) -> dict:
    keys = [json.dumps(c, sort_keys=True) for c in cells]
    gaps = [c for c, k in zip(cells, keys) if k not in tested]
    return {"cells": len(cells), "tested": len(cells) - len(gaps), "gaps": gaps,
            "ratio": round((len(cells) - len(gaps)) / len(cells), 4) if cells else 1.0}
