import time
from inv38_kernel_bypass_transport import release_gate as rg
KEY = b"release-key"
def _build(waivers=None): return rg.build(source_revision="rev1", package_digest="pd", waivers=waivers)
def test_verdict_conditional_go_with_inprogress_blocked():
    rec = _build()
    # our RTM has IN_PROGRESS + BLOCKED items -> CONDITIONAL_GO, not GO, not NO_GO
    assert rec["verdict"] == "CONDITIONAL_GO"
    assert rec["conditions"]  # named conditions present
def test_signature_roundtrip_and_tamper():
    rec = _build(); sig = rg.sign(rec, KEY)
    rg.verify(rec, sig, KEY)
    rec["verdict"] = "GO"
    try: rg.verify(rec, sig, KEY); assert False
    except rg.GateRejected: pass
def test_expired_waiver_rejected():
    rec = _build(waivers=[{"requirement":"INV-38-C068","expiry":0,"approver":"x"}])
    try: rg.enforce(rec, now=time.time()); assert False
    except rg.GateRejected: pass
def test_unapproved_waiver_rejected():
    rec = _build(waivers=[{"requirement":"INV-38-C068","expiry":time.time()+9999,"approver":""}])
    try: rg.enforce(rec, now=time.time()); assert False
    except rg.GateRejected: pass
def test_conditional_go_enforced_ok():
    rec = _build()
    assert rg.enforce(rec, now=time.time()) == "CONDITIONAL_GO"
