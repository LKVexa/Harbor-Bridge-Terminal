"""INV-38-C095 reconstruction: empty node -> verified healthy; keys recreated."""
from inv38_kernel_bypass_transport.transport import BypassQueue
from inv38_kernel_bypass_transport import recovery as r
def test_reconstruct_from_empty():
    q = BypassQueue()               # fresh (empty) node
    assert q.region_count == 0
    k = q.register(0, 4096)         # MR key recreated, not restored
    assert q.post(k, 0, 8, b"ok") == "bypass"
def test_keys_never_restored():
    assert not r.reconstructible("durable_key")
