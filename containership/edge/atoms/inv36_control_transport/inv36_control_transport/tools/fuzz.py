"""Bounded, seeded, dependency-free fuzz / property campaign (MC-14).

    python -m inv36_control_transport.tools.fuzz --iterations 2000 --seed 1 --out fuzz.json

Every target feeds attacker-controlled bytes to an untrusted boundary and
asserts the invariants in docs/FUZZING.md:

* no exception other than the target's typed refusal escapes (no crash);
* no allocation above the hard bound driven by an attacker-supplied length;
* failed opens never mutate session sequence state;
* accepted sequence numbers advance by exactly one;
* canonical encodings round-trip exactly.

Each case is generated from its own recorded seed, so a failure is exactly
reproducible from ``(target, case_seed)``.  Failures are written to
``fixtures/fuzz-regressions/<target>-<sha>.json`` and the unit tests replay
every persisted case forever after (MC-14.011).  Byte-level shrinking is not
implemented; the per-case seed is the minimal reproducer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import platform
import random
import sys
import time
import tracemalloc
import traceback
from typing import Callable

from .. import config as cfgmod
from .. import messages, stream
from ..errors import Inv36Error
from ..handshake import HandshakeError, ServerHandshake, parse_credential
from ..policy import AuthzError, PolicyDocument
from ..quarantine import QuarantineError, QuarantineRegistry
from ..transport import MAX_WIRE_FRAME, Session, TransportError

PKG = pathlib.Path(__file__).resolve().parents[1]
REGRESSIONS = PKG / "fixtures" / "fuzz-regressions"
SHARED = hashlib.sha256(b"fuzz shared").digest()
SID = bytes(range(16))
ALLOC_BOUND = 4 * MAX_WIRE_FRAME


class InvariantViolation(AssertionError):
    pass


def _mutate(rng: random.Random, data: bytes) -> bytes:
    b = bytearray(data)
    for _ in range(rng.randint(1, 4)):
        op = rng.randrange(7)
        if op == 0 and b:
            b[rng.randrange(len(b))] ^= 1 << rng.randrange(8)
        elif op == 1 and b:
            del b[rng.randrange(len(b)):rng.randrange(len(b)) + 1]
        elif op == 2:
            pos = rng.randrange(len(b) + 1)
            b[pos:pos] = rng.randbytes(rng.randint(1, 8))
        elif op == 3 and b:
            b = b[: rng.randrange(len(b))]
        elif op == 4 and len(b) >= 4:
            pos = rng.randrange(len(b) - 3)
            b[pos:pos + 4] = rng.choice([b"\xff\xff\xff\xff", b"\x00\x00\x00\x00", b"\x00\x01\x00\x1f",
                                         b"\x7f\xff\xff\xff"])
        elif op == 5 and b:
            pos = rng.randrange(len(b))
            b[pos] = rng.choice([0, 1, 0x7F, 0x80, 0xFF])
        else:
            b += b[: rng.randint(0, 16)]
    return bytes(b)


def _pair() -> tuple[Session, Session]:
    return Session("fz-a", "fz-b", SHARED, session_id=SID), Session("fz-b", "fz-a", SHARED, session_id=SID)


# ------------------------------------------------------------------------------ targets
def t_record_header(rng: random.Random) -> bytes:
    data = rng.randbytes(stream.RECORD_HEADER) if rng.random() < 0.5 else _mutate(rng, stream.encode_record(2, b"x"))[:6]
    try:
        stream.parse_record_header(data.ljust(6, b"\0")[:6])
    except stream.StreamError:
        pass
    return data


def t_stream_fragmented(rng: random.Random) -> bytes:
    """Valid records fragmented at random positions must reassemble exactly (MC-14.004)."""
    payloads = [rng.randbytes(rng.randint(0, 300)) for _ in range(rng.randint(1, 5))]
    wire = stream.PREAMBLE + b"".join(stream.encode_record(stream.FRAME, p) for p in payloads)
    a, b = stream.FakeStream.pair(a_plan=stream.FaultPlan(max_chunk=rng.randint(1, 7)))
    view = memoryview(wire)
    while view:
        n = a.send(bytes(view), 1.0)
        view = view[n:]
    a.close()
    conn = stream.Connection(b, read_timeout=1.0)
    conn.stream.send(stream.PREAMBLE, 1.0)
    got = conn._read_exact(len(stream.PREAMBLE), stream._Deadline(1.0), at_boundary=True)
    if got != stream.PREAMBLE:
        raise InvariantViolation("preamble mismatch after fragmentation")
    for p in payloads:
        rtype, body = conn.recv_record()
        if rtype != stream.FRAME or body != p:
            raise InvariantViolation("fragmented record did not reassemble exactly")
    try:
        conn.recv_record()
        raise InvariantViolation("expected EOF")
    except stream.StreamEOF:
        pass
    return wire


def t_stream_garbage(rng: random.Random) -> bytes:
    data = stream.PREAMBLE + (_mutate(rng, stream.encode_record(2, rng.randbytes(rng.randint(0, 64))))
                              if rng.random() < 0.7 else rng.randbytes(rng.randint(0, 64)))
    a, b = stream.FakeStream.pair()
    view = memoryview(data)
    while view:
        view = view[a.send(bytes(view), 1.0):]
    a.close()
    conn = stream.Connection(b, read_timeout=0.2)
    tracemalloc.start()
    try:
        conn._read_exact(len(stream.PREAMBLE), stream._Deadline(0.2), at_boundary=True)
        while True:
            conn.recv_record()
    except stream.StreamError:
        pass
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    if peak > ALLOC_BOUND:
        raise InvariantViolation(f"allocation {peak} above bound")
    return data


def t_frame_open(rng: random.Random) -> bytes:
    a, b = _pair()
    frames = [a.seal(rng.randbytes(rng.randint(0, 64))) for _ in range(3)]
    b.open(frames[0])
    before = b.recv_seq
    data = _mutate(rng, rng.choice(frames)) if rng.random() < 0.8 else rng.randbytes(rng.randint(0, 120))
    try:
        b.open(data)
        if b.recv_seq != before + 1:
            raise InvariantViolation("accepted frame did not advance sequence by exactly one")
    except TransportError as exc:
        if b.recv_seq != before:
            raise InvariantViolation("failed open mutated sequence state") from exc
    return data


def t_session_stateful(rng: random.Random) -> bytes:
    """Random drop/dup/reorder schedules: accepted sequence strictly +1 (MC-14.002/.015)."""
    a, b = _pair()
    frames = [a.seal(i.to_bytes(2, "big")) for i in range(12)]
    sched = []
    for f in frames:
        r = rng.random()
        if r < 0.15:
            continue
        sched.append(f)
        if r > 0.85:
            sched.append(f)
    if rng.random() < 0.3 and len(sched) > 2:
        i = rng.randrange(len(sched) - 1)
        sched[i], sched[i + 1] = sched[i + 1], sched[i]
    last = 0
    for f in sched:
        try:
            pt = b.open(f)
            n = int.from_bytes(pt, "big") + 1
            if n != last + 1 or b.recv_seq != n:
                raise InvariantViolation("sequence did not advance by exactly one")
            last = n
        except TransportError as exc:
            if b.recv_seq != last:
                raise InvariantViolation("rejected frame moved sequence") from exc
    return b"".join(sched)[:256]


def t_message_decode(rng: random.Random) -> bytes:
    good = messages.ControlMessage.of(rng.choice(list(messages.MESSAGE_TYPES)), "tenant-" + str(rng.randint(0, 9)),
                                      rng.randbytes(rng.randint(0, 40)),
                                      traceparent=rng.choice(["", "00-" + "a" * 32 + "-" + "b" * 16 + "-01"]))
    enc = good.encode()
    if messages.decode(enc) != good or messages.decode(enc).encode() != enc:
        raise InvariantViolation("canonical round trip failed")
    data = _mutate(rng, enc)
    try:
        m = messages.decode(data)
        if m.encode() != data:
            raise InvariantViolation("non-canonical encoding accepted")
    except Inv36Error:
        pass
    return data


_WORLD = None


def _world():
    global _WORLD
    if _WORLD is None:
        from ..testing import World
        w = World()
        key, cred = w.identity("fuzz:client", "host_agent", "t1")
        skey, scred = w.identity("fuzz:server", "guest_agent", "t1")
        from ..handshake import ClientHandshake
        ch = ClientHandshake(w.hs_policy(), key, cred).hello()
        _WORLD = (w, skey, scred, ch, cred)
    return _WORLD


def t_handshake(rng: random.Random) -> bytes:
    w, skey, scred, ch, cred = _world()
    data = _mutate(rng, ch) if rng.random() < 0.8 else rng.randbytes(rng.randint(0, 200))
    srv = ServerHandshake(w.hs_policy(), skey, scred)
    try:
        srv.on_client_hello(data)
    except (HandshakeError, Inv36Error):
        pass
    try:
        parse_credential(_mutate(rng, cred))
    except HandshakeError:
        pass
    return data


def t_config(rng: random.Random) -> bytes:
    base = cfgmod.merge(cfgmod.dev_profile())
    k = rng.choice(list(base) + ["bogus_field"])
    v: object = rng.choice([None, -1, 0, 1, 2 ** 70, "x" * 300, "secretref://prod/x", True, 1.5, {}, [], "../../etc"])
    base[k] = v
    try:
        cfgmod.validate(base)
    except (cfgmod.ConfigError, TypeError):
        pass
    return json.dumps({k: str(v)}).encode()


def t_policy(rng: random.Random) -> bytes:
    doc = {"version": rng.choice([0, 1, 2, "x", -5]), "issued_at": 0, "expires_at": rng.choice([1, -1, 1e12]),
           "rules": [{"effect": rng.choice(["allow", "deny", "maybe"]),
                      "roles": [rng.choice(["host_agent", "root", "*"])],
                      "capabilities": [rng.choice(["ctrl.drain", "*", "ctrl.nope", "ctrl.break_glass"])],
                      "tenants": [rng.choice(["$self", "*", "t2"])]}]}
    if rng.random() < 0.3:
        doc["extra"] = 1
    try:
        PolicyDocument.from_dict(doc)
    except (AuthzError, ValueError, KeyError, TypeError):
        pass
    return json.dumps(doc, default=str).encode()


def t_quarantine(rng: random.Random) -> bytes:
    reg = QuarantineRegistry({"k": bytes(32)})
    env = {"directive": {"id": "x", "version": rng.randint(-1, 3), "op": rng.choice(["apply", "lift", "nuke"]),
                         "scope": rng.choice(["peer", "global", "planet"]), "value": rng.choice(["*", "a", ""]),
                         "action": "deny_new_sessions", "issued_at": 0, "ttl_s": 1, "requested_by": "a",
                         "approvers": [], "reason": ""},
           "sig": rng.choice(["00" * 64, "zz", ""])}
    try:
        reg.submit(env, actor="fuzz")
    except (QuarantineError, ValueError):
        pass
    return json.dumps(env).encode()


TARGETS: dict[str, Callable[[random.Random], bytes]] = {
    "record_header": t_record_header, "stream_fragmented": t_stream_fragmented, "stream_garbage": t_stream_garbage,
    "frame_open": t_frame_open, "session_stateful": t_session_stateful, "message_decode": t_message_decode,
    "handshake": t_handshake, "config": t_config, "policy": t_policy, "quarantine": t_quarantine,
}


def run(iterations: int, seed: int, targets: list[str] | None = None, time_budget_s: float | None = None) -> dict:
    results = {}
    failures = []
    t_start = time.monotonic()
    for name in targets or list(TARGETS):
        fn = TARGETS[name]
        rng = random.Random(f"{seed}:{name}")
        n = 0
        t0 = time.monotonic()
        for i in range(iterations):
            if time_budget_s and time.monotonic() - t_start > time_budget_s:
                break
            case_seed = rng.randrange(1 << 62)
            try:
                fn(random.Random(case_seed))
            except Exception as exc:  # noqa: BLE001 - every escape is a finding
                digest = hashlib.sha256(f"{name}:{case_seed}".encode()).hexdigest()[:12]
                REGRESSIONS.mkdir(parents=True, exist_ok=True)
                rec = {"target": name, "case_seed": case_seed, "campaign_seed": seed, "iteration": i,
                       "error": f"{type(exc).__name__}: {exc}"[:500], "trace": traceback.format_exc()[-2000:]}
                (REGRESSIONS / f"{name}-{digest}.json").write_text(json.dumps(rec, indent=1))
                failures.append(rec)
            n += 1
        results[name] = {"iterations": n, "seconds": round(time.monotonic() - t0, 3)}
    return {"schema": "inv36.fuzz/1", "seed": seed, "iterations_per_target": iterations, "targets": results,
            "failures": failures, "ok": not failures, "python": platform.python_version(),
            "platform": platform.platform()}


def replay_regressions() -> list[str]:
    """Re-run every persisted regression case; return names of those that still fail."""
    bad: list[str] = []
    if not REGRESSIONS.exists():
        return bad
    for f in sorted(REGRESSIONS.glob("*.json")):
        rec = json.loads(f.read_text())
        try:
            TARGETS[rec["target"]](random.Random(rec["case_seed"]))
        except Exception:  # noqa: BLE001
            bad.append(f.name)
    return bad


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=500)
    ap.add_argument("--seed", type=int, default=int(os.environ.get("INV36_FUZZ_SEED", "1")))
    ap.add_argument("--target", action="append")
    ap.add_argument("--time-budget", type=float)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.iterations, a.seed, a.target, a.time_budget)
    text = json.dumps(res, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text)
    print(json.dumps({k: res[k] for k in ("seed", "ok")} | {"failures": len(res["failures"])}))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
