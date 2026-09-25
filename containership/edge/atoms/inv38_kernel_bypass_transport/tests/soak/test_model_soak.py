"""INV-38-C088 model soak: no leak / counter drift / stale-key accumulation."""
from inv38_kernel_bypass_transport.transport import BypassQueue
def test_soak_no_region_leak():
    q = BypassQueue(ring_size=4, completion_limit=100000)
    for i in range(20000):
        k = q.register(0, 4096)
        q.post(k, 0, 16, b"x")
        q.poll()
        q.pop_completion()
        q.deregister(k)
    assert q.region_count == 0
    assert q.ring_depth == 0
