from inv38_kernel_bypass_transport import negotiation as n
def test_common_version_chosen():
    assert n.negotiate({1,2}, {1,2}) == 2
def test_n_minus_one():
    assert n.negotiate({1,2}, {1}) == 1
def test_no_common_rejected():
    try: n.negotiate({2}, {3}); assert False
    except n.NegotiationError: pass
def test_mandatory_feature_missing():
    try: n.negotiate_features({"a"}, {"b"}, mandatory={"a"}); assert False
    except n.NegotiationError: pass
def test_feature_intersection():
    assert n.negotiate_features({"a","b"}, {"b","c"}) == {"b"}
