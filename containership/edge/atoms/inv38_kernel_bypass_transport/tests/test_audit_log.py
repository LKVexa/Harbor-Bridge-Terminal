from inv38_kernel_bypass_transport import audit_log as al
def _log():
    log = al.AuditLog()
    log.emit(event="REGISTER", actor="w1", resource="mr:1", decision="ALLOW", reason_code="PK_BYPASS_OK")
    log.emit(event="FALLBACK_ACTIVATED", actor="sys", resource="queue:0", decision="DEGRADE", reason_code="PK_BYPASS_KERNEL_FALLBACK")
    log.emit(event="AUTHZ_FAILURE", actor="w2", resource="mr:9", decision="DENY", reason_code="PK_BYPASS_UNAUTHORIZED")
    return log
def test_chain_intact():
    ok, msg = al.verify_chain(_log().records()); assert ok, msg
def test_deletion_detected():
    recs = _log().records(); del recs[1]
    ok, _ = al.verify_chain(recs); assert not ok
def test_mutation_detected():
    recs = _log().records(); recs[0]["actor"] = "attacker"
    ok, _ = al.verify_chain(recs); assert not ok
def test_reorder_detected():
    recs = _log().records(); recs[0], recs[1] = recs[1], recs[0]
    ok, _ = al.verify_chain(recs); assert not ok
def test_insertion_detected():
    log = _log(); recs = log.records()
    forged = dict(recs[-1]); forged["seq"] = 99
    recs.append(forged); ok, _ = al.verify_chain(recs); assert not ok
def test_log_injection_rejected():
    log = al.AuditLog()
    try:
        log.emit(event="REGISTER", actor="w1\n{fake}", resource="x", decision="ALLOW", reason_code="PK_BYPASS_OK")
        assert False
    except ValueError: pass
def test_unknown_event_rejected():
    try: al.AuditLog().emit(event="NOPE", actor="a", resource="r", decision="d", reason_code="x"); assert False
    except ValueError: pass
