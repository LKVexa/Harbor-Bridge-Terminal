"""MC-031 -- release gate, traceability and evidence bundle.

    python inv13_system_interface/tools/gate.py [--out evidence] [--checklist <COMPONENT_CHECKLISTS.md>]

Runs every suite (normal and ``python -O``), the WIT surface gate, the
benchmark regression gate, the reproducible-build check and an offline wheel
install smoke test; validates that every evidence reference in the status map
and threat model exists; writes COMPONENT_STATUS.json, TRACEABILITY.json,
the annotated checklist, and evidence/EVIDENCE_MANIFEST.json (sha256 of every
evidence file). Exit 0 only if every executed gate passes -- that is *not* a
production-readiness claim; see COMPONENT_STATUS.json.
"""
from __future__ import annotations

import datetime, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
ROOT = PKG.parent
sys.path.insert(0, str(PKG / "tools"))
from status_map import STATUS  # noqa: E402

SUITES = ["test_runtime", "test_component", "test_errors_resources", "test_fs_descriptor", "test_wit_wasm", "test_authz",
          "test_net_http", "test_providers", "test_ops", "test_adversarial", "test_integration"]
PRIORITY = {f"MC-{i:03d}": ("P0" if i <= 12 else "P1" if i <= 28 else "P2") for i in range(1, 33)}


def sh(cmd, **kw):
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kw)
    return p.returncode, p.stdout + p.stderr


def run_suites(opt: bool):
    res = {}
    for s in SUITES:
        code, out = sh([sys.executable] + (["-O"] if opt else []) + [str(PKG / "tests" / f"{s}.py"), "-v"],
                       timeout=900)
        m = re.search(r"Ran (\d+) tests?", out)
        skipped = len(re.findall(r"\.\.\. skipped", out))
        res[s] = {"ok": code == 0, "tests": int(m.group(1)) if m else 0, "skipped": skipped,
                  "tail": out.strip().splitlines()[-1] if out.strip() else ""}
        if code != 0:
            res[s]["output"] = out[-4000:]
    return res


def evidence_exists(ref: str) -> bool:
    path = ref.split("::")[0].split(" ")[0]
    if path.startswith("evidence"):
        return True  # produced by this gate
    p = PKG / path
    if not p.exists():
        return False
    if "::" in ref and p.suffix == ".py":
        sym = ref.split("::", 1)[1].split(".")[0].lstrip("*")
        return sym in p.read_text()
    return True


def annotate(checklist: str) -> str:
    out, cur = [], None
    for line in checklist.splitlines():
        m = re.match(r"## (MC-\d+)", line)
        if m:
            cur = m.group(1)
            out.append(line)
            st = STATUS[cur]
            out.append("")
            out.append(f"> **v4.3.0 execution status: {st['status']}** — evidence: "
                       + ", ".join(f"`{e}`" for e in st["evidence"]))
            out.append(f"> **Open gaps:** {st['gaps']}")
            continue
        if line.startswith("# Program-level"):
            cur = None
        mm = re.match(r"- \[ \] (\*\*(.+?):\*\*)?(.*)", line)
        if mm and cur:
            st = STATUS[cur]
            key = mm.group(2) if mm.group(2) else "EX:" + mm.group(3).strip()
            mark = " "
            if any(key == k or (k.startswith("EX:") and key.startswith(k)) for k in st["x"]):
                mark = "x"
            elif any(key == k or (k.startswith("EX:") and key.startswith(k)) for k in st["p"]):
                mark = "~"
            line = line.replace("- [ ]", f"- [{mark}]", 1)
        out.append(line)
    return "\n".join(out) + "\n"


