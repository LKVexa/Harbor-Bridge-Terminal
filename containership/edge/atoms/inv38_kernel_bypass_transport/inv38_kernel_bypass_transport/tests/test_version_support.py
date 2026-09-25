from inv38_kernel_bypass_transport import version_support as v
def test_supported_ok():
    v.check("pk_core", "1.5.0")
def test_unsupported_major_rejected():
    try: v.check("pk_core", "3.0.0"); assert False
    except v.UnsupportedVersion: pass
def test_preflight_collects_problems():
    probs = v.preflight({"pk_core":"3.0.0","INV-35":"4.1.0"})
    assert len(probs) == 1
