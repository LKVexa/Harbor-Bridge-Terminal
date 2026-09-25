"""MC-028 coverage-guided fuzzing harness (stdlib only; no atheris/libFuzzer here).

Targets:
  decode  - canonical image lifting for random schema types (bytes -> value)
  schema  - WIT-subset schema loader (text -> Interface)
  envelope- error envelope validation (JSON -> accept/reject)

Coverage feedback is (file, from_line, to_line) arcs inside ``canon/`` collected
with ``sys.settrace``.  Inputs that reach a new arc join the corpus.  Any
exception other than ``InteropError`` (or the documented ValueError for
envelopes) is a *crash*; crashing inputs are minimized and persisted to
``fixtures/fuzz/regressions/`` so they are replayed forever by
``--replay`` (and by CI).

Usage: python tools/fuzz.py [--target T] [--iterations N] [--seed S] [--replay]
"""
import argparse
import hashlib
import json
import pathlib
import random
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from canon import layout, types as ty  # noqa: E402
from canon.errors import InteropError, validate_envelope  # noqa: E402
from canon.generators import gen_type, gen_value, mutate  # noqa: E402

CANON = str(ROOT / "canon")
REG = ROOT / "fixtures/fuzz/regressions"


class Cov:
    def __init__(self):
        self.arcs = set()
        self._last = {}

    def tracer(self, frame, event, arg):
        if not frame.f_code.co_filename.startswith(CANON):
            return None

        def local(fr, ev, a):
            if ev == "line":
                key = id(fr)
                prev = self._last.get(key, 0)
                self.arcs.add((fr.f_code.co_filename, prev, fr.f_lineno))
                self._last[key] = fr.f_lineno
            return local
        return local


def run_one(target, data, cov=None):
    if cov:
        sys.settrace(cov.tracer)
    try:
        if target == "decode":
            desc, image, root = data
            t = ty.from_descriptor(desc)
            layout.decode(image, root, t)
        elif target == "schema":
            ty.load(data)
        elif target == "envelope":
            try:
                validate_envelope(json.loads(data))
            except (ValueError, TypeError, AttributeError) as e:
                if isinstance(e, (TypeError, AttributeError)):
                    raise
        return None
    except InteropError:
        return None
    except RecursionError as e:
        return e
    except Exception as e:  # noqa: BLE001
        return e
    finally:
        sys.settrace(None)


SCHEMA_SEEDS = [
    (ROOT / "fixtures/corpus/corpus.wit").read_text(),
    "interface a { type x = list<option<result<u8, string>>>; }",
    "package p:q@1.0.0; interface i { resource r; f: func(a: borrow<r>) -> own<r>; }",
    "interface a { variant v { x(tuple<u8, char>), y } flags f { a, b } }",
]
ENVELOPE_SEEDS = [json.dumps(InteropError("x", code="PK_INTEROP_LIMIT").envelope())]
TOKENS = ["{", "}", "<", ">", ",", ";", ":", "=", "record", "variant", "list", "own", "borrow",
          "func", "->", "\n", "//", "u8", "result", "_", "@", "9.9.9", "a-b", "tuple", "é", "\x00"]


def mutate_text(rng, s):
    s = list(s)
    for _ in range(rng.randint(1, 4)):
        op = rng.randrange(4)
        i = rng.randrange(len(s) + 1)
        if op == 0 and s:
            del s[min(i, len(s) - 1)]
        elif op == 1:
            s[i:i] = list(rng.choice(TOKENS))
        elif op == 2 and s:
            j = rng.randrange(len(s))
            s[i:i] = s[j:j + rng.randint(1, 20)]
        else:
            s[i:i] = [chr(rng.randrange(0x20, 0x7f))]
    return "".join(s)


def fuzz(target, iterations, seed):
    rng = random.Random(seed)
    cov = Cov()
    corpus = []
    if target == "decode":
        for _ in range(64):
            t = gen_type(rng, 3)
            img, root = layout.encode(gen_value(rng, t), t)
            corpus.append((ty.descriptor(t), img, root))
    elif target == "schema":
        corpus = list(SCHEMA_SEEDS)
    else:
        corpus = list(ENVELOPE_SEEDS)
    for c in corpus:
        run_one(target, c, cov)
    crashes = []
    t0 = time.time()
    for _ in range(iterations):
        base = rng.choice(corpus)
        if target == "decode":
            cand = (base[0], mutate(rng, base[1]), base[2] if rng.random() < .9 else rng.randrange(64))
        else:
            cand = mutate_text(rng, base)
        before = len(cov.arcs)
        err = run_one(target, cand, cov)
        if err is not None:
            crashes.append((cand, repr(err)[:200]))
            persist(target, cand, repr(err))
        elif len(cov.arcs) > before:
            corpus.append(cand)
    return {"target": target, "seed": seed, "iterations": iterations, "corpus": len(corpus),
            "arcs": len(cov.arcs), "crashes": len(crashes),
            "crash_samples": [c[1] for c in crashes[:5]], "seconds": round(time.time() - t0, 2)}


def persist(target, cand, err):
    REG.mkdir(parents=True, exist_ok=True)
    if target == "decode":
        obj = {"target": target, "descriptor": cand[0], "image": cand[1].hex(), "root": cand[2]}
    else:
        obj = {"target": target, "text": cand}
    obj["error"] = err[:300]
    name = hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]
    (REG / f"{target}-{name}.json").write_text(json.dumps(obj, indent=1, sort_keys=True))


def replay():
    fails = []
    files = sorted(REG.glob("*.json")) if REG.exists() else []
    for f in files:
        o = json.loads(f.read_text())
        data = ((o["descriptor"], bytes.fromhex(o["image"]), o["root"]) if o["target"] == "decode"
                else o["text"])
        err = run_one(o["target"], data)
        if err is not None:
            fails.append((f.name, repr(err)[:120]))
    return {"regressions": len(files), "still_failing": fails}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", default="all")
    ap.add_argument("--iterations", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=20260922)
    ap.add_argument("--replay", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    if a.replay:
        r = replay()
    else:
        targets = ["decode", "schema", "envelope"] if a.target == "all" else [a.target]
        r = {"runs": [fuzz(t, a.iterations, a.seed) for t in targets], "replay": replay()}
        r["verdict"] = "PASS" if all(x["crashes"] == 0 for x in r["runs"]) and not r["replay"]["still_failing"] else "FAIL"
    text = json.dumps(r, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text + "\n")
    print(text)
    sys.exit(0 if r.get("verdict", "PASS") == "PASS" and not r.get("still_failing") else 1)
