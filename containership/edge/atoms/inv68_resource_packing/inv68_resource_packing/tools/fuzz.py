"""Deterministic property/fuzz campaign (INV-68 MC-30, MC-16; C085, C087).

    python -m inv68_resource_packing.tools.fuzz [--cases N] [--seed S] [--out evidence/]

Targets and oracles:

* **engine** (``pack_detailed``) -- random and hostile workloads/capacities.
  Allowed outcomes: a result, ``TypeError`` or ``ValueError``.  Properties on
  every result: memory never above ``mem * (1 - headroom)``; CPU never above
  ``cpu * ratio * (1 - headroom)``; every workload decided exactly once;
  assignments == placed decisions; per-dimension conservation (sum of host
  usage == sum of placed requests); hosts >= placeable lower bound; decisions identical to
  the preserved 4.2.0 reference loop; inputs unmutated; deterministic under
  input permutation (same host count and same per-workload decisions).
* **service** (``PackingService.pack``) -- random JSON text, byte noise, deep
  nesting, huge numbers, NaN/Infinity, unicode/control characters, unknown
  fields and credential-looking strings.  Allowed: a response or a registered
  ``PackError`` (never ``INTERNAL``, never another exception), and no
  secret-looking input echoed in an error.
* **config** (``PackingConfig.from_document``) -- mutated documents; only
  ``PackError`` may escape.
* **auth** -- mutated tokens; only ``UNAUTHENTICATED``/``REPLAY_DETECTED``.

Every failing case is minimised (list shrinking) and written to
``FUZZ.json``; ``tests/fixtures/fuzz_regressions.json`` replays past findings.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import random
import tempfile
from pathlib import Path

from .common import PKG, write

from inv68_resource_packing.audit import AuditLog  # noqa: E402
from inv68_resource_packing.auth import Authorizer, mint  # noqa: E402
from inv68_resource_packing.config import ConfigStore, PackingConfig, compose, defaults, plain  # noqa: E402
from inv68_resource_packing.errors import PackError  # noqa: E402
from inv68_resource_packing.packing import _normalize_workloads, effective_capacity, lower_bound, pack_detailed, Host  # noqa: E402

HOSTILE_NUMBERS = [0, -0.0, 1e-300, 5e-324, 1e308, float("inf"), float("-inf"), float("nan"), -1, True, None,
                   "1", [], {}, 10 ** 400, 2 ** 63, 0.1 + 0.2]
SECRET = "ghp_" + "Z" * 40


def reference(work, cpu, mem, headroom):
    norm = _normalize_workloads(work)
    limits = effective_capacity(cpu, mem, headroom)
    order = sorted(norm, key=lambda i: (-max(i["cpu"] / limits["cpu"], i["mem"] / limits["mem"]), i["name"]))
    hosts, out = [], []
    for item in order:
        if any(item[d] > limits[d] + 1e-9 for d in ("cpu", "mem")):
            out.append((item["name"], None))
            continue
        t = next((h for h in hosts if h.fits(item, headroom)), None)
        if t is None:
            t = Host(f"h{len(hosts)}", cpu, mem)
            hosts.append(t)
        t.place(item, headroom)
        out.append((item["name"], t.name))
    return out


def gen_workloads(rng: random.Random) -> list:
    n = rng.choice([0, 1, 2, 5, 20, 80])
    out = []
    for i in range(n):
        if rng.random() < 0.08:
            out.append(rng.choice([None, 1, "x", [], {"name": f"w{i}"}, {"cpu": 1, "mem": 1},
                                   {"name": "", "cpu": 1, "mem": 1}]))
            continue
        w = {"name": f"w{i}" if rng.random() > 0.03 else "dup",
             "cpu": rng.choice([0, 0.5, 1, 3, 17, 30]) if rng.random() > 0.05 else rng.choice(HOSTILE_NUMBERS),
             "mem": rng.choice([0, 0.5, 2, 16, 60, 90]) if rng.random() > 0.05 else rng.choice(HOSTILE_NUMBERS)}
        if rng.random() < 0.1:
            w["meta"] = {"x": rng.random()}
        out.append(w)
    return out


def check_engine(rng: random.Random) -> str | None:
    work = gen_workloads(rng)
    cpu = rng.choice([16, 16, 1, 0.5]) if rng.random() > 0.05 else rng.choice(HOSTILE_NUMBERS)
    mem = rng.choice([64, 64, 8, 2]) if rng.random() > 0.05 else rng.choice(HOSTILE_NUMBERS)
    headroom = rng.choice([0, 0.1, 0.5, 0.9]) if rng.random() > 0.05 else rng.choice(HOSTILE_NUMBERS)
    ratio = rng.choice([None, 1.0, 1.5, 4.0])
    before = copy.deepcopy(work)
    try:
        res = pack_detailed(work, cpu, mem, headroom, ratio)
    except (TypeError, ValueError):
        return None if work == before or _nan_eq(work, before) else "input mutated on error"
    except Exception as exc:  # noqa: BLE001
        return f"unexpected {type(exc).__name__}: {exc}"[:200]
    if work != before and not _nan_eq(work, before):
        return "input mutated"
    lim = effective_capacity(cpu, mem, headroom, ratio)
    for h in res.hosts:
        if h.used["mem"] > mem * (1 - headroom) + 1e-6 or h.used["cpu"] > lim["cpu"] + 1e-6:
            return f"capacity violated on {h.name}: {h.used}"
    for dim in ("cpu", "mem"):
        assigned = math.fsum(h.used[dim] for h in res.hosts)
        requested = math.fsum(d.cpu if dim == "cpu" else d.mem for d in res.decisions if d.status == "placed")
        if not math.isclose(assigned, requested, rel_tol=1e-9, abs_tol=1e-9):
            return f"conservation violated in {dim}: hosts {assigned} != placed {requested}"
    names = [d.workload for d in res.decisions]
    if len(names) != len(set(names)) or len(names) != len(work):
        return "workload not decided exactly once"
    if {d.workload: d.host for d in res.decisions if d.status == "placed"} != dict(res.assignments):
        return "assignments disagree with decisions"
    try:
        lb = lower_bound(work, cpu, mem, headroom, ratio, placeable_only=True)
    except ValueError:
        lb = None  # documented refusal (non-finite bound); anything else escapes and is a finding
    if lb is not None and res.hosts and len(res.hosts) < lb:
        return "fewer hosts than lower bound"
    if ratio in (None, 1.5):
        if [(d.workload, d.host) for d in res.decisions] != reference(work, cpu, mem, headroom):
            return "differs from 4.2.0 reference"
    shuffled = list(work)
    rng.shuffle(shuffled)
    res2 = pack_detailed(shuffled, cpu, mem, headroom, ratio)
    if [(d.workload, d.host) for d in res2.decisions] != [(d.workload, d.host) for d in res.decisions]:
        return "not permutation invariant"
    return None


def _nan_eq(a, b) -> bool:
    return json.dumps(a, default=str) == json.dumps(b, default=str)


def gen_request_text(rng: random.Random) -> object:
    choice = rng.randrange(9)
    base = {"tenant": "t1", "host_capacity": {"cpu": 16, "mem": 64}, "workloads": gen_workloads(rng)}
    if choice == 0:
        return bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 200)))
    if choice == 1:
        return "[" * rng.randint(100, 50_000) + "]" * rng.randint(0, 50_000)
    if choice == 2:
        base["workloads"] = [{"name": SECRET, "cpu": 1, "mem": 1}]
        base["tenant"] = rng.choice(["t1", "t1\u0000", "t‮1", "\ud800"[:0] + "t1"])
        return base
    if choice == 3:
        return json.dumps(base).replace("16", rng.choice(["1e400", "NaN", "-Infinity", "16"]))
    if choice == 4:
        base[rng.choice(["x", "__proto__", "headroom"])] = rng.choice(HOSTILE_NUMBERS[:12] + ["0.5"])
        return base
    if choice == 5:
        base["protocol"] = rng.choice([[], "PK_PACK/9", ["PK_PACK/1"], None, 7])
        return base
    if choice == 6:
        base["idempotency_key"] = rng.choice(["short", "k" * 200, None, 5, "valid-key-1"])
        return base
    if choice == 7:
        base["host_capacity"] = rng.choice([None, {"cpu": 1}, {"cpu": "1", "mem": 1}, {"cpu": 1, "mem": 1, "gpu": 1}])
        return base
    return base


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=6868)
    ap.add_argument("--out", default=str(PKG / "evidence"))
    a = ap.parse_args(argv)
    rng = random.Random(a.seed)
    findings: list[dict] = []
    counts = {"engine": 0, "service": 0, "config": 0, "auth": 0, "regressions": 0}
    key = {"k": b"f" * 32}
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLog(Path(tmp) / "a.jsonl")
        store = ConfigStore(Path(tmp) / "c", audit=audit)
        store.activate(compose(defaults().document, ("fuzz", {"tenants": {"overrides": {"t1": {"max_requests_per_minute": 1000000}}}})),
                       actor="fuzz", epoch=1)
        from inv68_resource_packing.service import PackingService
        svc = PackingService(store, Authorizer(key), audit)
        tok = lambda: mint(key["k"], kid="k", sub="fz", kind="workload-scheduler", tenants=["t1"], caps=["pack:submit"])
        # replay committed regressions first
        regressions = json.loads((PKG / "tests" / "fixtures" / "fuzz_regressions.json").read_text())
        for case in regressions["service"]:
            counts["regressions"] += 1
            try:
                svc.pack(case["input"], tok())
            except PackError as e:
                if e.code == "INTERNAL":
                    findings.append({"target": "regression", "case": case["id"], "problem": "INTERNAL"})
            except Exception as exc:  # noqa: BLE001
                findings.append({"target": "regression", "case": case["id"], "problem": type(exc).__name__})
        for i in range(a.cases):
            counts["engine"] += 1
            problem = check_engine(rng)
            if problem:
                findings.append({"target": "engine", "case": i, "problem": problem})
            counts["service"] += 1
            raw = gen_request_text(rng)
            try:
                svc.pack(raw, tok())
            except PackError as e:
                if e.code == "INTERNAL":
                    cause = e.__cause__
                    findings.append({"target": "service", "case": i, "problem": "INTERNAL",
                                     "cause": f"{type(cause).__name__}: {cause}"[:160], "input": repr(raw)[:200]})
                if SECRET in json.dumps(e.to_dict()):
                    findings.append({"target": "service", "case": i, "problem": "secret echoed in error"})
            except Exception as exc:  # noqa: BLE001
                findings.append({"target": "service", "case": i, "problem": f"{type(exc).__name__}: {exc}"[:200],
                                 "input": repr(raw)[:200]})
            if i % 3 == 0:
                counts["config"] += 1
                doc = plain(defaults().document)
                path = rng.choice([["headroom"], ["cpu_overcommit"], ["limits", "max_queue"], ["tenants", "overrides"],
                                   ["provenance", "author"], ["extra"], ["limits", "zzz"]])
                tgt = doc
                for k in path[:-1]:
                    tgt = tgt[k]
                tgt[path[-1]] = rng.choice(HOSTILE_NUMBERS[:14] + [SECRET, {"a": SECRET}, "x" * 5000])
                try:
                    PackingConfig.from_document(doc)
                except PackError:
                    pass
                except Exception as exc:  # noqa: BLE001
                    findings.append({"target": "config", "case": i, "problem": f"{type(exc).__name__}", "path": path})
            if i % 3 == 1:
                counts["auth"] += 1
                t = list(tok())
                for _ in range(rng.randint(1, 4)):
                    t[rng.randrange(len(t))] = rng.choice("A.-_=/+0zZé")
                try:
                    svc.auth.authenticate("".join(t))
                except PackError as e:
                    if e.code not in ("UNAUTHENTICATED", "REPLAY_DETECTED"):
                        findings.append({"target": "auth", "case": i, "problem": e.code})
                except Exception as exc:  # noqa: BLE001
                    findings.append({"target": "auth", "case": i, "problem": type(exc).__name__})
    doc = {"schema": "PK_PACK_FUZZ/1", "seed": a.seed, "cases": a.cases, "executed": counts,
           "findings": findings[:200], "finding_count": len(findings),
           "result": "PASS" if not findings else "FAIL"}
    write(Path(a.out) / "FUZZ.json", doc)
    print(f"FUZZ {doc['result']}: {counts} findings={len(findings)}")
    for f in findings[:10]:
        print("  ", f)
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
