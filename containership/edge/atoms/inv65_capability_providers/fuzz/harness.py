"""Deterministic mutation fuzzer (M25).  Stdlib only, seedable, time-boxed.

    python -m inv65_capability_providers.fuzz.harness --iterations 20000 --seed 1

Targets and their invariants:
  authn       -- mutated/forged tokens never authenticate; only PK faults raised
  config      -- link config validator raises only InvalidLink, never crashes/hangs
  schema      -- validator returns a list or SchemaError for any JSON-ish input
  envelope    -- from_envelope raises only SchemaError/ProviderFault
  wal         -- random WAL bytes: recovery either loads or raises STATE_CORRUPT
  authz       -- mutated decisions never authorize
Crashes are written to fuzz/crashes/<target>-<n>.json for triage.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import tempfile
import time

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    __package__ = "inv65_capability_providers.fuzz"

from ..authn.authenticator import Authenticator, TrustRoot, issue_token  # noqa: E402
from ..authz.decision import AuthorizationEnforcer, sign_decision  # noqa: E402
from ..errors.mapping import ProviderFault, from_envelope  # noqa: E402
from ..identity.context import IdentityContext  # noqa: E402
from ..provider import InvalidLink, _validated_config  # noqa: E402
from ..schemas import SchemaError, load, validate  # noqa: E402
from ..state.store import LinkStateStore  # noqa: E402

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus")
IDN = {"tenant": "acme", "environment": "prod", "site": "sfo1", "workload": "shop", "component": "orders"}


def mutate_bytes(b: bytes, r: random.Random) -> bytes:
    b = bytearray(b)
    for _ in range(r.randint(1, 8)):
        op = r.randrange(5)
        if op == 0 and b:
            b[r.randrange(len(b))] = r.randrange(256)
        elif op == 1:
            b.insert(r.randrange(len(b) + 1), r.randrange(256))
        elif op == 2 and b:
            del b[r.randrange(len(b))]
        elif op == 3 and b:
            i = r.randrange(len(b)); b[i:i] = b[i:i + r.randint(1, 16)] * r.randint(1, 4)
        else:
            b += bytes(r.choice([b'"', b"{", b"}", b"\x00", b".", b"=", b"\xff", b"["]))
    return bytes(b[:8192])


def rand_json(r: random.Random, depth=0):
    gens = [
        lambda: None, lambda: True, lambda: r.randint(-2**40, 2**40),
        lambda: r.random() * 1e308 * r.choice([1, -1]), lambda: float("nan"),
        lambda: "".join(chr(r.randrange(0, 0x3000)) for _ in range(r.randint(0, 40))),
        lambda: [rand_json(r, depth + 1) for _ in range(r.randint(0, 4))],
        lambda: {r.choice(["bucket", "user", "token", "secret_ref", "apiKey", "", "x" * 300, "a"]): rand_json(r, depth + 1)
                 for _ in range(r.randint(0, 5))},
        lambda: {"bucket": "b", "user": "u", "k": rand_json(r, depth + 1)},
    ]
    return gens[r.randrange(9 if depth < 5 else 6)]()


def run(iterations: int, seed: int, budget_s: float = 60.0) -> dict:
    r = random.Random(seed)
    root = TrustRoot("pk-issuer", {"k1": b"k" * 32}, "inv65")
    good_tok = issue_token(root, "k1", IDN, nonce="fuzz-nonce-base", ttl_s=3600)
    pk = b"p" * 32
    enf = AuthorizationEnforcer({"pol": pk})
    ident = IdentityContext(**IDN, authenticated=True)
    now = time.time()
    good_dec = sign_decision(pk, {"schema": "PK_AUTHZ_DECISION/1", "decision_id": "d1", "subject": IDN, "action": "call",
                                  "resource": {"contract_id": "c:x", "link_name": "l", "operations": ["get"]}, "effect": "deny",
                                  "issued_at": now - 1, "expires_at": now + 600, "policy_version": "pol:1", "signature": "0" * 64})
    schemas = {n: load(n) for n in ("pk_provider_link", "pk_provider_error", "call_metadata", "authz_decision")}
    stats = {t: {"execs": 0, "expected_rejects": 0, "accepted": 0} for t in ("authn", "config", "schema", "envelope", "wal", "authz")}
    crashes = []
    t_end = time.monotonic() + budget_s
    wal_dir = tempfile.mkdtemp(prefix="inv65-fuzz-")
    for i in range(iterations):
        if time.monotonic() > t_end:
            break
        tgt = ("authn", "config", "schema", "envelope", "wal", "authz")[i % 6]
        s = stats[tgt]; s["execs"] += 1
        try:
            if tgt == "authn":
                tok = mutate_bytes(good_tok.encode(), r).decode("latin-1")
                a = Authenticator(root)
                try:
                    a.authenticate(tok)
                    if tok != good_tok:  # strict canonical decoding => any mutation must fail
                        raise AssertionError("mutated token authenticated")
                    s["accepted"] += 1
                except ProviderFault:
                    s["expected_rejects"] += 1
            elif tgt == "config":
                try:
                    _validated_config("c", rand_json(r)); s["accepted"] += 1
                except InvalidLink:
                    s["expected_rejects"] += 1
            elif tgt == "schema":
                inst = rand_json(r)
                out = validate(inst, schemas[r.choice(list(schemas))])
                s["accepted" if not out else "expected_rejects"] += 1
            elif tgt == "envelope":
                try:
                    from_envelope(rand_json(r) if r.random() < .5 else json.loads(json.dumps({"schema": "PK_PROVIDER_ERROR/1", "code": "PK_PROVIDER_NO_LINK", "message": "m", "retryable": False, "correlation_id": "ab" * 8})))
                    s["accepted"] += 1
                except (SchemaError, ProviderFault):
                    s["expected_rejects"] += 1
            elif tgt == "wal":
                d = os.path.join(wal_dir, str(i)); os.makedirs(d)
                seed_rec = b'{"ck":"x","key":"[]","op":"put","seq":1,"value":{}}\n'
                with open(os.path.join(d, "wal.jsonl"), "wb") as fh:
                    fh.write(mutate_bytes(seed_rec * r.randint(1, 3), r))
                try:
                    LinkStateStore(d); s["accepted"] += 1
                except ProviderFault as e:
                    if e.code != "PK_PROVIDER_STATE_CORRUPT":
                        raise
                    s["expected_rejects"] += 1
            elif tgt == "authz":
                d = json.loads(json.dumps(good_dec))
                k = r.choice(list(d))
                d[k] = rand_json(r) if r.random() < .5 else (d[k] if k != "effect" else "allow")
                try:
                    enf.enforce(d, identity=ident, action="call", contract_id="c:x", link_name="l", operation="get", now=now)
                    raise AssertionError("mutated deny decision authorized")
                except ProviderFault:
                    s["expected_rejects"] += 1
        except Exception as e:  # any other exception is a finding
            crashes.append({"target": tgt, "iteration": i, "error": f"{type(e).__name__}: {e}"[:300]})
    return {"seed": seed, "iterations": sum(v["execs"] for v in stats.values()), "stats": stats, "crashes": crashes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=65)
    ap.add_argument("--budget-s", type=float, default=60)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.iterations, a.seed, a.budget_s)
    if a.out:
        with open(a.out, "w") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps({k: res[k] for k in ("seed", "iterations")} | {"crashes": len(res["crashes"])}))
    return 1 if res["crashes"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
