"""Schema compatibility checker (MC-05 / MC-28): compare current schemas to a released baseline.

Breaking (requires a new major schema id): removing a property, adding a required field,
changing a type/const/pattern, narrowing an enum, or tightening a numeric/length bound.
Non-breaking: new optional property, widened bound, widened enum, doc changes.
Exit 1 when any breaking change is found for an unchanged schema id."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]


def compare(old: dict, new: dict) -> list[str]:
    out = []
    if old.get("$id") != new.get("$id"):
        return []  # new major id: anything goes
    op, np_ = old["properties"], new["properties"]
    for k in op:
        if k not in np_:
            out.append(f"removed property {k}")
            continue
        a, b = op[k], np_[k]
        for key in ("type", "const", "pattern"):
            if a.get(key) != b.get(key):
                out.append(f"{k}: {key} changed")
        if "enum" in a and not set(a["enum"]) <= set(b.get("enum", a["enum"])):
            out.append(f"{k}: enum narrowed")
        for lo in ("minimum", "exclusiveMinimum", "minLength"):
            if lo in b and (lo not in a or b[lo] > a[lo]):
                out.append(f"{k}: {lo} tightened")
        for hi in ("maximum", "exclusiveMaximum", "maxLength"):
            if hi in b and (hi not in a or b[hi] < a[hi]):
                out.append(f"{k}: {hi} tightened")
    for r in set(new["required"]) - set(old["required"]):
        out.append(f"new required field {r}")
    if old.get("additionalProperties") is True and new.get("additionalProperties") is False:
        out.append("additionalProperties closed")
    return out


def check(baseline: pathlib.Path, current: pathlib.Path) -> dict:
    res = {}
    for f in sorted(baseline.glob("*.json")):
        cur = current / f.name
        if not cur.exists():
            res[f.name] = ["schema file removed"]
            continue
        res[f.name] = compare(json.loads(f.read_text()), json.loads(cur.read_text()))
    return res


def main() -> int:
    res = check(ROOT / "compatibility" / "baseline-4.2.0", ROOT / "schemas")
    print(json.dumps(res, indent=1))
    return 1 if any(res.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
