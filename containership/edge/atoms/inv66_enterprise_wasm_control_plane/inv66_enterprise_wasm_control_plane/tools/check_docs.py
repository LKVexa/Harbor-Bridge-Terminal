"""Docs lane: relative links in Markdown resolve; claimed files exist; runbooks referenced by alerts exist."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# produced by `tools/release.py build` (after CI); documented, so allowed to be absent on a clean CI checkout
GENERATED = {"release/sbom.cdx.json", "release/exit_gate.json", "release/rtm.json", "release/mc_status.json",
             "release/evidence.json", "docs/COVERAGE.md", "release/provenance.intoto.json", "release/MANIFEST.sig.json",
             "governance/INV66_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.executed.md"}
bad = []
for md in ROOT.rglob("*.md"):
    if "__pycache__" in md.parts:
        continue
    for m in re.finditer(r"\]\(([^)#\s]+)(#[^)]*)?\)", md.read_text()):
        t = m.group(1)
        if t.startswith(("http://", "https://", "mailto:")):
            continue
        if not (md.parent / t).exists() and not (ROOT / t).exists():
            bad.append(f"{md.relative_to(ROOT)} -> {t}")
    for m in re.finditer(r"`((?:docs|tools|production|schemas|release|governance|ops|deploy|config|fixtures|tests)/[A-Za-z0-9_./\-]+)`", md.read_text()):
        t = m.group(1).rstrip(".")
        if "<" in t or "*" in t or t.endswith("/"):
            continue
        if not (ROOT / t).exists() and t not in GENERATED and \
                not t.startswith(("release/rtm-history", "release/bench_baseline", "release/reviews")):
            bad.append(f"{md.relative_to(ROOT)} mentions missing {t}")
readme = (ROOT / "README.md").read_text()
if "MASTER.md" in readme and not (ROOT / "MASTER.md").exists():
    bad.append("README claims MASTER.md but it is missing")
for line in (ROOT / "ops/alerts/inv66-rules.yml").read_text().splitlines():
    m = re.search(r"runbook: ([^,#}]+)", line)
    if m and not (ROOT / m.group(1).strip()).exists():
        bad.append(f"alert runbook missing: {m.group(1)}")
for b in bad:
    print("BROKEN:", b)
print(f"docs check: {len(bad)} problems")
sys.exit(1 if bad else 0)
