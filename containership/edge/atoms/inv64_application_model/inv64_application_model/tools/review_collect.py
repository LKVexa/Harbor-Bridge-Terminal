"""Automated data collection for recurring reviews (MC-35; C098).

    python -m inv64_application_model.tools.review_collect DOMAIN [--policy FILE] [--store DIR] [--out FILE]

Produces a ``PK_APP_REVIEW_INPUT/1`` snapshot for the reviewer — it does not
approve anything. Domains: access (grants per role/tenant, break-glass and
wildcard-resource grants), policy (policy/trust versions and digests),
dependency (compatibility rows, EOL dates, pk_core pin state), configuration
(active vs quarantined revisions, register entries past their review date),
architecture (ADR states, OAM baseline, adjacent contract ranges).
The reviewer records the outcome in ops/REVIEWS.json ``history`` with
reviewer, date, scope, the snapshot's digest, findings and next due date.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def collect(domain: str, policy: Path | None, store: Path | None, today: dt.date) -> dict:
    load = lambda rel: json.loads((ROOT / rel).read_text(encoding="utf-8"))
    data: dict = {}
    if domain == "access":
        pol = json.loads(policy.read_text()) if policy else {"grants": []}
        data["grants"] = [{"id": g["id"], "roles": g.get("roles", []), "principals": g.get("principals", []),
                           "capabilities": g["capabilities"], "tenants": g["tenants"],
                           "wildcard_resource": "*" in g["resources"], "breakglass": "breakglass" in g["capabilities"]}
                          for g in pol["grants"]]
        data["owners"] = load("ops/owners.json")["roles"]
    elif domain == "policy":
        pol = policy.read_bytes() if policy else b""
        data = {"authz_policy_sha256": hashlib.sha256(pol).hexdigest() if pol else None,
                "gate_policy_version": load("ops/GATE_POLICY.json")["version"],
                "telemetry_policy": "TELEMETRY_POLICY.md", "secret_policy": "SECURITY_ARCHITECTURE.md#secrets"}
    elif domain == "dependency":
        c = load("compatibility.json")
        data = {"python": c["python"], "pk_core": c["pk_core"], "optional": c["optional_dependencies"],
                "support_lines": c["support_lines"], "oam": c["oam"]}
    elif domain == "configuration":
        reg = load("ops/REGISTER.json")["entries"]
        data["register_past_review"] = [e["id"] for e in reg if dt.date.fromisoformat(e["expires"]) < today]
        if store and (store / "state.json").is_file():
            st = json.loads((store / "state.json").read_text())
            data["active"] = st["active"]
            data["quarantined"] = sorted(st["quarantine"])
    elif domain == "architecture":
        data = {"adrs": load("ops/decisions.json")["adrs"], "oam": load("compatibility.json")["oam"],
                "adjacent": load("compatibility.json")["adjacent"]}
    else:
        raise SystemExit(f"unknown domain {domain}")
    body = {"schema": "PK_APP_REVIEW_INPUT/1", "domain": domain, "collected": today.isoformat(), "data": data}
    body["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("domain", choices=["access", "policy", "dependency", "configuration", "architecture"])
    ap.add_argument("--policy")
    ap.add_argument("--store")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = collect(a.domain, Path(a.policy) if a.policy else None, Path(a.store) if a.store else None, dt.date.today())
    text = json.dumps(res, indent=2)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
