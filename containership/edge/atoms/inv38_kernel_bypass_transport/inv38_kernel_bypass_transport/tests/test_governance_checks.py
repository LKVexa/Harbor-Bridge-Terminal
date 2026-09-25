import time
from inv38_kernel_bypass_transport import governance_checks as g
def _waiver(**kw):
    base = dict(id="WV-1", requirement="INV-38-C068", scope="s", rationale="r", risk="k",
                compensating_controls="c", owner="o", approver="a",
                created=0, expiry=time.time()+9999, review=time.time()+100)
    base.update(kw); return base
def test_valid_waiver_ok():
    assert g.validate_waivers([_waiver()], time.time()) == []
def test_expired_waiver_flagged():
    assert any("expired" in x for x in g.validate_waivers([_waiver(expiry=0)], time.time()))
def test_duplicate_id_flagged():
    assert any("duplicate" in x for x in g.validate_waivers([_waiver(), _waiver()], time.time()))
def test_safety_invariant_waiver_rejected():
    assert any("safety" in x for x in g.validate_waivers([_waiver(waives_safety_invariant=True)], time.time()))
def test_overdue_review_detected():
    sched = [{"type":"security","next_review_epoch": 0}]
    assert g.overdue_reviews(sched, time.time()) == ["security"]
def test_missing_fields_flagged():
    assert any("missing" in x for x in g.validate_waivers([{"id":"WV-2"}], time.time()))
