from inv38_kernel_bypass_transport import failsafe as f
def test_fresh_dep_ok():
    ok, r = f.may_continue(f.DepStatus("policy", True, 0, 300)); assert ok
def test_expired_cache_fails_closed():
    ok, r = f.may_continue(f.DepStatus("key", False, 120, 60))
    assert not ok and r.startswith("PK_BYPASS_FAIL_CLOSED")
def test_cached_within_bound_holds_fastpath():
    ok, r = f.fast_path_permitted([f.DepStatus("policy", False, 10, 300)])
    assert not ok and "HOLD_FASTPATH" in r
def test_all_fresh_permits_fastpath():
    deps = [f.DepStatus(n, True, 0, 300) for n in f.DEPENDENCIES]
    ok, r = f.fast_path_permitted(deps); assert ok
