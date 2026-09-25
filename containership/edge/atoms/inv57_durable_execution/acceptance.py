"""Machine-readable production acceptance manifest and exit gate (MC-57, MC-65, RG-08 check).

The gate consumes, from the package directory:
  TRACEABILITY.json       100 C-items with status and evidence
  STATUS_REGISTER.json    MC/SG/RG remediation components with status, evidence, tests, blockers
  WAIVERS.json            exception/waiver ledger (MC-65)
  test-report.json        per-test outcomes from tools/run_tests.py (optional input)

Rules (fail-closed):
  * every evidence path (text before ``::``) must resolve inside the package; its sha256 is recorded;
  * every cited test must appear in the test report as ``passed`` — skipped/absent never counts;
  * a waiver counts only with a named approver, a reason and an unexpired date;
  * GO requires every C-item ``present`` (or validly waived) and every component ``CLOSED``;
  * the manifest is left unsigned unless a signing key is configured; unsigned → NO_GO.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
from typing import Any

MANIFEST_SCHEMA = "INV57_ACCEPTANCE_MANIFEST/1"
REGISTER_STATUSES = {"CLOSED", "IMPLEMENTED_LOCAL", "PARTIAL", "BLOCKED", "OPEN"}


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def _load(root: str, name: str, default: Any = None) -> Any:
    p = os.path.join(root, name)
    if not os.path.exists(p):
        if default is not None:
            return default
        raise FileNotFoundError(name)
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _resolve(root: str, ref: str) -> tuple[str, str | None]:
    """Resolve an evidence ref to a regular file physically inside the package.

    ``realpath`` defeats symlinks pointing outside the package, and any symlink on
    the path is refused outright: evidence must be real bytes in the candidate.
    """
    rel = ref.split("::", 1)[0]
    real_root = os.path.realpath(root)
    joined = os.path.join(root, rel)
    p = os.path.realpath(joined)
    if not p.startswith(real_root + os.sep) or not os.path.isfile(p):
        return rel, None
    cur = os.path.abspath(joined)
    stop = os.path.abspath(root)
    while cur != stop and cur.startswith(stop):
        if os.path.islink(cur):
            return rel, None
        cur = os.path.dirname(cur)
    return rel, _sha(p)


def valid_waiver(w: dict, today: _dt.date) -> tuple[bool, str]:
    for f in ("id", "target", "approver", "reason", "expires"):
        if not w.get(f):
            return False, f"missing {f}"
    try:
        if _dt.date.fromisoformat(w["expires"]) < today:
            return False, "expired"
    except ValueError:
        return False, "bad expiry date"
    return True, "ok"


def absent_artifact_claims(root: str) -> list[str]:
    """RG-08: flag docs that mention MASTER.md without stating it is absent/retired."""
    bad = []
    for name in os.listdir(root):
        if name.endswith(".md") and name != "AUDIT_REPORT.md":
            with open(os.path.join(root, name), encoding="utf-8") as fh:
                text = fh.read()
            for m in re.finditer(r"MASTER\.md", text):
                window = text[max(0, m.start() - 200): m.end() + 200].lower()
                if not re.search(r"not present|absent|missing|retired|non-authoritative|not included|removes", window):
                    bad.append(name)
    return sorted(set(bad))


def unresolved_owners(root: str) -> list[str]:
    """MC-01 stale-owner check: every role/target in OWNERS.yaml must be non-empty."""
    p = os.path.join(root, "OWNERS.yaml")
    if not os.path.exists(p):
        return ["OWNERS.yaml missing"]
    bad = []
    with open(p, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for line in lines:
        m = re.match(r'\s*([A-Za-z0-9_]+):\s*(?:\{target:\s*)?""', line)
        if m:
            bad.append(m.group(1))
    return bad


def evaluate(root: str, *, today: _dt.date | None = None,
             signing_key: bytes | None = None, key_id: str | None = None) -> dict[str, Any]:
    """Evaluate the exit gate.

    Signing: an HMAC key only counts when ``key_id`` is listed as an active release key in
    ``TRUST_POLICY.json``.  Even then it is an integrity MAC, not a public attestation;
    RG-06 (asymmetric signing + provenance) remains required and is reported as a blocker.
    The test report is hashed into the manifest; it is still self-reported until RG-06
    attests the CI run that produced it (documented limitation)."""
    today = today or _dt.date.today()
    trace = _load(root, "TRACEABILITY.json")
    register = _load(root, "STATUS_REGISTER.json")
    waivers = _load(root, "WAIVERS.json", {"waivers": []})["waivers"]
    report = _load(root, "test-report.json", {"tests": {}})
    tests = report.get("tests", {})

    wmap: dict[str, dict] = {}
    waiver_problems = []
    for w in waivers:
        ok, why = valid_waiver(w, today)
        if ok:
            wmap[w["target"]] = w
        else:
            waiver_problems.append({"id": w.get("id"), "problem": why})

    evidence_index: dict[str, str | None] = {}
    problems: list[dict] = []

    def check_refs(owner: str, refs: list[str]) -> bool:
        good = True
        for ref in refs:
            rel, digest = _resolve(root, ref)
            evidence_index[rel] = digest
            if digest is None:
                good = False
                problems.append({"owner": owner, "problem": f"evidence does not resolve: {rel}"})
        return good

    def check_tests(owner: str, ids: list[str]) -> bool:
        good = True
        for t in ids:
            outcome = tests.get(t)
            if outcome != "passed":
                good = False
                problems.append({"owner": owner, "problem": f"test {t} is {outcome or 'absent'}"})
        return good

    c_counts: dict[str, int] = {}
    for item in trace["items"]:
        st = item["status"]
        check_refs(item["check_id"], item.get("evidence", []))
        check_tests(item["check_id"], item.get("tests", []))
        if st != "present" and item["check_id"] in wmap:
            st = "waived"
        c_counts[st] = c_counts.get(st, 0) + 1

    comp_counts: dict[str, int] = {}
    for comp in register["components"]:
        if comp["status"] not in REGISTER_STATUSES:
            problems.append({"owner": comp["id"], "problem": f"bad status {comp['status']}"})
        refs_ok = check_refs(comp["id"], comp.get("evidence", []))
        tests_ok = check_tests(comp["id"], comp.get("tests", []))
        st = comp["status"]
        if st in ("CLOSED", "IMPLEMENTED_LOCAL") and not (refs_ok and tests_ok):
            st = "EVIDENCE_FAILED"
        if st != "CLOSED" and comp["id"] in wmap:
            st = "WAIVED"
        comp_counts[st] = comp_counts.get(st, 0) + 1

    for role in unresolved_owners(root):
        problems.append({"owner": "MC-01", "problem": f"OWNERS.yaml role unresolved: {role}"})

    doc_claims = absent_artifact_claims(root)
    for name in doc_claims:
        problems.append({"owner": "RG-08", "problem": f"{name} mentions MASTER.md as if present"})

    c_ok = all(k in ("present", "waived") for k in c_counts)
    comp_ok = all(k in ("CLOSED", "WAIVED") for k in comp_counts)
    blockers = []
    if not c_ok:
        blockers.append("not every C-item is present or validly waived")
    if not comp_ok:
        blockers.append("not every remediation component is CLOSED or validly waived")
    if problems:
        blockers.append(f"{len(problems)} evidence problem(s)")
    policy = _load(root, "TRUST_POLICY.json", {"release_keys": []})
    trusted = {k.get("key_id") for k in policy.get("release_keys", []) if k.get("status") == "active"}
    if signing_key is None:
        blockers.append("manifest unsigned: no release signing key / trust policy supplied")
    elif not key_id or key_id not in trusted:
        blockers.append("signing key is not an active key in TRUST_POLICY.json")
    if not policy.get("asymmetric_attestation"):
        blockers.append("no asymmetric provenance attestation (RG-06)")
    if not tests:
        blockers.append("no test report")

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "element": trace.get("element"),
        "version": _read(os.path.join(root, "VERSION")).strip(),
        "evaluated_on": today.isoformat(),
        "test_report": {"present": bool(tests), "counts": report.get("counts", {}),
                        "sha256": _sha(os.path.join(root, "test-report.json"))
                        if os.path.exists(os.path.join(root, "test-report.json")) else None,
                        "attested": False},
        "c_items": c_counts,
        "components": comp_counts,
        "waiver_problems": waiver_problems,
        "evidence": dict(sorted(evidence_index.items())),
        "problems": problems,
        "blockers": blockers,
        "verdict": "GO" if not blockers else "NO_GO",
    }
    body = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    manifest["manifest_digest"] = hashlib.sha256(body).hexdigest()
    if signing_key is not None:
        import hmac
        manifest["signature"] = {"alg": "HMAC-SHA256", "key_id": key_id, "kind": "integrity-mac-not-attestation",
                                 "value": hmac.new(signing_key, body, "sha256").hexdigest()}
    else:
        manifest["signature"] = None
    return manifest
