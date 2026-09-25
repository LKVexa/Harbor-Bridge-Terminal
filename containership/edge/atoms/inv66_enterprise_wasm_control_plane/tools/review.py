"""Recurring review extraction (MC-066): effective access, trust material, drift and staleness findings.

    python tools/review.py --config LAYER [LAYER...] [--journal ROOT] --out review.json

Findings need a human disposition. This tool never marks a finding resolved; reviewers append
dispositions to release/reviews.jsonl. Exit 0 means the extraction ran.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from inv66_enterprise_wasm_control_plane.production.config import build_policy, load_layers  # noqa: E402
from inv66_enterprise_wasm_control_plane.production.rbac import BUILTIN_ROLES  # noqa: E402

HIGH = {"org-admin", "security-admin"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", nargs="+", required=True)
    ap.add_argument("--journal")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    doc = load_layers(*[ROOT / c if not Path(c).is_absolute() else Path(c) for c in a.config])
    p = build_policy(doc)
    now = dt.datetime.now(dt.timezone.utc).timestamp()
    findings = []
    access = []
    for b in p.rbac.bindings:
        caps = sorted(p.rbac.roles[b.role])
        access.append({**b.to_doc(), "capabilities": caps})
        if b.role in HIGH and b.effect == "allow":
            findings.append({"kind": "elevated-grant", "severity": "review", "binding": b.to_doc()})
        if b.group and b.role in HIGH:
            findings.append({"kind": "elevated-group-grant", "severity": "high", "binding": b.to_doc(),
                             "why": "group membership is managed outside INV-66"})
    for s in p.signers.values():
        if s.revoked:
            findings.append({"kind": "revoked-signer-still-listed", "severity": "low", "signer": s.id})
        if s.not_after is None:
            findings.append({"kind": "signer-without-expiry", "severity": "medium", "signer": s.id})
        elif s.not_after - now < 30 * 86400:
            findings.append({"kind": "signer-expiring", "severity": "high", "signer": s.id})
    for h, sc in p.registries:
        if len(sc) == 1:
            findings.append({"kind": "org-wide-registry", "severity": "review", "registry": h})
    owners = json.loads((ROOT / "governance/owners.json").read_text())
    orphan = [r for r, v in owners["roles"].items() if "UNASSIGNED" in json.dumps(v)]
    if orphan:
        findings.append({"kind": "orphaned-ownership", "severity": "high", "roles": orphan})
    waivers = json.loads((ROOT / "release/waivers.json").read_text())["waivers"]
    findings += [{"kind": "unowned-waiver", "severity": "high", "waiver": w["id"]} for w in waivers if not w["owner"]]
    compat = json.loads((ROOT / "release/compatibility.json").read_text())
    findings += [{"kind": "untested-support-claim", "severity": "medium", "row": r} for r in compat["runtime_matrix"]
                 if r["status"] == "DECLARED_UNTESTED"]
    for role, caps in p.rbac.roles.items():
        if role not in BUILTIN_ROLES and {"policy.admin", "config.activate"} <= set(caps):
            findings.append({"kind": "custom-role-self-activation", "severity": "high", "role": role})
    journal = None
    if a.journal:
        from inv66_enterprise_wasm_control_plane.production.journal import Journal
        journal = Journal(Path(a.journal) / "journal").verify()
    out = {"schema": "PK_ECP_REVIEW/1", "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
           "config_generation": p.generation, "effective_access": access, "findings": findings,
           "journal_verification": journal, "dispositions_required": len(findings),
           "cadence": {"access": "90d", "elevated": "30d", "signers/registries": "30d", "dependencies": "weekly",
                       "architecture/threat model": "per material change + each exit gate"}}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(f"review: {len(access)} bindings, {len(findings)} findings needing disposition")
    return 0


if __name__ == "__main__":
    sys.exit(main())
