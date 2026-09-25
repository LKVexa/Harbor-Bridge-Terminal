#!/usr/bin/env python3
"""INV-38-C009-T12 / C020-T05 — reject missing/malformed/stale required artifacts."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(ROOT))
from inv38_kernel_bypass_transport import rtm_tools, remediation_status as rs

def main():
    problems = []
    rtm = rtm_tools.build()
    problems += rtm_tools.validate(rtm)
    # every declared artifact path must exist
    for cid, item in rs.full_status().items():
        for art in item["artifacts"]:
            p = os.path.join(ROOT, art)
            base = p.rstrip("/")
            if not (os.path.exists(base) or os.path.isdir(base)):
                problems.append(f"{item['id']}: missing artifact {art}")
    if problems:
        print("REPO INTEGRITY FAIL:"); [print("  -", p) for p in problems]
        return 1
    print("repo integrity OK:", len(rtm["rows"]), "requirements,",
          sum(len(i["artifacts"]) for i in rs.full_status().values()), "artifacts present")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
