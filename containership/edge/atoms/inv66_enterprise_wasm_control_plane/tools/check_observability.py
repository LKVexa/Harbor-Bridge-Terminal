"""Observability drift lane (MC-050-T07, MC-054-T08): every metric used by dashboards/alerts must exist in a
live /metrics render after a representative workload (admit, deny, refuse, shed, verify)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from inv66_enterprise_wasm_control_plane.production.errors import EcpError  # noqa: E402
from inv66_enterprise_wasm_control_plane.production.testing import Estate  # noqa: E402

e = Estate(fsync=False, max_inflight=1, per_tenant_inflight=1)
s = e.service
s.admit(e.request("api"), e.token("ops"))
s.admit(e.request("api", registry="evil.example"), e.token("ops"))
for tok in (e.token("dev"), "garbage"):
    try:
        s.admit(e.request("api"), tok)
    except EcpError:
        pass
s.shedder.acquire("payments")
try:
    s.admit(e.request("api"), e.token("ops"))
except EcpError:
    pass
s.shedder.release("payments")
s.verify_audit_background()
s.freeze("acme/analytics", e.principal("sec1"), "drill")
s.health()
s.metrics.inc("ecp_quota_exceeded_total", 0, tenant="payments")
s.metrics.inc("ecp_audit_append_failures_total", 0)
s.metrics.inc("ecp_audit_verify_failures_total", 0)
text = s.metrics.render()
present = set(re.findall(r"^([a-zA-Z_:][a-zA-Z0-9_:]*?)(?:_bucket|_sum|_count)?(?:\{| )", text, re.M))
present |= set(re.findall(r"^# TYPE (\S+)", text, re.M))
used = set()
for expr in [p["expr"] for p in json.loads((ROOT / "ops/dashboards/inv66-overview.json").read_text())["panels"]] + \
        re.findall(r"expr: (.+)", (ROOT / "ops/alerts/inv66-rules.yml").read_text()):
    used |= {m for m in re.findall(r"\b((?:ecp|process)_[a-z0-9_]+)", expr)}
used = {re.sub(r"_(bucket|sum|count)$", "", u) for u in used}
missing = sorted(u for u in used if u not in present)
print(f"metrics used={len(used)} present={len(present)} missing={missing}")
sys.exit(1 if missing else 0)
