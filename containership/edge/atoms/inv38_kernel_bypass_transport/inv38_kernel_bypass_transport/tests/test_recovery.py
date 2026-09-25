from inv38_kernel_bypass_transport import recovery as r
def test_restart_bumps_epoch_and_rejects_stale():
    inc = r.Incarnation()
    inc.validate(0)
    e = inc.restart()
    try: inc.validate(0); assert False
    except r.StaleIncarnation: pass
    inc.validate(e)
def test_inflight_classification():
    assert r.classify_inflight("posted_no_completion") == "UNKNOWN_REPLAYABLE"
    assert r.classify_inflight("validated_not_posted") == "REJECTED"
def test_keys_not_reconstructible():
    assert not r.reconstructible("durable_key")
    assert r.reconstructible("ephemeral")
