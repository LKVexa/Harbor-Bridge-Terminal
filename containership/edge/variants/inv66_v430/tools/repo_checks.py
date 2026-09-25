#!/usr/bin/env python3
"""Repository integrity checks run in CI (MC-001-T05/T13, MC-007-T04/T05, MC-067-T05, MC-071-T06/T08).

Fails (exit 1) when: a required artifact is missing; a relative markdown link is broken; versions
disagree; MASTER.md digest/count drifts from CHECKLIST.json; the RTM does not list C001-C100
exactly once or an MC lacks a disposition; a waiver is expired or lacks expiry; LICENSE/NOTICE
are missing from packaging; the release manifest does not verify.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "inv66_enterprise_wasm_control_plane"
REQUIRED = ["MASTER.md", "LICENSE", "NOTICE", "THIRD-PARTY-NOTICES.md", "pyproject.toml", "constraints.txt",
            "docs/ADR-0001-control-plane-architecture.md", "docs/OWNERSHIP.md", "docs/ARCHITECTURE.md",
            "docs/REQUIREMENTS.md", "docs/API.md", "docs/THREAT_MODEL.md", "docs/OPERATIONS.md", "docs/TESTING.md",
            "docs/CONSTRAINT_PRECEDENCE.md", "docs/SUPPLY_CHAIN.md", "governance/RTM.json", "governance/WAIVERS.json",
            "governance/CHECKLIST_STATUS.json", "governance/SBOM.cdx.json", "deploy/Dockerfile", "deploy/inv66.service",
            "deploy/rollout.yaml", "deploy/alerts.yaml", "deploy/dashboard.json", ".github/workflows/inv66-ci.yml",
            "perf/thresholds.json", "perf/baseline.json", "RELEASE_MANIFEST.sha256"]


def main(today: str | None = None) -> int:
    errs = []
    for r in REQUIRED:
        if not (ROOT / r).exists():
            errs.append(f"missing {r}")
    v = (PKG / "VERSION").read_text().strip()
    init = re.search(r'__version__ = "([^"]+)"', (PKG / "__init__.py").read_text()).group(1)
    pyp = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    if not v == init == pyp:
        errs.append(f"version mismatch VERSION={v} __init__={init} pyproject={pyp}")
    if f"## {v}" not in (PKG / "CHANGELOG.md").read_text():
        errs.append("CHANGELOG lacks current version")
    chk = PKG / "CHECKLIST.json"
    master = (ROOT / "MASTER.md").read_text()
    if hashlib.sha256(chk.read_bytes()).hexdigest() not in master:
        errs.append("MASTER.md source digest does not match CHECKLIST.json")
    if len(re.findall(r"^\| INV-66-C\d{3} \|", master, re.M)) != 100:
        errs.append("MASTER.md does not list exactly 100 requirements")
    readme = (PKG / "README.md").read_text()
    if "MASTER.md" in readme and not (ROOT / "MASTER.md").exists():
        errs.append("README claims MASTER.md but it is missing")
    rtm = json.loads((ROOT / "governance/RTM.json").read_text())
    ids = [c["id"] for c in rtm["controls"]]
    if sorted(ids) != [f"INV-66-C{i:03d}" for i in range(1, 101)]:
        errs.append("RTM must list C001-C100 exactly once")
    if len({c["id"] for c in rtm["components"]}) != 71:
        errs.append("RTM must list all 71 MC components")
    for c in rtm["components"]:
        if c["disposition"] != "n/a" and not c["artifacts"]:
            errs.append(f"{c['id']} has no implementation reference")
    today = today or dt.date.today().isoformat()
    wids = set()
    for w in json.loads((ROOT / "governance/WAIVERS.json").read_text())["waivers"]:
        wids.add(w["id"])
        if not w.get("expires"):
            errs.append(f"{w['id']} has no expiry")
        elif w["expires"] < today:
            errs.append(f"{w['id']} expired {w['expires']}")
    for c in rtm["components"]:
        for w in c["waivers"]:
            if w not in wids:
                errs.append(f"{c['id']} references unknown waiver {w}")
    for md in list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md")) + list(PKG.glob("*.md")):
        for link in re.findall(r"\]\(([^)#:]+)(?:#[^)]*)?\)", md.read_text()):
            if not (md.parent / link).exists():
                errs.append(f"{md.relative_to(ROOT)}: broken link {link}")
    if "LICENSE" not in (ROOT / "deploy/Dockerfile").read_text():
        errs.append("container does not ship LICENSE/NOTICE")
    if subprocess.run([sys.executable, str(ROOT / "tools/release_manifest.py")], capture_output=True).returncode:
        errs.append("release manifest does not verify")
    print(json.dumps({"errors": errs}, indent=1))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
