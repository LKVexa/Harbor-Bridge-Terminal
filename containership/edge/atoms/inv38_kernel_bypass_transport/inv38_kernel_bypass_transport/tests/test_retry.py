from inv38_kernel_bypass_transport import retry as rr
from inv38_kernel_bypass_transport import outcomes as o
class Clock:
    def __init__(self): self.t = 0.0
    def __call__(self): self.t += 0.0001; return self.t
def _rand(): return 0.5  # deterministic mid-jitter
def test_terminal_not_retried():
    calls = []
    def op(a): calls.append(a); return o.result_for("PK_BYPASS_OUT_OF_BOUNDS")
    res, led = rr.run_with_retry(op, rr.RetryPolicy(), now=Clock(), rand=_rand)
    assert led.attempts == 1 and not led.exhausted
def test_ring_full_retries_then_succeeds():
    seq = ["PK_BYPASS_RING_FULL", "PK_BYPASS_RING_FULL", "PK_BYPASS_OK"]
    def op(a): return o.result_for(seq[a-1])
    res, led = rr.run_with_retry(op, rr.RetryPolicy(), now=Clock(), rand=_rand)
    assert res.reason_code == "PK_BYPASS_OK" and led.attempts == 3
def test_attempts_bounded_no_storm():
    def op(a): return o.result_for("PK_BYPASS_RING_FULL")
    res, led = rr.run_with_retry(op, rr.RetryPolicy(max_attempts=4), now=Clock(), rand=_rand)
    assert led.attempts == 4 and led.exhausted
def test_idempotency_required_for_timeout():
    def op(a): return o.result_for("PK_BYPASS_TIMEOUT")
    res, led = rr.run_with_retry(op, rr.RetryPolicy(), now=Clock(), rand=_rand)
    assert led.attempts == 1  # no key -> not retried
    res2, led2 = rr.run_with_retry(op, rr.RetryPolicy(max_attempts=3), now=Clock(), rand=_rand, idempotency_key="k1")
    assert led2.attempts == 3
def test_jitter_within_range():
    p = rr.RetryPolicy(base_delay=0.01, jitter=0.5, multiplier=1.0, max_delay=1.0)
    lo, hi = p.backoff(1, 0.0), p.backoff(1, 1.0)
    assert abs(lo - 0.005) < 1e-9 and abs(hi - 0.015) < 1e-9
