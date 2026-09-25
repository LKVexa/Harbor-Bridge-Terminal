from inv38_kernel_bypass_transport import tracing as t
def test_valid_context_parses():
    ctx, safe = t.parse_incoming("0"*32, "1"*16, {"tenant": "t1"})
    assert ctx.trace_id == "0"*32
def test_privileged_baggage_stripped():
    _, safe = t.parse_incoming("a"*32, "b"*16, {"admin": "1", "tenant_override": "x", "ok": "y"})
    assert "admin" not in safe and "tenant_override" not in safe and safe["ok"] == "y"
def test_malformed_ids_rejected():
    try: t.parse_incoming("bad", "b"*16, {}); assert False
    except t.TraceError: pass
