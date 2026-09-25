"""Release tooling in one module (components 15, 25, 39, 47, 48, 49, 50, 53, 54).

    python -m inv07_gitops_transition_layer.components.tools.gates regression   # 47
    python -m ... sbom          # 25/53: CycloneDX 1.5 SBOM + license inventory
    python -m ... dashboards    # 39: Grafana dashboard + Prometheus alert rules
    python -m ... lint          # 49: AST security/static rules
    python -m ... coverage      # 49: stdlib line coverage of components/*.py
    python -m ... platform      # 48: platform/determinism report
    python -m ... apidocs       # 54: docs/API_REFERENCE.md generated from code
    python -m ... docs          # 51/54: documentation consistency check
    python -m ... manifest      # 50: MANIFEST.sha256 over the overlay

Every sub-command writes machine-readable output under ``evidence/`` (or the
named file) and exits non-zero on a failed gate.  Thresholds used by
``regression`` are PROPOSED values -- they gate, but a human must approve them
(docs/WAIVERS.json W-004).
"""
from __future__ import annotations

import ast
import hashlib
import json
import locale
import os
import platform
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMP = os.path.dirname(HERE)
PKG = os.path.dirname(COMP)
ROOT = os.path.dirname(PKG)
EVID = os.path.join(COMP, "evidence")
sys.path.insert(0, ROOT)
sys.dont_write_bytecode = True
VERSION = "5.0.0"

THRESHOLDS = {  # PROPOSED -- p50 seconds (local laptop-class hardware)
    "ed25519_verify": 0.10, "commit_verify": 0.12, "yaml_parse_deployment": 0.01,
    "reconcile_no_change_100_resources": 2.0, "reconcile_initial_100_resources": 5.0,
    "cold_start_build_recover": 3.0,
}
REGRESSION_FACTOR = 1.5


