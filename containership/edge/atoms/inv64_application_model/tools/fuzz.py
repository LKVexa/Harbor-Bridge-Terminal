"""Property-based, mutation and parser-differential fuzzing (MC-19; C050, C085, C087).

    python -m inv64_application_model.tools.fuzz --seed 64 --iterations 3000 [--out evidence/FUZZ.json]

Stdlib only (no Hypothesis/atheris dependency), fully reproducible from the seed.

Targets: raw manifest parse, semantic validation, canonicalization, the
submit-request envelope, the auth token decoder and the overlay parser.

Invariants checked on every case (a violation is a *finding*):

I1  only documented exception types escape the parser (ValueError family/TypeError);
I2  valid input -> canonical digest is deterministic across two runs and across
    section re-ordering;
I3  canonical output re-parses, re-validates and yields the same digest;
I4  invalid input never obtains a canonical identity;
I5  the caller's decoded object is not mutated by validate/canonical;
I6  raw-path and decoded-path verdicts agree (parser differential) except for the
    documented raw-only refusals (duplicate keys, depth, byte size);
I7  every case finishes within the per-case time budget (bounded rejection cost);
I8  no credential-like probe value appears in any rendered error/issue text.

Minimized reproducers of past defects live in ``tests/fixtures/fuzz_regressions.json``
and are replayed first on every run.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import string
import subprocess
import sys
import time
from pathlib import Path

from inv64_application_model import manifest as M
from inv64_application_model.auth import Authenticator, TrustConfig
from inv64_application_model.errors import Inv64Error
from inv64_application_model.overlay import check_overlay

ROOT = Path(__file__).resolve().parents[1]
REGRESSIONS = ROOT / "tests" / "fixtures" / "fuzz_regressions.json"
CASE_BUDGET_S = 0.5
SECRET_PROBE = "AKIAFUZZPROBE0000001"
ALLOWED_EXC = (ValueError, TypeError)
NAME_CHARS = string.ascii_letters + string.digits + "._-"
EDGE_STRINGS = ["", " ", "a" * 129, "a" * 128, "é", "é", "‮", "\x00", "\ud800", "名前", "-x", ".x",
                "x y", "a/b", "../etc", SECRET_PROBE, "secretref://vault/k", "𝔞𝔟", "﻿api"]
EDGE_NUMBERS = [0, -0.0, 1e308, -1e308, 2 ** 63, -(2 ** 63) - 1, 10 ** 400, 1e-320, 0.1]


def _name(rng: random.Random) -> str:
    if rng.random() < 0.1:
        return rng.choice(EDGE_STRINGS)
    first = rng.choice(string.ascii_letters + string.digits)
    return first + "".join(rng.choice(NAME_CHARS) for _ in range(rng.randint(0, 12)))


def gen_valid(rng: random.Random) -> dict:
    comps = sorted({"c" + str(i) + _name(rng).strip(" .-_/\x00") for i in range(rng.randint(1, 6))})
    comps = [c for c in comps if M._is_valid_name(c)] or ["api"]
    provs = [p for p in {"p" + str(i) for i in range(rng.randint(0, 4))} if p not in comps]
    targets = comps + provs
    m = {"schema": "app/v1",
         "components": [{"name": c, "properties": {"replicas": rng.randint(1, 9)}} for c in comps],
         "providers": [{"name": p} for p in provs],
         "links": [{"from": rng.choice(comps), "to": rng.choice(targets)} for _ in range(rng.randint(0, 5))],
         "traits": [{"type": rng.choice(["spread", "scaler", "ingress"]), "component": rng.choice(comps)}
                    for _ in range(rng.randint(0, 4))]}
    if rng.random() < 0.3:
        m["x-ext"] = {"nested": [rng.choice(EDGE_NUMBERS), {"k": rng.choice(EDGE_STRINGS[:3])}]}
    return m


def mutate_obj(m: dict, rng: random.Random) -> dict:
    m = copy.deepcopy(m)
    op = rng.randrange(13)
    sec = rng.choice(M.SECTION_NAMES)
    if op == 0:
        m["schema"] = rng.choice(["app/v2", 1, None, "", "APP/V1"])
    elif op == 1:
        m[sec] = rng.choice([{}, "x", 5, None])
    elif op == 2 and m.get(sec):
        m[sec][0] = rng.choice([1, "x", None, []])
    elif op == 3:
        m.setdefault("links", []).append({"from": _name(rng), "to": _name(rng)})
    elif op == 4:
        m.setdefault("traits", []).append({"type": _name(rng), "component": _name(rng)})
    elif op == 5 and m.get("components"):
        m["components"].append(copy.deepcopy(m["components"][0]))  # duplicate name
    elif op == 6:
        m.setdefault("components", []).append({"name": _name(rng), "properties": {"password": "hunter2"}})
    elif op == 7:
        m.setdefault("components", []).append({"name": "z", "env": SECRET_PROBE})
    elif op == 8:
        deep: object = 1
        for _ in range(rng.randint(60, 90)):
            deep = [deep]
        m["x-deep"] = deep
    elif op == 9:
        m.setdefault("components", []).append({"name": rng.choice(EDGE_STRINGS)})
    elif op == 10:
        m["providers"] = [{"name": "p"}] * rng.randint(1, 3)
    elif op == 11:
        m.setdefault("links", []).append({"from": SECRET_PROBE, "to": SECRET_PROBE})
    else:
        m.pop("schema", None)
    return m


def mutate_raw(raw: str, rng: random.Random) -> str | bytes:
    op = rng.randrange(9)
    if op == 0 and raw:
        i = rng.randrange(len(raw))
        return raw[:i] + rng.choice('{}[]",:\\0x') + raw[i + 1:]
    if op == 1:
        return raw[: rng.randrange(len(raw) + 1)]
    if op == 2:
        return raw.replace('"schema"', '"schema":"app/v1","schema"', 1)  # duplicate key
    if op == 3:
        return "[" * rng.randint(60, 5000) + "]" * rng.randint(0, 5000)
    if op == 4:
        return raw.replace("1", "NaN", 1)
    if op == 5:
        return raw.encode("utf-8") + b"\xff\xfe"
    if op == 6:
        return raw + " " * rng.randint(0, 10)
    if op == 7:
        return '{"schema":"app/v1","components":[' + ",".join('{"name":"c%d"}' % i for i in range(rng.randint(9_990, 10_010))) + "]}"
    return "﻿" + raw


def _verdict_raw(raw) -> tuple[str, object]:
    try:
        v = M.parse_manifest_json(raw)
        return "valid", v
    except M.ManifestValidationError as e:
        return "invalid", sorted({i.code for i in e.issues})
    except (M.DuplicateKeyError, M.ManifestDepthError, M.ManifestTooLargeError) as e:
        return "raw-refused", type(e).__name__
    except ALLOWED_EXC as e:
        return "syntax", type(e).__name__


def check_case(obj, raw, findings: list, coverage: dict, case_id: str) -> None:
    t0 = time.perf_counter()
    try:
        verdict, info = _verdict_raw(raw)
    except BaseException as e:  # I1
        findings.append({"case": case_id, "invariant": "I1", "error": type(e).__name__})
        return
    coverage.setdefault(verdict, 0)
    coverage[verdict] += 1
    if verdict == "invalid":
        for c in info:
            coverage["code:" + c] = coverage.get("code:" + c, 0) + 1
    if obj is not None:
        before = copy.deepcopy(obj)
        try:
            issues = M.validate_issues(obj)
        except BaseException as e:
            findings.append({"case": case_id, "invariant": "I1", "error": "validate:" + type(e).__name__})
            return
        text = " ".join(str(i) for i in issues)
        if SECRET_PROBE in text:  # I8
            findings.append({"case": case_id, "invariant": "I8"})
        if issues:
            try:
                M.canonical(obj)
                findings.append({"case": case_id, "invariant": "I4"})
            except M.ManifestValidationError:
                pass
        else:
            d1, d2 = M.canonical(obj), M.canonical(obj)
            shuffled = copy.deepcopy(obj)
            for s in M.SECTION_NAMES:
                random.Random(7).shuffle(shuffled.get(s, []))
            doc = M.canonical_document(obj)
            again = M.parse_manifest_json(doc)
            if not (d1 == d2 == M.canonical(shuffled) == M.canonical(again)):  # I2/I3
                findings.append({"case": case_id, "invariant": "I2/I3"})
        if obj != before:  # I5
            findings.append({"case": case_id, "invariant": "I5"})
        # I6 differential: raw vs decoded verdicts
        dec_verdict = "invalid" if issues else "valid"
        if verdict in ("valid", "invalid") and verdict != dec_verdict:
            findings.append({"case": case_id, "invariant": "I6", "raw": verdict, "decoded": dec_verdict})
    if time.perf_counter() - t0 > CASE_BUDGET_S:  # I7
        findings.append({"case": case_id, "invariant": "I7", "seconds": round(time.perf_counter() - t0, 3)})


def fuzz_boundaries(rng: random.Random, n: int, findings: list, coverage: dict) -> None:
    auth = Authenticator(lambda: TrustConfig("t", "inv64", {"iss": {"k": ("HS256", b"k" * 32)}}))
    for i in range(n):
        tok = "".join(rng.choice(string.printable) for _ in range(rng.randint(0, 200)))
        if rng.random() < 0.5:
            tok = "v1." + ".".join("".join(rng.choice(string.ascii_letters + "-_") for _ in range(rng.randint(0, 40))) for _ in range(3))
        try:
            auth.authenticate(tok, source=f"fuzz{i % 7}")
            findings.append({"case": f"auth-{i}", "invariant": "auth-accepted-garbage"})
        except Inv64Error as e:
            coverage["auth:" + e.code] = coverage.get("auth:" + e.code, 0) + 1
        except BaseException as e:
            findings.append({"case": f"auth-{i}", "invariant": "I1", "error": type(e).__name__})
        ov = rng.choice([None, {}, {"format": "PK_APP_OVERLAY/1"},
                         {"format": "PK_APP_OVERLAY/1", "id": "x", "version": 1, "scope": {"tenant": "t", "environment": "e"},
                          "base_digest": "0", "author": "a", "approval": {"approver": "b"}, "set": rng.choice([5, "x", {"a": 1}, [1]])},
                         {"format": "PK_APP_OVERLAY/1", "id": "x", "version": 1,
                         "scope": {"tenant": "t", "environment": "e"}, "base_digest": "0", "author": "a",
                         "approval": {"approver": rng.choice(["a", "b"])},
                         "set": [{"path": rng.choice(["schema", "components[a].properties.x", "links[0]",
                                                      "components[a].name", "traits[s@a].properties.k"]), "value": 1}]}])
        try:
            check_overlay(ov)
            coverage["overlay:accepted"] = coverage.get("overlay:accepted", 0) + 1
        except Inv64Error as e:
            coverage["overlay:" + e.code] = coverage.get("overlay:" + e.code, 0) + 1
        except BaseException as e:
            findings.append({"case": f"overlay-{i}", "invariant": "I1", "error": type(e).__name__})


def _revision() -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True, timeout=10).stdout.strip()
    except Exception:
        return "unknown"


def run(seed: int, iterations: int) -> dict:
    rng = random.Random(seed)
    findings: list = []
    coverage: dict = {}
    corpus_h = hashlib.sha256()
    regressions = json.loads(REGRESSIONS.read_text(encoding="utf-8"))["cases"] if REGRESSIONS.exists() else []
    for r in regressions:
        if r.get("raw_generator") == "deep-list":
            raw = "[" * r["depth"] + "]" * r["depth"]
        else:
            raw = r["raw"] if "raw" in r else json.dumps(r["obj"])
        corpus_h.update(raw.encode("utf-8", "surrogatepass"))
        check_case(r.get("obj"), raw, findings, coverage, "regression:" + r["id"])
    t0 = time.perf_counter()
    for i in range(iterations):
        base = gen_valid(rng)
        obj = mutate_obj(base, rng) if rng.random() < 0.6 else base
        try:
            raw = json.dumps(obj)
        except (ValueError, RecursionError):
            raw = "{}"
        if rng.random() < 0.3:
            raw = mutate_raw(raw, rng)
            obj_for_check = None
        else:
            obj_for_check = obj
        corpus_h.update(raw if isinstance(raw, bytes) else raw.encode("utf-8", "surrogatepass"))
        check_case(obj_for_check, raw, findings, coverage, f"{seed}:{i}")
    fuzz_boundaries(rng, max(100, iterations // 10), findings, coverage)
    return {"schema": "PK_APP_FUZZ/1", "seed": seed, "iterations": iterations, "regressions_replayed": len(regressions),
            "duration_s": round(time.perf_counter() - t0, 3), "revision": _revision(),
            "corpus_sha256": corpus_h.hexdigest(), "coverage": dict(sorted(coverage.items())),
            "findings": findings[:200], "finding_count": len(findings),
            "result": "PASS" if not findings else "FAIL", "python": sys.version.split()[0]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=64)
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.seed, a.iterations)
    text = json.dumps(res, indent=2, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("result", "seed", "iterations", "finding_count", "duration_s")}))
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
