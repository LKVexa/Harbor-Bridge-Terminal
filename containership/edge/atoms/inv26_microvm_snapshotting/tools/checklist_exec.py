"""Produce the executed copy of the supplied checklist: every control section gets a 6.0.0 status block,
and only the acceptance-package boxes that are demonstrably true are ticked:
  - "Repository artifact(s)"          ticked for IMPLEMENTED_LOCAL, PARTIAL, GOVERNANCE_PENDING (artifacts exist)
  - "Automated test evidence"         ticked for IMPLEMENTED_LOCAL only
  - "Machine-readable gate record"    ticked for every control (EXIT_GATE.json + RTM.json record it, incl. open ones)
  - "Owner/reviewer sign-off"         never ticked (no owner assigned)
Engineering-checklist boxes are left as supplied; the status block names what is done and what is open.
"""
import json
import re
import sys
from pathlib import Path

PKG = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
src = (PKG / "source" / "INV-26_v5.0.0_Missing_Component_Engineering_Checklist.md").read_text()
status = json.loads((PKG / "COMPONENTS_STATUS.json").read_text())["controls"]
out, cur = [], None
for line in src.splitlines():
    m = re.match(r"^## (?:INV-26-)?(C\d{3}|X\d{3})\b", line)
    if m:
        cur = m.group(1)
        out.append(line)
        st = status.get(cur)
        if st:
            out.append("")
            out.append(f"> **6.0.0 status: {st['status']}** — artifacts: " + ", ".join(f"`{a}`" for a in st["artifacts"][:6]))
            if st.get("tests"):
                out.append(f"> tests: " + ", ".join(f"`{t}`" for t in st["tests"][:5]))
            if st.get("evidence"):
                out.append(f"> evidence: " + ", ".join(f"`{e}`" for e in st["evidence"]))
            if st.get("gaps"):
                out.append(f"> open: " + "; ".join(st["gaps"]))
        continue
    if cur and line.startswith("- [ ]"):
        s = status.get(cur, {}).get("status")
        if "Repository artifact(s)" in line and s in ("IMPLEMENTED_LOCAL", "PARTIAL", "GOVERNANCE_PENDING"):
            line = line.replace("- [ ]", "- [x]", 1)
        elif "Automated test evidence" in line and s == "IMPLEMENTED_LOCAL":
            line = line.replace("- [ ]", "- [x]", 1)
        elif "Machine-readable gate record" in line and s:
            line = line.replace("- [ ]", "- [x]", 1) + " *(recorded in evidence/EXIT_GATE.json with its true status)*"
    if line.startswith("# Recommended implementation sequence"):
        cur = None
    out.append(line)
header = ["<!-- EXECUTED COPY generated from COMPONENTS_STATUS.json by the 6.0.0 chop-shop pass; the supplied original is "
          "source/INV-26_v5.0.0_Missing_Component_Engineering_Checklist.md -->", ""]
(PKG / "source" / "INV-26_v5.0.0_Missing_Component_Engineering_Checklist.executed.md").write_text("\n".join(header + out) + "\n")
counts = {}
for c, v in status.items():
    counts[v["status"]] = counts.get(v["status"], 0) + 1
print(counts)
