from inv38_kernel_bypass_transport import lifecycle as L

def test_legal_bootstrap_to_ready():
    m = L.LifecycleMachine()
    m.transition(L.CompState.BOOTSTRAPPING)
    g = m.transition(L.CompState.READY)
    assert m.state is L.CompState.READY
    assert g >= 1

def test_illegal_transition_raises_without_mutation():
    m = L.LifecycleMachine()
    before = m.state
    try:
        m.transition(L.CompState.READY)  # UNINIT->READY illegal
        assert False, "expected IllegalTransition"
    except L.IllegalTransition:
        pass
    assert m.state is before

def test_generation_monotonic_on_restart():
    m = L.LifecycleMachine()
    m.transition(L.CompState.BOOTSTRAPPING); m.transition(L.CompState.READY)
    g1 = m.generation
    m.transition(L.CompState.DRAINING); m.transition(L.CompState.QUIESCED)
    m.transition(L.CompState.BOOTSTRAPPING)
    assert m.generation > g1

def test_region_active_to_deregistering_requires_draining():
    # ACTIVE cannot jump straight to DEREGISTERING (must DRAIN first) -> mirrors RegionBusy
    try:
        L.region_transition(L.RegionState.ACTIVE, L.RegionState.DEREGISTERING)
        assert False
    except L.IllegalTransition:
        pass
    assert L.region_transition(L.RegionState.ACTIVE, L.RegionState.DRAINING) is L.RegionState.DRAINING
