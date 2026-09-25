"""Item-level status of the governing checklist (source/PLN05_v4.1.1_…md), MC-01..MC-34.

Every checkbox of every MC section gets one status:
  DONE              satisfied by repository content with automated evidence
  PARTIAL           partly satisfied; the gap is named in NOTES
  OPEN_EXTERNAL     needs something outside this repository (pk_core, siblings, KMS, forge, hardware)
  OPEN_GOVERNANCE   needs a human decision/approval/assignment by the owner
Component status is driven by the Definition-of-Done items:
  COMPLETE only when every item incl. closure approval is DONE (impossible without owner sign-off);
  otherwise BLOCKED_EXTERNAL > GOVERNANCE_PENDING > PARTIAL > IMPLEMENTED_LOCAL.

    python tools/mc_status.py [--out FILE] [--annotate FILE.md]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "source" / "PLN05_v4.1.1_Missing_Component_Remediation_Checklists.md"
CODE = {"D": "DONE", "P": "PARTIAL", "E": "OPEN_EXTERNAL", "G": "OPEN_GOVERNANCE"}
XCUT = "GDPDDDDDDE"   # spec approved first / unit / integration(real adapters) / codes / telemetry / trace / docs / evidence / versioned / clean CI no skips
CLOSE = "DDDDDG"      # ... owner/reviewer approval

# (required deliverables, component-specific, definition of done)
MAP = {
    "MC-01": ("DPDD", "DDDGDDDDDDDDDDDG", "GPDD"),
    "MC-02": ("DDDG", "GDDDDDDDDDDDDDD", "GDDG"),
    "MC-03": ("DDDD", "D" * 18, "DDDD"),
    "MC-04": ("DDDD", "DPDDDDDPDDDDDDDD", "DDD"),
    "MC-05": ("DDDP", "DDPDDDDDDDDDDDDDDD", "DDDD"),
    "MC-06": ("DDDD", "DDDDDDDDDDDDDPEDP", "DDDD"),
    "MC-07": ("DDDD", "DPDDDDDDDDDDPDDDDD", "PDDD"),
    "MC-08": ("DDDD", "DDPPDDDDDDDDDDDDDD", "DPD"),
    "MC-09": ("DDDD", "DDDDDDDDDPDDDDDPDD", "PDD"),
    "MC-10": ("DDDD", "DDDDDDDDDDPDDDDDPDDD", "DDD"),
    "MC-11": ("DDDD", "DDDDDDDDDDDDDDPDPDDD", "DPD"),
    "MC-12": ("DDPD", "DDDDDDPDDEDDDDDDDD", "DPD"),
    "MC-13": ("DDDD", "DDDDDDDDDDDDDPDDD", "DDD"),
    "MC-14": ("DDDD", "DDDDDDDDDDDDDDDDPDDD", "DDD"),
    "MC-15": ("DDDD", "DDDDDDDDDDDDDDDDPD", "DDD"),
    "MC-16": ("DDDD", "DDDPDDDDDDDDPDPDDD", "DDDD"),
    "MC-17": ("DDDD", "DDDDDDDDDDDDDDDDPD", "DPD"),
    "MC-18": ("DDDD", "D" * 20, "DDDD"),
    "MC-19": ("DDDD", "DDDDDDDDDDPDDDDDDD", "DDD"),
    "MC-20": ("DDDD", "DPDPDPDDDDDDDDDPDED", "DDD"),
    "MC-21": ("DDDD", "DDDDDDPDDDDDDPDDEDDDD", "PDD"),
    "MC-22": ("DDDD", "DDPDDDDDDDDDDDDDDDDEPD", "DDD"),
    "MC-23": ("DDDD", "DDDDDDDDPDDPDDDDDDD", "DGD"),
    "MC-24": ("DDDD", "DDDDDDDDDDDDDDDDDDE", "DDD"),
    "MC-25": ("DDDD", "DDDDPPPDDDDDDDPDDDDDDP", "DDD"),
    "MC-26": ("DDDD", "DDDDDDDDPDDPEDDDDPP", "DDD"),
    "MC-27": ("DDDD", "DDDDDDDDDDDPDDDDDDDDD", "DDD"),
    "MC-28": ("DDDD", "DDDDDPDDDDDDDPPDPDDD", "PDD"),
    "MC-29": ("DDDD", "DDDDDDPPPDPDDPDDDPDDP", "PDE"),
    "MC-30": ("DDPD", "DDDDDDDDDDDPDDDDDDDPD", "DDD"),
    "MC-31": ("DDDD", "DDDDDDDDDDDDDDDDDDDDG", "PDPD"),
    "MC-32": ("DPDD", "DDDDDDDDDDDDDDDPD", "DDD"),
    "MC-33": ("DDDD", "DDDEDDDDPDDDDDDDDPDPDDDG", "PDD"),
    "MC-34": ("GDDD", "GDDDDDDDDDDDDDPDDDDD", "GDD"),
}
NOTES = {
    "MC-01": "ADR-0001 PROPOSED; CHECKLIST.json C010/C011 text kept verbatim and marked superseded-proposed in traceability.",
    "MC-02": "roles defined, every assignee UNASSIGNED; approvals.json empty.",
    "MC-04": "no per-requirement rationale field; dependency relationships recorded only for C011 and the SHALL set.",
    "MC-05": "field units/default semantics partly in descriptions only; validators are Python only (no generated bindings for other languages).",
    "MC-06": "break-glass issuance approval and runtime sandbox are deployment/issuer obligations; audit records lack policy version (explain has it).",
    "MC-07": "transport deadlines are adapter obligations (no network code here); no request-rate limiter beyond admission.",
    "MC-08": "not every constrained field has a wrong-type/out-of-range fixture; target schema omission fixtures cover 7 of 16 required fields.",
    "MC-09": "Windows bootstrap untested; no vulnerability scanner run (zero third-party runtime deps); framework tier unresolvable (pk_core).",
    "MC-10": "rollback does not capture a free-text reason (audit records actor/ticket-less rollback); config files rely on directory permissions set by deployment.",
    "MC-11": "release signature is an ephemeral HMAC, not a managed signing identity.",
    "MC-12": "authenticated transport encryption and at-rest encryption/KMS are external (adapters, volume/KMS).",
    "MC-13": "audit confidentiality delegated to storage encryption.",
    "MC-14": "timing side channels covered only for MAC comparison.",
    "MC-15": "flapping integration test absent (detector implemented).",
    "MC-16": "retry budget per policy object (not per dependency); breaker thresholds on consecutive failures only; breaker state and retries not exported as metrics.",
    "MC-17": "residency is carried by scope identity only; no residency model beyond that; consistent failover requires a shared/replicated state_dir.",
    "MC-19": "no dry-run for control actions (status shows the current state before acting).",
    "MC-20": "process kill simulated by restart-from-disk; no network-level (packet loss/DNS/bandwidth) or read-only-volume injection; no production-like disaster run.",
    "MC-21": "baseline recorded on the CI container, not a declared reference environment; GC not profiled; instance-count scaling not measured; power not measured (W-001).",
    "MC-22": "memory copies not measured; power not measured.",
    "MC-23": "single-platform baseline; no CPU pinning of noisy hosts; baseline PROPOSED, needs approval.",
    "MC-24": "orchestrator probe wiring belongs to the embedding service.",
    "MC-25": "per-workload target gauges intentionally not emitted (cardinality policy); queue/breaker/lease gauges missing; one span per decision; log schema not versioned.",
    "MC-26": "no topology snapshot; build provenance only as version/build_id; explain records are not integrity-protected; explain tests do not cover every outcome.",
    "MC-28": "min/max Python versions not tested; config not exercised concurrently; no race detector; no cancellation-under-concurrency test.",
    "MC-29": "soak is presubmit length (60k decisions); no multi-site, leader-handoff or credential rotation during soak; no declared fleet targets or reference infrastructure.",
    "MC-30": "no third-party linter/type checker adopted; bundle signature is ephemeral HMAC.",
    "MC-31": "canary not exercised; runbooks not executed by an operator; game days scheduled, none held.",
    "MC-32": "no separate workflows/ directory (source/ carries the governing checklist); clean-checkout run recorded in evidence only for this container.",
    "MC-33": "GitHub workflows written but not executed on a forge; action pins not verified; pk_core tier unresolvable; branch protection is a forge setting.",
    "MC-34": "license choice is the owner's; no issue templates.",
}


def parse():
    text = SRC.read_text(encoding="utf-8")
    secs = re.split(r"^# (MC-\d\d) — (.+)$", text, flags=re.M)
    out = {}
    for i in range(1, len(secs), 3):
        mc, title, body = secs[i], secs[i + 1], secs[i + 2].split("\n# Final")[0]
        groups = {}
        for part in re.split(r"^## ", body, flags=re.M)[1:]:
            head = part.split("\n")[0].strip()
            groups[head] = [l[6:].strip() for l in part.split("\n") if l.startswith("- [ ]")]
        out[mc] = (title.strip(), groups)
    return out


def build() -> dict:
    parsed = parse()
    comps, totals = [], {v: 0 for v in CODE.values()}
    for mc, (title, groups) in parsed.items():
        rd, cs, dod = MAP[mc]
        plan = {"Required deliverables": rd, "Component-specific implementation checklist": cs,
                "Cross-cutting engineering gates": XCUT, "Definition of done / acceptance criteria": dod,
                "Closure evidence to attach": CLOSE}
        items = []
        for head, entries in groups.items():
            codes = plan[head]
            if len(codes) != len(entries):
                raise SystemExit(f"{mc} {head}: {len(entries)} items but {len(codes)} statuses")
            for text, c in zip(entries, codes):
                items.append({"group": head, "item": text, "status": CODE[c]})
                totals[CODE[c]] += 1
        dstat = set(dod)
        if all(i["status"] == "DONE" for i in items):
            status = "COMPLETE"
        elif "E" in dstat:
            status = "BLOCKED_EXTERNAL"
        elif "G" in dstat:
            status = "GOVERNANCE_PENDING"
        elif "P" in dstat:
            status = "PARTIAL"
        else:
            status = "IMPLEMENTED_LOCAL"
        counts = {v: sum(1 for i in items if i["status"] == v) for v in CODE.values()}
        comps.append({"id": mc, "title": title, "status": status, "counts": counts,
                      "note": NOTES.get(mc), "items": items})
    by = {}
    for c in comps:
        by[c["status"]] = by.get(c["status"], 0) + 1
    return {"schema": "PLN05_MC_STATUS/1", "source_sha256": json.loads((ROOT / "source" / "SOURCE.json").read_text())["sha256"],
            "components": comps, "component_status_counts": by, "item_totals": totals,
            "items": sum(totals.values())}


def annotate(out: pathlib.Path, status: dict) -> None:
    """Write an executed copy of the checklist with [x] / [~] / [E] / [G] marks."""
    mark = {"DONE": "[x]", "PARTIAL": "[~]", "OPEN_EXTERNAL": "[E]", "OPEN_GOVERNANCE": "[G]"}
    lookup = {}
    for c in status["components"]:
        for it in c["items"]:
            lookup.setdefault((c["id"], it["group"], it["item"]), mark[it["status"]])
    lines, mc, group = [], None, None
    for line in SRC.read_text(encoding="utf-8").split("\n"):
        m = re.match(r"^# (MC-\d\d) — ", line)
        if m:
            mc = m.group(1)
        if line.startswith("# Final"):
            mc = None
        if line.startswith("## "):
            group = line[3:].strip()
        if mc and line.startswith("- [ ]"):
            line = line.replace("- [ ]", "- " + lookup.get((mc, group, line[6:].strip()), "[ ]"), 1)
        if line.startswith("# MC-") and mc:
            comp = next(c for c in status["components"] if c["id"] == mc)
            line += f"  \n**4.2.0 status: {comp['status']}** — {comp['note'] or 'all Definition-of-Done items met locally; closure needs owner approval'}"
        lines.append(line)
    header = ("<!-- Executed copy produced by tools/mc_status.py for PLN-05 4.2.0. Marks: [x] DONE, [~] PARTIAL, "
              "[E] OPEN_EXTERNAL, [G] OPEN_GOVERNANCE. Global gates and final closure are evaluated by tools/gate.py. -->\n")
    out.write_text(header + "\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--annotate")
    a = ap.parse_args(argv)
    st = build()
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(st, indent=1), encoding="utf-8")
    if a.annotate:
        annotate(pathlib.Path(a.annotate), st)
    print(json.dumps({"component_status_counts": st["component_status_counts"], "item_totals": st["item_totals"],
                      "items": st["items"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
