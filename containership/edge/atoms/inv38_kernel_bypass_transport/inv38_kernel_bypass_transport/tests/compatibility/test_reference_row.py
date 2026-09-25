"""INV-38-C084 reference row: core contract/safety on the reference model."""
from inv38_kernel_bypass_transport.transport import BypassQueue, OutOfBounds
def test_reference_row_bounds_and_fallback():
    q = BypassQueue(ring_size=2)
    k = q.register(0x1000, 0x1000)
    assert q.post(k, 0x1000, 16, b"hi") == "bypass"
    try: q.post(k, 0x5000, 16, b"x"); assert False
    except OutOfBounds: pass
    q.set_available(False)
    assert q.post(0, 0, 16, b"kern") == "kernel"
