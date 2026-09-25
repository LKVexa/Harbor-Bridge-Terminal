from inv38_kernel_bypass_transport import telemetry_policy as tp
def test_security_audit_never_sampled():
    p = tp.TelemetryPolicy()
    assert p.effective_sample_rate("security_audit", is_error_or_security=False) == 1.0
def test_errors_fully_sampled():
    p = tp.TelemetryPolicy()
    assert p.effective_sample_rate("traces", is_error_or_security=True) == 1.0
def test_validate_flags_weakened_audit():
    p = tp.TelemetryPolicy(); p.sample_rate["security_audit"] = 0.5
    assert any("security_audit" in x for x in p.validate())
