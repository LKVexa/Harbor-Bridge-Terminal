#!/usr/bin/env python3
"""Semantic acceptance check for IOS735_LCTL/VERIFY/2 evidence (M02.3-M02.5, M09.3 cross-field rules).

JSON Schema proves the envelope is well-formed; this proves it is *accepted release evidence*:
  - verdict PASS, outputs committed, toolchain unchanged during the run
  - every aggregate gate == units == |source/*.lctlc|; every per-unit gate PASS
  - unit membership == source stems; canonical/ holds exactly those .lctl units, all non-empty
  - evidence/lctl160/{causal-dag,parallel-plan,provenance} hold exactly one non-empty file per unit
  - observed JAR hashes and lock digest equal toolchains/LOCK.json APPROVED pins

  python tools/evidence_check.py [--evidence PATH] [--lock PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from schema_check import validate_file  # noqa: E402

PKG = Path(__file__).resolve().parents[1]
GATES = ("lctl161_column_verify", "lctl161_column_compile", "lctl160_canonical_verify", "lctl160_causal_dag",
         "lctl160_parallel_plan", "lctl160_provenance", "lctl161_column_stats")
ANALYSES = ("causal-dag", "parallel-plan", "provenance")


def check(evidence: Path, lock: Path, root: Path = PKG) -> list[str]:
    errs = validate_file(root / "schemas/verify-v2.schema.json", evidence)
    if errs:
        return [f"schema: {e}" for e in errs]
    ev = json.loads(evidence.read_text(encoding="utf-8"))
    stems = sorted(p.stem for p in (root / "source").glob("*.lctlc"))
    n = len(stems)
    if ev["verdict"] != "PASS":
        errs.append(f"verdict is {ev['verdict']}")
    if not ev["generated_outputs_committed"]:
        errs.append("generated_outputs_committed is false")
    if not ev["toolchain_unchanged_during_run"]:
        errs.append("toolchain JAR changed during the run")
    if ev["units"] != n:
        errs.append(f"units {ev['units']} != source units {n}")
    for g in GATES:
        if ev["gates"][g] != n:
            errs.append(f"gate {g} = {ev['gates'][g]} != {n}")
    detail_units = sorted(u["unit"][:-len(".lctlc")] for u in ev["units_detail"])
    if detail_units != stems:
        errs.append("units_detail membership differs from source/*.lctlc")
    for u in ev["units_detail"]:
        bad = [g for g in GATES if u[g] != "PASS"]
        if bad:
            errs.append(f"{u['unit']}: non-PASS gates {bad}")
    if not ev["translation_check"].startswith("PASS"):
        errs.append("translation_check did not report PASS")
    canon = sorted(p.stem for p in (root / "canonical").glob("*.lctl"))
    if canon != stems:
        errs.append("canonical/ membership differs from source/")
    errs += [f"empty canonical {p.name}" for p in (root / "canonical").glob("*.lctl") if p.stat().st_size == 0]
    for a in ANALYSES:
        files = sorted((root / "evidence/lctl160" / a).glob("*.txt"))
        if [p.stem for p in files] != stems:
            errs.append(f"evidence/lctl160/{a} membership differs from source/")
        errs += [f"empty analysis {a}/{p.name}" for p in files if p.stat().st_size == 0]
    try:
        raw = lock.read_bytes()
        lk = json.loads(raw)
    except (OSError, ValueError) as exc:
        return errs + [f"cannot read lock: {exc}"]
    ti = ev["toolchain_identity"]
    if ti["lock_sha256"] != hashlib.sha256(raw).hexdigest():
        errs.append("evidence was produced under a different lock file")
    for tc in lk["toolchains"]:
        if tc["status"] != "APPROVED":
            errs.append(f"lock entry {tc['role']} is {tc['status']}, not APPROVED")
        elif ti[f"{tc['role']}_jar_sha256"] != tc["sha256"]:
            errs.append(f"{tc['role']} observed hash != approved pin")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--evidence", type=Path, default=PKG / "evidence/VERIFY.json")
    ap.add_argument("--lock", type=Path, default=PKG / "toolchains/LOCK.json")
    a = ap.parse_args(argv)
    head = json.loads(a.evidence.read_text(encoding="utf-8")).get("schema")
    if head != "IOS735_LCTL/VERIFY/2":
        print(f"FAIL: evidence schema is {head!r}; genuine IOS735_LCTL/VERIFY/2 evidence is required (M02 open)")
        return 1
    errs = check(a.evidence, a.lock)
    for e in errs[:40]:
        print("FAIL:", e)
    if not errs:
        print("PASS: VERIFY/2 evidence accepted (schema + semantic + lock correlation)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
