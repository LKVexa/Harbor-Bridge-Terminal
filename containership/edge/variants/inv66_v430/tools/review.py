#!/usr/bin/env python3
"""Recurring review automation (MC-066): access, config, dependency, waiver and architecture review.

    python tools/review.py --config CONFIG.json [--today YYYY-MM-DD] [--out governance/reviews/<date>.json]

Every finding carries id, severity, subject, remediation and an empty ``disposition`` block the
reviewer fills (who, decision, ticket).  Exit 1 if any High/Critical finding is present.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from importlib import metadata

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inv66_enterprise_wasm_control_plane.rbac import ROLE_CAPABILITIES  # noqa: E402


def review(cfg: dict, today: dt.date) -> list[dict]:
    f = []
    now = int(dt.datetime.combine(today, dt.time()).timestamp())

    def add(sev, subj, msg, fix):
        f.append({"id": f"RV-{len(f)+1:03d}", "severity": sev, "subject": subj, "finding": msg, "remediation": fix,
                  "disposition": {"reviewer": None, "decision": None, "ticket": None}})
    subjects: dict[str, set] = {}
    for b in cfg.get("bindings", []):
        subjects.setdefault(b["subject"], set()).add(b["role"])
        exp = b.get("expires_at")
        if exp is not None and exp <= now:
            add("Medium", b["subject"], f"expired binding {b['role']} on {b['scope']} still configured", "remove it")
        elif exp is not None and exp - now < 14 * 86400:
            add("Low", b["subject"], f"binding {b['role']} on {b['scope']} expires within 14 days", "renew or let lapse")
        if b["effect"] == "allow" and b["scope"].count("/") == 0 and b["role"] in ("org-admin", "policy-admin"):
            add("Medium", b["subject"], f"organisation-wide {b['role']}", "confirm still required; prefer tenant scope")
        if b["subject"].startswith("user:") and b["role"] == "org-admin":
            add("Low", b["subject"], "human with org-admin (prefer group binding)", "bind via group")
    for s, roles in subjects.items():
        caps = set().union(*(ROLE_CAPABILITIES[r] for r in roles))
        if {"admit", "config.activate"} <= caps and not s.startswith("group:"):
            add("High", s, "separation of duties: can both change policy and deploy", "split roles or document exception in WAIVERS.json")
    if cfg.get("environment") == "prod" and not (set(cfg.get("approved_by", [])) - {cfg.get("author")}):
        add("Critical", "config", "prod config lacks an independent approver", "obtain approval")
    for sgn in cfg.get("signers", []):
        if sgn.get("not_after") and sgn["not_after"] <= now:
            add("Medium", f"signer:{sgn['id']}", "expired signer key still listed", "remove")
    pins = dict(l.split("==") for l in (ROOT / "constraints.txt").read_text().splitlines() if "==" in l and not l.startswith("#"))
    for name, ver in pins.items():
        try:
            inst = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
        if inst != ver:
            add("Medium", f"dependency:{name}", f"installed {inst} differs from pinned {ver}", "reconcile constraints")
    for w in json.loads((ROOT / "governance/WAIVERS.json").read_text())["waivers"]:
        days = (dt.date.fromisoformat(w["expires"]) - today).days
        if days < 0:
            add("High", w["id"], "waiver expired", "close or re-approve")
        elif days < 30:
            add("Medium", w["id"], f"waiver expires in {days} days", "plan closure")
        if w.get("approved_by") is None:
            add("Medium", w["id"], "waiver not yet approved", "obtain approval from owner")
    own = (ROOT / "docs/OWNERSHIP.md").read_text()
    if "*TBD*" in own or "to be confirmed" in own:
        add("Medium", "ownership", "ownership roles without confirmed named holders", "name owners (W-001)")
    adr = (ROOT / "docs/ADR-0001-control-plane-architecture.md").read_text()
    if "**Proposed**" in adr:
        add("Medium", "ADR-0001", "architecture decision not yet approved", "hold architecture board review")
    return f


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--out")
    a = ap.parse_args()
    today = dt.date.fromisoformat(a.today)
    res = {"schema": "PK_ECP_REVIEW/1", "date": a.today, "findings": review(json.loads(pathlib.Path(a.config).read_text()), today)}
    out = pathlib.Path(a.out or ROOT / "governance" / "reviews" / f"{a.today}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2) + "\n")
    sev = [x["severity"] for x in res["findings"]]
    print(json.dumps({"findings": len(sev), "by_severity": {s: sev.count(s) for s in set(sev)}, "out": str(out.relative_to(ROOT))}))
    return 1 if {"High", "Critical"} & set(sev) else 0


if __name__ == "__main__":
    sys.exit(main())
