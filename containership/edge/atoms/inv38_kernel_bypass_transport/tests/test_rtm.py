from inv38_kernel_bypass_transport import rtm_tools as rt
def test_hundred_unique_ids_valid():
    rtm = rt.build(); assert len(rtm["rows"]) == 100
    assert not rt.validate(rtm), rt.validate(rtm)
def test_done_requires_evidence():
    rtm = rt.build()
    for row in rtm["rows"]:
        if row["status"] == "DONE":
            assert row["evidence"] and row["tests"] and row["artifacts"], row["id"]
def test_digest_stable():
    assert rt.digest(rt.build()) == rt.digest(rt.build())
def test_rollup_counts_fifty():
    r = rt.rollup(rt.build()); assert r["in_scope_total"] == 50
