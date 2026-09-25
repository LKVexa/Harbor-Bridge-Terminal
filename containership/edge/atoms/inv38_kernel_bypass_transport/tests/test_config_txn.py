from inv38_kernel_bypass_transport import config_txn as c
def _ok(cfg):
    if cfg.get("ring_size", 1) < 1: raise ValueError("bad ring")
def test_commit_advances_generation():
    s = c.ConfigStore()
    g = s.apply({"ring_size": 8}, validate=_ok, expected_generation=0)
    assert g == 1 and s.active["ring_size"] == 8
def test_validation_failure_rolls_back():
    s = c.ConfigStore(); s.apply({"ring_size": 8}, validate=_ok, expected_generation=0)
    try: s.apply({"ring_size": 0}, validate=_ok, expected_generation=1); assert False
    except c.TxnError: pass
    assert s.active == {"ring_size": 8} and s.generation == 1
def test_optimistic_conflict():
    s = c.ConfigStore(); s.apply({"ring_size": 8}, validate=_ok, expected_generation=0)
    try: s.apply({"ring_size": 16}, validate=_ok, expected_generation=0); assert False
    except c.TxnConflict: pass