def _write(name, doc):
    os.makedirs(EVID, exist_ok=True)
    with open(os.path.join(EVID, name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    return doc


def regression(baseline: dict, current: dict) -> tuple[int, list[str]]:
    b = {r["name"]: r for r in baseline["results"]}
    fails = []
    for r in current["results"]:
        name, p50 = r["name"], r["p50"]
        lim = THRESHOLDS.get(name)
        if lim is not None and p50 > lim:
            fails.append(f"{name}: p50 {p50:.4f}s > absolute threshold {lim}s")
        if (r.get("n", 10) >= 10 and name in b and b[name]["p50"] and p50 > b[name]["p50"] * REGRESSION_FACTOR
                and p50 > 0.005):   # relative check only where p50 is a real percentile (n >= 10)
            fails.append(f"{name}: p50 {p50:.4f}s regressed > {REGRESSION_FACTOR}x baseline {b[name]['p50']:.4f}s")
    return (1 if fails else 0), fails


def files(root=PKG):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in ("__pycache__", ".git"))
        for f in sorted(fns):
            if f.endswith((".pyc", ".tmp")):
                continue
            p = os.path.join(dp, f)
            out.append(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    return out


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


def sbom() -> dict:
    comps = [{"type": "file", "name": f, "hashes": [{"alg": "SHA-256", "content": sha256(os.path.join(ROOT, f))}]}
             for f in files() if not f.startswith(f"{os.path.basename(PKG)}/components/evidence/")]
    doc = {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
           "metadata": {"component": {"type": "application", "name": "inv07-gitops-transition-layer",
                                      "version": VERSION, "licenses": [{"license": {"name": "UNDECLARED -- owner decision pending (W-006)"}}]},
                        "tools": [{"name": "inv07-gates", "version": VERSION}]},
           "components": comps,
           "dependencies": [],
           "properties": [{"name": "runtime.third_party_python_dependencies", "value": "none (stdlib only)"},
                          {"name": "runtime.external_executables", "value": "git>=2.31; optional gpg"},
                          {"name": "vendored.from", "value": "gap09_unified_observability v5.1.0 components "
                                                             "(ed25519.py, canonical.py; adapted audit/config/controls)"}]}
    lic = {"schema": "INV07-LICENSE-INVENTORY/1", "project_license": "UNDECLARED (owner decision; W-006)",
           "third_party_runtime": [], "vendored": [
               {"source": "gap09_unified_observability v5.1.0 (same owner, shop build)", "files":
                ["components/ed25519.py", "components/canonical.py", "components/vectors/rfc8032_ed25519.json"],
                "license": "no LICENSE file in donor (owner's own work)"}],
           "test_lanes": [{"name": "jsonschema", "use": "optional reference validator lane", "license": "MIT"}]}
    _write("LICENSE_INVENTORY.json", lic)
    return _write("SBOM.cdx.json", doc)


ALERTS = [
    ("INV07UnsignedCommitRefused", "increase(inv07_unsigned_refusals_total[5m]) > 0", "critical",
     "A commit failed signature/trust/provenance verification (provenance SLO has no budget)."),
    ("INV07DriftReverted", "increase(inv07_drift_reverts_total[15m]) > 0", "warning",
     "Out-of-band changes were reverted; find who changed live state."),
    ("INV07SyncStalled", "time() - inv07_last_sync_timestamp_seconds > 3 * 60", "critical",
     "No successful sync for three sync intervals (convergence SLO burn)."),
    ("INV07ConvergenceSLOBurn", "sum(rate(inv07_syncs_total{outcome=~\"failed|refused\"}[1h])) / "
     "sum(rate(inv07_syncs_total[1h])) > 0.01", "warning", "More than 1% of reconciliations failing (error budget)."),
    ("INV07PartialApplyFrozen", "inv07_frozen == 1", "critical", "Reconciliation frozen (manual or partial apply)."),
    ("INV07GitCircuitOpen", "inv07_circuit_open == 1", "warning", "Git dependency circuit breaker open."),
    ("INV07NoLeader", "max(inv07_leader) == 0", "critical", "No controller instance holds the lease."),
    ("INV07LeaderChurn", "changes(inv07_leader[30m]) > 4", "warning", "Leadership flapping."),
    ("INV07QueueSaturated", "inv07_queue_saturation > 0.8", "warning", "Admission queue above 80%."),
    ("INV07PolicyDenials", "increase(inv07_policy_denials_total[15m]) > 0", "info", "Policy denied desired state."),
    ("INV07LogDrops", "increase(inv07_log_drops_total[15m]) > 0", "warning", "Structured log sink failing."),
]


def dashboards() -> dict:
    dep = os.path.join(COMP, "deploy")
    os.makedirs(dep, exist_ok=True)
    lines = ["groups:", "  - name: inv07-gitops", "    rules:"]
    for name, expr, sev, desc in ALERTS:
        lines += [f"      - alert: {name}", f"        expr: {json.dumps(expr)}", "        for: 2m",
                  f"        labels: {{severity: {sev}}}",
                  f"        annotations: {{summary: {json.dumps(desc)}, runbook: \"docs/RUNBOOKS.md#{name.lower()}\"}}"]
    with open(os.path.join(dep, "prometheus-alerts.yaml"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    panels = [("Syncs by outcome", "sum by (outcome) (rate(inv07_syncs_total[5m]))"),
              ("Reconcile p95 (s)", "histogram_quantile(0.95, sum by (le) (rate(inv07_reconcile_seconds_bucket[5m])))"),
              ("Verify p95 (s)", "histogram_quantile(0.95, sum by (le) (rate(inv07_verify_seconds_bucket[5m])))"),
              ("Unsigned/untrusted refusals", "sum by (reason) (increase(inv07_unsigned_refusals_total[1h]))"),
              ("Drift reverts", "increase(inv07_drift_reverts_total[1h])"),
              ("Seconds since last sync", "time() - inv07_last_sync_timestamp_seconds"),
              ("Leader", "inv07_leader"), ("Frozen", "inv07_frozen"), ("Git circuit open", "inv07_circuit_open"),
              ("Queue saturation", "inv07_queue_saturation"),
              ("Dependency errors", "sum by (dependency) (increase(inv07_dependency_errors_total[1h]))")]
    dash = {"title": "INV-07 GitOps transition layer", "uid": "inv07-gitops", "schemaVersion": 39,
            "tags": ["inv07", "gitops"], "time": {"from": "now-6h", "to": "now"},
            "panels": [{"id": i + 1, "type": "timeseries", "title": t,
                        "gridPos": {"h": 8, "w": 12, "x": (i % 2) * 12, "y": (i // 2) * 8},
                        "targets": [{"expr": q, "refId": "A"}]} for i, (t, q) in enumerate(panels)]}
    with open(os.path.join(dep, "grafana-dashboard.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dash, fh, indent=1, sort_keys=True)
    return {"alerts": len(ALERTS), "panels": len(panels)}


FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}


def lint() -> dict:
    findings = []
    for f in files(COMP):
        if not f.endswith(".py") or "/tests/" in f:
            continue
        src = open(os.path.join(ROOT, f), encoding="utf-8").read()
        tree = ast.parse(src, f)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                fn = node.func
                name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else "")
                if isinstance(fn, ast.Name) and name in FORBIDDEN_CALLS:   # builtins only (re.compile is fine)
                    findings.append((f, node.lineno, f"forbidden call {name}"))
                if name in ("loads", "load") and isinstance(fn, ast.Attribute) and getattr(fn.value, "id", "") in (
                        "pickle", "marshal", "yaml"):
                    findings.append((f, node.lineno, "unsafe deserializer"))
                for kw in node.keywords:
                    if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        findings.append((f, node.lineno, "subprocess shell=True"))
            if isinstance(node, ast.Assert) and "/tools/" not in f:
                findings.append((f, node.lineno, "bare assert in library code (stripped by -O)"))
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                findings.append((f, node.lineno, "bare except"))
    return _write("LINT.json", {"schema": "INV07-LINT/1", "findings": [list(x) for x in findings],
                                "rules": sorted(FORBIDDEN_CALLS) + ["unsafe deserializer", "shell=True", "bare assert",
                                                                    "bare except"], "passed": not findings})


def coverage() -> dict:
    import trace
    import unittest
    tdir = os.path.join(COMP, "tests")
    sys.path.insert(0, tdir)
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.prefix, sys.exec_prefix])
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for fn in sorted(os.listdir(tdir)):
        if fn.startswith("test_") and fn.endswith(".py") and fn != "test_tools.py":
            suite.addTests(loader.loadTestsFromName(fn[:-3]))
    result = {}
    import threading
    threading.settrace(tracer.globaltrace)          # server handler threads too
    tracer.runfunc(lambda: result.setdefault("r", unittest.TextTestRunner(stream=open(os.devnull, "w"),
                                                                           verbosity=0).run(suite)))
    threading.settrace(None)
    counts = tracer.results().counts
    per = {}
    for f in files(COMP):
        if not f.endswith(".py") or "/tests/" in f or "/tools/" in f or f.endswith(("__init__.py", "run_all.py",
                                                                                     "bindings.py")):
            continue
        p = os.path.join(ROOT, f)
        exe = set()
        with open(p, encoding="utf-8") as fh:
            src = fh.read()
        # statements inside function bodies only: module/class-level lines run at import, before tracing starts
        for fnode in ast.walk(ast.parse(src)):
            if isinstance(fnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for node in ast.walk(fnode):
                    if node is fnode or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        continue
                    if isinstance(node, ast.stmt) and not (isinstance(node, ast.Expr) and
                                                           isinstance(getattr(node, "value", None), ast.Constant)):
                        exe.add(node.lineno)
        hit = {ln for (fn, ln), c in counts.items() if os.path.abspath(fn) == os.path.abspath(p) and c > 0}
        per[f] = {"statements": len(exe), "covered": len(exe & hit),
                  "percent": round(100.0 * len(exe & hit) / len(exe), 1) if exe else 100.0}
    tot_s = sum(v["statements"] for v in per.values())
    tot_c = sum(v["covered"] for v in per.values())
    r = result["r"]
    return _write("COVERAGE.json", {"schema": "INV07-COVERAGE/1", "kind": "statement (stdlib trace); no branch "
                                    "or mutation coverage", "total_percent": round(100.0 * tot_c / tot_s, 1),
                                    "files": per, "tests_run": r.testsRun, "failures": len(r.failures) + len(r.errors),
                                    "proposed_threshold_percent": 85})


def platform_report() -> dict:
    from inv07_gitops_transition_layer.components.canonical import canonicalize
    from inv07_gitops_transition_layer.components import ed25519
    sample = {"b": [1, 2.5, "ü"], "a": {"z": None, "y": True}}
    canon = canonicalize(sample)
    sig = ed25519.sign(b"\x01" * 32, canon.encode()).hex()
    gitv = subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
    os.makedirs(EVID, exist_ok=True)
    probe = os.path.join(EVID, "CaseProbe.tmp")
    open(probe, "w").close()
    case_insensitive = os.path.exists(os.path.join(EVID, "caseprobe.tmp"))
    os.unlink(probe)
    return _write("PLATFORM.json", {"schema": "INV07-PLATFORM/1", "os": platform.system(), "release": platform.release(),
                                    "machine": platform.machine(), "python": platform.python_version(),
                                    "implementation": platform.python_implementation(), "git": gitv,
                                    "locale": locale.getlocale(), "fs_case_insensitive": case_insensitive,
                                    "canonical_sha256": hashlib.sha256(canon.encode()).hexdigest(),
                                    "expected_canonical_sha256": "see tests/test_tools.TestPlatform",
                                    "ed25519_signature": sig})


def api_docs() -> str:
    from inv07_gitops_transition_layer.components import cli, config, errors, schemas
    from inv07_gitops_transition_layer.components.telemetry import Registry, standard_metrics
    out = [f"# INV-07 API & operator reference (v{VERSION})", "",
           "_Generated by `tools/gates.py apidocs` from the running code -- do not edit by hand._", "",
           "## Wire schemas", ""]
    for n in sorted(schemas.SCHEMAS):
        s = schemas.SCHEMAS[n]
        out.append(f"### `{n.replace('_1', '/1').replace('PK_GITOPS_', 'PK_GITOPS_')}` -- `schemas/{n}.schema.json`")
        out.append("")
        out.append("| field | required | constraint |")
        out.append("|---|---|---|")
        for k, v in s["properties"].items():
            c = v.get("const") or v.get("enum") or v.get("type") or ""
            out.append(f"| `{k}` | {'yes' if k in s['required'] else 'no'} | `{json.dumps(c)[:80]}` |")
        out.append("")
    out += ["Compatibility: additive optional fields only within a major; anything else is `/N+1` "
            "(see `schemas.py` docstring).", "", "## Error codes (`PK_GITOPS_ERROR/1`)", "",
            "| code | name | category | retry |", "|---|---|---|---|"]
    for code, (name, cat, retry) in sorted(errors.REGISTRY.items()):
        out.append(f"| `{code}` | {name} | {cat} | {retry} |")
    out += ["", "## Configuration (`PK_GITOPS_CONFIG/1`)", "", "| section.key | type | range / values | default |",
            "|---|---|---|---|"]
    for sec, keys in config.SCHEMA.items():
        for k, (typ, lo, hi) in keys.items():
            rng = config.ENUMS.get((sec, k)) or (f"{lo}..{hi}" if lo is not None else "")
            default = config.DEFAULTS.get(sec, {}).get(k, "(required)" if (sec, k) not in config.OPTIONAL else "(optional)")
            flag = " (immutable)" if (sec, k) in config.IMMUTABLE else ""
            out.append(f"| `{sec}.{k}`{flag} | {typ.__name__} | {sorted(rng) if isinstance(rng, set) else rng} | "
                       f"`{json.dumps(default)[:60]}` |")
    out += ["", "Environment overrides: `INV07_<SECTION>__<KEY>=value`; precedence defaults < file < env.", "",
            "## Metrics", "", "| metric | type | help |", "|---|---|---|"]
    r = standard_metrics(Registry())
    for name, m in sorted(r._m.items()):
        out.append(f"| `{name}` | {m['kind']} | {m['help']} |")
    out += ["", "## CLI", "", "```text", cli.__doc__.strip(), "```", "",
            "## Security guidance", "",
            "* Never put credentials in `repository.url` or config; use `credential_ref` (`env:`/`file:`).",
            "* Keep `trust.require_signed`, `network.verify_tls` and `telemetry.metrics_require_auth` on "
            "(the validator refuses to turn them off).",
            "* Rotate trust roots by adding the new key, waiting one sync interval, then revoking the old key.",
            "* Deprecation: a schema major is supported for one release after its successor ships.", ""]
    text = "\n".join(out)
    with open(os.path.join(COMP, "docs", "API_REFERENCE.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return text


REQUIRED_DOCS = ["ADR-001-v5-production-overlay.md", "THREAT_MODEL.md", "RUNBOOKS.md", "OPERATIONS.md",
                 "COMPATIBILITY.md", "MIGRATION_FROM_IAC.md", "BACKUP_RESTORE.md", "VULN_EOL_POLICY.md",
                 "TELEMETRY_POLICY.md", "WAIVERS.json", "OWNERS.md", "API_REFERENCE.md", "REQUIREMENTS.md"]


def doc_check() -> list[dict]:
    probs = []
    d = os.path.join(COMP, "docs")
    for f in REQUIRED_DOCS:
        if not os.path.exists(os.path.join(d, f)):
            probs.append({"file": f, "problem": "missing"})
    for f in ("MASTER.md", "VERSION", "CHANGELOG.md", "README.md", "pyproject.toml", "NOTICE",
              "THIRD-PARTY-NOTICES.md"):
        if not os.path.exists(os.path.join(PKG, f)):
            probs.append({"file": f, "problem": "missing"})
    ver = open(os.path.join(PKG, "VERSION")).read().strip()
    if ver != VERSION:
        probs.append({"file": "VERSION", "problem": f"{ver} != {VERSION}"})
    if f"## {VERSION}" not in open(os.path.join(PKG, "CHANGELOG.md"), encoding="utf-8").read():
        probs.append({"file": "CHANGELOG.md", "problem": "no entry for current version"})
    pyp = open(os.path.join(PKG, "pyproject.toml"), encoding="utf-8").read() if os.path.exists(
        os.path.join(PKG, "pyproject.toml")) else ""
    if f'version = "{VERSION}"' not in pyp:
        probs.append({"file": "pyproject.toml", "problem": "version mismatch"})
    from inv07_gitops_transition_layer import __version__
    if __version__ != VERSION:
        probs.append({"file": "__init__.py", "problem": "__version__ mismatch"})
    if os.path.exists(os.path.join(d, "API_REFERENCE.md")):
        cur = open(os.path.join(d, "API_REFERENCE.md"), encoding="utf-8").read()
        if cur != api_docs_text():
            probs.append({"file": "API_REFERENCE.md", "problem": "stale; run gates.py apidocs"})
    _write("DOC_CHECK.json", {"schema": "INV07-DOCCHECK/1", "problems": probs, "passed": not probs})
    return probs


def api_docs_text() -> str:
    path = os.path.join(COMP, "docs", "API_REFERENCE.md")
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
    text = api_docs()
    if old is not None:
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(old)
    return text


def manifest() -> str:
    lines = [f"{sha256(os.path.join(ROOT, f))}  {f}" for f in files()
             if not f.endswith("MANIFEST.sha256") and "/evidence/" not in f]
    p = os.path.join(PKG, "MANIFEST.sha256")
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    return p


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "regression":
        base = json.load(open(os.path.join(EVID, "perf_baseline.json")))
        from inv07_gitops_transition_layer.components.tools import bench
        rc, fails = regression(base, bench.main(None, quick=True))
        _write("REGRESSION_GATE.json", {"schema": "INV07-REGRESSION/1", "failures": fails, "passed": rc == 0,
                                        "thresholds": THRESHOLDS, "thresholds_status": "PROPOSED"})
        print(json.dumps(fails))
        return rc
    if cmd == "sbom":
        print(len(sbom()["components"]))
        return 0
    if cmd == "dashboards":
        print(dashboards())
        return 0
    if cmd == "lint":
        return 0 if lint()["passed"] else 1
    if cmd == "coverage":
        d = coverage()
        print(d["total_percent"])
        return 0
    if cmd == "platform":
        print(platform_report())
        return 0
    if cmd == "apidocs":
        api_docs()
        return 0
    if cmd == "docs":
        p = doc_check()
        print(p)
        return 1 if p else 0
    if cmd == "manifest":
        print(manifest())
        return 0
    print(__doc__)
    return 64


if __name__ == "__main__":
    sys.exit(main(sys.argv))
