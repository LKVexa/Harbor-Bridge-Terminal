from inv38_kernel_bypass_transport import health_stall as h
def test_stall_detected():
    d = h.StallDetector()
    st, r = d.observe(oldest_inflight_age=0.06, completion_delta=0, ring_nonempty=True)
    assert st == "FAILED" and r == "PK_BYPASS_STALL_DETECTED"
def test_no_progress_is_stall():
    d = h.StallDetector()
    st, _ = d.observe(oldest_inflight_age=0.0, completion_delta=0, ring_nonempty=True)
    assert st == "FAILED"
def test_hysteresis_requires_streak():
    d = h.StallDetector()
    d.observe(oldest_inflight_age=0.06, completion_delta=0, ring_nonempty=True)  # FAILED
    st1, r1 = d.observe(oldest_inflight_age=0.0, completion_delta=1, ring_nonempty=False)
    assert r1 == "PK_BYPASS_RECOVERING"
    d.observe(oldest_inflight_age=0.0, completion_delta=1, ring_nonempty=False)
    st3, r3 = d.observe(oldest_inflight_age=0.0, completion_delta=1, ring_nonempty=False)
    assert st3 == "HEALTHY"
