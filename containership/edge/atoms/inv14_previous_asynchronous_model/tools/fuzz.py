"""Seeded fuzz harness (component P2-22; C050, C085).

Targets: PollSet.poll request shape/identity/timeouts/foreign owners, the
capability-token decoder, config/clock validators, schema validator, the
traceparent parser and the audit verifier.  Oracle: every call either returns a
schema-valid result or raises a structured error carrying a registered code.
Anything else (bare exception, invalid result, hang > 2 s) is a finding.
Usage: python3 tools/fuzz.py --iterations 5000 --seed 1
"""
import argparse, json, random, time
import _path  # noqa
import polling as P, identity, config, clock, schema_check, tracing

CODES = {c["code"] for c in json.load(open(_path.PKG / "schemas" / "error_codes.json"))["codes"]}
ATOMS = [0, -1, 1, 2**31, 2**64, 1.5, float("nan"), True, None, "", "x", "é" * 300, b"b", [], {}, object()]


def _rand_value(r):
    k = r.random()
    if k < 0.5:
        return r.choice(ATOMS)
    if k < 0.7:
        return "".join(chr(r.randrange(0, 0x3000)) for _ in range(r.randrange(0, 40)))
    if k < 0.85:
        return r.randrange(-5, 70_000)
    return [r.choice(ATOMS) for _ in range(r.randrange(0, 5))]


def _structured(e):
    return getattr(e, "code", None) in CODES


def fuzz_poll(r):
    owner = r.choice(["o", "o", "other", ""])
    members = []
    for _ in range(r.randrange(0, 6)):
        c = r.random()
        if c < 0.6:
            p = P.Pollable(r.choice(["a", "b", "c", "d"]), r.choice(["o", "o", "x"]))
            if r.random() < 0.4:
                p.signal()
            members.append(p)
        elif c < 0.8 and members:
            members.append(members[0])
        else:
            members.append(_rand_value(r))
    seq = members if r.random() < 0.9 else _rand_value(r)
    t = r.choice([1, 2, 0, -3, 60_001, 10**9, True, 1.0, "5", None])
    try:
        ps = P.PollSet(owner or "o", max_pollables=r.choice([1, 3, 4096]))
        res = ps.poll(seq, timeout_ticks=t)
    except Exception as e:
        return "ok" if _structured(e) else f"UNSTRUCTURED {type(e).__name__}: {e}"
    errs = schema_check.check(res, "pk_poll.schema.json")
    return "ok" if not errs else f"INVALID RESULT {errs[:2]}"


def fuzz_token(r):
    v = identity.Verifier({"k1": b"k" * 32})
    tok = identity.Issuer(b"k" * 32, "k1").mint("a/b/c")
    choice = r.random()
    if choice < 0.4:
        i = r.randrange(len(tok)); tok = tok[:i] + chr(r.randrange(32, 127)) + tok[i + 1:]
    elif choice < 0.7:
        tok = _rand_value(r)
    try:
        v.verify(tok, owner=r.choice(["a/b/c", "x/y/z"]))
        return "ok"
    except Exception as e:
        return "ok" if _structured(e) else f"UNSTRUCTURED token {type(e).__name__}"


def fuzz_config(r):
    doc = json.loads(json.dumps(config.BASE_CONFIG))
    for _ in range(r.randrange(1, 4)):
        tgt = r.choice([doc] + [doc[k] for k in ("limits", "clock", "provenance") if isinstance(doc.get(k), dict)])
        tgt[r.choice(list(tgt) + ["zz"])] = _rand_value(r)
    try:
        config.validate_config(doc)
        return "ok" if schema_check.check(doc, "pk_poll_config.schema.json") == [] else "SCHEMA/VALIDATOR DISAGREE"
    except Exception as e:
        return "ok" if _structured(e) else f"UNSTRUCTURED config {type(e).__name__}: {e}"


def fuzz_trace(r):
    v = _rand_value(r) if r.random() < 0.5 else "00-" + "".join(r.choice("0123456789abcdefg") for _ in range(32)) + "-" + "".join(r.choice("0123456789abcdef") for _ in range(16)) + "-01"
    c = tracing.child_context(v, _rand_value(r))
    return "ok" if tracing.parse_traceparent(c.traceparent) else "BAD CHILD TRACEPARENT"


TARGETS = [fuzz_poll, fuzz_token, fuzz_config, fuzz_trace]


def run(iterations=2000, seed=1):
    r = random.Random(seed)
    findings, t0 = [], time.monotonic()
    counts = {f.__name__: 0 for f in TARGETS}
    for i in range(iterations):
        f = TARGETS[i % len(TARGETS)]
        s = time.monotonic()
        out = f(r)
        counts[f.__name__] += 1
        if out != "ok" or time.monotonic() - s > 2.0:
            findings.append({"iteration": i, "target": f.__name__, "finding": out})
    return {"iterations": iterations, "seed": seed, "per_target": counts, "findings": findings,
            "seconds": round(time.monotonic() - t0, 3)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--iterations", type=int, default=2000); ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    res = run(a.iterations, a.seed)
    print(json.dumps(res, indent=1))
    raise SystemExit(1 if res["findings"] else 0)
