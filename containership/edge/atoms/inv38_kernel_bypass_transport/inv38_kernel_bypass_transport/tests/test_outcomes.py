from inv38_kernel_bypass_transport import outcomes as o
from inv38_kernel_bypass_transport.transport import (
    OutOfBounds, NotRegistered, RegionBusy, RingFull, CompletionRingFull,
    RegionLimitReached, BypassError)

def test_every_error_code_maps():
    for exc in (OutOfBounds, NotRegistered, RegionBusy, RingFull,
                CompletionRingFull, RegionLimitReached, BypassError):
        assert exc.code in o.ERROR_CODE_TO_REASON, exc.code
        reason = o.ERROR_CODE_TO_REASON[exc.code]
        assert reason in o.REASONS

def test_classify_error_is_stable():
    r1 = o.classify_error(OutOfBounds("x"))
    r2 = o.classify_error(OutOfBounds("y"))
    assert r1.reason_code == r2.reason_code == "PK_BYPASS_OUT_OF_BOUNDS"
    assert r1.outcome is o.Outcome.TERMINAL_FAILURE
    assert r1.retryability is o.Retryability.NOT_RETRYABLE

def test_ring_full_is_retryable():
    r = o.classify_error(RingFull("full"))
    assert r.outcome is o.Outcome.RETRYABLE_FAILURE
    assert r.retryability is o.Retryability.SAFE

def test_public_projection_never_leaks_internal():
    for code, spec in o.REASONS.items():
        pub = o.result_for(code).to_public()
        if not spec.tenant_safe:
            assert pub["reason_code"] == "PK_BYPASS_INTERNAL"
        assert pub["outcome"] in {e.value for e in o.Outcome}

def test_closed_reason_set_pattern():
    for code in o.REASONS:
        assert code.startswith("PK_BYPASS_")
