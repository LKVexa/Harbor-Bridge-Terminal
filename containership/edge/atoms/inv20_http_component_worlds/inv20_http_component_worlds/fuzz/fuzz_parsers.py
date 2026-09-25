"""Seeded property fuzzing for INV-20 parsers/state machines (checklist component 19).

Oracles (any violation is a failure):
  * only registered ``Inv20Error`` subclasses may escape a parser (no crash/defect);
  * accepted authorities re-parse to the identical value (idempotent canonicalisation);
  * accepted field values never contain CR/LF/NUL; accepted trailers never contain forbidden names;
  * the body-stream / lifecycle state machines never reach an illegal state silently;
  * per-input wall time is bounded (hang detection).

    python -m inv20_http_component_worlds.fuzz.fuzz_parsers --iterations 20000 --seed 1
Crashes are written to fuzz/crashes/ and must be added to fuzz/corpus/ once fixed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys
import time

from ..config import validate as config_validate
from ..errors import Inv20Error, error_from_dict
from ..protocol import FORBIDDEN_IN_TRAILERS, Fields, parse_authority, validate_method, validate_path_with_query
from ..runtime import BodyStream, Completion, canonical_host

HERE = pathlib.Path(__file__).resolve().parent
ALPHABET = list("abcxyz019.-_:[]@%/?#\\ \t\r\n\x00") + ["ü", "​", "ｅ", "::", "0x", "%00", "%zz", ".."]
PER_INPUT_S = 0.05


def corpus() -> list:
    return [l for l in (HERE / "corpus" / "seeds.txt").read_text(encoding="utf-8").splitlines() if l]


def mutate(rng: random.Random, s: str) -> str:
    ops = rng.randint(1, 4)
    chars = list(s)
    for _ in range(ops):
        k = rng.random()
        if k < 0.4 and chars:
            chars[rng.randrange(len(chars))] = rng.choice(ALPHABET)
        elif k < 0.7:
            chars.insert(rng.randrange(len(chars) + 1), rng.choice(ALPHABET))
        elif k < 0.85 and chars:
            del chars[rng.randrange(len(chars))]
        else:
            chars = chars * rng.randint(2, 40)       # length amplification
    return "".join(chars)[:4096]


def check_one(target: str, data: str) -> None:
    if target == "authority":
        try:
            a = parse_authority(data)
        except Inv20Error:
            return
        if parse_authority(a.render()) != a:
            raise AssertionError("authority canonicalisation not idempotent")
        if any(c in a.host for c in "@/?# \r\n\x00%"):
            raise AssertionError("unsafe character accepted into host")
    elif target == "host":
        try:
            h = canonical_host(data)
        except Inv20Error:
            return
        if canonical_host(h) != h:
            raise AssertionError("host canonicalisation not idempotent")
    elif target == "field":
        name, _, value = data.partition(":")
        for trailers in (False, True):
            try:
                f = Fields([(name, value)], trailers=trailers)
            except Inv20Error:
                continue
            for n, v in f.items():
                if any(c in v for c in "\r\n\x00"):
                    raise AssertionError("CR/LF/NUL accepted in value")
                if trailers and n in FORBIDDEN_IN_TRAILERS:
                    raise AssertionError("forbidden trailer accepted")
    elif target == "path":
        try:
            validate_path_with_query(data)
        except Inv20Error:
            return
        if data.startswith("//") or "#" in data:
            raise AssertionError("ambiguous path accepted")
    elif target == "method":
        try:
            validate_method(data)
        except Inv20Error:
            return
    elif target == "config":
        try:
            obj = json.loads(data)
        except ValueError:
            obj = {"schema": "INV20_CONFIG/1", "allowed_authorities": [data], "outgoing_enabled": True,
                   "capability_ref": "secret://x"}
        try:
            config_validate(obj)
        except Inv20Error:
            return
    elif target == "error":
        e = error_from_dict({"schema": "INV20_ERROR/1", "code": data, "detail": data})
        if not e.code.startswith("E_"):
            raise AssertionError("error decoder produced unregistered code")
    elif target == "stream":
        rng = random.Random(data)
        s, c = BodyStream(limit=rng.randint(0, 64)), Completion()
        for _ in range(rng.randint(0, 20)):
            op = rng.random()
            try:
                if op < 0.5:
                    s.write(b"x" * rng.randint(0, 16))
                elif op < 0.8:
                    s.forward()
                else:
                    c.resolve(1)
            except Inv20Error:
                pass
            if s.total > s.limit:
                raise AssertionError("stream exceeded its limit")


TARGETS = ("authority", "host", "field", "path", "method", "config", "error", "stream")


def run(iterations: int, seed: int) -> dict:
    rng = random.Random(seed)
    seeds = corpus()
    failures, slow = [], 0
    for i in range(iterations):
        target = TARGETS[i % len(TARGETS)]
        data = mutate(rng, rng.choice(seeds))
        t0 = time.perf_counter()
        try:
            check_one(target, data)
        except Exception as exc:  # crash, defect or oracle violation
            failures.append({"target": target, "input": data, "error": f"{type(exc).__name__}: {exc}"[:200]})
        if time.perf_counter() - t0 > PER_INPUT_S:
            slow += 1
            failures.append({"target": target, "input": data[:200], "error": "hang/slow input"})
    if failures:
        d = HERE / "crashes"
        d.mkdir(exist_ok=True)
        (d / f"seed{seed}.json").write_text(json.dumps(failures[:50], indent=1))
    digest = hashlib.sha256("\n".join(seeds).encode()).hexdigest()
    return {"schema": "INV20_FUZZ/1", "tool": "inv20-seeded-fuzz/1", "python": sys.version.split()[0],
            "seed": seed, "iterations": iterations, "targets": list(TARGETS), "corpus_sha256": digest,
            "failures": len(failures), "slow_inputs": slow, "ok": not failures}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args(argv)
    res = run(a.iterations, a.seed)
    print(json.dumps(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
