"""Exhaustive interleaving checker for the INV-14 wake protocol (component P2-23; C086).

This checks a *model* of polling.py's protocol, step for step, not the Python
code itself (the real code is covered by the thread-stress tests).  Threads:
  poller     : REG (register event on each pollable; promote pending)
               CHK (scan readiness; done if any ready)
               WAIT (block unless event set; on wake: clear event, back to CHK)
  signaller k: S1 (lock: if not ready/pending -> pending=True; snapshot waiters)
               S2 (set every snapshotted event)
  clearer    : CLR (ready = pending = False)      [optional]
  canceller  : CAN1 (cancelled=True; snapshot)  CAN2 (set events)  [optional]
Property LOST_WAKEUP: a terminal state where the poller is blocked in WAIT while
some member is latched (pending or ready) or the cancel token is set.
A mutant (``check_before_register``) reproduces the classic bug and MUST be
caught -- that proves the checker can see the failure it claims to exclude.
"""
import itertools, json, sys


def explore(n_pollables=2, signals=(0, 1), clearer=False, canceller=False, mutant=None):
    init = {"pc": 0, "ev": False, "reg": frozenset(), "pend": (False,) * n_pollables,
            "ready": (False,) * n_pollables, "sig": tuple(0 for _ in signals), "snap": tuple(frozenset() for _ in signals),
            "clr": 0 if clearer else 2, "can": 0 if canceller else 3, "cancelled": False, "can_snap": False, "done": False}
    POLLER = ["CHK", "REG", "WAIT"] if mutant == "check_before_register" else ["REG", "CHK", "WAIT"]
    states, stack, terminals, violations = set(), [init], 0, []

    def key(s):
        return tuple(sorted((k, v if not isinstance(v, dict) else tuple(v.items())) for k, v in s.items()))

    def promote(s):
        pend, ready = list(s["pend"]), list(s["ready"])
        for i in range(n_pollables):
            if pend[i]:
                ready[i], pend[i] = True, False
        s["pend"], s["ready"] = tuple(pend), tuple(ready)

    while stack:
        s = stack.pop()
        k = key(s)
        if k in states:
            continue
        states.add(k)
        moves = []
        if not s["done"]:
            step = POLLER[s["pc"]] if s["pc"] < len(POLLER) else "WAIT"
            t = dict(s)
            if step == "REG":
                t["reg"] = frozenset(range(n_pollables)); promote(t) if mutant != "no_promote" else None; t["pc"] += 1; moves.append(t)
            elif step == "CHK":
                promote(t)
                if any(t["ready"]) or t["cancelled"]:
                    t["done"] = True
                else:
                    t["pc"] += 1
                moves.append(t)
            elif step == "WAIT":
                if t["ev"]:
                    t["ev"] = False; t["pc"] = POLLER.index("CHK"); moves.append(t)
                # else blocked: no move
        for j, target in enumerate(signals):
            if s["sig"][j] == 0:
                t = dict(s)
                if not (t["ready"][target] or t["pend"][target]):
                    p = list(t["pend"]); p[target] = True; t["pend"] = tuple(p)
                    sn = list(t["snap"]); sn[j] = frozenset({"poller"} if target in t["reg"] else set()); t["snap"] = tuple(sn)
                sg = list(t["sig"]); sg[j] = 1; t["sig"] = tuple(sg); moves.append(t)
            elif s["sig"][j] == 1:
                t = dict(s)
                if s["snap"][j]:
                    t["ev"] = True
                sg = list(t["sig"]); sg[j] = 2; t["sig"] = tuple(sg); moves.append(t)
        if s["clr"] == 0:
            t = dict(s); t["pend"] = (False,) * n_pollables; t["ready"] = (False,) * n_pollables; t["clr"] = 2; moves.append(t)
        if s["can"] == 0:
            t = dict(s); t["cancelled"] = True; t["can_snap"] = s["pc"] > 0 or POLLER[0] != "REG"; t["can"] = 1; moves.append(t)
        elif s["can"] == 1:
            t = dict(s); t["can"] = 3
            if s["can_snap"]:
                t["ev"] = True
            moves.append(t)
        if not moves:
            terminals += 1
            blocked = not s["done"]
            latched = any(s["ready"]) or any(s["pend"]) or s["cancelled"]
            if blocked and latched:
                violations.append({k2: (list(v) if isinstance(v, (tuple, frozenset)) else v) for k2, v in s.items()})
        stack.extend(moves)
    return {"states": len(states), "terminals": terminals, "violations": len(violations),
            "example": violations[0] if violations else None}


def main():
    cases = {
        "1 pollable, 1 signal": dict(n_pollables=1, signals=(0,)),
        "2 pollables, 2 signals": dict(n_pollables=2, signals=(0, 1)),
        "2 pollables, 3 signals, clear": dict(n_pollables=2, signals=(0, 1, 1), clearer=True),
        "2 pollables, 2 signals, cancel": dict(n_pollables=2, signals=(0, 1), canceller=True),
        "3 pollables, 3 signals, clear+cancel": dict(n_pollables=3, signals=(0, 1, 2), clearer=True, canceller=True),
    }
    out = {name: explore(**kw) for name, kw in cases.items()}
    out["MUTANT check_before_register"] = explore(n_pollables=1, signals=(0,), mutant="check_before_register")
    print(json.dumps(out, indent=1, default=str))
    ok = all(v["violations"] == 0 for k, v in out.items() if not k.startswith("MUTANT")) \
        and out["MUTANT check_before_register"]["violations"] > 0
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
