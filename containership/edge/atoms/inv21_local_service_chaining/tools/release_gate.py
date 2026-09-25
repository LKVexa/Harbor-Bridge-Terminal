"""Production exit gate (GAP-037 / C090 / C100).

    python -m inv21_local_service_chaining.tools.release_gate [--out-dir evidence] [--quick]

Runs every mandatory check from a clean copy of the source tree and writes a
machine-readable evidence bundle. A check that cannot run is a FAILURE. The
verdict is GO only if every mandatory check passes; this tool never waives.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
REPO = PKG.parent
EPOCH = "1790000000"


def _run(cmd, cwd, env=None, timeout=900):
    t = time.time()
    r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    return {"cmd": " ".join(map(str, cmd)), "returncode": r.returncode, "seconds": round(time.time() - t, 2),
            "tail": (r.stdout + r.stderr)[-4000:]}


def _tree_digest(root: pathlib.Path) -> tuple:
    files = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        # governance/approvals.json is excluded: a review record must bind to the tree it reviewed,
        # and writing that record must not change the digest it binds to
        if p.is_file() and "__pycache__" not in rel and not rel.startswith(("inv21_local_service_chaining/evidence/", "build/"))\
                and ".egg-info" not in rel and rel != "inv21_local_service_chaining/governance/approvals.json":
            files[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    h = hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in files.items()).encode()).hexdigest()
    return h, files


def _unittest_summary(tail: str) -> dict:
    import re
    ran = re.search(r"Ran (\d+) tests?", tail)
    skipped = re.search(r"skipped=(\d+)", tail)
    return {"ran": int(ran.group(1)) if ran else 0, "skipped": int(skipped.group(1)) if skipped else 0,
            "ok": "\nOK" in tail and "FAILED" not in tail}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(PKG / "evidence"))
    ap.add_argument("--quick", action="store_true", help="skip multi-interpreter matrix and benchmarks")
    a = ap.parse_args(argv)
    out = pathlib.Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    checks: dict = {}
    work = pathlib.Path(tempfile.mkdtemp(prefix="inv21-gate-"))
    try:
        clean = work / "src"
        shutil.copytree(REPO, clean, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "build", "*.egg-info",
                                                                   "evidence", ".git"))
        src_digest, files = _tree_digest(clean)
        env = {k: v for k, v in os.environ.items() if k != "INV21_ALLOW_PK_CORE_SKIP"}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0")
        pk = clean / "inv21_local_service_chaining"

        checks["compile"] = _run([sys.executable, "-m", "compileall", "-q", str(pk)], clean, env)
        checks["compile"]["pass"] = checks["compile"]["returncode"] == 0
        shutil.rmtree(pk / "__pycache__", ignore_errors=True)

        t = _run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "tests"], pk, env)
        t.update(_unittest_summary(t["tail"]))
        t["pass"] = t["returncode"] == 0 and t["ok"] and t["skipped"] == 0
        t["rule"] = "zero failures AND zero skips (a skipped mandatory test is a failure)"
        checks["tests_full"] = t

        o = _run([sys.executable, "-B", "-O", "-m", "unittest", "discover", "-s", "tests", "-t", "tests"], pk,
                 dict(env, INV21_ALLOW_PK_CORE_SKIP="1"))
        o.update(_unittest_summary(o["tail"]))
        o["pass"] = o["returncode"] == 0 and (o["skipped"] == 0 or not t["pass"])  # skips tolerated only
        # when tests_full already fails for the same (pk_core) reason
        o["note"] = "python -O parity of the runtime suite (pk_core presence judged by tests_full)"
        checks["tests_optimised"] = o

        f = _run([sys.executable, "-B", "-m", "unittest", "test_fuzz_property"], pk / "tests",
                 dict(env, INV21_FUZZ_ITERS="5000"))
        f["pass"] = f["returncode"] == 0; checks["fuzz_5000"] = f

        if not a.quick:
            mx = {}
            for py in ("python3.10", "python3.11", "python3.12", "python3.13"):
                exe = shutil.which(py)
                if not exe:
                    mx[py] = {"pass": False, "why": "interpreter not available"}; continue
                r = _run([exe, "-B", "-m", "unittest", "discover", "-s", "tests", "-t", "tests"], pk,
                         dict(env, INV21_ALLOW_PK_CORE_SKIP="1"))
                r.update(_unittest_summary(r["tail"])); r["pass"] = r["returncode"] == 0; mx[py] = r
            checks["python_matrix"] = {"pass": all(v["pass"] for v in mx.values()), "results": mx,
                                       "platform": f"{os.uname().sysname} {os.uname().machine}",
                                       "untested": ["aarch64", "macOS", "Windows"]}

        snap = pk / "tests/fixtures/schema_snapshot.v1.json"
        s = _run([sys.executable, "-B", "-m", "inv21_local_service_chaining.tools.schema_diff", str(snap)], clean, env)
        s["pass"] = s["returncode"] == 0; checks["schema_compat"] = s

        # build artifacts reproducibly in an isolated venv with the pinned backend
        venv = work / "venv"
        subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True)
        vpy = str(venv / "bin" / "python")
        sys.path.insert(0, str(pk / "tests"))
        import test_packaging  # reuse the pinned-backend installer
        test_packaging.REPO = clean
        vpy = test_packaging._venv(str(work / "venv2"))
        d1, d2 = work / "dist1", work / "dist2"
        w1, s1 = test_packaging._build(vpy, str(d1), EPOCH)
        w2, _ = test_packaging._build(vpy, str(d2), EPOCH)
        art = {w1.name: hashlib.sha256(w1.read_bytes()).hexdigest(), s1.name: hashlib.sha256(s1.read_bytes()).hexdigest()}
        repro = art[w1.name] == hashlib.sha256(w2.read_bytes()).hexdigest()
        checks["build_reproducible"] = {"pass": repro, "artifacts": art}
        (out / "dist").mkdir(exist_ok=True)
        shutil.copy(w1, out / "dist" / w1.name); shutil.copy(s1, out / "dist" / s1.name)

        # clean install + smoke from the built artifact
        tgt = work / "site"
        r = _run([vpy, "-m", "pip", "install", "-q", "--no-index", "--no-deps", "--target", str(tgt), str(w1)], work, env)
        smoke = _run([vpy, "-I", "-c", "import sys;sys.path.insert(0,sys.argv[1]);import inv21_local_service_chaining as m;"
                      "from inv21_local_service_chaining.residency import Residency;from inv21_local_service_chaining.chain import Chainer;"
                      "r=Residency('h');r.place('b','t',lambda *a:'ok');assert Chainer(r).call('b','t',1)=='ok';print(m.__version__)",
                      str(tgt)], "/", env)
        checks["artifact_install_smoke"] = {"pass": r["returncode"] == 0 and smoke["returncode"] == 0, "install": r, "smoke": smoke}

        sys.path.insert(0, str(clean))
        from inv21_local_service_chaining.tools import sbom as S
        version = (pk / "VERSION").read_text().strip()
        (out / "sbom.cdx.json").write_text(json.dumps(S.sbom(str(w1), version, {k: v for k, v in files.items()
                                                                                if k.endswith(".py") or k.endswith(".json")}), indent=1))
        (out / "provenance.intoto.json").write_text(json.dumps(S.provenance(art, src_digest, "inv21-release-gate/local"), indent=1))
        checks["sbom"] = {"pass": True, "file": "sbom.cdx.json"}
        sig_cmd = os.environ.get("INV21_SIG_VERIFY_CMD")  # e.g. "cosign verify-blob --key k.pub --signature {sig} {file}"
        sig = out / "release_manifest.sig"
        allowed = {"cosign", "gpg", "gpgv", "openssl", "sigstore", "minisign", "ssh-keygen"}
        if sig_cmd and sig_cmd.split()[0] not in allowed:
            checks["signature"] = {"pass": False, "why": f"verifier '{sig_cmd.split()[0]}' is not an allow-listed "
                                   f"signature tool {sorted(allowed)}"}
        elif sig_cmd and sig.exists():
            sv = _run(sig_cmd.format(sig=sig, file=out / "release_manifest.json").split(), clean, env)
            checks["signature"] = {"pass": sv["returncode"] == 0, "verify": sv}
        else:
            checks["signature"] = {"pass": False, "why": "no signature and/or no INV21_SIG_VERIFY_CMD verifier configured; "
                                   "artifacts and provenance are UNSIGNED (a .sig file alone is never accepted)"}
        checks["vulnerability_scan"] = {"pass": False, "status": "NOT_RUN",
                                        "why": "no scanner or advisory index reachable; 0 third-party runtime deps recorded in SBOM"}
        (out / "vulnerability_scan.json").write_text(json.dumps(checks["vulnerability_scan"], indent=1))

        if not a.quick:
            b = _run([sys.executable, "-B", "-m", "inv21_local_service_chaining.tools.bench", "--n", "20000", "--out",
                      str(out / "bench.json")], clean, env)
            c = _run([sys.executable, "-B", "-m", "inv21_local_service_chaining.tools.bench", "--check", str(out / "bench.json"),
                      "--baseline", str(PKG / "evidence/bench_baseline.json")], clean, env)
            slo = json.loads((out / "bench.json").read_text())["slo_local_dispatch_p99_under_20us"]
            checks["benchmark_regression"] = {"pass": b["returncode"] == 0 and c["returncode"] == 0, "check": c["tail"][-600:]}
            checks["slo_local_dispatch"] = {"pass": all(slo.values()), "measured": slo}

        import tomllib
        pin = tomllib.loads((clean / "pyproject.toml").read_text())["tool"]["inv21"]["pk_core"]
        import re as _re
        pin_ok = bool(_re.fullmatch(r"[0-9a-f]{64}", str(pin["sha256"]))) and pin["source"] not in ("", "UNRESOLVED") \
            and bool(_re.fullmatch(r"\d+\.\d+\.\d+", str(pin["version"])))
        checks["pk_core_pinned"] = {"pass": pin_ok and checks["tests_full"]["pass"], "pin": pin,
                                    "rule": "immutable source + semver + sha256, AND conformance actually executed"}
        lic = clean / "LICENSE"
        py_lic = tomllib.loads((clean / "pyproject.toml").read_text())["project"].get("license")
        checks["license"] = {"pass": lic.exists() and lic.stat().st_size > 200 and py_lic != "LicenseRef-INV21-Pending",
                             "why": "owner licence decision pending (GAP-039)"}
        today = time.strftime("%Y-%m-%d")
        wv = json.loads((pk / "governance/waivers.json").read_text())["entries"]
        def _approved(w):
            return bool(w.get("approved") and w.get("approver") and w.get("approved_on")
                        and w.get("expires") and str(w["expires"]) > today)
        checks["waivers_approved"] = {"pass": all(_approved(w) for w in wv),
                                      "unapproved_or_expired": [w["id"] for w in wv if not _approved(w)],
                                      "rule": "approved + approver + approved_on + unexpired 'expires'"}
        ap_ = json.loads((pk / "governance/approvals.json").read_text())["approvals"]
        implementers = {"claude", "cowork", "inv21-release-gate", "automation"}
        def _indep(x):
            return (x.get("kind") == "independent_verification" and x.get("reviewer")
                    and x["reviewer"].lower() not in implementers and x.get("date")
                    and x.get("reviewed_source_tree_sha256") == src_digest)
        checks["independent_review"] = {"pass": any(_indep(x) for x in ap_),
                                        "rule": "non-implementer reviewer bound to THIS source_tree_sha256",
                                        "source_tree_sha256": src_digest}
        failing_modules = sorted(set(_re.findall(r"^(?:FAIL|ERROR): \S+ \((test_\w+)\.", t["tail"], _re.M)))
        from inv21_local_service_chaining.tools import traceability as T
        tr = T.build(failing_modules=failing_modules)
        (out / "traceability.json").write_text(json.dumps(tr, indent=1))
        checks["traceability"] = {"pass": not tr["unmapped"] and tr["summary_gaps"]["blocked"] == 0
                                  and tr["summary_gaps"]["partial"] == 0,
                                  "complete_mapping": not tr["unmapped"], "summary_checklist": tr["summary_checklist"],
                                  "summary_gaps": tr["summary_gaps"]}
    finally:
        shutil.rmtree(work, ignore_errors=True)

    failed = sorted(k for k, v in checks.items() if not v.get("pass"))
    result = {"schema": "INV21_GATE/1", "component": "INV-21", "version": version,
              "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "source_tree_sha256": src_digest,
              "artifacts": art, "verdict": "GO" if not failed else "NO_GO", "failed_checks": failed, "checks": checks}
    (out / "gate_result.json").write_text(json.dumps(result, indent=1))
    manifest = {"version": version, "source_tree_sha256": src_digest, "artifacts": art,
                "evidence": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.json"))
                             if p.name != "release_manifest.json"}}
    (out / "release_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(json.dumps({"verdict": result["verdict"], "failed_checks": failed}, indent=1))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
