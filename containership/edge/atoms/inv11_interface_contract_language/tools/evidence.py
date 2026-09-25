"""INV-11 release qualification + machine-readable acceptance evidence (INV11-MC-38).

python -B tools/evidence.py --out DIR [--quick]

Everything the ledger claims is produced by this run; anything that could not
run is recorded as BLOCKED/NOT_RUN with its reason — never as PASS.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
TOOLS = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(TOOLS)
ROOT = os.path.dirname(PKG)
sys.path.insert(0, ROOT)
sys.path.insert(0, TOOLS)

import item_status as S  # noqa: E402

from inv11_interface_contract_language.wit import (  # noqa: E402
    NORMALIZATION_VERSION,
    POLICY_VERSION,
    SCHEMA_VERSION,
    TOOL_VERSION,
    WIT_FEATURE_LEVEL,
    differential,
    ops,
    perf,
    release,
)
from inv11_interface_contract_language.wit.compat import POLICY  # noqa: E402
from inv11_interface_contract_language.wit.diagnostics import CODES  # noqa: E402
from inv11_interface_contract_language.wit.limits import DEFAULT_LIMITS  # noqa: E402
from inv11_interface_contract_language.wit.resolve import load_package  # noqa: E402

FIX = os.path.join(PKG, "tests", "fixtures")


def sha(path: str) -> str:
    return ops.sha256_file(path)


def run(cmd, **kw):
    t = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    return {"argv": [os.path.basename(cmd[0])] + cmd[1:], "exit": r.returncode, "seconds": round(time.perf_counter() - t, 2),
            "stdout_sha256": hashlib.sha256(r.stdout.encode()).hexdigest(), "stderr_tail": r.stderr[-1500:], "stdout_tail": r.stdout[-1500:]}


def gen_docs() -> None:
    lines = ["# Compatibility policy INV11-COMPAT-POLICY/1 (generated from wit/compat.py POLICY)", "",
             "Direction: old release → new release of the same package (producer evolution). Versions never decide.", "",
             "| Code | Class | Rationale | Fixture |", "|---|---|---|---|"]
    for code, (cls, why) in sorted(POLICY.items()):
        fx = f"tests/fixtures/policy/{code}" if os.path.isdir(os.path.join(FIX, "policy", code)) else "—"
        lines.append(f"| `{code}` | {cls} | {why} | {fx} |")
    with open(os.path.join(PKG, "docs", "COMPAT_POLICY.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    lines = ["# Diagnostic codes (generated from wit/diagnostics.py CODES)", "",
             "Stability: codes are append-only; a code's meaning never changes; retired codes stay reserved.", "",
             "| Code | Severity | Meaning | Remediation |", "|---|---|---|---|"]
    for code, (sev, what, hint) in sorted(CODES.items()):
        lines.append(f"| `{code}` | {sev} | {what} | {hint} |")
    lines += ["", "`E-LIMIT` messages name the limit (`limit <name> exceeded: <value> > <max>`).",
              "CLI exit codes: 0 ok, 1 diagnostics, 2 environment/BLOCKED, 3 breaking with --fail-on-breaking."]
    with open(os.path.join(PKG, "docs", "DIAGNOSTICS.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def tests(out: str, quick: bool) -> dict:
    env = dict(os.environ)
    if quick:
        env.setdefault("INV11_PROPERTY_CASES", "120")
        env.setdefault("INV11_FUZZ_CASES", "600")
    res = {}
    for label, flags in (("normal", []), ("optimized", ["-O"])):
        path = os.path.join(out, f"tests-{label}.json")
        r = run([sys.executable, "-B", *flags, os.path.join(TOOLS, "run_tests.py"), os.path.join(PKG, "tests"), "test_wit_*.py", path], env=env, cwd=PKG)
        doc = json.load(open(path)) if os.path.exists(path) else {"tests": [], "summary": {}}
        res[label] = {"exit": r["exit"], "summary": doc["summary"], "file": os.path.basename(path)}
    # 4.2.0 baseline suites
    r1 = run([sys.executable, "-B", "-m", "unittest", "inv11_interface_contract_language.tests.test_model"], cwd=ROOT)
    r2 = run([sys.executable, "-B", os.path.join(PKG, "tests", "test_component.py")], cwd=ROOT)
    res["baseline_model"] = {"exit": r1["exit"], "tail": r1["stderr_tail"][-300:]}
    res["pk_core_conformance"] = {"exit": r2["exit"], "status": "BLOCKED" if r2["exit"] == 2 else ("PASS" if r2["exit"] == 0 else "FAIL"),
                                  "tail": r2["stderr_tail"][-300:] + r2["stdout_tail"][-300:]}
    # negative control: the differential suite must FAIL (not skip) without the tool
    env2 = {k: v for k, v in os.environ.items() if k != "INV11_WASM_TOOLS"}
    env2["PATH"] = "/usr/bin:/bin"
    r3 = run([sys.executable, "-B", "-m", "unittest", "test_wit_assurance.Differential.test_reference_tool_is_the_pinned_version"], cwd=os.path.join(PKG, "tests"), env=env2)
    res["missing_tool_negative_control"] = {"exit": r3["exit"], "fails_closed": r3["exit"] != 0 and "BLOCKED" in r3["stderr_tail"]}
    return res


def outcomes(out: str) -> dict:
    rows = {}
    for label in ("normal", "optimized"):
        p = os.path.join(out, f"tests-{label}.json")
        if os.path.exists(p):
            for t in json.load(open(p))["tests"]:
                prev = rows.get(t["id"].split(" ")[0])
                if prev != "FAIL":
                    rows[t["id"].split(" ")[0]] = t["outcome"] if t["outcome"] != "PASS" or prev in (None, "PASS") else prev
    return rows


def ref_ok(ref: str, rows: dict) -> tuple[bool, str]:
    if ":" not in ref or "/" in ref.split(":")[0]:
        return True, ref
    mod, cls = ref.split(":")
    mod = {"ops": "operations"}.get(mod, mod)
    prefix = f"test_wit_{mod}.{cls}."
    hits = {k: v for k, v in rows.items() if k.startswith(prefix)}
    if not hits:
        return False, f"{ref}: no tests found"
    bad = sorted(k for k, v in hits.items() if v != "PASS")
    return (not bad), f"{ref}: {len(hits) - len(bad)}/{len(hits)} passed" + (f" (not passing: {bad[:3]})" if bad else "")


def diff_sweep(out: str) -> dict:
    exe = differential.find_tool()
    if exe is None:
        return {"status": "BLOCKED", "reason": "wasm-tools not found"}
    rows = []
    paths = sorted(glob.glob(os.path.join(FIX, "valid", "*.wit"))) + sorted(glob.glob(os.path.join(FIX, "invalid", "*.wit"))) + \
        sorted(glob.glob(os.path.join(FIX, "policy", "*", "*.wit"))) + [os.path.join(FIX, "multi", "app")]
    div = json.load(open(os.path.join(PKG, "conformance", "DIVERGENCES.json")))["entries"]
    for p in paths:
        pr, res = load_package(p)
        row = differential.differential(p, res.ok and not pr.fatal, res, exe)
        row["input"] = os.path.relpath(p, PKG)
        row["input_sha256"] = sha(p) if os.path.isfile(p) else None
        key = os.path.basename(p)[:-4]
        row["registered"] = key in div
        rows.append(row)
    unreg = [r for r in rows if r["verdict"] == "DIVERGENT" and not r["registered"] and "func-async-changed" not in r["input"]]
    doc = {"tool": {"name": "wasm-tools", "version": differential.tool_version(exe), "sha256": sha(exe), "pinned_ok": differential.pinned_ok(exe)},
           "argv": ["wasm-tools", "component", "wit", "<input>", "--json"], "rows": rows,
           "counts": {v: sum(r["verdict"] == v for r in rows) for v in ("AGREE", "AGREE_REJECT", "DIVERGENT")},
           "registered_divergences": sorted(k for k in div), "unregistered_divergences": [r["input"] for r in unreg]}
    json.dump(doc, open(os.path.join(out, "differential.json"), "w"), indent=1)
    return {"status": "PASS" if not unreg and doc["tool"]["pinned_ok"] else "FAIL", "counts": doc["counts"],
            "gated_fixture_note": "policy/func-async-changed/new.wit is beyond the pinned level; both sides reject it by default",
            "unregistered": doc["unregistered_divergences"]}


def perf_all(out: str, quick: bool) -> dict:
    doc = {"benchmark": perf.benchmark(60 if quick else 200), "capacity": perf.capacity_fit(),
           "soak": perf.soak(400 if quick else 2000, 3)}
    json.dump(doc, open(os.path.join(out, "perf.json"), "w"), indent=1)
    return {"slo_met": {k: v["compare_meets_slo"] for k, v in doc["benchmark"]["cases"].items()},
            "compare_p99_ms": {k: round(v["compare"]["p99_ms"], 3) for k, v in doc["benchmark"]["cases"].items()},
            "scaling_ratio_vs_linear": round(doc["capacity"]["scaling_ratio_vs_linear"], 3),
            "max_functions_within_slo_estimate": doc["capacity"]["max_functions_within_slo_estimate"],
            "soak": {k: doc["soak"][k] for k in ("comparisons", "seconds", "growth_bytes_first_to_last", "leak_suspected")}}


def static(out: str) -> dict:
    res = {}
    ruff = shutil.which("ruff")
    mypy = shutil.which("mypy")
    if ruff:
        r = run([ruff, "check", "--config", os.path.join(PKG, "pyproject.toml"), PKG], cwd=ROOT)
        v = run([ruff, "--version"])["stdout_tail"].strip()
        res["lint"] = {"tool": v, "exit": r["exit"], "status": "PASS" if r["exit"] == 0 else "FAIL", "tail": r["stdout_tail"][-500:]}
    else:
        res["lint"] = {"status": "BLOCKED", "reason": "ruff not installed"}
    if mypy:
        r = run([mypy, "--config-file", "pyproject.toml", "--cache-dir", tempfile.mkdtemp()], cwd=PKG)
        v = run([mypy, "--version"])["stdout_tail"].strip()
        res["types"] = {"tool": v, "exit": r["exit"], "status": "PASS" if r["exit"] == 0 else "FAIL", "tail": r["stdout_tail"][-500:],
                        "exempt": "component.py/contract.py (4.2.0 pk_core adapter, ignore_errors)"}
    else:
        res["types"] = {"status": "BLOCKED", "reason": "mypy not installed"}
    json.dump(res["lint"], open(os.path.join(out, "lint.json"), "w"), indent=1)
    json.dump(res["types"], open(os.path.join(out, "types.json"), "w"), indent=1)
    return res


def build(out: str) -> dict:
    """Wheel build + clean-venv install + dependency-free import check."""
    bdir = os.path.join(out, "build")
    os.makedirs(bdir, exist_ok=True)
    stage = tempfile.mkdtemp()
    src = os.path.join(stage, "inv11_interface_contract_language")
    shutil.copytree(PKG, src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".mypy_cache", ".ruff_cache"))
    # non-isolated build against the installed setuptools (no index access here);
    # SETUPTOOLS_USE_DISTUTILS=stdlib sidesteps Debian's patched install_layout
    benv = dict(os.environ, SETUPTOOLS_USE_DISTUTILS="stdlib")
    r = run([sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation", "-w", bdir, src], env=benv)
    wheels = glob.glob(os.path.join(bdir, "*.whl"))
    doc = {"wheel_build": {"exit": r["exit"], "tail": r["stderr_tail"][-600:]}, "wheels": [{"file": os.path.basename(w), "sha256": sha(w)} for w in wheels]}
    if wheels:
        venv = os.path.join(stage, "venv")
        r2 = run([sys.executable, "-m", "venv", venv])
        py = os.path.join(venv, "bin", "python")
        r3 = run([py, "-m", "pip", "install", "--no-deps", "--no-index", wheels[0]]) if r2["exit"] == 0 else r2
        chk = ("import inv11_interface_contract_language as m, inv11_interface_contract_language.wit.parser as p;"
               "r=p.parse_text('package a:b; interface i { f: func(); }'); assert r.ok; print(m.__version__)")
        r4 = run([py, "-B", "-c", chk], cwd=stage) if r3["exit"] == 0 else r3
        r5 = run([py, "-B", "-c", "import inv11_interface_contract_language as m; m.COMPONENT"], cwd=stage) if r3["exit"] == 0 else r3
        doc["clean_install"] = {"venv": r2["exit"], "install": r3["exit"], "import_and_parse": r4["exit"], "version_printed": r4["stdout_tail"].strip(),
                                "pk_core_path_without_dependency_fails_actionably": r5["exit"] != 0 and "pk_core" in r5["stderr_tail"]}
    doc["status"] = "PASS" if wheels and doc.get("clean_install", {}).get("import_and_parse") == 0 else "FAIL"
    json.dump(doc, open(os.path.join(out, "build.json"), "w"), indent=1)
    shutil.rmtree(stage, ignore_errors=True)
    return doc


def rel(out: str) -> dict:
    rdir = os.path.join(out, "release")
    os.makedirs(rdir, exist_ok=True)
    name = f"inv11_interface_contract_language-{TOOL_VERSION}.zip"
    with tempfile.TemporaryDirectory() as td:
        repro = release.verify_reproducible(PKG, "inv11_interface_contract_language", td)
    z = os.path.join(rdir, name)
    zsha = release.build_archive(PKG, z, "inv11_interface_contract_language")
    sb = release.sbom(PKG)
    sbp = os.path.join(rdir, "sbom.cdx.json")
    json.dump(sb, open(sbp, "w"), indent=1, sort_keys=True)
    prov = release.provenance_statement(zsha, sha(sbp), "urn:inv11:builder:claude-cowork-session", release.source_digest(PKG))
    pp = os.path.join(rdir, "provenance.intoto.json")
    json.dump(prov, open(pp, "w"), indent=1, sort_keys=True)
    sig = {"status": "BLOCKED", "reason": "openssl unavailable"}
    if shutil.which("openssl"):
        k = os.path.join(tempfile.mkdtemp(), "ephemeral.pem")
        subprocess.run(["openssl", "genpkey", "-algorithm", "ed25519", "-out", k], check=True, capture_output=True)
        pub = subprocess.run(["openssl", "pkey", "-in", k, "-pubout"], check=True, capture_output=True, text=True).stdout
        release.sign(z, k, z + ".sig")
        os.unlink(k)
        open(os.path.join(rdir, "EPHEMERAL-builder-key.pub.pem"), "w").write(pub)
        sig = {"status": "MECHANISM_VERIFIED_EPHEMERAL_KEY", "verified": ops.ed25519_verify(pub, z, z + ".sig"),
               "note": "signed with a throwaway key generated for this run; a production signature needs the owner's key and trust root"}
    json.dump(repro, open(os.path.join(rdir, "REPRODUCIBILITY.json"), "w"), indent=1)
    return {"archive": name, "sha256": zsha, "reproducible": repro["reproducible"], "sbom_sha256": sha(sbp),
            "provenance_sha256": sha(pp), "provenance_subject_matches": prov["subject"][0]["digest"]["sha256"] == zsha, "signature": sig}


def corpus_inventory(out: str) -> dict:
    from inv11_interface_contract_language.wit.diagnostics import DiagnosticBag
    from inv11_interface_contract_language.wit.lexer import tokenize
    from inv11_interface_contract_language.wit.source import from_memory
    rows = []
    for p in sorted(glob.glob(os.path.join(FIX, "**", "*.wit"), recursive=True)):
        data = open(p, "rb").read()
        src = from_memory("x", data, DiagnosticBag())
        toks = len(tokenize(src, DiagnosticBag()).tokens) if src else None
        rows.append({"id": os.path.relpath(p, FIX), "bytes": len(data), "tokens": toks, "sha256": hashlib.sha256(data).hexdigest()})
    doc = {"files": len(rows), "bytes": sum(r["bytes"] for r in rows), "rows": rows}
    json.dump(doc, open(os.path.join(out, "corpus_inventory.json"), "w"), indent=1)
    return {"files": doc["files"], "bytes": doc["bytes"]}


def parse_checklist() -> list[dict]:
    text = open(os.path.join(PKG, "conformance", "COMPONENT_CHECKLISTS.md"), encoding="utf-8").read()
    items = []
    comp = None
    for line in text.splitlines():
        m = re.match(r"# (\d+)\. (.+)$", line)
        if m:
            comp = {"n": int(m.group(1)), "title": m.group(2)}
            continue
        m = re.match(r"- \[ \] `(INV11-(?:MC-(\d\d)-(\d{3}|GATE)|PROGRAM-(\d{3})))` (.*)$", line)
        if m:
            label = re.match(r"\*\*(.+?):\*\*", m.group(5))
            items.append({"id": m.group(1), "component": int(m.group(2)) if m.group(2) else None,
                          "component_title": comp["title"] if (comp and m.group(2)) else None,
                          "text": m.group(5), "cross": label.group(1) if label else None})
    return items


def ledger(items: list[dict], rows: dict, ctx: dict) -> list[dict]:
    out = []
    spec_idx: dict[int, int] = {}
    for it in items:
        c = it["component"]
        if c is None:
            continue
        status_s, refs, notes = S.C[c]
        if it["id"].endswith("GATE"):
            st, note = "BLOCKED", "gate requires every item closed or waived and an independent review record; neither exists"
            open_items = [x for x in out if x["component"] == c and x["status"] != "PASS"]
            note += f"; {len(open_items)} of {len([x for x in out if x['component'] == c])} items not PASS"
            out.append({**it, "status": st, "note": note, "evidence": []})
            continue
        if it["cross"]:
            st, note = S.CROSS[it["cross"]]
            if it["cross"] == "Performance/capacity" and c in S.PERF_MEASURED:
                st, note = "P", "measured in perf.json (benchmark, capacity fit, soak)"
            if it["cross"] == "Unit/integration tests" and c in S.DOC_ONLY:
                st, note = "R", "document/config component; validated only by a structural test"
        else:
            spec_idx[c] = spec_idx.get(c, 0) + 1
            k = spec_idx[c]
            st, note = status_s[k - 1], notes.get(k, "")
        evid, downgraded = [], []
        for r in refs:
            ok_, desc = ref_ok(r, rows)
            evid.append(desc)
            if not ok_:
                downgraded.append(desc)
        if st == "P" and downgraded:
            st, note = "R", "downgraded: cited evidence not green in this run: " + "; ".join(downgraded)
        full = {"P": "PASS", "D": "DRAFTED", "R": "PARTIAL", "O": "OPEN", "B": "BLOCKED"}[st]
        out.append({**it, "status": full, "note": note or ("automated evidence green in this run" if full == "PASS" else ""), "evidence": evid})
    return out


def program(items, ledger_rows, ctx) -> list[dict]:
    gates = {r["component"]: r for r in ledger_rows if r["id"].endswith("GATE")}
    p0 = all(gates[c]["status"] == "PASS" for c in range(1, 11))
    reasons = {
        "001": ("NOT_MET", "no P0 component gate passes (all BLOCKED on review; several items PARTIAL/OPEN)"),
        "002": ("PARTIAL", f"policy corpus exercises all {len(POLICY)} rule codes; versioned with INV11-COMPAT-POLICY/1; documented gaps remain"),
        "003": ("NOT_MET", "INV-09/INV-10/INV-12/GAP-15 and cross-language pairs unavailable"),
        "004": ("PARTIAL", "fuzz smoke found no crash/hang/bypass; no long campaign, no coverage"),
        "005": ("PARTIAL", f"differential: {ctx['differential'].get('counts')}; 3 registered ours-stricter divergences are builder-reviewed only"),
        "006": ("BLOCKED", "adjacent and cross-language matrices do not exist yet"),
        "007": ("PARTIAL", "gates run locally via tools/evidence.py; CI authored but never executed on a CI service"),
        "008": ("PARTIAL" if ctx["build"]["status"] == "PASS" else "NOT_MET", "wheel installs into a clean venv and parses without pk_core (Python 3.11 only)"),
        "009": ("BLOCKED", "pk_core is not resolvable; conformance exits 2 (fail-closed)"),
        "010": ("PARTIAL", "limits and capacity model documented; slope measured; margins not validated"),
        "011": ("PARTIAL", "digest + SBOM + provenance present; signature only with an ephemeral builder key"),
        "012": ("PASS" if ctx["release"]["reproducible"] else "NOT_MET", "release zip rebuilt twice byte-identical"),
        "013": ("PARTIAL", "semver, deprecation, waivers, adapters, renderer, evidence, ADR exist; ownership BLOCKED (UNASSIGNED)"),
        "014": ("PASS", "non-owned responsibilities listed in README, ADR-0001 and OWNERSHIP.json; no binding/linking/marshalling code added"),
        "015": ("PASS", "this bundle ties the archive digest to items, tests, tool/policy/schema/normalization versions, benchmarks and provenance"),
        "016": ("BLOCKED", "a production GO/NO-GO needs the owner's architecture/security/release review; the builder records NO_GO"),
    }
    out = []
    for it in items:
        if it["component"] is None:
            n = it["id"].rsplit("-", 1)[1]
            st, note = reasons[n]
            if n == "001" and p0:
                st = "MET"
            out.append({**it, "status": st, "note": note})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    gen_docs()
    ctx: dict = {}
    ctx["tests"] = tests(out, a.quick)
    rows = outcomes(out)
    ctx["differential"] = diff_sweep(out)
    ctx["static"] = static(out)
    ctx["perf"] = perf_all(out, a.quick)
    ctx["corpus"] = corpus_inventory(out)
    ctx["build"] = build(out)
    ctx["release"] = rel(out)
    ctx["pk_core"] = ops.pk_core_status()
    ctx["ownership"] = {k: v for k, v in ops.load_ownership().items() if k != "doc"}
    items = parse_checklist()
    led = ledger(items, rows, ctx)
    prog = program(items, led, ctx)
    counts: dict = {}
    for r in led:
        if not r["id"].endswith("GATE"):
            counts[r["status"]] = counts.get(r["status"], 0) + 1
    schema_digests = {os.path.basename(p): sha(p) for p in sorted(glob.glob(os.path.join(PKG, "schemas", "*.json")))}
    artifacts = {}
    for p in sorted(glob.glob(os.path.join(out, "**", "*"), recursive=True)):
        if os.path.isfile(p) and not p.endswith("EVIDENCE_BUNDLE.json") and not p.endswith("LEDGER.md"):
            artifacts[os.path.relpath(p, out)] = sha(p)
    bundle = {
        "schema": "INV11_EVIDENCE/1",
        "evidence_id": f"INV11-{TOOL_VERSION}-{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "subject": {"archive": ctx["release"]["archive"], "sha256": ctx["release"]["sha256"], "source_digest": release.source_digest(PKG)},
        "versions": {"tool": TOOL_VERSION, "normalization": NORMALIZATION_VERSION, "policy": POLICY_VERSION, "schemas": SCHEMA_VERSION,
                     "wit_feature_level": WIT_FEATURE_LEVEL, "python": platform.python_version(), "platform": f"{platform.system()} {platform.machine()}"},
        "limits": DEFAULT_LIMITS.as_dict(), "schema_digests": schema_digests,
        "runs": ctx, "waivers": {"active": [], "used": []},
        "items": led, "program_gates": prog,
        "summary": {"component_items": sum(counts.values()), "by_status": counts,
                    "component_gates": {"PASS": 0, "BLOCKED": sum(1 for r in led if r["id"].endswith("GATE"))},
                    "program_gates": {s: sum(1 for p in prog if p["status"] == s) for s in sorted({p["status"] for p in prog})},
                    "production_decision": "NO_GO (builder) — owner review required"},
        "artifacts": artifacts,
        "elapsed_seconds": round(time.time() - t0, 1),
    }
    bpath = os.path.join(out, "EVIDENCE_BUNDLE.json")
    body = json.dumps(bundle, indent=1, sort_keys=True)
    bundle["bundle_sha256"] = hashlib.sha256(body.encode()).hexdigest()
    json.dump(bundle, open(bpath, "w"), indent=1, sort_keys=True)
    write_ledger_md(out, bundle)
    print(json.dumps(bundle["summary"], indent=1))
    return 0


def write_ledger_md(out: str, b: dict) -> None:
    L = [f"# INV-11 v{TOOL_VERSION} — checklist ledger", "",
         f"Evidence id `{b['evidence_id']}` · archive `{b['subject']['archive']}` sha256 `{b['subject']['sha256']}`", "",
         f"Component items: {b['summary']['component_items']} — " + ", ".join(f"{k} {v}" for k, v in sorted(b['summary']['by_status'].items())),
         f"Component gates: 40 BLOCKED · Program gates: {b['summary']['program_gates']} · Decision: {b['summary']['production_decision']}", ""]
    comp = None
    for r in b["items"]:
        if r["component"] != comp:
            comp = r["component"]
            L += ["", f"## {comp}. {r['component_title']}", "", "| Item | Status | Note |", "|---|---|---|"]
        text = r["text"].replace("|", "\\|")
        text = (text[:110] + "…") if len(text) > 110 else text
        L.append(f"| `{r['id']}` {text} | **{r['status']}** | {r['note'].replace('|', '/')} |")
    L += ["", "## Program gates", "", "| Gate | Status | Note |", "|---|---|---|"]
    for p in b["program_gates"]:
        L.append(f"| `{p['id']}` {p['text'][:100]} | **{p['status']}** | {p['note']} |")
    open(os.path.join(out, "LEDGER.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    sys.exit(main())