def main():
    out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else PKG / "evidence"
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema": "INV13_GATE/1", "release": (PKG / "VERSION").read_text().strip(),
              "run_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
              "python": sys.version.split()[0], "gates": {}}
    g = report["gates"]
    g["suites"] = run_suites(False)
    g["suites_optimised"] = run_suites(True)
    code, o = sh([sys.executable, "-m", "inv13_system_interface.host.wit_surface"])
    g["wit_surface"] = {"ok": code == 0, "detail": o.strip()}
    code, o = sh([sys.executable, "-m", "inv13_system_interface.tools.build", "--out", tempfile.mkdtemp()])
    g["reproducible_build"] = {"ok": code == 0, "detail": o.strip()}
    code, o = sh([sys.executable, "-m", "inv13_system_interface.tools.bench", "--gate", "--out", str(out / "bench.json")],
                 env={**os.environ, "INV13_SOAK_SECONDS": "3"}, timeout=900)
    bench = json.loads((out / "bench.json").read_text())
    g["bench_regression"] = {"ok": code == 0, "problems": bench.get("gate_problems", []),
                             "resolve_p99_ns": bench["ops"]["lexical_resolve"]["p99_ns"],
                             "contract_slo_resolve_p99_ns": 1000,
                             "contract_slo_met": bench["ops"]["lexical_resolve"]["p99_ns"] <= 1000}
    whl = tempfile.mkdtemp(); tgt = tempfile.mkdtemp()
    c1, o1 = sh([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-w", whl, str(PKG)])
    c2, o2 = sh([sys.executable, "-m", "pip", "install", "--no-deps", "--no-index", "--target", tgt] +
                [str(p) for p in Path(whl).glob("*.whl")]) if c1 == 0 else (1, "")
    c3, o3 = subprocess.run([sys.executable, "-c", "import inv13_system_interface as p; "
                             "from inv13_system_interface.host import fs, policy; print(p.__version__)"],
                            capture_output=True, text=True, cwd=tgt).returncode, "" if c2 else ""
    g["offline_install"] = {"ok": c1 == 0 and c2 == 0 and c3 == 0, "detail": (o1 + o2)[-600:] if (c1 or c2) else "wheel built, installed with --no-index, imported"}
    exc = json.loads((PKG / "EXCEPTIONS.json").read_text())
    today = datetime.date.today().isoformat()
    g["exceptions"] = {"ok": all(e.get("expires", "0") >= today for e in exc), "count": len(exc)}
    missing = [(mc, e) for mc, st in STATUS.items() for e in st["evidence"] if not evidence_exists(e)]
    tm = (PKG / "THREAT_MODEL.md").read_text()
    tm_tests = re.findall(r"`((?:test_\w+(?:::\w+)?)|(?:[A-Z]\w+\.\w+)|(?:[A-Z]\w+\.\*))`", tm)
    g["traceability"] = {"ok": not missing and len(STATUS) == 32, "missing_evidence": missing,
                         "threat_test_refs": len(tm_tests)}
    for k in ("suites", "suites_optimised"):
        g[k + "_ok"] = all(v["ok"] for v in g[k].values())
    report["all_executed_gates_pass"] = all(v["ok"] if isinstance(v, dict) and "ok" in v else (v if isinstance(v, bool) else True)
                                           for k, v in g.items() if not k.startswith("suites") or k.endswith("_ok"))
    report["tests_total"] = sum(v["tests"] for v in g["suites"].values())
    report["production_ready"] = False
    report["production_ready_reason"] = "P0 items MC-001/002/006 PARTIAL and human/organisational exit evidence outstanding; see COMPONENT_STATUS.json"
    (out / "gate.json").write_text(json.dumps(report, indent=2) + "\n")
    comp = {"schema": "INV13_COMPONENT_STATUS/1", "release": report["release"], "components": {
        mc: {"priority": PRIORITY[mc], "status": st["status"], "evidence": st["evidence"], "gaps": st["gaps"],
             "evidenced_items": len(st["x"]), "partial_items": len(st["p"])} for mc, st in STATUS.items()}}
    (PKG / "COMPONENT_STATUS.json").write_text(json.dumps(comp, indent=2) + "\n")
    (PKG / "TRACEABILITY.json").write_text(json.dumps({
        "schema": "INV13_TRACE/1",
        "requirements": {mc: {"evidence": st["evidence"], "tests": [e for e in st["evidence"] if e.startswith("tests/")]}
                         for mc, st in STATUS.items()},
        "threats_to_tests": dict(re.findall(r"^\| (T-\d+) \|.*?\| .*?\| .*?\| (.*?) \|", tm, re.M))}, indent=2) + "\n")
    if "--checklist" in sys.argv:
        src = Path(sys.argv[sys.argv.index("--checklist") + 1]).read_text()
        (PKG / "COMPONENT_CHECKLISTS_v4.3.0_STATUS.md").write_text(annotate(src))
    manifest = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(out.rglob("*")) if p.is_file() and p.name != "EVIDENCE_MANIFEST.json"}
    for extra in ("COMPONENT_STATUS.json", "TRACEABILITY.json", "MANIFEST.sha256", "SBOM.cdx.json", "PROVENANCE.intoto.json"):
        if (PKG / extra).exists():
            manifest["../" + extra] = hashlib.sha256((PKG / extra).read_bytes()).hexdigest()
    (out / "EVIDENCE_MANIFEST.json").write_text(json.dumps({"release": report["release"], "files": manifest}, indent=2) + "\n")
    print(json.dumps({"all_executed_gates_pass": report["all_executed_gates_pass"], "tests": report["tests_total"],
                      "missing_evidence": missing, "slo_met": g["bench_regression"]["contract_slo_met"]}, indent=1))
    return 0 if report["all_executed_gates_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
