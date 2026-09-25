from inv38_kernel_bypass_transport import decisions as d
def test_every_record_has_reason_code():
    log = d.DecisionLog()
    for kind in ["KERNEL_FALLBACK","REJECTION","RETRY"]:
        rec = log.record(kind=kind, operation_id="op1", action="act", reason_code="PK_BYPASS_OK")
        assert rec["reason_code"] and rec["decision_id"]
def test_no_payload_in_record():
    log = d.DecisionLog()
    rec = log.record(kind="ADMISSION", operation_id="op", action="admit",
                     reason_code="PK_BYPASS_OK", inputs={"payload": b"secret-bytes"})
    # only fingerprints stored, never raw payload
    assert "secret" not in str(rec)
    assert len(rec["input_fingerprints"]["payload"]) == 16
def test_explain_human_and_machine():
    log = d.DecisionLog()
    rec = log.record(kind="KERNEL_FALLBACK", operation_id="op", action="fallback", reason_code="PK_BYPASS_KERNEL_FALLBACK")
    human = d.explain(rec); machine = d.explain(rec, machine=True)
    assert "fallback" in human and machine["decision_id"] == rec["decision_id"]
def test_unknown_kind_rejected():
    try: d.DecisionLog().record(kind="NOPE", operation_id="o", action="a", reason_code="r"); assert False
    except ValueError: pass
