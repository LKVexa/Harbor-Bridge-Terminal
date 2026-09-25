"""M52 - formal production exit gate (PK_PRODUCTION_GATE/1).

Deterministic function of: the release digest, evidence/*.json (each must be
bound to that digest), the per-item checklist status, the waiver register and
OWNERS.yaml.  Missing, stale or corrupt evidence is BLOCKED, never an implicit
pass.  There is no override parameter.

Verdict: GO only if every mandatory control PASSes; CONDITIONAL_GO if the only
non-PASS controls are covered by valid, unexpired, in-scope waivers;
otherwise NO_GO.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
from typing import Any

from .waivers import Waiver

REQUIRED_EVIDENCE = ("tests", "fuzz_campaign", "perf_gate", "benchmark", "soak", "static_scan", "sbom.cdx",
                     "build_metadata", "coverage")


def _load(ev: pathlib.Path, name: str, release: str) -> tuple[str, Any]:
    p = ev / f"{name}.json"
    if not p.exists():
        return "BLOCKED", f"missing evidence/{name}.json"
    try:
        doc = json.loads(p.read_text())
    except ValueError:
        return "BLOCKED", f"corrupt evidence/{name}.json"
    if doc.get("release_digest") != release:
        return "BLOCKED", f"stale evidence/{name}.json (bound to another release)"
    return "OK", doc


def controls(ev: pathlib.Path, release: str) -> list[dict[str, Any]]:
    out = []

    def add(cid, status, detail):
        out.append({"control": cid, "status": status, "detail": detail})

    loaded = {}
    for name in REQUIRED_EVIDENCE:
        st, doc = _load(ev, name, release)
        if st != "OK":
            add(f"evidence:{name}", "BLOCKED", doc)
        else:
            loaded[name] = doc
    if "tests" in loaded:
        runs = loaded["tests"]["runs"]
        ok = all(r["returncode"] == 0 for r in runs) and len(runs) == 2
        add("tests:normal+optimized", "PASS" if ok else "FAIL", [r["summary"] for r in runs])
    if "fuzz_campaign" in loaded:
        f = loaded["fuzz_campaign"]
        d = f.get("differential", {})
        add("fuzz:no-crash", "PASS" if f["crashes"] == 0 and f["nondeterministic"] == 0 and f["executions"] > 0
            else "FAIL", f"{f['executions']} execs, {f['crashes']} crashes")
        add("differential:no-false-accept", "PASS" if d.get("total", 0) > 0 and d.get("critical", 1) == 0 else
            ("BLOCKED" if not d.get("total") else "FAIL"), f"{d.get('total', 0)} compared, {d.get('critical')} false accepts")
        add("differential:false-reject-dispositioned",
            "PASS" if d.get("disagreements", {}).get("FALSE_REJECT", 0) == 0 else "FAIL", d.get("disagreements"))
        add("differential:two-references", "FAIL", "only one independent reference implementation (M15-007)")
    if "perf_gate" in loaded:
        add("perf:M30", "PASS" if loaded["perf_gate"]["verdict"] == "PASS" else "FAIL",
            loaded["perf_gate"].get("breaches"))
    if "static_scan" in loaded:
        add("static:no-high", "PASS" if loaded["static_scan"]["high"] == 0 else "FAIL",
            f"{loaded['static_scan']['high']} high findings")
    if "soak" in loaded:
        s = loaded["soak"]
        add("soak:single-process", "PASS" if s["health"] == "ready" else "FAIL", f"{s['validations']} validations")
        add("soak:fleet-scale(M31)", "BLOCKED", "fleet-scale soak not executed")
    return out


def owners_complete(path: pathlib.Path) -> bool:
    return path.exists() and "TBD" not in path.read_text()


def evaluate(root: pathlib.Path, release: str, status_items: list[dict[str, Any]], waivers: list[Waiver],
             today: dt.date) -> dict[str, Any]:
    ctl = controls(root / "evidence", release)
    ctl.append({"control": "governance:owners(M50)", "status": "PASS" if owners_complete(root / "OWNERS.yaml")
                else "BLOCKED", "detail": "OWNERS.yaml"})
    active = [w for w in waivers if w.valid_on(today)]
    waived_items = {i for w in active for i in w.items}
    counts: dict[str, int] = {}
    blocking_items = []
    for it in status_items:
        st = it["status"]
        if st != "PASS" and it["id"] in waived_items:
            st = "WAIVED"
        counts[st] = counts.get(st, 0) + 1
        if st not in ("PASS", "WAIVED"):
            blocking_items.append(it["id"])
    ctl_bad = [c for c in ctl if c["status"] not in ("PASS", "WAIVED")]
    if not ctl_bad and not blocking_items:
        verdict = "CONDITIONAL_GO" if counts.get("WAIVED") else "GO"
    else:
        verdict = "NO_GO"
    return {"schema": "PK_PRODUCTION_GATE/1", "release": release, "verdict": verdict,
            "evaluated_on": today.isoformat(), "controls": ctl, "counts": dict(sorted(counts.items())),
            "active_waivers": [w.id for w in active],
            "blocking": {"controls": [c["control"] for c in ctl_bad], "items": len(blocking_items),
                         "p0_items": sum(1 for i in blocking_items if int(i[1:3]) <= 15)}}
