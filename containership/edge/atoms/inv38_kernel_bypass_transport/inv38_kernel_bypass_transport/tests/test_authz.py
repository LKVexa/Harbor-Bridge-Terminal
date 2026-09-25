from inv38_kernel_bypass_transport import authz as a
def _p(**kw):
    base = dict(identity="w1", tenant="t1", workload="wl1", caps=frozenset({"register","post"}))
    base.update(kw); return a.Principal(**base)
def test_authorize_ok():
    a.authorize(_p(), "register", tenant="t1", workload="wl1")
def test_unauthenticated_rejected():
    try: a.authorize(_p(authenticated=False), "register", tenant="t1", workload="wl1"); assert False
    except a.AuthnError: pass
def test_missing_capability_rejected():
    try: a.authorize(_p(), "administer", tenant="t1", workload="wl1"); assert False
    except a.AuthzError: pass
def test_context_mismatch_rejected():
    try: a.authorize(_p(), "register", tenant="OTHER", workload="wl1"); assert False
    except a.AuthzError: pass
def test_cross_tenant_key_reuse_rejected():
    b = a.MRKeyBinding(key=1, tenant="t1", workload="wl1", generation=3)
    try: a.check_key(b, tenant="t2", workload="wl1", generation=3); assert False
    except a.AuthzError: pass
def test_stale_generation_rejected():
    b = a.MRKeyBinding(key=1, tenant="t1", workload="wl1", generation=3)
    try: a.check_key(b, tenant="t1", workload="wl1", generation=4); assert False
    except a.AuthzError: pass
