"""GAP02-MC-48 release regression gate (+ MC-54 provenance-presence check).

Mandatory checks; any FAIL/NOT_RUN → NO_GO. Prints machine-readable JSON.

    python -m gap02_hardware_capability_discovery.tools.release_gate
"""
import hashlib, json, os, subprocess, sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_DOCS = ["README.md", "CHANGELOG.md", "RUNBOOKS.md", "COMPATIBILITY_MATRIX.json", "PK_CORE_CONTRACT.json",
                 "SBOM.cdx.json", "MANIFEST.sha256", "COMPONENT_STATUS.json", "MASTER.md"]


def check_manifest():
    bad = []
    for line in open(os.path.join(PKG, "MANIFEST.sha256")):
        h, p = line.split(None, 1); p = p.strip()[2:]
        fp = os.path.join(PKG, p)
        if not os.path.exists(fp) or hashlib.sha256(open(fp, "rb").read()).hexdigest() != h:
            bad.append(p)
    return bad


def run(skip_tests=False):
    checks = []
    def add(cid, ok, detail="", mandatory=True):
        checks.append({"id": cid, "result": "PASS" if ok is True else ("NOT_RUN" if ok is None else "FAIL"),
                       "mandatory": mandatory, "detail": detail})
    for d in REQUIRED_DOCS:
        add(f"present:{d}", os.path.exists(os.path.join(PKG, d)), "" if os.path.exists(os.path.join(PKG, d)) else "missing")
    try:
        bad = check_manifest(); add("manifest", not bad, ",".join(bad[:10]))
    except OSError as e:
        add("manifest", False, str(e))
    if skip_tests:
        add("unit-tests", None, "skipped by caller")
    else:
        r = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", os.path.join(PKG, "tests")],
                           capture_output=True, text=True, cwd=os.path.dirname(PKG), timeout=600)
        add("unit-tests", r.returncode == 0, r.stderr.strip().splitlines()[-1] if r.stderr.strip() else "")
    try:
        import pk_core  # noqa: F401
        add("pk_core-gate", None, "pk_core importable but full-estate gate must be run by MC-55 procedure")
    except ModuleNotFoundError:
        add("pk_core-gate", None, "pk_core not available")
    st = json.load(open(os.path.join(PKG, "COMPONENT_STATUS.json"))) if os.path.exists(os.path.join(PKG, "COMPONENT_STATUS.json")) else {"components": []}
    blocked = [c["id"] for c in st["components"] if c["status"] != "COMPLETE"]
    add("all-components-complete", not blocked and bool(st["components"]), f"{len(blocked)} not complete")
    verdict = "GO" if all(c["result"] == "PASS" for c in checks if c["mandatory"]) else "NO_GO"
    return {"schema": "GAP02_RELEASE_GATE/1", "verdict": verdict, "checks": checks}


if __name__ == "__main__":
    res = run("--skip-tests" in sys.argv)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res["verdict"] == "GO" else 1)
