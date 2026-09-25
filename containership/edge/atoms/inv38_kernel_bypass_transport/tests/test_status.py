from inv38_kernel_bypass_transport.transport import BypassQueue
from inv38_kernel_bypass_transport import lifecycle as L, status as S
def _reporter():
    q = BypassQueue(ring_size=4)
    m = L.LifecycleMachine(); m.transition(L.CompState.BOOTSTRAPPING); m.transition(L.CompState.READY)
    return S.StatusReporter(q, m, version="4.2.0", build_digest="bd", config_digest="cd")
def test_ready_when_deps_fresh():
    r = _reporter(); snap = r.snapshot()
    assert snap["liveness"] and snap["readiness"] and snap["reason_code"] == "PK_BYPASS_READY"
def test_stale_dep_blocks_readiness():
    r = _reporter(); r.dependencies["key"].age_seconds = 999
    ready, reason = r.readiness(); assert not ready and reason.startswith("PK_BYPASS_DEP_UNHEALTHY")
def test_snapshot_has_no_secrets():
    snap = _reporter().snapshot()
    blob = str(snap).lower()
    assert "secret" not in blob and "payload" not in blob
def test_generation_consistent():
    r = _reporter(); snap = r.snapshot()
    assert snap["generation"] == r.lifecycle.generation
