"""INV-38-C089 model faults: crash/stale-key/fencing/partition semantics."""
from inv38_kernel_bypass_transport import recovery as r, fencing as f
def test_stale_key_after_restart_rejected():
    inc = r.Incarnation(); inc.restart()
    try: inc.validate(0); assert False
    except r.StaleIncarnation: pass
def test_partition_does_not_dual_own():
    reg = f.OwnershipRegistry(); reg.acquire("A", now=0, ttl=100)
    try: reg.acquire("B", now=1, ttl=100); assert False
    except f.FencedOut: pass
def test_inflight_after_crash_classified():
    assert r.classify_inflight("completed") == "COMPLETED"
