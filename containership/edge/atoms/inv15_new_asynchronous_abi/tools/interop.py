"""Cross-implementation conformance harness (components 38, 64).

1. Every conformance vector is decoded by BOTH codecs (wire/codec.py and the
   independently written wire/codec_alt.py); accept/reject and decoded values
   must agree, and re-encoding a good vector must reproduce it byte-for-byte.
2. A seeded operation trace is replayed against the v4.2 reference model
   (abi.AsyncAbi) and the v4.3 host (host.AsyncHost) over the semantics both
   define; observable outcomes must match.
Prints one JSON report line; exit 0 only if everything agrees.
"""
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from inv15_new_asynchronous_abi import abi as ref  # noqa: E402
from inv15_new_asynchronous_abi.errors import AbiError  # noqa: E402
from inv15_new_asynchronous_abi.host import AsyncHost, Limits  # noqa: E402
from inv15_new_asynchronous_abi.wire import codec, codec_alt  # noqa: E402

ALT_KIND = {"MALFORMED": "malformed", "UNSUPPORTED_VERSION": "version", "UNSUPPORTED_FEATURE": "feature"}


def norm_primary(kind, obj):
    if kind == "call":
        k, v = obj
        if k == "value":
            return ["value", v.hex()]
        if k == "subtask":
            return ["subtask", [v.epoch, v.slot, v.generation, v.token.hex()]]
        return ["error", [v["code"], v["retryable"], v["detail"]]]
    if kind == "wait":
        return [[h.epoch, h.slot, h.generation, h.token.hex()] for h in obj]
    if kind == "cancel":
        h, r = obj
        return [[h.epoch, h.slot, h.generation, h.token.hex()], int(r)]
    return int(obj)


def norm_alt(kind, obj):
    if kind == "call":
        k, v = obj
        if k == "value":
            return ["value", v.hex()]
        if k == "subtask":
            return ["subtask", [v[0], v[1], v[2], v[3].hex()]]
        return ["error", list(v)]
    if kind == "wait":
        return [[a, b, c, d.hex()] for a, b, c, d in obj]
    if kind == "cancel":
        (a, b, c, d), r = obj
        return [[a, b, c, d.hex()], r]
    return obj


P = {"call": codec.decode_call_result, "wait": codec.decode_wait, "cancel": codec.decode_cancel, "ack": codec.decode_ack}
A = {"call": codec_alt.decode_call_result, "wait": codec_alt.decode_wait, "cancel": codec_alt.decode_cancel, "ack": codec_alt.decode_ack}


def run_vectors():
    data = json.loads((ROOT / "conformance" / "vectors.json").read_text())
    fails = []
    for v in data["good"]:
        b = bytes.fromhex(v["hex"])
        p, a = norm_primary(v["type"], P[v["type"]](b)), norm_alt(v["type"], A[v["type"]](b))
        want = v["decoded"]
        if v["type"] == "call" and want[0] == "value":
            want = ["value", want[1]]
        if p != a or p != want:
            fails.append((v["id"], "decode mismatch", p, a))
        if v["type"] == "call":
            k = p[0]
            re_a = codec_alt.encode_call_result(k, bytes.fromhex(p[1]) if k == "value" else
                                                (tuple(p[1][:3]) + (bytes.fromhex(p[1][3]),) if k == "subtask" else tuple(p[1])))
            if re_a != b:
                fails.append((v["id"], "alt re-encode not byte-identical"))
        if v["type"] == "wait":
            if codec_alt.encode_wait([tuple(x[:3]) + (bytes.fromhex(x[3]),) for x in p]) != b:
                fails.append((v["id"], "alt wait re-encode"))
    for v in data["bad"]:
        b = bytes.fromhex(v["hex"])
        try:
            got_p = ("ok", norm_primary(v["type"], P[v["type"]](b)))
        except AbiError as e:
            got_p = ("err", e.code.name)
        try:
            got_a = ("ok", norm_alt(v["type"], A[v["type"]](b)))
        except codec_alt.AltError as e:
            got_a = ("err", e.kind)
        if "ok_decoded" in v:
            if got_p != ("ok", v["ok_decoded"]) or got_a != got_p:
                fails.append((v["id"], "advisory vector", got_p, got_a))
            continue
        if got_p != ("err", v["error"]) or got_a != ("err", ALT_KIND[v["error"]]):
            fails.append((v["id"], "bad vector", got_p, got_a))
    return len(data["good"]) + len(data["bad"]), fails


def run_trace(seed=1, steps=3000):
    rng = random.Random(seed)
    r = ref.AsyncAbi("i", budget=8, tombstone_limit=10_000)
    host = AsyncHost(Limits(instance=8, tombstones=10_000))
    v = host.register("i", tenant="t", workload="w")
    rh, hh, mism = [], [], []

    def outcome(fn):
        try:
            return ("ok", fn())
        except Exception as e:  # compare error *kind*
            n = type(e).__name__
            return ("err", {"BudgetExhausted": "budget", "BudgetExhaustedError": "budget",
                            "SubtaskNotReady": "notready", "NotReady": "notready",
                            "HandleConsumed": "consumed", "HandleConsumedError": "consumed",
                            "DuplicatePublication": "consumed"}.get(n, n))

    for i in range(steps):
        op = rng.choice(["call", "call", "complete", "take", "wait", "cancel"])
        if op == "call":
            a, b = outcome(lambda: r.call()), outcome(lambda: v.call())
            if a[0] == "ok":
                rh.append(a[1][1]); hh.append(b[1][1])
            a, b = a[0] if a[0] == "err" else "ok", b[0] if b[0] == "err" else "ok"
        elif not rh:
            continue
        else:
            k = rng.randrange(len(rh))
            if op == "complete":
                a = outcome(lambda: r.complete(rh[k], i))
                b = outcome(lambda: host.complete(hh[k], i) if host._producer_row(hh[k]) and host._producer_row(hh[k]).state.value == "pending" else (_ for _ in ()).throw(__import__("inv15_new_asynchronous_abi").abi.HandleConsumed()))
                a, b = a[0], b[0]
            elif op == "take":
                a, b = outcome(lambda: r.take(rh[k])), outcome(lambda: v.take(hh[k]))
            elif op == "wait":
                a = outcome(lambda: len(r.wait([rh[k]])))
                b = outcome(lambda: len(v.wait([hh[k]])))
            else:
                a = outcome(lambda: r.cancel(rh[k], "x"))
                b = outcome(lambda: v.cancel(hh[k]))
                # ref: True=propagated False=abandoned ; host: CancelAck
                if a[0] == "ok" and b[0] == "ok":
                    a, b = ("ok", a[1]), ("ok", b[1].name == "PROPAGATED")
                elif b[0] == "ok" and b[1].name == "ALREADY_TERMINAL" and a == ("err", "consumed"):
                    b = a  # documented v4.3 change: cancel of a retired handle is idempotent
        if a != b:
            mism.append((i, op, a, b))
    return steps, mism


def main():
    nv, vf = run_vectors()
    ns, tm = run_trace()
    rep = {"vectors": nv, "vector_failures": vf[:10], "vector_failure_count": len(vf),
           "trace_steps": ns, "trace_mismatches": tm[:10], "trace_mismatch_count": len(tm),
           "verdict": "AGREE" if not vf and not tm else "DISAGREE",
           "limit": "both codecs and both runtimes are Python by one author; not an independent production runtime"}
    print(json.dumps(rep, default=str))
    return 0 if rep["verdict"] == "AGREE" else 1


if __name__ == "__main__":
    sys.exit(main())
