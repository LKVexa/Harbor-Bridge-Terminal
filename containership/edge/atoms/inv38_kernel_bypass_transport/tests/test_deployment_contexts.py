import os, yaml
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _load(): return yaml.safe_load(open(os.path.join(ROOT, "specs", "deployment-contexts.yaml")))
def test_four_profiles_present():
    p = _load()["profiles"]
    for name in ("datacenter","cloud_vm","near_edge","far_edge"):
        assert name in p
def test_far_edge_rdma_unsupported_falls_back():
    p = _load()["profiles"]["far_edge"]
    assert p["rdma"] == "unsupported" and p["fallback"] == "kernel_only"
def test_every_profile_defines_fallback():
    for prof in _load()["profiles"].values():
        assert "fallback" in prof
