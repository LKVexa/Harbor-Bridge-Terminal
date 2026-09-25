from inv38_kernel_bypass_transport import supply_chain as sc
KEY = b"test-signing-key"
def _artifacts(): return {"pkg.whl": b"binary-contents"}
def _manifest(a): return {"digests": {n: sc.sha256_bytes(b) for n, b in a.items()}}
def test_valid_signature_and_digests_pass():
    a = _artifacts(); m = _manifest(a); sig = sc.sign(m, KEY)
    sc.verify_artifacts(m, a, sig, KEY)
def test_tampered_artifact_blocked():
    a = _artifacts(); m = _manifest(a); sig = sc.sign(m, KEY)
    a["pkg.whl"] = b"tampered"
    try: sc.verify_artifacts(m, a, sig, KEY); assert False
    except sc.VerificationError: pass
def test_tampered_manifest_signature_blocked():
    a = _artifacts(); m = _manifest(a); sig = sc.sign(m, KEY)
    m["digests"]["evil"] = "00"
    try: sc.verify_signature(m, sig, KEY); assert False
    except sc.VerificationError: pass
def test_vuln_policy_blocks_high():
    assert sc.VulnPolicy().blocks("HIGH")
    assert not sc.VulnPolicy().blocks("LOW")
