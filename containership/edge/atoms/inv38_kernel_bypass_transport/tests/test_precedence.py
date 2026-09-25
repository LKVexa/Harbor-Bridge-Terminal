from inv38_kernel_bypass_transport import precedence as p
def test_security_beats_performance():
    assert p.security_beats_performance()
    w, r = p.resolve(["PERFORMANCE", "SECURITY"]); assert w == "SECURITY"
def test_residency_beats_availability():
    w, _ = p.resolve(["AVAILABILITY", "RESIDENCY"]); assert w == "RESIDENCY"
def test_deterministic_order():
    import itertools
    for combo in itertools.permutations(["SECURITY","COST","PERFORMANCE"]):
        assert p.resolve(list(combo))[0] == "SECURITY"
def test_unknown_rejected():
    try: p.resolve(["FOO"]); assert False
    except p.PrecedenceError: pass
