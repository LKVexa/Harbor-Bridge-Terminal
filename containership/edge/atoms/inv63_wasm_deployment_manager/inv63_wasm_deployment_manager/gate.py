"""INV-63 production exit gate (INV-63-C090, C098, C099, C100).

    python gate.py [--out release/GATE_RESULT.json] [--now YYYY-MM-DD]

Consumes fresh evidence (evidence/audit_bundle.json, evidence/test_results.json,
AUDIT_RESULTS.json, perf/results.json) plus OWNERS.yaml, pins.json,
governance/{WAIVERS,REVIEWS}.json and emits a ``PK_DEPLOY_GATE/1`` verdict bound
to the package source digest.  Criterion statuses: PASS, FAIL, BLOCKED,
SKIPPED, NOT_RUN, WAIVED.

Verdict: any FAIL -> NO_GO; any mandatory BLOCKED/SKIPPED/NOT_RUN -> BLOCKED;
any WAIVED -> CONDITIONAL_GO; else GO.  A GO is impossible without a signature
from the gate key (``INV63_GATE_SIGNING_KEY`` = env:/file: ref to a hex Ed25519 seed).
Exit code 0 only for GO / CONDITIONAL_GO.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import pathlib
import sys

PKG_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(PKG_DIR.parent))
evidence = importlib.import_module(f"{PKG_DIR.name}.evidence")
schema = importlib.import_module(f"{PKG_DIR.name}.schema")


def _load(root: pathlib.Path, rel: str):
    p = root / rel
    return json.loads(p.read_text()) if p.is_file() else None


def parse_owners(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].rstrip()
        if line and not line.startswith(" ") and ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def revision_signed(root: pathlib.Path, digest: str, today: dt.date) -> bool:
    a = _load(root, "governance/APPROVALS.json") or {}
    for r in a.get("approvals", []):
        try:
            ok_date = dt.date.fromisoformat(r.get("expires", "")) >= today
        except ValueError:
            ok_date = False
        if r.get("key") == "revision-signoff" and r.get("revision") == digest and r.get("approver") \
                and r.get("signature") and ok_date:
            return True
    return False


def check_owners(root: pathlib.Path, today: dt.date) -> tuple[str, str]:
    p = root / "OWNERS.yaml"
    if not p.is_file():
        return "FAIL", "OWNERS.yaml missing"
    o = parse_owners(p.read_text())
    required = ["service_owner", "engineering_owner", "oncall_rotation", "security_contact", "release_approver",
                "architecture_approver", "review_date"]
    unassigned = [k for k in required if not o.get(k) or o[k] == "UNASSIGNED"]
    if unassigned:
        return "BLOCKED", f"unassigned: {unassigned}"
    try:
        age = (today - dt.date.fromisoformat(o["review_date"])).days
    except ValueError:
        return "FAIL", "review_date malformed"
    if age > 90:
        return "FAIL", f"ownership review {age} days old (> 90)"
    return "PASS", "all roles assigned; review current"


def check_waivers(root: pathlib.Path, today: dt.date) -> tuple[str, str, list[dict]]:
    w = _load(root, "governance/WAIVERS.json") or {"waivers": []}
    active, expired = [], []
    for x in w.get("waivers", []):
        needed = ("id", "criterion", "risk_owner", "compensating_control", "expires")
        if any(not x.get(k) for k in needed):
            return "FAIL", f"waiver {x.get('id')} incomplete", []
        (expired if dt.date.fromisoformat(x["expires"]) < today else active).append(x)
    if expired:
        return "FAIL", f"expired waivers: {[x['id'] for x in expired]}", active
    return "PASS", f"{len(active)} active waivers", active


def check_reviews(root: pathlib.Path, today: dt.date) -> tuple[str, str]:
    r = _load(root, "governance/REVIEWS.json")
    if r is None:
        return "FAIL", "REVIEWS.json missing"
    last: dict[str, dt.date] = {}
    for c in r.get("completed", []):
        try:
            d = dt.date.fromisoformat(c["date"])
        except (KeyError, ValueError):
            return "FAIL", "malformed review record"
        if c.get("kind") and c.get("reviewer"):
            last[c["kind"]] = max(d, last.get(c["kind"], d))
    overdue = [k for k, days in r["cadence_days"].items() if k not in last or (today - last[k]).days > days]
    if overdue:
        return "BLOCKED", f"no current review for: {overdue}"
    return "PASS", "all recurring reviews current"


def evaluate(root: pathlib.Path = PKG_DIR, today: dt.date | None = None, env: dict | None = None) -> dict:
    today = today or dt.date.today()
    env = os.environ if env is None else env
    policy = _load(root, "release/GATE_POLICY.json")
    digest = evidence.source_digest(root)
    bundle = _load(root, "evidence/audit_bundle.json")
    tests = _load(root, "evidence/test_results.json")
    audit = _load(root, "AUDIT_RESULTS.json")
    perf = _load(root, "perf/results.json")
    pins = _load(root, "pins.json") or {}
    results: dict[str, tuple[str, str]] = {}

    # G-08 freshness/binding first: stale evidence invalidates G-01/G-02
    fresh = False
    if not bundle:
        results["G-08"] = ("NOT_RUN", "no evidence bundle; run audit.py")
    elif bundle["source_digest"] != digest:
        results["G-08"] = ("FAIL", "evidence was produced for a different source digest")
    else:
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(bundle["generated_at"])).days
        if age > policy["evidence_max_age_days"]:
            results["G-08"] = ("FAIL", f"evidence {age} days old")
        else:
            fresh = True
            results["G-08"] = ("PASS", "evidence bound to current source digest")

    if not tests or not fresh:
        results["G-01"] = ("NOT_RUN", "no fresh test results")
    elif tests["failed"]:
        results["G-01"] = ("FAIL", f"{tests['failed']} tests failed")
    elif tests["skipped"]:
        results["G-01"] = ("SKIPPED", f"{tests['skipped']} mandatory tests skipped (skips never count as passes)")
    else:
        results["G-01"] = ("PASS", f"{tests['passed']} tests passed")

    if not audit or not fresh:
        results["G-02"] = ("NOT_RUN", "no fresh audit")
    else:
        s = audit["summary"]
        if s["MISSING"]:
            results["G-02"] = ("FAIL", f"{s['MISSING']} requirements MISSING")
        elif s["PARTIAL"]:
            results["G-02"] = ("BLOCKED", f"{s['PARTIAL']} requirements await external evidence")
        elif not revision_signed(root, digest, today):
            results["G-02"] = ("BLOCKED", "100/100 SATISFIED but no revision-signoff approval for this source digest")
        else:
            results["G-02"] = ("PASS", "100/100 SATISFIED and revision signed off")

    if not perf:
        results["G-03"] = ("NOT_RUN", "perf/results.json missing; run perf/bench.py")
    elif perf.get("source_digest") != digest:
        results["G-03"] = ("NOT_RUN", "perf results not bound to current source digest")
    elif perf.get("gate_failures"):
        results["G-03"] = ("FAIL", "; ".join(perf["gate_failures"]))
    elif "PROPOSED" in (_load(root, "perf/thresholds.json") or {}).get("status", ""):
        results["G-03"] = ("BLOCKED", "thresholds met but not yet approved on reference hardware")
    else:
        results["G-03"] = ("PASS", "no regression")

    unpinned = [k for k, v in pins.items() if isinstance(v, dict) and (not v.get("approved") or v.get("version") == "UNPINNED")]
    results["G-04"] = ("BLOCKED", f"unpinned/unapproved: {unpinned}") if unpinned else ("PASS", "all pinned + approved")
    results["G-05"] = check_owners(root, today)
    ws, wmsg, active = check_waivers(root, today)
    results["G-06"] = (ws, wmsg)
    results["G-07"] = check_reviews(root, today)
    pk = tests and any(t.startswith("test_component.") and r["status"] == "PASS" for t, r in tests["tests"].items())
    results["G-09"] = ("PASS", "pk_core conformance executed") if pk else \
        ("BLOCKED", "pk_core not installed: framework conformance was skipped, which is not a pass")

    key_ref = env.get("INV63_GATE_SIGNING_KEY")
    priv = None
    if key_ref:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            sec = importlib.import_module(f"{PKG_DIR.name}.security")
            priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(sec.resolve_secret_ref(key_ref, env).decode()))
            results["G-10"] = ("PASS", "gate key available")
        except Exception as exc:  # fail closed
            results["G-10"] = ("BLOCKED", f"gate key unusable: {type(exc).__name__}")
    else:
        results["G-10"] = ("BLOCKED", "INV63_GATE_SIGNING_KEY not provisioned")

    waived = {w["criterion"] for w in active}
    criteria = []
    for c in policy["criteria"]:
        st, why = results[c["id"]]
        if st != "PASS" and c["id"] in waived and st != "FAIL":
            st, why = "WAIVED", f"{why} (waived)"
        criteria.append({"id": c["id"], "name": c["name"], "mandatory": c["mandatory"], "status": st, "detail": why})
    sts = [c["status"] for c in criteria if c["mandatory"]]
    if "FAIL" in sts:
        verdict = "NO_GO"
    elif any(s in ("BLOCKED", "SKIPPED", "NOT_RUN") for s in sts):
        verdict = "BLOCKED"
    elif "WAIVED" in sts:
        verdict = "CONDITIONAL_GO"
    else:
        verdict = "GO"
    out = {"schema": "PK_DEPLOY_GATE/1", "verdict": verdict, "criteria": criteria,
           "bound_to": {"source_digest": digest, "version": (root / "VERSION").read_text().strip(),
                        "evidence_bundle": bundle and bundle.get("audit_results_sha256"),
                        "pins": {k: v.get("version") for k, v in pins.items() if isinstance(v, dict)}},
           "waivers": active, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "signature": None}
    if priv is not None:
        body = {k: v for k, v in out.items() if k != "signature"}
        pub = priv.public_key().public_bytes_raw().hex()
        out["signature"] = {"alg": "ed25519", "public_key": pub, "sig": priv.sign(evidence.canonical(body)).hex()}
    elif verdict in ("GO", "CONDITIONAL_GO"):
        out["verdict"] = "BLOCKED"          # unsigned verdicts can never promote
    schema.validate(out, "PK_DEPLOY_GATE/1")
    return out


def verify_signature(result: dict) -> bool:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    sig = result.get("signature")
    if not sig:
        return False
    body = {k: v for k, v in result.items() if k != "signature"}
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(sig["public_key"])).verify(bytes.fromhex(sig["sig"]),
                                                                                   evidence.canonical(body))
        return True
    except Exception:
        return False


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG_DIR / "release/GATE_RESULT.json"))
    ap.add_argument("--now")
    a = ap.parse_args(argv)
    res = evaluate(today=dt.date.fromisoformat(a.now) if a.now else None)
    pathlib.Path(a.out).write_text(json.dumps(res, indent=2) + "\n")
    print(json.dumps({"verdict": res["verdict"], "criteria": {c["id"]: c["status"] for c in res["criteria"]}}))
    return 0 if res["verdict"] in ("GO", "CONDITIONAL_GO") else 2


if __name__ == "__main__":
    sys.exit(main())
