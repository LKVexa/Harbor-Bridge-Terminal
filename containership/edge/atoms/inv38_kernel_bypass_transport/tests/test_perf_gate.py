from inv38_kernel_bypass_transport import perf_gate as pg
def test_latency_regression_fails():
    r = pg.compare("p99_us", 4.0, 4.5, 5.0)   # +12.5% > 5%
    assert not r.passed and r.reason == "PK_BYPASS_PERF_REGRESSION"
def test_latency_within_threshold_passes():
    r = pg.compare("p99_us", 4.0, 4.1, 5.0)
    assert r.passed
def test_throughput_drop_fails():
    r = pg.compare("throughput_mps", 1000.0, 900.0, 5.0)  # -10% > 5%
    assert not r.passed
def test_missing_evidence_fails_gate():
    ok, results = pg.gate({"p99_us": 4.0}, {}, {"p99_us": 5.0})
    assert not ok and results[0].reason == "PK_BYPASS_PERF_EVIDENCE_MISSING"
