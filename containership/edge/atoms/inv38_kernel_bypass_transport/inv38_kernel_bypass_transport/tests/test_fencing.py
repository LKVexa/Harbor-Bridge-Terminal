from inv38_kernel_bypass_transport import fencing as f
def test_single_writer_and_fencing():
    reg = f.OwnershipRegistry()
    l1 = reg.acquire("nodeA", now=0, ttl=10)
    try: reg.acquire("nodeB", now=1, ttl=10); assert False
    except f.FencedOut: pass
    reg.guard(l1.epoch)
def test_stale_epoch_rejected_after_takeover():
    reg = f.OwnershipRegistry()
    old = reg.acquire("nodeA", now=0, ttl=1)
    reg.acquire("nodeB", now=5, ttl=10)  # A's lease expired
    try: reg.guard(old.epoch); assert False
    except f.FencedOut: pass
