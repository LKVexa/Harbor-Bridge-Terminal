#!/usr/bin/env python3
"""Lower and verify every translated unit with the owner LCTL toolchains.

The run is transactional: canonical and lctl160 analysis outputs are produced in a temporary
staging directory and are committed only after every required gate and the independent
back-translation/map check pass. A failing run therefore cannot leave a partially refreshed
canonical corpus mixed with stale evidence.

  python tools/verify.py --lctl161 PATH --lctl160 PATH

Defaults may be supplied by LCTL161/LCTL160 environment variables or matching sibling folders.
Both JARs are authenticated against toolchains/LOCK.json (see tools/toolchain_trust.py)
before anything is executed. Requires Java 21+ and Python 3.10+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from toolchain_trust import DEFAULT_LOCK, TrustError, authenticate  # noqa: E402

PKG = Path(__file__).resolve().parents[1]
ENV = {**os.environ, "JAVA_TOOL_OPTIONS": "", "_JAVA_OPTIONS": ""}
REQUIRED_ANALYSES = ("causal-dag", "parallel-plan", "provenance")



def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def java(java_bin: str, jar: Path, *args, timeout=600):
    cmd = [java_bin, "-jar", str(jar), *map(str, args)]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=timeout, check=False)
        lines = [
            line for line in (cp.stdout + cp.stderr).splitlines()
            if not line.startswith("Picked up JAVA_TOOL_OPTIONS") and not line.startswith("Picked up _JAVA_OPTIONS")
        ]
        return cp.returncode, lines
    except subprocess.TimeoutExpired:
        return 124, [f"TIMEOUT after {timeout}s: {' '.join(cmd[:4])} ..."]
    except OSError as exc:
        return 127, [f"EXEC_ERROR: {exc}"]


def _last_json(lines):
    for line in reversed(lines):
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    return lines[-3:]


def one(src: Path, hf161: Path, rt160: Path, java_bin: str, stage_canonical: Path, stage_evidence: Path):
    name = src.stem
    canon = stage_canonical / f"{name}.lctl"
    result = {"unit": src.name}

    rc, out = java(java_bin, hf161, "column-verify", src)
    result["lctl161_column_verify"] = "PASS" if rc == 0 and any('"status":"PASS"' in line for line in out[-3:]) else f"FAIL_{rc}"
    result["column_verify_detail"] = _last_json(out)

    rc, out = java(java_bin, hf161, "column-compile", src, canon)
    result["lctl161_column_compile"] = "PASS" if rc == 0 and canon.is_file() and canon.stat().st_size > 0 else f"FAIL_{rc}"
    result["column_compile_detail"] = out[-3:]

    if canon.is_file() and canon.stat().st_size > 0:
        rc, out = java(java_bin, rt160, "verify", canon)
        result["lctl160_canonical_verify"] = "PASS" if rc == 0 and any(line.startswith("PASS") for line in out[-3:]) else f"FAIL_{rc}"
        result["lctl160_verify_line"] = out[-1] if out else ""
        for cmd in REQUIRED_ANALYSES:
            rc, out = java(java_bin, rt160, cmd, canon)
            analysis_dir = stage_evidence / cmd
            analysis_dir.mkdir(parents=True, exist_ok=True)
            (analysis_dir / f"{name}.txt").write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            result[f"lctl160_{cmd.replace('-', '_')}"] = "PASS" if rc == 0 else f"FAIL_{rc}"
    else:
        result["lctl160_canonical_verify"] = "SKIPPED"
        result["lctl160_verify_line"] = "canonical compile unavailable"
        for cmd in REQUIRED_ANALYSES:
            result[f"lctl160_{cmd.replace('-', '_')}"] = "SKIPPED"

    rc, out = java(java_bin, hf161, "column-stats", src)
    result["lctl161_column_stats"] = "PASS" if rc == 0 else f"FAIL_{rc}"
    result["column_stats"] = out[-1] if out else ""
    return result


def sync_generated_files(stage: Path, target: Path, pattern: str):
    target.mkdir(parents=True, exist_ok=True)
    expected = {p.name for p in stage.glob(pattern) if p.is_file()}
    for src in stage.glob(pattern):
        if not src.is_file():
            continue
        dst = target / src.name
        tmp = target / (src.name + ".new")
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)
    for stale in target.glob(pattern):
        if stale.is_file() and stale.name not in expected:
            stale.unlink()


def commit_outputs(stage_canonical: Path, stage_evidence: Path):
    sync_generated_files(stage_canonical, PKG / "canonical", "*.lctl")
    for cmd in REQUIRED_ANALYSES:
        sync_generated_files(stage_evidence / cmd, PKG / "evidence" / "lctl160" / cmd, "*.txt")


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lctl161", type=Path, help="LCTL 1.6.1-RC1 toolchain root")
    ap.add_argument("--lctl160", type=Path, help="LCTL 1.6.0-RC1 toolchain root")
    ap.add_argument("--lock", type=Path, default=DEFAULT_LOCK, help="owner-approved toolchain trust lock")
    ap.add_argument("--jobs", type=int, default=min(6, os.cpu_count() or 1), help="parallel unit verifications (default: up to 6)")
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if not 1 <= args.jobs <= 32:
        print("FAIL: --jobs must be between 1 and 32", file=sys.stderr)
        return 2
    # M01/M04: authenticate both toolchains and the Java runtime BEFORE any `java -jar`.
    try:
        trusted = authenticate(args.lctl161, args.lctl160, args.lock)
    except TrustError as exc:
        print(f"FAIL[{exc.kind}]: {exc}", file=sys.stderr)
        return exc.code
    java_bin = trusted.java["path"]
    java_version_line = trusted.java["version_line"]
    l161, l160 = trusted.roots["lctl161"], trusted.roots["lctl160"]
    hf161, rt160 = trusted.jars["lctl161"], trusted.jars["lctl160"]

    units = sorted((PKG / "source").glob("*.lctlc"))
    if not units:
        print("FAIL: no source/*.lctlc units found", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="ios735-lctl-verify-") as td:
        stage = Path(td)
        stage_canonical = stage / "canonical"
        stage_evidence = stage / "evidence/lctl160"
        stage_canonical.mkdir(parents=True)
        stage_evidence.mkdir(parents=True)

        with ThreadPoolExecutor(max_workers=args.jobs) as executor:
            results = list(executor.map(
                lambda src: one(src, hf161, rt160, java_bin, stage_canonical, stage_evidence),
                units,
            ))

        gate_keys = (
            "lctl161_column_verify",
            "lctl161_column_compile",
            "lctl160_canonical_verify",
            "lctl160_causal_dag",
            "lctl160_parallel_plan",
            "lctl160_provenance",
            "lctl161_column_stats",
        )
        tool_gates_ok = all(result.get(key) == "PASS" for result in results for key in gate_keys)

        checker = subprocess.run(
            [
                sys.executable, "-B", str(PKG / "tools/check_translation.py"),
                "--canonical-dir", str(stage_canonical),
                "--source-dir", str(PKG / "source"),
                "--map", str(PKG / "map/TRANSLATION_MAP.json"),
                "--skeleton", str(PKG / "input/iOS735_Skeleton"),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        checker_lines = (checker.stdout + checker.stderr).strip().splitlines()
        checker_ok = checker.returncode == 0
        post_hashes = {"lctl161": sha256_file(hf161), "lctl160": sha256_file(rt160)}
        toolchain_stable = post_hashes == trusted.hashes
        ok = tool_gates_ok and checker_ok and toolchain_stable

        summary = {
            "schema": "IOS735_LCTL/VERIFY/2",
            "verdict": "PASS" if ok else "FAIL",
            "units": len(results),
            "lctl161_root": l161.name,
            "lctl160_root": l160.name,
            "toolchain_identity": {
                "java": java_version_line,
                "lctl161_jar_sha256": sha256_file(hf161),
                "lctl160_jar_sha256": sha256_file(rt160),
                **trusted.evidence(),
            },
            "gates": {key: sum(result.get(key) == "PASS" for result in results) for key in gate_keys},
            "translation_check": checker_lines[-1] if checker_lines else "checker produced no output",
            "toolchain_unchanged_during_run": toolchain_stable,
            "generated_outputs_committed": bool(ok),
            "units_detail": results,
        }

        if ok:
            commit_outputs(stage_canonical, stage_evidence)
        atomic_write(PKG / "evidence/VERIFY.json", json.dumps(summary, indent=1) + "\n")
        print(json.dumps({k: v for k, v in summary.items() if k != "units_detail"}, indent=1))
        if not checker_ok and checker_lines:
            print("checker output:")
            print("\n".join(checker_lines[-20:]))
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
