from inv38_kernel_bypass_transport import logging_schema as lg
def test_redaction():
    rec = lg.make_record(level="INFO", event="post", operation_id="op1",
                         reason_code="PK_BYPASS_OK", extra={"mr_key": 42, "addr": 0xdead, "size": 128})
    assert rec["mr_key"] == "<redacted>" and rec["addr"] == "<redacted>" and rec["size"] == 128
def test_control_char_escaped():
    rec = lg.make_record(level="WARN", event="rejection", operation_id="op2",
                         reason_code="PK_BYPASS_OUT_OF_BOUNDS", extra={"note": "line1\nline2"})
    assert "\\n" in rec["note"] and "\n" not in rec["note"]
def test_unknown_event_rejected():
    try: lg.make_record(level="INFO", event="nope", operation_id="x", reason_code="y"); assert False
    except ValueError: pass
def test_serialize_is_single_line():
    rec = lg.make_record(level="INFO", event="poll", operation_id="op", reason_code="PK_BYPASS_OK")
    assert "\n" not in lg.serialize(rec)
