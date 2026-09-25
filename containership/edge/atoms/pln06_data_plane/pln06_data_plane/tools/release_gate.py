"""WP #47 / C100 formal production exit gate.  Fails closed.

    python tools/release_gate.py [--dossier evidence/dossier.json] [--today YYYY-MM-DD]
    python tools/release_gate.py --config config/base.json --overlay config/overlays/prod.json --config-only
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))


def _sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def checks(today: dt.date, dossier: dict | None) -> list[dict]:
    res: list[dict] = []

    def add(cid: str, ok: bool, detail: str, wp: str) -> None:
        res.append({"check": cid, "ok": bool(ok), "detail": detail, "work_package": wp})

    own = json.loads((PKG / "OWNERSHIP.json").read_text())
    bad = [r for r, v in own["roles"].items() if v.get("status") != "confirmed" or not v.get("name")]
    add("ownership.roles_confirmed", not bad, f"unconfirmed/vacant: {bad}" if bad else "all roles confirmed", "#1")
    lr = own.get("last_reviewed")
    fresh = lr is not None and (today - dt.date.fromisoformat(lr)).days <= own["review_cadence_days"]
    add("ownership.review_fresh", fresh, f"last_reviewed={lr}", "#1/#51")
    co = (PKG / ".github/CODEOWNERS").read_text()
    add("codeowners.no_placeholders", "@OWNER-TBD" not in co, "placeholders present" if "@OWNER-TBD" in co else "ok", "#1")

    for adr in sorted((PKG / "docs").glob("ADR-*.md")):
        txt = adr.read_text()
        add(f"adr.approved:{adr.name}", bool(re.search(r"\*\*Status:\*\*\s*Accepted", txt)),
            "Proposed" if "Proposed" in txt else "see file", "#2")

    lic = PKG / "LICENSE"
    add("legal.license_present", lic.exists(), "LICENSE present" if lic.exists() else "no LICENSE file (W-010)", "#63")

    readme = (PKG / "README.md").read_text()
    add("hygiene.no_false_master_claim", not (re.search(r"MASTER\.md.*(included|shipped)", readme) and not (PKG / "MASTER.md").exists()),
        "README does not claim an absent MASTER.md", "#59")

    reg = json.loads((PKG / "WAIVERS.json").read_text())
    unapproved = [w["id"] for w in reg["entries"] if w["kind"] == "waiver" and not (w.get("approved_by") and w.get("approved_at"))]
    selfapp = [w["id"] for w in reg["entries"] if w.get("approved_by") and w["approved_by"] in str(w["owner"])]
    expired = [w["id"] for w in reg["entries"] if dt.date.fromisoformat(w["expires"]) < today]
    add("waivers.approved", not unapproved, f"unapproved: {unapproved}", "#52")
    add("waivers.not_self_approved", not selfapp, f"self-approved: {selfapp}", "#52")
    add("waivers.not_expired", not expired, f"expired: {expired}", "#52")

    from pln06_data_plane.tools import traceability
    tdoc = traceability.load()
    probs = traceability.check(tdoc)
    add("traceability.consistent", not probs, "; ".join(probs[:5]) or "ok", "#47")
    missing = [r["check_id"] for r in tdoc["items"] if r["status"] == "Missing"]
    add("traceability.no_missing", not missing, f"missing: {missing}", "#47")
    critical_partial = [r["check_id"] for r in tdoc["items"] if r["status"] == "Partial" and not r["waivers"]]
    add("traceability.partials_waived", not critical_partial, f"unwaived partial: {critical_partial}", "#47")

    sums = PKG / "SHA256SUMS.txt"
    skip = ("./evidence/", "./.mypy_cache/", "./.ruff_cache/")
    mism = []
    if sums.exists():
        for line in sums.read_text().splitlines():
            h, name = line.split(maxsplit=1)
            if name.startswith(skip) or "__pycache__" in name:
                continue
            p = PKG / name.removeprefix("./")
            if not p.exists() or _sha(p) != h:
                mism.append(name)
    add("integrity.sha256sums", sums.exists() and not mism, f"mismatched: {mism[:5]}" if mism else "ok", "#15")

    prod_asserts = [p.name for p in PKG.glob("*.py") if re.search(r"^\s*assert\s", p.read_text(), re.M)]
    add("code.no_runtime_asserts", not prod_asserts, f"{prod_asserts}", "#64")

    if dossier is None:
        add("evidence.dossier_present", False, "no dossier supplied (run tools/evidence.py)", "#47")
    else:
        add("evidence.tests_green", all(r.get("ok") for r in dossier.get("tests", {}).values()) and bool(dossier.get("tests")),
            json.dumps({k: {"run": v.get("run"), "ok": v.get("ok")} for k, v in dossier.get("tests", {}).items()}), "#61")
        add("evidence.static_analysis", all(v.get("ok") for v in dossier.get("static_analysis", {}).values()),
            json.dumps({k: v.get("ok") for k, v in dossier.get("static_analysis", {}).items()}), "#64")
        add("evidence.perf_gate", dossier.get("perf_gate", {}).get("ok") is True, str(dossier.get("perf_gate", {}).get("failures")), "#33")
        add("evidence.sbom", bool(dossier.get("sbom_sha256")), "sbom recorded", "#62")
        add("evidence.artifact_bound", bool(dossier.get("artifact", {}).get("sha256")), str(dossier.get("artifact")), "#15")
        add("evidence.signature", dossier.get("signature", {}).get("alg") == "HMAC-SHA256",
            "dossier HMAC-signed" if dossier.get("signature") else "unsigned (set PK06_EVIDENCE_KEY)", "#47")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dossier")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--out")
    ap.add_argument("--config")
    ap.add_argument("--overlay", action="append", default=[])
    ap.add_argument("--config-only", action="store_true")
    a = ap.parse_args(argv)
    if a.config_only:
        from pln06_data_plane import config
        cfg = config.load(a.config, [json.loads(pathlib.Path(o).read_text()) for o in a.overlay])
        print(json.dumps({"ok": True, "sha256": config.fingerprint(cfg), "context": cfg["context"]}))
        return 0
    dossier = json.loads(pathlib.Path(a.dossier).read_text()) if a.dossier else None
    res = checks(dt.date.fromisoformat(a.today), dossier)
    gate = {"schema": "PK_PRODUCTION_GATE/1", "element": "PLN-06", "evaluated": a.today,
            "artifact_sha256": (dossier or {}).get("artifact", {}).get("sha256"),
            "passed": all(r["ok"] for r in res), "checks": res,
            "summary": {"passed": sum(r["ok"] for r in res), "failed": sum(not r["ok"] for r in res)}}
    text = json.dumps(gate, indent=2)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    for r in res:
        print(("PASS " if r["ok"] else "FAIL ") + f"{r['check']:<40} {r['detail'][:110]}")
    print("PRODUCTION GATE:", "PASS" if gate["passed"] else "FAIL (fail-closed)")
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
